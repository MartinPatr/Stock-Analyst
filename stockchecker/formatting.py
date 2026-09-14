"""Human-friendly rendering of numbers shared by the CLI and the Discord bot."""

from __future__ import annotations

from datetime import datetime

NA = "n/a"


def format_market_cap(value: float | None) -> str:
    if value is None or value <= 0:
        return NA
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if value >= threshold:
            return f"${value / threshold:.2f}{suffix}"
    return f"${value:.0f}"


def format_price(value: float | None) -> str:
    if value is None:
        return NA
    return f"${value:,.2f}"


def format_score(value: float | None, digits: int = 2) -> str:
    if value is None:
        return NA
    return f"{value:.{digits}f}/5"


def format_pct(value: float | None, digits: int = 1, signed: bool = True) -> str:
    """Percent with a sign and no floating-point noise: 7.000000000000001 -> '+7.0%'."""
    if value is None:
        return NA
    rounded = round(value, digits)
    if rounded == 0:
        rounded = 0.0  # avoid '-0.0%'
    sign = "+" if signed and rounded > 0 else ""
    return f"{sign}{rounded:.{digits}f}%"


def format_delta(value: float | None, digits: int = 2) -> str:
    if value is None:
        return NA
    rounded = round(value, digits)
    if rounded == 0:
        return f"{0:.{digits}f}"
    return f"{rounded:+.{digits}f}"


def format_ratio(value: float | None, digits: int = 2) -> str:
    if value is None:
        return NA
    return f"{value:.{digits}f}"


def format_date(value: datetime | None) -> str:
    if value is None:
        return NA
    return value.strftime("%b %d, %Y")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return NA
    return value.strftime("%b %d, %Y %H:%M UTC")


def upside(price: float | None, target: float | None) -> float | None:
    """Percent distance from price to an analyst price target."""
    if price is None or target is None or price <= 0:
        return None
    return (target - price) / price * 100.0
