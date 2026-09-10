"""Yahoo Finance via ``yfinance``: analyst consensus plus the company profile/fundamentals.

Yahoo is the one source that also gives us sector, price, market cap and valuation ratios,
so it doubles as the :class:`~stockchecker.sources.base.FundamentalsProvider`.
"""

from __future__ import annotations

import logging
from typing import Any

from stockchecker.models import CompanyProfile, Fundamentals, Rating, RatingLabel
from stockchecker.normalize import label_from_text, score_from_label, yahoo_mean_to_canonical
from stockchecker.sources.base import Source, SourceError, TickerNotFound

log = logging.getLogger(__name__)


def _load_info(ticker: str) -> dict[str, Any]:
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # yfinance raises a grab-bag of exception types
        raise SourceError(f"yfinance failed for {ticker}: {exc}") from exc
    # Unknown tickers come back as a near-empty dict rather than an error.
    if not info or ("regularMarketPrice" not in info and "currentPrice" not in info):
        if not info.get("longName") and not info.get("shortName"):
            raise TickerNotFound(f"Yahoo has no data for {ticker}")
    return info


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None  # drop NaN


def rating_from_info(info: dict[str, Any], source_name: str) -> Rating | None:
    mean = _num(info.get("recommendationMean"))
    key = info.get("recommendationKey")
    if mean is None and not key:
        return None
    if mean is not None:
        score = yahoo_mean_to_canonical(mean)
        label = RatingLabel.from_score(score)
        if key and key.lower() not in ("none", ""):
            try:
                label = label_from_text(str(key))
            except ValueError:
                pass
        raw = f"{key or label.value} ({mean:.2f}/5, 1=Strong Buy)"
    else:
        try:
            label = label_from_text(str(key))
        except ValueError:
            return None
        score = score_from_label(label)
        raw = str(key)
    return Rating(
        source=source_name,
        label=label,
        score=round(score, 3),
        analysts=int(info["numberOfAnalystOpinions"])
        if _num(info.get("numberOfAnalystOpinions")) is not None
        else None,
        price_target=_num(info.get("targetMeanPrice")),
        raw=raw,
    )


def profile_from_info(info: dict[str, Any]) -> CompanyProfile:
    debt_to_equity = _num(info.get("debtToEquity"))
    if debt_to_equity is not None:
        debt_to_equity /= 100.0  # Yahoo reports this as a percentage
    fundamentals = Fundamentals(
        pe=_num(info.get("trailingPE")) or _num(info.get("forwardPE")),
        ps=_num(info.get("priceToSalesTrailing12Months")),
        pb=_num(info.get("priceToBook")),
        ev_to_sales=_num(info.get("enterpriseToRevenue")),
        current_ratio=_num(info.get("currentRatio")),
        debt_to_equity=debt_to_equity,
    )
    return CompanyProfile(
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        price=_num(info.get("currentPrice")) or _num(info.get("regularMarketPrice")),
        market_cap=_num(info.get("marketCap")),
        fundamentals=fundamentals,
    )


class YahooSource(Source):
    name = "Yahoo Finance"
    weight = 1.0

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def _info(self, ticker: str) -> dict[str, Any]:
        ticker = ticker.upper()
        if ticker not in self._cache:
            self._cache[ticker] = _load_info(ticker)
        return self._cache[ticker]

    def fetch(self, ticker: str) -> Rating | None:
        return rating_from_info(self._info(ticker), self.name)

    def fetch_profile(self, ticker: str) -> CompanyProfile:
        return profile_from_info(self._info(ticker))
