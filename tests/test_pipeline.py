from pathlib import Path

from stockchecker.models import CompanyProfile, Fundamentals, Rating, RatingLabel
from stockchecker.pipeline import analyze, scan
from stockchecker.sources.base import ParseError, Source, SourceBlocked, TickerNotFound
from stockchecker.storage import Store
from stockchecker.universe import Checkpoint, load_universe


class FixedSource(Source):
    name = "Fixed"

    def __init__(self, score: float = 4.0) -> None:
        self.score = score

    def fetch(self, ticker: str) -> Rating | None:
        return Rating(self.name, RatingLabel.from_score(self.score), self.score, 5, 10.0, "x")


class ProfileSource(Source):
    """Rates *and* provides fundamentals, like the Yahoo source."""

    name = "Profile"

    def fetch(self, ticker: str) -> Rating | None:
        return None  # covers the ticker, no analyst opinion

    def fetch_profile(self, ticker: str) -> CompanyProfile:
        return CompanyProfile(
            name=f"{ticker} Corp",
            sector="Technology",
            industry="Software",
            price=50.0,
            market_cap=1e9,
            fundamentals=Fundamentals(
                pe=30, ps=6, pb=6, ev_to_sales=6, current_ratio=1.8, debt_to_equity=0.6
            ),
        )


class FailingSource(Source):
    name = "Failing"

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def fetch(self, ticker: str) -> Rating | None:
        raise self.exc


def test_analyze_combines_sources_and_profile() -> None:
    snap = analyze(" aapl ", [FixedSource(4.0), ProfileSource()])
    assert snap.ticker == "AAPL"
    assert snap.name == "AAPL Corp" and snap.sector == "Technology"
    assert [r.source for r in snap.ratings] == ["Fixed"]
    assert snap.coverage == 1
    # every ratio sits exactly on the Technology benchmark -> fundamentals ~2.5
    assert snap.fundamentals_score is not None
    assert 2.3 < snap.fundamentals_score.score < 2.7
    assert snap.composite == round((4.0 + snap.fundamentals_score.score) / 2, 2)
    assert snap.errors == {}


def test_analyze_records_failures_without_aborting() -> None:
    sources = [
        FailingSource(TickerNotFound("nope")),
        FailingSource(SourceBlocked("403")),
        FailingSource(ParseError("layout changed")),
        FailingSource(RuntimeError("boom")),
        FixedSource(3.0),
    ]
    snap = analyze("X", sources)
    assert snap.composite == 3.0 and snap.coverage == 1
    assert snap.errors["Failing"].startswith(("not found", "blocked", "parse error", "unexpected"))


def test_analyze_with_nothing_has_no_score() -> None:
    snap = analyze("X", [FailingSource(TickerNotFound("nope"))])
    assert snap.composite is None and snap.coverage == 0


def test_scan_persists_and_summarises(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    seen = []
    summary = scan(
        ["AAA", "BBB", "ccc"],
        store,
        workers=2,
        sources_factory=lambda: [FixedSource(), FailingSource(SourceBlocked("403"))],
        on_result=lambda s: seen.append(s.ticker),
    )
    assert summary.completed == 3 and summary.rated == 3 and summary.requested == 3
    assert sorted(seen) == ["AAA", "BBB", "CCC"]
    assert summary.failures_by_source() == {"Failing": {"blocked": 3}}
    assert store.count() == 3
    assert store.run_ids() == [summary.run_id]


def test_scan_resume_skips_finished_tickers(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    checkpoint = Checkpoint(tmp_path / "ckpt.json")
    checkpoint.save({"AAA"})
    summary = scan(
        ["AAA", "BBB"],
        store,
        resume=True,
        checkpoint=checkpoint,
        sources_factory=lambda: [FixedSource()],
    )
    assert summary.skipped_resume == 1 and summary.completed == 1
    assert store.latest_for("AAA") is None
    assert not checkpoint.path.exists()  # finished -> cleared


def test_scan_without_resume_clears_stale_checkpoint(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    checkpoint = Checkpoint(tmp_path / "ckpt.json")
    checkpoint.save({"AAA"})
    summary = scan(["AAA"], store, checkpoint=checkpoint, sources_factory=lambda: [FixedSource()])
    assert summary.skipped_resume == 0 and summary.completed == 1


def test_load_universe_parses_and_dedupes(tmp_path: Path) -> None:
    path = tmp_path / "u.txt"
    path.write_text(
        "A,Agilent Technologies,NYSE\n"
        "# comment\n"
        "\n"
        "brk.b,Berkshire Hathaway,NYSE\n"
        "A,Duplicate,NYSE\n"
        "not a ticker!,x,y\n"
        "MSFT\n"
    )
    entries = load_universe(path)
    assert [e.ticker for e in entries] == ["A", "BRK.B", "MSFT"]
    assert entries[0].name == "Agilent Technologies" and entries[0].exchange == "NYSE"
    assert entries[2].name is None


def test_repo_universe_file_loads() -> None:
    entries = load_universe(Path(__file__).parent.parent / "data" / "tickers.txt")
    assert len(entries) > 5000
    assert entries[0].ticker == "A"
