"""Build Discord embeds from snapshots. Pure functions, so they are unit-testable offline."""

from __future__ import annotations

import discord

from stockchecker.formatting import (
    NA,
    format_date,
    format_delta,
    format_market_cap,
    format_pct,
    format_price,
    format_score,
    upside,
)
from stockchecker.models import RatingLabel, StockSnapshot
from stockchecker.queries import Mover

LABEL_COLOURS = {
    RatingLabel.STRONG_BUY: discord.Colour.from_rgb(46, 160, 67),
    RatingLabel.BUY: discord.Colour.from_rgb(87, 171, 90),
    RatingLabel.HOLD: discord.Colour.from_rgb(210, 153, 34),
    RatingLabel.SELL: discord.Colour.from_rgb(207, 102, 79),
    RatingLabel.STRONG_SELL: discord.Colour.from_rgb(180, 35, 24),
}
NEUTRAL_COLOUR = discord.Colour.greyple()

MAX_EMBED_FIELDS = 25


def colour_for(snapshot: StockSnapshot) -> discord.Colour:
    return LABEL_COLOURS.get(snapshot.label, NEUTRAL_COLOUR) if snapshot.label else NEUTRAL_COLOUR


def stock_embed(snapshot: StockSnapshot) -> discord.Embed:
    """Full detail card for one stock."""
    title = f"{snapshot.name or snapshot.ticker} ({snapshot.ticker})"
    subtitle = " · ".join(p for p in (snapshot.sector, snapshot.industry) if p)
    embed = discord.Embed(title=title, description=subtitle or None, colour=colour_for(snapshot))

    embed.add_field(name="Price", value=format_price(snapshot.price), inline=True)
    embed.add_field(name="Market cap", value=format_market_cap(snapshot.market_cap), inline=True)
    if snapshot.composite is not None:
        embed.add_field(
            name="Composite",
            value=f"**{format_score(snapshot.composite)} {snapshot.label.value}**",
            inline=True,
        )
    else:
        embed.add_field(name="Composite", value="no data", inline=True)

    for rating in snapshot.ratings:
        details = [f"{rating.label.value} · {format_score(rating.score)}"]
        if rating.analysts is not None:
            details.append(f"{rating.analysts} analysts")
        if rating.price_target is not None:
            target = format_price(rating.price_target)
            gain = upside(snapshot.price, rating.price_target)
            suffix = f" ({format_pct(gain)})" if gain is not None else ""
            details.append(f"target {target}{suffix}")
        embed.add_field(name=rating.source, value="\n".join(details), inline=True)

    if snapshot.fundamentals_score is not None:
        embed.add_field(
            name="StockChecker fundamentals",
            value=format_score(snapshot.fundamentals_score.score),
            inline=True,
        )

    unavailable = [name for name in snapshot.errors if not name.endswith("profile")]
    if unavailable:
        embed.add_field(name="No data from", value=", ".join(unavailable), inline=False)

    embed.set_footer(text=f"Sources: {snapshot.coverage} · Updated {format_date(snapshot.as_of)}")
    return embed


def _ranking_line(rank: int, snapshot: StockSnapshot) -> str:
    label = snapshot.label.value if snapshot.label else NA
    return (
        f"**{rank}. {snapshot.ticker}** — {snapshot.name or NA}\n"
        f"{format_score(snapshot.composite)} {label} · {format_price(snapshot.price)}"
        f" · {format_market_cap(snapshot.market_cap)} · {snapshot.coverage} src"
    )


def top_embed(rows: list[StockSnapshot], sector: str | None, min_cap: str | None) -> discord.Embed:
    filters = [f for f in (sector, f"cap ≥ {min_cap}" if min_cap else None) if f]
    title = f"Top {len(rows)} by composite score"
    if filters:
        title += f" ({', '.join(filters)})"
    embed = discord.Embed(title=title, colour=discord.Colour.blurple())
    if not rows:
        embed.description = "No stored results match. Run a scan first."
        return embed
    embed.description = "\n\n".join(_ranking_line(i, s) for i, s in enumerate(rows, 1))
    return embed


def movers_embed(rows: list[Mover], down: bool, empty_message: str | None = None) -> discord.Embed:
    title = f"Top {len(rows)} {'drops' if down else 'gains'} since last snapshot"
    embed = discord.Embed(
        title=title, colour=discord.Colour.red() if down else discord.Colour.green()
    )
    if not rows:
        embed.description = empty_message or "No movers yet."
        return embed
    lines = []
    for i, mover in enumerate(rows, 1):
        s = mover.snapshot
        lines.append(
            f"**{i}. {s.ticker}** — {s.name or NA}\n"
            f"{format_score(mover.previous)} → {format_score(s.composite)}"
            f" (**{format_delta(mover.delta)}**, {format_pct(mover.pct_change)})"
        )
    embed.description = "\n\n".join(lines)
    return embed


def sectors_embed(counts: dict[str, int]) -> discord.Embed:
    embed = discord.Embed(title="Sectors in the database", colour=discord.Colour.blurple())
    if not counts:
        embed.description = "No stored results. Run a scan first."
        return embed
    embed.description = "\n".join(f"**{name}** · {n}" for name, n in counts.items())
    return embed
