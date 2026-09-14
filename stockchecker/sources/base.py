"""Contract every rating source implements, plus the errors they are allowed to raise.

A source turns a ticker into a :class:`~stockchecker.models.Rating` on the canonical 0-5
scale. It must never let a transport or parsing problem escape as a generic exception:
map it to one of the ``SourceError`` subclasses so the pipeline can count and report it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from stockchecker.models import CompanyProfile, Rating


class SourceError(Exception):
    """Base class for anything a source can fail with."""


class SourceBlocked(SourceError):
    """The site refused us (403, bot wall, WAF challenge). Retrying now will not help."""


class TickerNotFound(SourceError):
    """The source has no page/data for this ticker."""


class ParseError(SourceError):
    """We got a page but could not find the data in it; the site layout probably changed."""


class Source(ABC):
    """A provider of analyst consensus for a ticker.

    Subclasses set ``name`` (shown to users, used as the storage key) and optionally
    ``weight`` (relative influence in the composite score), then implement :meth:`fetch`.
    """

    name: str = "unnamed"
    weight: float = 1.0

    @abstractmethod
    def fetch(self, ticker: str) -> Rating | None:
        """Return the normalized rating, ``None`` if the source covers the ticker but has no
        analyst opinion, or raise a :class:`SourceError`."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r} weight={self.weight}>"


@runtime_checkable
class FundamentalsProvider(Protocol):
    """A source that can also describe the company (sector, price, valuation ratios)."""

    def fetch_profile(self, ticker: str) -> CompanyProfile: ...
