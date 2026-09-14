"""Map every source's rating vocabulary and numeric scale onto one canonical 0-5 scale.

Canonical scale (higher is more bullish):

    1 = Strong Sell, 2 = Sell, 3 = Hold, 4 = Buy, 5 = Strong Buy

Sources report on wildly different scales (MarketBeat 1-4, Yahoo 1-5 inverted, count
breakdowns, free-text labels). Everything funnels through these pure functions so the
composite score in :mod:`stockchecker.scoring` compares like with like.
"""

from __future__ import annotations

import re

from stockchecker.models import RatingLabel

SCALE_MIN = 0.0
SCALE_MAX = 5.0

LABEL_SCORES: dict[RatingLabel, float] = {
    RatingLabel.STRONG_SELL: 1.0,
    RatingLabel.SELL: 2.0,
    RatingLabel.HOLD: 3.0,
    RatingLabel.BUY: 4.0,
    RatingLabel.STRONG_BUY: 5.0,
}

# Ordered so specific phrases match before their substrings ("strong buy" before "buy").
_LABEL_SYNONYMS: tuple[tuple[str, RatingLabel], ...] = (
    ("strong buy", RatingLabel.STRONG_BUY),
    ("strong sell", RatingLabel.STRONG_SELL),
    ("moderate buy", RatingLabel.BUY),
    ("moderate sell", RatingLabel.SELL),
    ("outperform", RatingLabel.BUY),
    ("underperform", RatingLabel.SELL),
    ("overweight", RatingLabel.BUY),
    ("underweight", RatingLabel.SELL),
    ("accumulate", RatingLabel.BUY),
    ("reduce", RatingLabel.SELL),
    ("market perform", RatingLabel.HOLD),
    ("sector perform", RatingLabel.HOLD),
    ("equal weight", RatingLabel.HOLD),
    ("equal-weight", RatingLabel.HOLD),
    ("neutral", RatingLabel.HOLD),
    ("hold", RatingLabel.HOLD),
    ("buy", RatingLabel.BUY),
    ("sell", RatingLabel.SELL),
)


def clamp(score: float) -> float:
    return max(SCALE_MIN, min(SCALE_MAX, float(score)))


def label_from_text(text: str) -> RatingLabel:
    """Interpret a free-text analyst label ("Moderate Buy", "underperform", "strong_buy")."""
    cleaned = re.sub(r"[_\-]+", " ", text.strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    for phrase, label in _LABEL_SYNONYMS:
        if phrase in cleaned:
            return label
    raise ValueError(f"unrecognised rating label: {text!r}")


def score_from_label(label: RatingLabel) -> float:
    return LABEL_SCORES[label]


def marketbeat_score_to_canonical(score: float) -> float:
    """MarketBeat scores 1 (Sell) .. 4 (Strong Buy); shift so 2 (Hold) lands on canonical 3."""
    return clamp(score + 1.0)


def yahoo_mean_to_canonical(mean: float) -> float:
    """Yahoo's ``recommendationMean`` is 1 (Strong Buy) .. 5 (Strong Sell); invert it."""
    return clamp(6.0 - mean)


def counts_to_canonical(
    strong_buy: int, buy: int, hold: int, sell: int, strong_sell: int
) -> float | None:
    """Weighted mean of a Strong Buy/Buy/Hold/Sell/Strong Sell headcount. ``None`` if empty."""
    total = strong_buy + buy + hold + sell + strong_sell
    if total <= 0:
        return None
    weighted = (
        strong_buy * LABEL_SCORES[RatingLabel.STRONG_BUY]
        + buy * LABEL_SCORES[RatingLabel.BUY]
        + hold * LABEL_SCORES[RatingLabel.HOLD]
        + sell * LABEL_SCORES[RatingLabel.SELL]
        + strong_sell * LABEL_SCORES[RatingLabel.STRONG_SELL]
    )
    return clamp(weighted / total)
