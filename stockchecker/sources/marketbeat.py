"""MarketBeat consensus rating (https://www.marketbeat.com).

We request the NASDAQ path for every ticker; MarketBeat redirects to the right exchange
(NYSE, OTCMKTS, ...) when we guess wrong, and to the bare exchange index when the ticker
does not exist. The forecast page exposes:

- the consensus label ("Moderate Buy", "Reduce", ...) and analyst count in the
  "Consensus Rating" panel,
- a numeric "Consensus Rating Score" on MarketBeat's 1-4 scale,
- the "Consensus Price Target" panel.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from stockchecker.models import Rating
from stockchecker.normalize import (
    label_from_text,
    marketbeat_score_to_canonical,
    score_from_label,
)
from stockchecker.sources.base import ParseError, Source, TickerNotFound
from stockchecker.sources.http import PoliteSession, get_session

log = logging.getLogger(__name__)

URL_TEMPLATE = "https://www.marketbeat.com/stocks/NASDAQ/{ticker}/forecast/"

# MarketBeat's own weighting: Sell=1, Hold=2, Buy=3, Strong Buy=4. Used when the numeric
# score row is missing and we have to rebuild it from the headcount.
_MB_BUCKET_WEIGHTS = {"Sell": 1.0, "Hold": 2.0, "Buy": 3.0, "Strong Buy": 4.0}

_RE_ANALYSTS = re.compile(r"Based on\s+(\d+)\s+Analyst", re.I)
_RE_SCORE_ROW = re.compile(r"Consensus Rating Score\D{0,40}?(\d\.\d{1,2})", re.I)
_RE_MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")
_RE_BUCKET = re.compile(r"\b(Strong Buy|Buy|Hold|Sell)\b\s*(?:\|\s*)+(\d+)\b")


@dataclass(frozen=True, slots=True)
class MarketBeatConsensus:
    label_text: str
    score_1_to_4: float | None
    analysts: int | None
    price_target: float | None


def parse_forecast_page(html: str) -> MarketBeatConsensus | None:
    """Extract the consensus block. Returns ``None`` when the page has no analyst coverage."""
    soup = BeautifulSoup(html, "lxml")
    heading = soup.find("h3", string=re.compile(r"^\s*Consensus Rating\s*$"))
    if heading is None:
        return None
    panel = heading.find_next_sibling("div")
    if panel is None:
        raise ParseError("Consensus Rating heading found but panel is missing")

    panel_text = panel.get_text(" | ", strip=True)
    label_text = panel_text.split("|", 1)[0].strip()
    if not label_text:
        raise ParseError("empty consensus label")

    analysts_match = _RE_ANALYSTS.search(panel_text)
    analysts = int(analysts_match.group(1)) if analysts_match else None

    page_text = soup.get_text(" ", strip=True)
    score_match = _RE_SCORE_ROW.search(page_text)
    score = float(score_match.group(1)) if score_match else _score_from_buckets(panel_text)

    price_target = None
    target_heading = soup.find("h3", string=re.compile(r"^\s*Consensus Price Target\s*$"))
    if target_heading is not None:
        target_panel = target_heading.find_next_sibling()
        if target_panel is not None:
            money = _RE_MONEY.search(target_panel.get_text(" ", strip=True))
            if money:
                price_target = float(money.group(1).replace(",", ""))

    return MarketBeatConsensus(label_text, score, analysts, price_target)


def _score_from_buckets(panel_text: str) -> float | None:
    counts = {bucket: int(n) for bucket, n in _RE_BUCKET.findall(panel_text)}
    total = sum(counts.values())
    if total == 0:
        return None
    return sum(_MB_BUCKET_WEIGHTS[b] * n for b, n in counts.items()) / total


def to_rating(consensus: MarketBeatConsensus, source_name: str) -> Rating:
    try:
        label = label_from_text(consensus.label_text)
    except ValueError as exc:
        raise ParseError(str(exc)) from exc
    if consensus.score_1_to_4 is not None:
        score = marketbeat_score_to_canonical(consensus.score_1_to_4)
        raw = f"{consensus.label_text} ({consensus.score_1_to_4:.2f}/4)"
    else:
        score = score_from_label(label)
        raw = consensus.label_text
    return Rating(
        source=source_name,
        label=label,
        score=round(score, 3),
        analysts=consensus.analysts,
        price_target=consensus.price_target,
        raw=raw,
    )


class MarketBeatSource(Source):
    name = "MarketBeat"
    weight = 1.0

    def __init__(self, session: PoliteSession | None = None) -> None:
        self._session = session

    @property
    def session(self) -> PoliteSession:
        if self._session is None:
            self._session = get_session()
        return self._session

    def fetch(self, ticker: str) -> Rating | None:
        ticker = ticker.upper()
        response = self.session.get(URL_TEMPLATE.format(ticker=ticker))
        if not _url_mentions_ticker(response.url, ticker):
            raise TickerNotFound(f"MarketBeat redirected {ticker} to {response.url}")
        consensus = parse_forecast_page(response.text)
        if consensus is None:
            log.debug("MarketBeat has no analyst coverage for %s", ticker)
            return None
        return to_rating(consensus, self.name)


def _url_mentions_ticker(url: str, ticker: str) -> bool:
    parts = [p.upper() for p in urlsplit(url).path.split("/") if p]
    return ticker in parts
