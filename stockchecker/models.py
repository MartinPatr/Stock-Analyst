"""Core data types shared by sources, scoring, storage, CLI and bot.

Everything here is a plain dataclass with JSON round-tripping so snapshots can be
stored as-is and reconstructed later without a schema migration story.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RatingLabel(StrEnum):
    STRONG_SELL = "Strong Sell"
    SELL = "Sell"
    HOLD = "Hold"
    BUY = "Buy"
    STRONG_BUY = "Strong Buy"

    @classmethod
    def from_score(cls, score: float) -> RatingLabel:
        """Bucket a canonical 0-5 score into a label. Boundaries sit halfway between buckets."""
        if score < 1.5:
            return cls.STRONG_SELL
        if score < 2.5:
            return cls.SELL
        if score < 3.5:
            return cls.HOLD
        if score < 4.5:
            return cls.BUY
        return cls.STRONG_BUY


def utcnow() -> datetime:
    return datetime.now(UTC)


def _dt_to_str(value: datetime) -> str:
    return value.isoformat()


def _dt_from_str(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Rating:
    """One source's opinion about one ticker, already normalized to the 0-5 canonical scale."""

    source: str
    label: RatingLabel
    score: float
    analysts: int | None = None
    price_target: float | None = None
    raw: str = ""
    fetched_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "label": self.label.value,
            "score": self.score,
            "analysts": self.analysts,
            "price_target": self.price_target,
            "raw": self.raw,
            "fetched_at": _dt_to_str(self.fetched_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rating:
        return cls(
            source=data["source"],
            label=RatingLabel(data["label"]),
            score=float(data["score"]),
            analysts=data.get("analysts"),
            price_target=data.get("price_target"),
            raw=data.get("raw", ""),
            fetched_at=_dt_from_str(data["fetched_at"]),
        )


@dataclass(frozen=True, slots=True)
class Fundamentals:
    pe: float | None = None
    ps: float | None = None
    pb: float | None = None
    ev_to_sales: float | None = None
    current_ratio: float | None = None
    debt_to_equity: float | None = None

    FIELDS = ("pe", "ps", "pb", "ev_to_sales", "current_ratio", "debt_to_equity")

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.FIELDS}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fundamentals:
        return cls(**{name: data.get(name) for name in cls.FIELDS})

    def available(self) -> int:
        return sum(getattr(self, name) is not None for name in self.FIELDS)


@dataclass(frozen=True, slots=True)
class FundamentalsScore:
    """0-5 valuation/health score with the per-metric contributions that produced it."""

    score: float
    breakdown: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "breakdown": dict(self.breakdown)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FundamentalsScore:
        return cls(score=float(data["score"]), breakdown=dict(data.get("breakdown", {})))


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Descriptive and fundamental data for a company, independent of analyst opinions."""

    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    price: float | None = None
    market_cap: float | None = None
    fundamentals: Fundamentals = field(default_factory=Fundamentals)


@dataclass(slots=True)
class StockSnapshot:
    """Everything we know about a ticker at one point in time."""

    ticker: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    price: float | None = None
    market_cap: float | None = None
    ratings: list[Rating] = field(default_factory=list)
    fundamentals: Fundamentals | None = None
    fundamentals_score: FundamentalsScore | None = None
    composite: float | None = None
    coverage: int = 0
    as_of: datetime = field(default_factory=utcnow)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def label(self) -> RatingLabel | None:
        return RatingLabel.from_score(self.composite) if self.composite is not None else None

    def rating_for(self, source: str) -> Rating | None:
        return next((r for r in self.ratings if r.source == source), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "industry": self.industry,
            "price": self.price,
            "market_cap": self.market_cap,
            "ratings": [r.to_dict() for r in self.ratings],
            "fundamentals": self.fundamentals.to_dict() if self.fundamentals else None,
            "fundamentals_score": (
                self.fundamentals_score.to_dict() if self.fundamentals_score else None
            ),
            "composite": self.composite,
            "coverage": self.coverage,
            "as_of": _dt_to_str(self.as_of),
            "errors": dict(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StockSnapshot:
        return cls(
            ticker=data["ticker"],
            name=data.get("name"),
            sector=data.get("sector"),
            industry=data.get("industry"),
            price=data.get("price"),
            market_cap=data.get("market_cap"),
            ratings=[Rating.from_dict(r) for r in data.get("ratings", [])],
            fundamentals=(
                Fundamentals.from_dict(data["fundamentals"]) if data.get("fundamentals") else None
            ),
            fundamentals_score=(
                FundamentalsScore.from_dict(data["fundamentals_score"])
                if data.get("fundamentals_score")
                else None
            ),
            composite=data.get("composite"),
            coverage=int(data.get("coverage", 0)),
            as_of=_dt_from_str(data["as_of"]),
            errors=dict(data.get("errors", {})),
        )
