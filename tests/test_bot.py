from stockchecker import queries
from stockchecker.bot.formatting import movers_embed, sectors_embed, stock_embed, top_embed
from stockchecker.bot.main import StockCheckerBot, _looks_like_ticker
from stockchecker.storage import Store
from tests.conftest import make_snapshot


def test_stock_embed_lists_every_source() -> None:
    snap = make_snapshot()
    snap.errors["Yahoo Finance"] = "blocked: 403"
    embed = stock_embed(snap)
    names = [f.name for f in embed.fields]
    assert embed.title == "Apple Inc. (AAPL)"
    assert "MarketBeat" in names and "StockAnalysis" in names
    assert "StockChecker fundamentals" in names
    assert names[-1] == "No data from"
    assert "Yahoo Finance" in embed.fields[-1].value
    assert "4.00/5 Buy" in embed.fields[2].value
    assert "target $120.00 (+20.0%)" in embed.fields[3].value
    assert "Sources: 2" in embed.footer.text


def test_stock_embed_without_score() -> None:
    embed = stock_embed(make_snapshot(composite=None, name=None))
    assert embed.title == "AAPL (AAPL)"
    assert embed.fields[2].value == "no data"


def test_top_and_movers_embeds(populated_store: Store) -> None:
    rows = queries.top(populated_store, n=3, sector="Technology")
    embed = top_embed(rows, "Technology", "1B")
    assert embed.title == "Top 3 by composite score (Technology, cap ≥ 1B)"
    assert embed.description.startswith("**1. TINY**")

    movers = queries.movers(populated_store)
    embed = movers_embed(movers, down=False)
    assert "**1. AAPL**" in embed.description
    assert "3.20/5 → 3.60/5 (**+0.40**, +12.5%)" in embed.description

    assert "No movers yet" in movers_embed([], down=True).description
    assert "No stored results" in top_embed([], None, None).description


def test_sectors_embed() -> None:
    assert sectors_embed({"Energy": 1, "Technology": 3}).description == (
        "**Energy** · 1\n**Technology** · 3"
    )
    assert "No stored results" in sectors_embed({}).description


def test_bot_registers_slash_commands(store: Store) -> None:
    bot = StockCheckerBot(store)
    assert sorted(c.name for c in bot.tree.get_commands()) == ["movers", "sectors", "stock", "top"]


def test_looks_like_ticker() -> None:
    assert _looks_like_ticker("AAPL") and _looks_like_ticker("brk.b") and _looks_like_ticker("BF-B")
    assert not _looks_like_ticker("Apple Inc") and not _looks_like_ticker("")
