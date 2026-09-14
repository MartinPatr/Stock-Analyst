"""Turn tickers into snapshots: fan out to every source, score, and (optionally) persist."""

from __future__ import annotations

import logging
import threading
import uuid
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from stockchecker.models import StockSnapshot, utcnow
from stockchecker.scoring import composite_score, score_fundamentals
from stockchecker.sources import get_sources
from stockchecker.sources.base import (
    FundamentalsProvider,
    ParseError,
    Source,
    SourceBlocked,
    SourceError,
    TickerNotFound,
)
from stockchecker.storage import Store
from stockchecker.universe import Checkpoint

log = logging.getLogger(__name__)

CHECKPOINT_EVERY = 10


def _error_kind(exc: Exception) -> str:
    if isinstance(exc, TickerNotFound):
        return "not found"
    if isinstance(exc, SourceBlocked):
        return "blocked"
    if isinstance(exc, ParseError):
        return "parse error"
    if isinstance(exc, SourceError):
        return "error"
    return "unexpected"


def analyze(
    ticker: str,
    sources: Sequence[Source] | None = None,
    fundamentals_weight: float = 1.0,
) -> StockSnapshot:
    """Query every source for ``ticker`` and assemble a scored snapshot.

    Individual source failures never abort the analysis; they are recorded in
    ``snapshot.errors`` keyed by source name.
    """
    ticker = ticker.strip().upper()
    sources = list(sources) if sources is not None else get_sources()
    snapshot = StockSnapshot(ticker=ticker, as_of=utcnow())

    for source in sources:
        try:
            rating = source.fetch(ticker)
        except Exception as exc:  # noqa: BLE001 - one bad source must not sink the ticker
            kind = _error_kind(exc)
            snapshot.errors[source.name] = f"{kind}: {exc}"
            level = logging.DEBUG if kind == "not found" else logging.WARNING
            log.log(level, "%s: %s failed (%s)", ticker, source.name, exc)
            continue
        if rating is not None:
            snapshot.ratings.append(rating)

    provider = next((s for s in sources if isinstance(s, FundamentalsProvider)), None)
    if provider is not None and provider.name not in snapshot.errors:
        try:
            profile = provider.fetch_profile(ticker)
        except Exception as exc:  # noqa: BLE001
            snapshot.errors[f"{provider.name} profile"] = f"{_error_kind(exc)}: {exc}"
        else:
            snapshot.name = profile.name
            snapshot.sector = profile.sector
            snapshot.industry = profile.industry
            snapshot.price = profile.price
            snapshot.market_cap = profile.market_cap
            snapshot.fundamentals = profile.fundamentals
            snapshot.fundamentals_score = score_fundamentals(profile.fundamentals, profile.sector)

    weights = {s.name: s.weight for s in sources}
    snapshot.composite, snapshot.coverage = composite_score(
        snapshot.ratings, snapshot.fundamentals_score, weights, fundamentals_weight
    )
    return snapshot


@dataclass
class ScanSummary:
    run_id: str
    requested: int = 0
    completed: int = 0
    rated: int = 0  # snapshots with a composite score
    skipped_resume: int = 0
    source_failures: Counter = field(default_factory=Counter)  # (source, kind) -> count
    unrated_tickers: list[str] = field(default_factory=list)

    def failures_by_source(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for (source, kind), n in sorted(self.source_failures.items()):
            out.setdefault(source, {})[kind] = n
        return out


ProgressCallback = Callable[[StockSnapshot], None]


def scan(
    tickers: Iterable[str],
    store: Store,
    workers: int = 4,
    resume: bool = False,
    checkpoint: Checkpoint | None = None,
    on_result: ProgressCallback | None = None,
    sources_factory: Callable[[], Sequence[Source]] = get_sources,
) -> ScanSummary:
    """Analyze many tickers concurrently and persist every snapshot under one ``run_id``.

    Each worker thread gets its own source instances (sources may cache per ticker), but
    they all share the process-wide polite HTTP session, so per-host rate limits hold.
    """
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    summary = ScanSummary(run_id=uuid.uuid4().hex[:12], requested=len(tickers))

    done: set[str] = set()
    if checkpoint is not None:
        if resume:
            done = checkpoint.load()
        else:
            checkpoint.clear()
    todo = [t for t in tickers if t not in done]
    summary.skipped_resume = len(tickers) - len(todo)

    local = threading.local()

    def worker(ticker: str) -> StockSnapshot:
        if not hasattr(local, "sources"):
            local.sources = sources_factory()
        return analyze(ticker, local.sources)

    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(worker, t): t for t in todo}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                snapshot = future.result()
            except Exception as exc:  # noqa: BLE001 - keep the scan alive
                log.error("%s: analysis crashed: %s", ticker, exc)
                snapshot = StockSnapshot(ticker=ticker, errors={"pipeline": str(exc)})
            store.save(snapshot, summary.run_id)
            with lock:
                summary.completed += 1
                if snapshot.composite is not None:
                    summary.rated += 1
                else:
                    summary.unrated_tickers.append(ticker)
                for source, message in snapshot.errors.items():
                    summary.source_failures[(source, message.split(":", 1)[0])] += 1
                done.add(ticker)
                if checkpoint is not None and summary.completed % CHECKPOINT_EVERY == 0:
                    checkpoint.save(done)
            if on_result is not None:
                on_result(snapshot)

    if checkpoint is not None:
        if len(done) >= len(tickers):
            checkpoint.clear()  # finished: the next scan starts over
        else:
            checkpoint.save(done)
    return summary
