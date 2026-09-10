from datetime import UTC, datetime

import pytest

from stockchecker import queries
from stockchecker.storage import Store
from tests.conftest import make_snapshot


def test_save_and_reload_round_trip(store: Store) -> None:
    snap = make_snapshot("AAPL")
    store.save(snap, run_id="r1")
    assert store.latest_for("aapl") == snap
    assert store.count() == 1
    assert store.run_ids() == ["r1"]


def test_latest_returns_one_row_per_ticker(populated_store: Store) -> None:
    latest = {s.ticker: s for s in populated_store.latest()}
    assert set(latest) == {"AAPL", "MSFT", "XOM", "TINY", "NODATA"}
    assert latest["AAPL"].composite == 3.6  # run2 wins over run1
    assert latest["MSFT"].composite == 4.1


def test_previous_and_history(populated_store: Store) -> None:
    assert populated_store.previous_for("AAPL").composite == 3.2
    assert populated_store.previous_for("MSFT") is None
    history = populated_store.history("AAPL")
    assert [h.composite for h in history] == [3.6, 3.2]
    assert populated_store.previous_composites() == {"AAPL": 3.2, "XOM": 2.9}


def test_sectors_and_sector_filter(populated_store: Store) -> None:
    assert populated_store.sectors() == ["Energy", "Technology"]
    assert [s.ticker for s in populated_store.latest(sector="energy")] == ["XOM"]


def test_store_creates_parent_directories(tmp_path) -> None:
    Store(tmp_path / "nested" / "dir" / "x.db").close()
    assert (tmp_path / "nested" / "dir" / "x.db").exists()


# --- queries --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [("500M", 5e8), ("$1.2b", 1.2e9), ("2T", 2e12), ("750k", 7.5e5), ("1,000", 1000.0), (5, 5.0)],
)
def test_parse_market_cap(text, value) -> None:
    assert queries.parse_market_cap(text) == value


def test_parse_market_cap_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        queries.parse_market_cap("lots")


def test_lookup_by_ticker_then_by_name(populated_store: Store) -> None:
    assert queries.lookup(populated_store, "msft").ticker == "MSFT"
    assert queries.lookup(populated_store, "exxon").ticker == "XOM"
    # Shortest matching name wins: "Apple Inc." over "Tiny Apple Software".
    assert queries.lookup(populated_store, "apple").ticker == "AAPL"
    assert queries.lookup(populated_store, "nothing here") is None
    assert queries.lookup(populated_store, "   ") is None


def test_top_orders_and_filters(populated_store: Store) -> None:
    assert [s.ticker for s in queries.top(populated_store)] == ["TINY", "MSFT", "AAPL", "XOM"]
    assert [s.ticker for s in queries.top(populated_store, n=2)] == ["TINY", "MSFT"]
    assert [s.ticker for s in queries.top(populated_store, sector="energy")] == ["XOM"]
    assert [s.ticker for s in queries.top(populated_store, min_market_cap=1e9)] == [
        "MSFT",
        "AAPL",
        "XOM",
    ]
    assert [s.ticker for s in queries.top(populated_store, min_coverage=2)] == [
        "MSFT",
        "AAPL",
        "XOM",
    ]


def test_movers_use_previous_snapshot(populated_store: Store) -> None:
    up = queries.movers(populated_store)
    assert [(m.snapshot.ticker, m.delta) for m in up] == [("AAPL", 0.4), ("XOM", -0.5)]
    assert up[0].pct_change == pytest.approx(12.5)
    down = queries.movers(populated_store, direction="down")
    assert down[0].snapshot.ticker == "XOM"
    assert queries.movers(populated_store, sector="Technology")[0].snapshot.ticker == "AAPL"


def test_movers_empty_without_history(store: Store) -> None:
    store.save(make_snapshot("AAPL", as_of=datetime(2026, 1, 1, tzinfo=UTC)), "r1")
    assert queries.movers(store) == []
