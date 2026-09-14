from pathlib import Path

from typer.testing import CliRunner

from stockchecker import cli, pipeline
from stockchecker.storage import Store
from tests.conftest import make_snapshot
from tests.test_pipeline import FixedSource, ProfileSource

runner = CliRunner()


def _seed(db: Path) -> None:
    store = Store(db)
    store.save_many(
        [
            make_snapshot("AAPL", 3.2, "Technology", 3e12, "Apple Inc."),
            make_snapshot("XOM", 2.9, "Energy", 5e11, "Exxon Mobil Corporation"),
        ],
        run_id="seed",
    )
    store.close()


def test_help_lists_commands() -> None:
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    for command in ("analyze", "scan", "top", "movers", "sectors", "show", "export"):
        assert command in result.output


def test_top_and_sectors_and_show(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    _seed(db)

    result = runner.invoke(cli.app, ["top", "--db", str(db), "-n", "1"])
    assert result.exit_code == 0 and "AAPL" in result.output and "XOM" not in result.output

    result = runner.invoke(cli.app, ["top", "--db", str(db), "--sector", "energy"])
    assert result.exit_code == 0 and "XOM" in result.output

    result = runner.invoke(cli.app, ["top", "--db", str(db), "--min-cap", "1T"])
    assert result.exit_code == 0 and "XOM" not in result.output

    result = runner.invoke(cli.app, ["top", "--db", str(db), "--min-cap", "lots"])
    assert result.exit_code != 0

    result = runner.invoke(cli.app, ["sectors", "--db", str(db)])
    assert result.exit_code == 0 and "Energy" in result.output and "Technology" in result.output

    result = runner.invoke(cli.app, ["show", "exxon", "--db", str(db)])
    assert result.exit_code == 0 and "XOM" in result.output and "Ratios:" in result.output

    result = runner.invoke(cli.app, ["show", "NOPE", "--db", str(db)])
    assert result.exit_code == 1


def test_empty_database_messages(tmp_path: Path) -> None:
    db = str(tmp_path / "empty.db")
    for args in (["top"], ["movers"], ["sectors"], ["export", str(tmp_path / "o.csv")]):
        result = runner.invoke(cli.app, [*args, "--db", db])
        assert result.exit_code == 1, args


def test_export_csv_and_json(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    _seed(db)
    csv_path = tmp_path / "out" / "results.csv"
    result = runner.invoke(cli.app, ["export", str(csv_path), "--db", str(db)])
    assert result.exit_code == 0
    lines = csv_path.read_text().splitlines()
    assert lines[0].startswith("ticker,name,sector")
    assert "MarketBeat score" in lines[0] and len(lines) == 3

    json_path = tmp_path / "results.json"
    result = runner.invoke(
        cli.app, ["export", str(json_path), "--db", str(db), "--sector", "Energy"]
    )
    assert result.exit_code == 0 and '"ticker": "XOM"' in json_path.read_text()
    assert '"AAPL"' not in json_path.read_text()


def test_analyze_and_scan_with_fake_sources(tmp_path: Path, monkeypatch) -> None:
    fake = lambda: [FixedSource(4.2), ProfileSource()]  # noqa: E731
    monkeypatch.setattr(pipeline, "get_sources", fake)
    db = tmp_path / "t.db"

    result = runner.invoke(cli.app, ["analyze", "aapl", "--db", str(db)])
    assert result.exit_code == 0
    assert "AAPL Corp" in result.output and "Composite:" in result.output

    result = runner.invoke(cli.app, ["analyze", "msft", "--json", "--no-save", "--db", str(db)])
    assert result.exit_code == 0 and '"ticker": "MSFT"' in result.output

    result = runner.invoke(cli.app, ["scan", "AAA", "BBB", "--db", str(db), "--workers", "2"])
    assert result.exit_code == 0 and "2 scanned" in result.output

    store = Store(db)
    assert store.count() == 3  # AAPL from analyze + AAA + BBB
    assert store.latest_for("MSFT") is None  # --no-save honoured

    result = runner.invoke(cli.app, ["movers", "--db", str(db)])
    assert result.exit_code == 1  # only one snapshot per ticker so far

    result = runner.invoke(cli.app, ["scan", "AAA", "--db", str(db)])
    assert result.exit_code == 0
    result = runner.invoke(cli.app, ["movers", "--db", str(db)])
    assert result.exit_code == 1  # identical score -> not a mover


def test_scan_with_universe_file_and_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "get_sources", lambda: [FixedSource()])
    universe = tmp_path / "u.txt"
    universe.write_text("A,Agilent,NYSE\nB,Barnes,NYSE\nC,Citi,NYSE\n")
    db = tmp_path / "t.db"
    result = runner.invoke(
        cli.app,
        ["scan", "--universe", str(universe), "--limit", "2", "--offset", "1", "--db", str(db)],
    )
    assert result.exit_code == 0
    assert sorted(s.ticker for s in Store(db).latest()) == ["B", "C"]

    result = runner.invoke(
        cli.app, ["scan", "--universe", str(tmp_path / "missing.txt"), "--db", str(db)]
    )
    assert result.exit_code == 1
