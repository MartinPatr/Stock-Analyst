"""Source registry. Adding a source means writing one ``Source`` subclass and listing it here."""

from __future__ import annotations

from stockchecker.sources.base import (
    FundamentalsProvider,
    ParseError,
    Source,
    SourceBlocked,
    SourceError,
    TickerNotFound,
)
from stockchecker.sources.marketbeat import MarketBeatSource
from stockchecker.sources.stockanalysis import StockAnalysisSource
from stockchecker.sources.yahoo import YahooSource

SOURCES: tuple[type[Source], ...] = (MarketBeatSource, StockAnalysisSource, YahooSource)


def get_sources() -> list[Source]:
    return [cls() for cls in SOURCES]


__all__ = [
    "SOURCES",
    "FundamentalsProvider",
    "MarketBeatSource",
    "ParseError",
    "Source",
    "SourceBlocked",
    "SourceError",
    "StockAnalysisSource",
    "TickerNotFound",
    "YahooSource",
    "get_sources",
]
