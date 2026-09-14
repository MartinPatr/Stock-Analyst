from datetime import UTC, datetime

from stockchecker.formatting import (
    format_date,
    format_delta,
    format_market_cap,
    format_pct,
    format_price,
    format_score,
    upside,
)


def test_market_cap_units() -> None:
    assert format_market_cap(4.6e12) == "$4.60T"
    assert format_market_cap(1_660_000_000) == "$1.66B"
    assert format_market_cap(501_880_000) == "$501.88M"
    assert format_market_cap(2_500) == "$2.50K"
    assert format_market_cap(900) == "$900"
    assert format_market_cap(None) == "n/a"
    assert format_market_cap(0) == "n/a"


def test_percent_has_no_float_noise_or_double_sign() -> None:
    # The original bot rendered "+7.000000000000001%%".
    assert format_pct(7.000000000000001) == "+7.0%"
    assert format_pct(-3.456) == "-3.5%"
    assert format_pct(0.0) == "0.0%"
    assert format_pct(-0.001) == "0.0%"
    assert format_pct(None) == "n/a"
    assert format_pct(12.345, digits=2, signed=False) == "12.35%"


def test_delta_score_price_date() -> None:
    assert format_delta(0.4) == "+0.40"
    assert format_delta(-0.5) == "-0.50"
    assert format_delta(0.001) == "0.00"
    assert format_score(3.789) == "3.79/5"
    assert format_score(None) == "n/a"
    assert format_price(1234.5) == "$1,234.50"
    assert format_date(datetime(2024, 8, 3, tzinfo=UTC)) == "Aug 03, 2024"


def test_upside() -> None:
    assert upside(100, 110) == 10.0
    assert upside(None, 110) is None
    assert upside(0, 110) is None
