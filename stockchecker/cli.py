"""``stockchecker`` command line interface."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from stockchecker import __version__, queries
from stockchecker.config import configure_logging, get_settings
from stockchecker.formatting import (
    NA,
    format_datetime,
    format_delta,
    format_market_cap,
    format_pct,
    format_price,
    format_ratio,
    format_score,
    upside,
)
from stockchecker.models import StockSnapshot
from stockchecker.storage import Store

app = typer.Typer(
    help="Aggregate analyst consensus from several sources into one 0-5 rating.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
log = logging.getLogger(__name__)

SCORE_STYLES = (
    (4.5, "bold green"),
    (3.5, "green"),
    (2.5, "yellow"),
    (1.5, "red"),
    (0.0, "bold red"),
)


METRIC_LABELS = {
    "pe": "P/E",
    "ps": "P/S",
    "pb": "P/B",
    "ev_to_sales": "EV/S",
    "current_ratio": "CR",
    "debt_to_equity": "D/E",
}


def _style(score: float | None) -> str:
    if score is None:
        return "dim"
    return next(style for threshold, style in SCORE_STYLES if score >= threshold)


def _scored(score: float | None) -> str:
    return f"[{_style(score)}]{format_score(score)}[/]"


def _store(db: Path | None) -> Store:
    return Store(db or get_settings().db_path)


def _parse_cap(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return queries.parse_market_cap(text)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.callback()
def _main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Debug logging.")] = False,
) -> None:
    configure_logging("DEBUG" if verbose else None)


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"stockchecker {__version__}")


# --------------------------------------------------------------------------------------
# Live analysis
# --------------------------------------------------------------------------------------


def render_snapshot(snapshot: StockSnapshot) -> None:
    title = f"[bold]{snapshot.ticker}[/]"
    if snapshot.name:
        title += f"  {snapshot.name}"
    meta = " | ".join(
        part
        for part in (
            snapshot.sector,
            snapshot.industry,
            format_price(snapshot.price) if snapshot.price else None,
            format_market_cap(snapshot.market_cap) if snapshot.market_cap else None,
        )
        if part
    )
    console.print(title)
    if meta:
        console.print(f"[dim]{meta}[/]")

    table = Table(box=None, pad_edge=False, show_edge=False, header_style="bold dim")
    table.add_column("Source")
    table.add_column("Rating")
    table.add_column("Score", justify="right")
    table.add_column("Analysts", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Upside", justify="right")
    table.add_column("Detail", style="dim")
    for rating in snapshot.ratings:
        table.add_row(
            rating.source,
            rating.label.value,
            _scored(rating.score),
            str(rating.analysts) if rating.analysts is not None else NA,
            format_price(rating.price_target),
            format_pct(upside(snapshot.price, rating.price_target)),
            rating.raw,
        )
    if snapshot.fundamentals_score is not None:
        parts = "  ".join(
            f"{METRIC_LABELS.get(k, k)} {v:.1f}"
            for k, v in snapshot.fundamentals_score.breakdown.items()
        )
        table.add_row(
            "StockChecker fundamentals",
            "",
            _scored(snapshot.fundamentals_score.score),
            "",
            "",
            "",
            parts,
        )
    for source, message in snapshot.errors.items():
        table.add_row(source, "[dim]—[/]", "", "", "", "", f"[red]{message}[/]")
    console.print(table)

    if snapshot.composite is None:
        console.print("[yellow]No rating: not enough data from any source.[/]")
    else:
        label = snapshot.label.value if snapshot.label else NA
        console.print(
            f"[bold]Composite:[/] {_scored(snapshot.composite)} [bold]{label}[/]"
            f"  [dim](from {snapshot.coverage} analyst source"
            f"{'s' if snapshot.coverage != 1 else ''}"
            f"{' + fundamentals' if snapshot.fundamentals_score else ''})[/]"
        )
    console.print()


@app.command()
def analyze(
    tickers: Annotated[list[str], typer.Argument(help="One or more tickers, e.g. AAPL MSFT.")],
    save: Annotated[bool, typer.Option(help="Persist the result to the database.")] = True,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")] = False,
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """Fetch live ratings for tickers and print the scored breakdown."""
    from stockchecker.pipeline import analyze as run_analyze

    store = _store(db) if save else None
    results = []
    for ticker in tickers:
        with console.status(f"Fetching {ticker.upper()}...", spinner="dots"):
            snapshot = run_analyze(ticker)
        if store is not None:
            store.save(snapshot, run_id="analyze")
        results.append(snapshot)
        if not as_json:
            render_snapshot(snapshot)
    if as_json:
        console.print_json(json.dumps([s.to_dict() for s in results]))


@app.command()
def scan(
    tickers: Annotated[
        list[str] | None, typer.Argument(help="Tickers to scan; default: the universe file.")
    ] = None,
    limit: Annotated[int | None, typer.Option(help="Only scan the first N tickers.")] = None,
    offset: Annotated[int, typer.Option(help="Skip the first N tickers.")] = 0,
    universe: Annotated[Path | None, typer.Option(help="Universe file (default .env).")] = None,
    workers: Annotated[int | None, typer.Option(help="Parallel tickers (default .env).")] = None,
    resume: Annotated[bool, typer.Option(help="Skip tickers finished in an interrupted run.")] = (
        False
    ),
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """Analyze many tickers and store a snapshot of each. Safe to interrupt and --resume."""
    from stockchecker.pipeline import scan as run_scan
    from stockchecker.universe import Checkpoint, load_universe

    settings = get_settings()
    if tickers:
        universe_tickers = [t.upper() for t in tickers]
    else:
        path = universe or settings.universe_file
        if not path.exists():
            console.print(f"[red]Universe file not found: {path}[/]")
            raise typer.Exit(code=1)
        universe_tickers = [e.ticker for e in load_universe(path)]
    selected = universe_tickers[offset : offset + limit if limit else None]
    if not selected:
        console.print("[yellow]Nothing to scan.[/]")
        raise typer.Exit(code=1)

    store = _store(db)
    checkpoint = Checkpoint(store.path.parent / ".scan_checkpoint.json")
    n_workers = workers or settings.max_workers
    console.print(
        f"Scanning [bold]{len(selected)}[/] tickers with {n_workers} workers"
        f" into [dim]{store.path}[/]"
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("scan", total=len(selected))

        def on_result(snapshot: StockSnapshot) -> None:
            progress.advance(task)
            progress.update(
                task, description=f"{snapshot.ticker:<6} {format_score(snapshot.composite)}"
            )

        summary = run_scan(
            selected,
            store,
            workers=n_workers,
            resume=resume,
            checkpoint=checkpoint,
            on_result=on_result,
        )

    console.print(
        f"Run [bold]{summary.run_id}[/]: {summary.completed} scanned,"
        f" [green]{summary.rated} rated[/],"
        f" [yellow]{len(summary.unrated_tickers)} without data[/]"
        + (f", {summary.skipped_resume} skipped (resume)" if summary.skipped_resume else "")
    )
    failures = summary.failures_by_source()
    if failures:
        table = Table(title="Source failures", box=None, header_style="bold dim")
        table.add_column("Source")
        table.add_column("Kind")
        table.add_column("Count", justify="right")
        for source, kinds in failures.items():
            for kind, n in kinds.items():
                table.add_row(source, kind, str(n))
        console.print(table)


# --------------------------------------------------------------------------------------
# Querying stored results
# --------------------------------------------------------------------------------------


def _ranking_table(title: str) -> Table:
    table = Table(title=title, header_style="bold", title_justify="left")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Ticker", style="bold")
    table.add_column("Company")
    table.add_column("Sector")
    table.add_column("Price", justify="right")
    table.add_column("Mkt cap", justify="right")
    table.add_column("Rating")
    table.add_column("Score", justify="right")
    table.add_column("Src", justify="right")
    return table


def _base_row(rank: int, s: StockSnapshot) -> list[str]:
    return [
        str(rank),
        s.ticker,
        (s.name or NA)[:40],
        s.sector or NA,
        format_price(s.price),
        format_market_cap(s.market_cap),
        s.label.value if s.label else NA,
        _scored(s.composite),
        str(s.coverage),
    ]


@app.command()
def top(
    n: Annotated[int, typer.Option("--n", "-n", help="How many rows.")] = 10,
    sector: Annotated[str | None, typer.Option(help="Filter by sector, e.g. Technology.")] = None,
    min_cap: Annotated[str | None, typer.Option(help="Minimum market cap, e.g. 500M, 2B.")] = None,
    min_coverage: Annotated[int, typer.Option(help="Minimum analyst sources.")] = 1,
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """Highest-rated stocks from the most recent snapshots."""
    store = _store(db)
    rows = queries.top(
        store, n=n, sector=sector, min_market_cap=_parse_cap(min_cap), min_coverage=min_coverage
    )
    if not rows:
        console.print("[yellow]No stored results match. Run `stockchecker scan` first.[/]")
        raise typer.Exit(code=1)
    table = _ranking_table(f"Top {len(rows)} by composite score")
    for i, s in enumerate(rows, 1):
        table.add_row(*_base_row(i, s))
    console.print(table)


@app.command()
def movers(
    n: Annotated[int, typer.Option("--n", "-n", help="How many rows.")] = 10,
    sector: Annotated[str | None, typer.Option(help="Filter by sector.")] = None,
    min_cap: Annotated[str | None, typer.Option(help="Minimum market cap, e.g. 500M.")] = None,
    down: Annotated[bool, typer.Option("--down", help="Largest drops instead of gains.")] = False,
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """Biggest composite-score changes since each ticker's previous snapshot."""
    store = _store(db)
    rows = queries.movers(
        store,
        n=n,
        sector=sector,
        min_market_cap=_parse_cap(min_cap),
        direction="down" if down else "up",
    )
    if not rows:
        console.print("[yellow]No movers yet: a ticker needs at least two snapshots.[/]")
        raise typer.Exit(code=1)
    table = _ranking_table(f"Top {len(rows)} {'drops' if down else 'gains'} in composite score")
    table.add_column("Prev", justify="right")
    table.add_column("Change", justify="right")
    for i, m in enumerate(rows, 1):
        style = "green" if m.delta > 0 else "red"
        table.add_row(
            *_base_row(i, m.snapshot),
            format_score(m.previous),
            f"[{style}]{format_delta(m.delta)} ({format_pct(m.pct_change)})[/]",
        )
    console.print(table)


@app.command()
def sectors(
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """List sectors present in the stored results."""
    store = _store(db)
    found = queries.sectors(store)
    if not found:
        console.print("[yellow]No stored results. Run `stockchecker scan` first.[/]")
        raise typer.Exit(code=1)
    counts = {s: 0 for s in found}
    for snap in store.latest():
        if snap.sector in counts:
            counts[snap.sector] += 1
    table = Table(header_style="bold")
    table.add_column("Sector")
    table.add_column("Tickers", justify="right")
    for name in found:
        table.add_row(name, str(counts[name]))
    console.print(table)


@app.command()
def show(
    query: Annotated[str, typer.Argument(help="Ticker or part of a company name.")],
    history: Annotated[int, typer.Option(help="How many past snapshots to list.")] = 10,
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """Show the stored snapshot for one stock, plus its score history."""
    store = _store(db)
    snapshot = queries.lookup(store, query)
    if snapshot is None:
        console.print(
            f"[yellow]No stored data for {query!r}. Try `stockchecker analyze {query}`.[/]"
        )
        raise typer.Exit(code=1)
    render_snapshot(snapshot)
    if snapshot.fundamentals is not None:
        ratios = "  ".join(
            f"{METRIC_LABELS[name]} {format_ratio(value)}"
            for name, value in snapshot.fundamentals.to_dict().items()
        )
        console.print(f"[dim]Ratios: {ratios}[/]")
    past = store.history(snapshot.ticker, limit=history)
    if len(past) > 1:
        table = Table(title="History", box=None, header_style="bold dim", title_justify="left")
        table.add_column("As of")
        table.add_column("Composite", justify="right")
        table.add_column("Sources", justify="right")
        table.add_column("Price", justify="right")
        for item in past:
            table.add_row(
                format_datetime(item.as_of),
                _scored(item.composite),
                str(item.coverage),
                format_price(item.price),
            )
        console.print(table)


@app.command()
def export(
    path: Annotated[Path, typer.Argument(help="Destination .csv or .json file.")],
    sector: Annotated[str | None, typer.Option(help="Filter by sector.")] = None,
    db: Annotated[Path | None, typer.Option(help="SQLite path (default from .env).")] = None,
) -> None:
    """Export the latest snapshot of every ticker to CSV or JSON."""
    store = _store(db)
    rows = store.latest(sector=sector)
    if not rows:
        console.print("[yellow]Nothing to export.[/]")
        raise typer.Exit(code=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps([s.to_dict() for s in rows], indent=2))
    else:
        source_names = sorted({r.source for s in rows for r in s.ratings})
        with path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "ticker",
                    "name",
                    "sector",
                    "industry",
                    "price",
                    "market_cap",
                    "composite",
                    "label",
                    "coverage",
                    "fundamentals_score",
                    "as_of",
                ]
                + [f"{n} score" for n in source_names]
                + [f"{n} target" for n in source_names]
            )
            for s in rows:
                by_source = {r.source: r for r in s.ratings}
                writer.writerow(
                    [
                        s.ticker,
                        s.name,
                        s.sector,
                        s.industry,
                        s.price,
                        s.market_cap,
                        s.composite,
                        s.label.value if s.label else None,
                        s.coverage,
                        s.fundamentals_score.score if s.fundamentals_score else None,
                        s.as_of.isoformat(),
                    ]
                    + [by_source[n].score if n in by_source else None for n in source_names]
                    + [by_source[n].price_target if n in by_source else None for n in source_names]
                )
    console.print(f"Wrote {len(rows)} rows to [bold]{path}[/]")


@app.command()
def sources() -> None:
    """List the registered rating sources and their composite weights."""
    from stockchecker.sources import get_sources

    table = Table(header_style="bold")
    table.add_column("Source")
    table.add_column("Weight", justify="right")
    table.add_column("Also provides fundamentals")
    from stockchecker.sources.base import FundamentalsProvider

    for source in get_sources():
        table.add_row(
            source.name,
            f"{source.weight:.1f}",
            "yes" if isinstance(source, FundamentalsProvider) else "",
        )
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
