import pytest

from stockchecker.models import Fundamentals, FundamentalsScore
from stockchecker.scoring import (
    DEFAULT_BENCHMARKS,
    SECTOR_BENCHMARKS,
    benchmarks_for,
    composite_score,
    score_fundamentals,
    score_higher_is_better,
    score_lower_is_better,
)
from tests.conftest import make_rating


def test_lower_is_better_curve() -> None:
    assert score_lower_is_better(20, 20) == pytest.approx(0.5)
    assert score_lower_is_better(0, 20) == 1.0
    assert score_lower_is_better(40, 20) == pytest.approx(0.2)
    assert score_lower_is_better(60, 20) == pytest.approx(0.1)
    assert score_lower_is_better(-5, 20) == 0.0  # losses are not "cheap"


def test_higher_is_better_curve() -> None:
    assert score_higher_is_better(0, 1.5) == 0.0
    assert score_higher_is_better(1.5, 1.5) == pytest.approx(0.5)
    assert score_higher_is_better(3.0, 1.5) == pytest.approx(0.8)
    assert score_higher_is_better(10, 1.5) > 0.95
    assert score_higher_is_better(-1, 1.5) == 0.0


def test_benchmarks_are_sector_specific_and_case_insensitive() -> None:
    assert benchmarks_for("technology") is SECTOR_BENCHMARKS["technology"]
    assert benchmarks_for("  Technology ") is SECTOR_BENCHMARKS["technology"]
    assert benchmarks_for(None) is DEFAULT_BENCHMARKS
    assert benchmarks_for("Space Mining") is DEFAULT_BENCHMARKS


def test_same_ratios_score_higher_in_a_pricier_sector() -> None:
    ratios = Fundamentals(pe=28, ps=5, pb=5, ev_to_sales=5, current_ratio=1.5, debt_to_equity=0.8)
    tech = score_fundamentals(ratios, "Technology")
    utility = score_fundamentals(ratios, "Utilities")
    assert tech is not None and utility is not None
    assert tech.score > utility.score
    assert set(tech.breakdown) == set(Fundamentals.FIELDS)


def test_missing_metrics_are_dropped_and_weights_renormalised() -> None:
    partial = Fundamentals(pe=20, pb=3)  # both exactly at default benchmark -> 0.5 each
    result = score_fundamentals(partial, None)
    assert result is not None
    assert result.score == pytest.approx(2.5, abs=0.01)
    assert set(result.breakdown) == {"pe", "pb"}


def test_too_little_data_yields_none() -> None:
    assert score_fundamentals(Fundamentals(pe=15), None) is None
    assert score_fundamentals(Fundamentals(), "Technology") is None


def test_score_is_bounded() -> None:
    great = Fundamentals(pe=2, ps=0.1, pb=0.2, ev_to_sales=0.1, current_ratio=9, debt_to_equity=0)
    awful = Fundamentals(pe=-1, ps=90, pb=90, ev_to_sales=90, current_ratio=0, debt_to_equity=50)
    assert 4.5 < score_fundamentals(great, None).score <= 5.0
    assert 0.0 <= score_fundamentals(awful, None).score < 0.1


def test_composite_is_weighted_mean_with_coverage() -> None:
    ratings = [make_rating("A", 4.0), make_rating("B", 2.0)]
    composite, coverage = composite_score(ratings, None)
    assert (composite, coverage) == (3.0, 2)

    composite, coverage = composite_score(ratings, None, source_weights={"A": 3.0, "B": 1.0})
    assert (composite, coverage) == (3.5, 2)


def test_composite_includes_fundamentals_but_not_in_coverage() -> None:
    ratings = [make_rating("A", 4.0)]
    fundamentals = FundamentalsScore(score=2.0, breakdown={})
    assert composite_score(ratings, fundamentals) == (3.0, 1)
    assert composite_score(ratings, fundamentals, fundamentals_weight=0) == (4.0, 1)
    assert composite_score([], fundamentals) == (2.0, 0)


def test_composite_with_nothing_is_none() -> None:
    assert composite_score([], None) == (None, 0)
