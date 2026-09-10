"""Read-side questions the CLI and the Discord bot both ask of the store."""

from __future__ import annotations

import re
from dataclasses import dataclass

from stockchecker.models import StockSnapshot
from stockchecker.storage import Store

_SUFFIXES = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}
_RE_MARKET_CAP = re.compile(r"^\s*\$?\s*([\d,]*\.?\d+)\s*([kmbt])?\s*$", re.I)


def parse_market_cap(text: str | float | int) -> float:
    """Turn '500M', '$1.2b', '2T' or a bare number into dollars. Raises ValueError otherwise."""
    if isinstance(text, int | float):
        return float(text)
    match = _RE_MARKET_CAP.match(text)
    if not match:
        raise ValueError(f"cannot parse market cap: {text!r}")
    number = float(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").lower()
    return number * _SUFFIXES.get(suffix, 1.0)


def _filter(
    snapshots: list[StockSnapshot], sector: str | None, min_market_cap: float | None
) -> list[StockSnapshot]:
    result = snapshots
    if sector and sector.lower() != "all":
        wanted = sector.strip().lower()
        result = [s for s in result if (s.sector or "").lower() == wanted]
    if min_market_cap:
        result = [s for s in result if s.market_cap is not None and s.market_cap >= min_market_cap]
    return result


def lookup(store: Store, query: str) -> StockSnapshot | None:
    """Exact ticker match first, then case-insensitive company-name substring."""
    query = query.strip()
    if not query:
        return None
    exact = store.latest_for(query.upper())
    if exact is not None:
        return exact
    needle = query.lower()
    candidates = [s for s in store.latest() if s.name and needle in s.name.lower()]
    if not candidates:
        return None
    # Prefer the shortest name: "Apple Inc." over "Apple Hospitality REIT" for "apple".
    return min(candidates, key=lambda s: len(s.name or ""))


def top(
    store: Store,
    n: int = 10,
    sector: str | None = None,
    min_market_cap: float | None = None,
    min_coverage: int = 1,
) -> list[StockSnapshot]:
    """Highest composite scores. Ties broken by analyst coverage, then market cap."""
    rows = _filter(store.latest(), sector, min_market_cap)
    rows = [s for s in rows if s.composite is not None and s.coverage >= min_coverage]
    rows.sort(key=lambda s: (s.composite or 0, s.coverage, s.market_cap or 0), reverse=True)
    return rows[:n]


@dataclass(frozen=True, slots=True)
class Mover:
    snapshot: StockSnapshot
    previous: float
    delta: float

    @property
    def pct_change(self) -> float:
        return (self.delta / self.previous * 100.0) if self.previous else 0.0


def movers(
    store: Store,
    n: int = 10,
    sector: str | None = None,
    min_market_cap: float | None = None,
    direction: str = "up",
) -> list[Mover]:
    """Tickers whose composite changed most since their previous snapshot."""
    previous = store.previous_composites()
    rows = _filter(store.latest(), sector, min_market_cap)
    result = [
        Mover(s, previous[s.ticker], round(s.composite - previous[s.ticker], 2))
        for s in rows
        if s.composite is not None and s.ticker in previous
    ]
    result = [m for m in result if m.delta != 0]
    result.sort(key=lambda m: m.delta, reverse=(direction != "down"))
    return result[:n]


def sectors(store: Store) -> list[str]:
    return store.sectors()
