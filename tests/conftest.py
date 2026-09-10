from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from stockchecker.models import (
    Fundamentals,
    FundamentalsScore,
    Rating,
    RatingLabel,
    StockSnapshot,
)
from stockchecker.storage import Store

FIXTURES = Path(__file__).parent / "fixtures"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--live", action="store_true", default=False, help="run network tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="needs --live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="ignore")


def make_rating(
    source: str = "MarketBeat",
    score: float = 4.0,
    analysts: int | None = 10,
    price_target: float | None = 120.0,
) -> Rating:
    return Rating(
        source=source,
        label=RatingLabel.from_score(score),
        score=score,
        analysts=analysts,
        price_target=price_target,
        raw=f"{source} raw",
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def make_snapshot(
    ticker: str = "AAPL",
    composite: float | None = 4.0,
    sector: str | None = "Technology",
    market_cap: float | None = 3e12,
    name: str | None = "Apple Inc.",
    as_of: datetime | None = None,
    coverage: int = 2,
) -> StockSnapshot:
    return StockSnapshot(
        ticker=ticker,
        name=name,
        sector=sector,
        industry="Consumer Electronics",
        price=100.0,
        market_cap=market_cap,
        ratings=[make_rating("MarketBeat", 4.0), make_rating("StockAnalysis", 3.8, 20, 110.0)],
        fundamentals=Fundamentals(
            pe=30, ps=7, pb=40, ev_to_sales=7, current_ratio=1.0, debt_to_equity=1.5
        ),
        fundamentals_score=FundamentalsScore(score=2.0, breakdown={"pe": 2.5, "pb": 0.1}),
        composite=composite,
        coverage=coverage,
        as_of=as_of or datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture
def populated_store(store: Store) -> Store:
    """Two runs: run1 for four tickers, run2 re-scores two of them."""
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    t1 = t0 + timedelta(days=1)
    run1 = [
        make_snapshot("AAPL", 3.2, "Technology", 3e12, "Apple Inc.", t0),
        make_snapshot("MSFT", 4.1, "Technology", 3e12, "Microsoft Corporation", t0),
        make_snapshot("XOM", 2.9, "Energy", 5e11, "Exxon Mobil Corporation", t0),
        make_snapshot("TINY", 4.8, "Technology", 5e7, "Tiny Apple Software", t0, coverage=1),
        make_snapshot("NODATA", None, None, None, None, t0, coverage=0),
    ]
    store.save_many(run1, run_id="run1")
    run2 = [
        make_snapshot("AAPL", 3.6, "Technology", 3e12, "Apple Inc.", t1),
        make_snapshot("XOM", 2.4, "Energy", 5e11, "Exxon Mobil Corporation", t1),
    ]
    store.save_many(run2, run_id="run2")
    return store
