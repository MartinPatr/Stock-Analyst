"""Scores: the fundamentals-based "StockChecker" rating and the multi-source composite.

Both are pure functions of their inputs so they are trivial to test and to explain.

Fundamentals score
------------------
Each valuation/health ratio is compared to a benchmark for the company's sector (a P/E of
30 is ordinary for software and alarming for a utility). Each ratio goes through a
saturating curve that is exactly 0.5 at its benchmark: *lower is better* ratios (P/E,
P/S, P/B, EV/Sales, Debt/Equity) fall from 1 towards 0 as they grow, the *higher is
better* current ratio rises from 0 towards 1. Each component lands in ``[0, 1]``; a
weighted mean is scaled to the canonical ``0-5`` range. Metrics
that are missing are dropped and the remaining weights renormalised, so a partial
profile still scores, but at least :data:`MIN_METRICS` must be present.

Composite score
---------------
Weighted mean of every source's canonical score plus the fundamentals score. ``coverage``
counts analyst sources only, so a stock rated by fundamentals alone shows coverage 0.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from stockchecker.models import Fundamentals, FundamentalsScore, Rating
from stockchecker.normalize import SCALE_MAX, clamp

MIN_METRICS = 2

# Relative importance of each metric inside the fundamentals score.
DEFAULT_WEIGHTS: Mapping[str, float] = {
    "pe": 0.20,
    "ps": 0.15,
    "pb": 0.15,
    "ev_to_sales": 0.15,
    "current_ratio": 0.15,
    "debt_to_equity": 0.20,
}

LOWER_IS_BETTER = frozenset({"pe", "ps", "pb", "ev_to_sales", "debt_to_equity"})


@dataclass(frozen=True, slots=True)
class Benchmarks:
    """Typical ratio values for a sector; the point at which a metric scores 0.5."""

    pe: float
    ps: float
    pb: float
    ev_to_sales: float
    current_ratio: float
    debt_to_equity: float

    def for_metric(self, metric: str) -> float:
        return getattr(self, metric)


DEFAULT_BENCHMARKS = Benchmarks(
    pe=20, ps=2.5, pb=3.0, ev_to_sales=3.0, current_ratio=1.5, debt_to_equity=1.0
)

# Keyed by Yahoo Finance sector names. Rough long-run medians; the point is relative
# fairness between sectors, not precision.
SECTOR_BENCHMARKS: Mapping[str, Benchmarks] = {
    "technology": Benchmarks(30, 6.0, 6.0, 6.0, 1.8, 0.6),
    "healthcare": Benchmarks(25, 4.0, 4.0, 4.0, 1.8, 0.7),
    "financial services": Benchmarks(13, 3.0, 1.3, 3.0, 1.0, 2.0),
    "energy": Benchmarks(12, 1.2, 1.5, 1.5, 1.2, 0.6),
    "utilities": Benchmarks(18, 2.5, 1.8, 3.5, 0.9, 1.5),
    "consumer defensive": Benchmarks(20, 1.5, 4.0, 2.0, 1.2, 1.0),
    "consumer cyclical": Benchmarks(20, 1.5, 4.0, 2.0, 1.3, 1.2),
    "communication services": Benchmarks(20, 3.0, 3.0, 3.5, 1.3, 1.0),
    "industrials": Benchmarks(22, 2.0, 4.0, 2.5, 1.4, 1.0),
    "basic materials": Benchmarks(16, 1.5, 2.0, 2.0, 1.8, 0.6),
    "real estate": Benchmarks(35, 6.0, 2.0, 8.0, 1.0, 1.2),
}


def benchmarks_for(sector: str | None) -> Benchmarks:
    if not sector:
        return DEFAULT_BENCHMARKS
    return SECTOR_BENCHMARKS.get(sector.strip().lower(), DEFAULT_BENCHMARKS)


CURVE_STEEPNESS = 2.0


def score_lower_is_better(value: float, benchmark: float) -> float:
    """1 at zero, exactly 0.5 at the benchmark, 0.2 at 2x, tending to 0 as the value grows.

    A negative P/E or Debt/Equity means losses or negative equity, both red flags rather
    than "cheap", so they get the worst score instead of the best.
    """
    if value < 0:
        return 0.0
    return 1.0 / (1.0 + (value / benchmark) ** CURVE_STEEPNESS)


def score_higher_is_better(value: float, benchmark: float) -> float:
    """Mirror image: 0 at zero, 0.5 at the benchmark, 0.8 at 2x, saturating towards 1."""
    if value <= 0:
        return 0.0
    return 1.0 - score_lower_is_better(value, benchmark)


def score_fundamentals(
    fundamentals: Fundamentals,
    sector: str | None = None,
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
) -> FundamentalsScore | None:
    """Return the 0-5 score and per-metric breakdown, or ``None`` if too little data."""
    bench = benchmarks_for(sector)
    components: dict[str, float] = {}
    for metric, weight in weights.items():
        value = getattr(fundamentals, metric, None)
        if value is None or weight <= 0:
            continue
        if metric in LOWER_IS_BETTER:
            components[metric] = score_lower_is_better(float(value), bench.for_metric(metric))
        else:
            components[metric] = score_higher_is_better(float(value), bench.for_metric(metric))

    if len(components) < MIN_METRICS:
        return None

    total_weight = sum(weights[m] for m in components)
    blended = sum(weights[m] * s for m, s in components.items()) / total_weight
    breakdown = {m: round(s * SCALE_MAX, 2) for m, s in components.items()}
    return FundamentalsScore(score=round(clamp(blended * SCALE_MAX), 2), breakdown=breakdown)


def composite_score(
    ratings: list[Rating],
    fundamentals_score: FundamentalsScore | None,
    source_weights: Mapping[str, float] | None = None,
    fundamentals_weight: float = 1.0,
) -> tuple[float | None, int]:
    """Blend analyst ratings and the fundamentals score. Returns ``(composite, coverage)``."""
    weighted_sum = 0.0
    total_weight = 0.0
    for rating in ratings:
        weight = (source_weights or {}).get(rating.source, 1.0)
        if weight <= 0:
            continue
        weighted_sum += weight * rating.score
        total_weight += weight
    coverage = len(ratings)

    if fundamentals_score is not None and fundamentals_weight > 0:
        weighted_sum += fundamentals_weight * fundamentals_score.score
        total_weight += fundamentals_weight

    if total_weight == 0:
        return None, coverage
    return round(clamp(weighted_sum / total_weight), 2), coverage
