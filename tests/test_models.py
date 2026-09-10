import pytest

from stockchecker.models import RatingLabel, StockSnapshot
from tests.conftest import make_snapshot


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.0, RatingLabel.STRONG_SELL),
        (1.49, RatingLabel.STRONG_SELL),
        (1.5, RatingLabel.SELL),
        (2.49, RatingLabel.SELL),
        (2.5, RatingLabel.HOLD),
        (3.49, RatingLabel.HOLD),
        (3.5, RatingLabel.BUY),
        (4.49, RatingLabel.BUY),
        (4.5, RatingLabel.STRONG_BUY),
        (5.0, RatingLabel.STRONG_BUY),
    ],
)
def test_label_from_score_boundaries(score: float, label: RatingLabel) -> None:
    assert RatingLabel.from_score(score) is label


def test_snapshot_round_trips_through_dict() -> None:
    original = make_snapshot()
    original.errors["Yahoo Finance"] = "blocked: 403"
    restored = StockSnapshot.from_dict(original.to_dict())
    assert restored == original
    assert restored.as_of.tzinfo is not None
    assert restored.ratings[0].label is RatingLabel.BUY


def test_snapshot_helpers() -> None:
    snap = make_snapshot(composite=4.6)
    assert snap.label is RatingLabel.STRONG_BUY
    assert snap.rating_for("MarketBeat") is snap.ratings[0]
    assert snap.rating_for("Nope") is None
    assert make_snapshot(composite=None).label is None
