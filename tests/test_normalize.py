import pytest

from stockchecker.models import RatingLabel
from stockchecker.normalize import (
    counts_to_canonical,
    label_from_text,
    marketbeat_score_to_canonical,
    score_from_label,
    yahoo_mean_to_canonical,
)


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("Strong Buy", RatingLabel.STRONG_BUY),
        ("strong_buy", RatingLabel.STRONG_BUY),
        ("Moderate Buy", RatingLabel.BUY),
        ("buy", RatingLabel.BUY),
        ("Outperform", RatingLabel.BUY),
        ("Overweight", RatingLabel.BUY),
        ("Hold", RatingLabel.HOLD),
        ("Neutral", RatingLabel.HOLD),
        ("Market Perform", RatingLabel.HOLD),
        ("Equal-Weight", RatingLabel.HOLD),
        ("Reduce", RatingLabel.SELL),
        ("Underperform", RatingLabel.SELL),
        ("Moderate Sell", RatingLabel.SELL),
        ("Sell", RatingLabel.SELL),
        ("Strong Sell", RatingLabel.STRONG_SELL),
        ("  STRONG   SELL ", RatingLabel.STRONG_SELL),
    ],
)
def test_label_from_text(text: str, label: RatingLabel) -> None:
    assert label_from_text(text) is label


def test_label_from_text_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        label_from_text("banana")


def test_label_scores_are_monotonic() -> None:
    scores = [score_from_label(label) for label in RatingLabel]
    assert scores == sorted(scores)
    assert scores[0] == 1.0 and scores[-1] == 5.0


def test_marketbeat_mapping_keeps_hold_at_three() -> None:
    assert marketbeat_score_to_canonical(2.0) == 3.0
    assert marketbeat_score_to_canonical(4.0) == 5.0
    assert marketbeat_score_to_canonical(1.0) == 2.0
    assert marketbeat_score_to_canonical(9.0) == 5.0  # clamped


def test_yahoo_mean_is_inverted() -> None:
    assert yahoo_mean_to_canonical(1.0) == 5.0  # 1 = Strong Buy at Yahoo
    assert yahoo_mean_to_canonical(3.0) == 3.0
    assert yahoo_mean_to_canonical(5.0) == 1.0


def test_counts_to_canonical() -> None:
    assert counts_to_canonical(10, 0, 0, 0, 0) == 5.0
    assert counts_to_canonical(0, 0, 4, 0, 0) == 3.0
    assert counts_to_canonical(1, 1, 1, 1, 1) == 3.0
    assert counts_to_canonical(0, 0, 0, 0, 0) is None
    assert counts_to_canonical(19, 6, 13, 3, 3) == pytest.approx(3.795, abs=1e-3)
