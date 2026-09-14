"""StockChecker Discord bot.

Slash commands are thin wrappers over :mod:`stockchecker.queries`; all the data comes
from the SQLite store populated by ``stockchecker scan``. ``/stock`` can optionally fetch
live data for a ticker that has not been scanned yet.

Run with ``python -m stockchecker.bot`` after setting ``DISCORD_TOKEN`` in ``.env``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord
from discord import app_commands

from stockchecker import queries
from stockchecker.bot.formatting import movers_embed, sectors_embed, stock_embed, top_embed
from stockchecker.config import configure_logging, get_settings
from stockchecker.storage import Store

log = logging.getLogger(__name__)


def _parse_cap(text: str | None) -> float | None:
    if not text:
        return None
    return queries.parse_market_cap(text)


class StockCheckerBot(discord.Client):
    def __init__(self, store: Store, allow_live: bool = True) -> None:
        super().__init__(intents=discord.Intents.default())
        self.store = store
        self.allow_live = allow_live
        self.tree = app_commands.CommandTree(self)
        register_commands(self.tree, self)

    async def setup_hook(self) -> None:
        synced = await self.tree.sync()
        log.info("synced %d slash commands", len(synced))

    async def on_ready(self) -> None:
        log.info("logged in as %s", self.user)
        await self.change_presence(activity=discord.Game(name="/stock · /top · /movers"))


def register_commands(tree: app_commands.CommandTree, bot: StockCheckerBot) -> None:
    @tree.command(name="stock", description="Analyst consensus and StockChecker score for a stock")
    @app_commands.describe(
        query="Ticker (AAPL) or part of a company name (apple)",
        live="Fetch fresh data now instead of using the last scan",
    )
    async def stock(interaction: discord.Interaction, query: str, live: bool = False) -> None:
        await interaction.response.defer(thinking=True)
        snapshot = None if live else queries.lookup(bot.store, query)
        if snapshot is None and bot.allow_live and _looks_like_ticker(query):
            from stockchecker.pipeline import analyze

            snapshot = await asyncio.to_thread(analyze, query)
            if snapshot.composite is not None or snapshot.ratings:
                bot.store.save(snapshot, run_id="discord")
            else:
                snapshot = None
        if snapshot is None:
            await interaction.followup.send(f"Nothing found for **{query}**.")
            return
        await interaction.followup.send(embed=stock_embed(snapshot))

    @tree.command(name="top", description="Highest-rated stocks from the latest scan")
    @app_commands.describe(
        count="How many (1-25)",
        sector="Sector filter, e.g. Technology",
        min_cap="Minimum market cap, e.g. 500M or 2B",
    )
    async def top(
        interaction: discord.Interaction,
        count: app_commands.Range[int, 1, 25] = 5,
        sector: str | None = None,
        min_cap: str | None = None,
    ) -> None:
        try:
            cap = _parse_cap(min_cap)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        rows = queries.top(bot.store, n=count, sector=sector, min_market_cap=cap)
        await interaction.response.send_message(embed=top_embed(rows, sector, min_cap))

    @tree.command(name="movers", description="Biggest score changes since the previous scan")
    @app_commands.describe(
        count="How many (1-25)",
        sector="Sector filter",
        min_cap="Minimum market cap, e.g. 500M",
        down="Show the biggest drops instead of gains",
    )
    async def movers(
        interaction: discord.Interaction,
        count: app_commands.Range[int, 1, 25] = 5,
        sector: str | None = None,
        min_cap: str | None = None,
        down: bool = False,
    ) -> None:
        try:
            cap = _parse_cap(min_cap)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        rows = queries.movers(
            bot.store,
            n=count,
            sector=sector,
            min_market_cap=cap,
            direction="down" if down else "up",
        )
        empty_message = queries.no_movers_message(bot.store) if not rows else None
        await interaction.response.send_message(embed=movers_embed(rows, down, empty_message))

    @tree.command(name="sectors", description="Sectors present in the database")
    async def sectors(interaction: discord.Interaction) -> None:
        names = queries.sectors(bot.store)
        counts = dict.fromkeys(names, 0)
        for snap in bot.store.latest():
            if snap.sector in counts:
                counts[snap.sector] += 1
        await interaction.response.send_message(embed=sectors_embed(counts))


def _looks_like_ticker(text: str) -> bool:
    text = text.strip()
    return 1 <= len(text) <= 10 and text.replace(".", "").replace("-", "").isalnum()


def main(db: Path | None = None) -> None:
    configure_logging()
    settings = get_settings()
    if not settings.discord_token:
        raise SystemExit("DISCORD_TOKEN is not set. Put it in .env (see .env.example).")
    bot = StockCheckerBot(Store(db or settings.db_path))
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":  # pragma: no cover
    main()
