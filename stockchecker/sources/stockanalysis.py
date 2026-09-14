"""StockAnalysis.com analyst forecast (https://stockanalysis.com), data from S&P Global.

The forecast page states the consensus in one sentence and publishes a monthly
Strong Buy / Buy / Hold / Sell / Strong Sell headcount table. We score from the latest
month's headcount, which is finer-grained than the label alone.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from stockchecker.models import Rating, RatingLabel
from stockchecker.normalize import counts_to_canonical, label_from_text, score_from_label
from stockchecker.sources.base import ParseError, Source, TickerNotFound
from stockchecker.sources.http import PoliteSession, get_session

log = logging.getLogger(__name__)

URL_TEMPLATE = "https://stockanalysis.com/stocks/{ticker}/forecast/"

_RE_SENTENCE = re.compile(
    r"According to (\d+) analysts?.*?consensus rating of\s*[\"“]([^\"”]+)[\"”]"
    r"(?:\s*and an average price target of \$([\d,]+(?:\.\d+)?))?",
    re.I | re.S,
)
_RE_CONSENSUS_LABEL = re.compile(r"Analyst Consensus:\s*([A-Za-z ]+?)(?:\s{2,}|$|\|)")

_BUCKETS = ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell")


@dataclass(frozen=True, slots=True)
class StockAnalysisConsensus:
    label_text: str
    analysts: int | None
    price_target: float | None
    counts: dict[str, int]  # latest month, keys from _BUCKETS (may be empty)


def parse_forecast_page(html: str) -> StockAnalysisConsensus | None:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    sentence = _RE_SENTENCE.search(text)
    label_text: str | None = None
    analysts: int | None = None
    price_target: float | None = None
    if sentence:
        analysts = int(sentence.group(1))
        label_text = sentence.group(2).strip()
        if sentence.group(3):
            price_target = float(sentence.group(3).replace(",", ""))
    else:
        alt = _RE_CONSENSUS_LABEL.search(text)
        if alt:
            label_text = alt.group(1).strip()

    counts = _parse_trend_table(soup)

    if label_text is None and not counts:
        if "analyst" not in text.lower():
            raise ParseError("page does not look like a StockAnalysis forecast page")
        return None
    if label_text is None:
        label_text = ""
    return StockAnalysisConsensus(label_text, analysts, price_target, counts)


def _parse_trend_table(soup: BeautifulSoup) -> dict[str, int]:
    """Latest-month headcount from the 'Recommendation Trends' table, or ``{}``."""
    for table in soup.find_all("table"):
        rows = {}
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) >= 2 and cells[0] in _BUCKETS:
                try:
                    rows[cells[0]] = int(cells[-1].replace(",", ""))
                except ValueError:
                    continue
        if len(rows) >= 3:
            return {bucket: rows.get(bucket, 0) for bucket in _BUCKETS}
    return {}


def to_rating(consensus: StockAnalysisConsensus, source_name: str) -> Rating:
    score = None
    if consensus.counts:
        score = counts_to_canonical(
            consensus.counts.get("Strong Buy", 0),
            consensus.counts.get("Buy", 0),
            consensus.counts.get("Hold", 0),
            consensus.counts.get("Sell", 0),
            consensus.counts.get("Strong Sell", 0),
        )
    label = None
    if consensus.label_text:
        try:
            label = label_from_text(consensus.label_text)
        except ValueError:
            label = None
    if score is None and label is None:
        raise ParseError("neither a consensus label nor a rating breakdown was found")
    if score is None:
        score = score_from_label(label)  # type: ignore[arg-type]
    if label is None:
        label = RatingLabel.from_score(score)

    analysts = consensus.analysts
    if analysts is None and consensus.counts:
        analysts = sum(consensus.counts.values())

    raw = consensus.label_text or label.value
    if consensus.counts:
        breakdown = "/".join(str(consensus.counts.get(b, 0)) for b in _BUCKETS)
        raw = f"{raw} (SB/B/H/S/SS {breakdown})"

    return Rating(
        source=source_name,
        label=label,
        score=round(score, 3),
        analysts=analysts,
        price_target=consensus.price_target,
        raw=raw,
    )


def _slug_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = [p for p in urlsplit(url).path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "stocks":
        return parts[1].lower()
    return None


class StockAnalysisSource(Source):
    name = "StockAnalysis"
    weight = 1.0

    def __init__(self, session: PoliteSession | None = None) -> None:
        self._session = session

    @property
    def session(self) -> PoliteSession:
        if self._session is None:
            self._session = get_session()
        return self._session

    def fetch(self, ticker: str) -> Rating | None:
        # StockAnalysis uses dashes where exchanges use dots (BRK.B -> brk-b).
        slug = ticker.lower().replace(".", "-")
        response = self.session.get(URL_TEMPLATE.format(ticker=slug))
        final_slug = _slug_from_url(response.url)
        if final_slug is not None and final_slug != slug:
            # Renamed/acquired tickers redirect to the successor (ABC -> AMT). That is a
            # different company, so do not attribute its rating to the old symbol.
            raise TickerNotFound(f"StockAnalysis redirected {ticker} to {final_slug.upper()}")
        consensus = parse_forecast_page(response.text)
        if consensus is None:
            log.debug("StockAnalysis has no analyst coverage for %s", ticker)
            return None
        return to_rating(consensus, self.name)
