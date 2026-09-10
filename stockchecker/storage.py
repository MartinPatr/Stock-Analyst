"""SQLite persistence for snapshots.

One row per ticker per run. Rows are never updated, so the table doubles as history:
"how did the composite move since last scan" is a query, not a spreadsheet formula.
The full snapshot is stored as JSON alongside the columns we filter and sort on.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from stockchecker.models import StockSnapshot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    as_of       TEXT NOT NULL,
    name        TEXT,
    sector      TEXT,
    industry    TEXT,
    price       REAL,
    market_cap  REAL,
    composite   REAL,
    coverage    INTEGER NOT NULL DEFAULT 0,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_asof ON snapshots (ticker, as_of DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_run ON snapshots (run_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_sector ON snapshots (sector);
"""

# The most recent row per ticker.
_LATEST_CTE = """
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY as_of DESC, id DESC) AS rn
    FROM snapshots
)
"""


class Store:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def close(self) -> None:
        self._conn.close()

    # -- writes ---------------------------------------------------------------------------

    def save(self, snapshot: StockSnapshot, run_id: str) -> None:
        self.save_many([snapshot], run_id)

    def save_many(self, snapshots: Iterable[StockSnapshot], run_id: str) -> None:
        rows = [
            (
                run_id,
                s.ticker.upper(),
                s.as_of.isoformat(),
                s.name,
                s.sector,
                s.industry,
                s.price,
                s.market_cap,
                s.composite,
                s.coverage,
                json.dumps(s.to_dict()),
            )
            for s in snapshots
        ]
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO snapshots (run_id, ticker, as_of, name, sector, industry, price,"
                " market_cap, composite, coverage, payload) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )

    # -- reads ----------------------------------------------------------------------------

    @staticmethod
    def _load(row: sqlite3.Row) -> StockSnapshot:
        return StockSnapshot.from_dict(json.loads(row["payload"]))

    def latest(self, sector: str | None = None) -> list[StockSnapshot]:
        """Most recent snapshot for every ticker we have ever scanned."""
        sql = _LATEST_CTE + "SELECT * FROM ranked WHERE rn = 1"
        params: list[object] = []
        if sector:
            sql += " AND LOWER(sector) = LOWER(?)"
            params.append(sector)
        sql += " ORDER BY ticker"
        with self._connect() as conn:
            return [self._load(r) for r in conn.execute(sql, params)]

    def latest_for(self, ticker: str) -> StockSnapshot | None:
        return self._nth_for(ticker, offset=0)

    def previous_for(self, ticker: str) -> StockSnapshot | None:
        """The snapshot before the latest one (from an earlier run), if any."""
        return self._nth_for(ticker, offset=1)

    def _nth_for(self, ticker: str, offset: int) -> StockSnapshot | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM snapshots WHERE ticker = ? ORDER BY as_of DESC, id DESC"
                " LIMIT 1 OFFSET ?",
                (ticker.upper(), offset),
            ).fetchone()
        return self._load(row) if row else None

    def history(self, ticker: str, limit: int = 20) -> list[StockSnapshot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM snapshots WHERE ticker = ? ORDER BY as_of DESC, id DESC"
                " LIMIT ?",
                (ticker.upper(), limit),
            ).fetchall()
        return [self._load(r) for r in rows]

    def previous_composites(self) -> dict[str, float]:
        """ticker -> composite from each ticker's second-most-recent snapshot."""
        sql = _LATEST_CTE + (
            "SELECT ticker, composite FROM ranked WHERE rn = 2 AND composite IS NOT NULL"
        )
        with self._connect() as conn:
            return {r["ticker"]: r["composite"] for r in conn.execute(sql)}

    def sectors(self) -> list[str]:
        sql = _LATEST_CTE + (
            "SELECT DISTINCT sector FROM ranked WHERE rn = 1 AND sector IS NOT NULL"
            " AND sector != '' ORDER BY sector"
        )
        with self._connect() as conn:
            return [r["sector"] for r in conn.execute(sql)]

    def run_ids(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id FROM snapshots GROUP BY run_id ORDER BY MIN(as_of)"
            ).fetchall()
        return [r["run_id"] for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(DISTINCT ticker) FROM snapshots").fetchone()[0])
