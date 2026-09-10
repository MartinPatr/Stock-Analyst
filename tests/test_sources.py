"""Parser tests run against saved HTML so they are deterministic and offline.

Live tests (``pytest --live``) hit the real sites and catch layout changes.
"""

from unittest.mock import MagicMock

import pytest
import requests

from stockchecker.models import RatingLabel
from stockchecker.sources import marketbeat, stockanalysis, yahoo
from stockchecker.sources.base import ParseError, SourceBlocked, TickerNotFound
from stockchecker.sources.http import PoliteSession
from tests.conftest import read_fixture

# --- MarketBeat -----------------------------------------------------------------------------


def test_marketbeat_parses_consensus_block() -> None:
    consensus = marketbeat.parse_forecast_page(read_fixture("marketbeat_aapl.html"))
    assert consensus is not None
    assert consensus.label_text == "Moderate Buy"
    assert consensus.score_1_to_4 == 2.51
    assert consensus.analysts == 39
    assert consensus.price_target == 331.53


def test_marketbeat_to_rating_normalises() -> None:
    consensus = marketbeat.parse_forecast_page(read_fixture("marketbeat_aapl.html"))
    rating = marketbeat.to_rating(consensus, "MarketBeat")
    assert rating.label is RatingLabel.BUY
    assert rating.score == pytest.approx(3.51)
    assert rating.analysts == 39
    assert rating.raw == "Moderate Buy (2.51/4)"


def test_marketbeat_page_without_consensus_means_no_coverage() -> None:
    assert marketbeat.parse_forecast_page("<html><body><h1>NASDAQ</h1></body></html>") is None


def test_marketbeat_falls_back_to_bucket_counts() -> None:
    html = """
    <h3>Consensus Rating</h3>
    <div><span>Hold</span><span>Based on 4 Analyst Ratings</span>
      <span>Sell</span><span>1</span><span>Hold</span><span>2</span>
      <span>Buy</span><span>1</span></div>
    """
    consensus = marketbeat.parse_forecast_page(html)
    assert consensus is not None
    assert consensus.score_1_to_4 == pytest.approx(2.0)  # (1*1 + 2*2 + 3*1) / 4
    assert consensus.analysts == 4


def test_marketbeat_garbled_label_is_parse_error() -> None:
    consensus = marketbeat.MarketBeatConsensus("???", None, None, None)
    with pytest.raises(ParseError):
        marketbeat.to_rating(consensus, "MarketBeat")


def test_marketbeat_redirect_to_index_is_not_found() -> None:
    response = MagicMock(url="https://www.marketbeat.com/stocks/NASDAQ/", text="")
    session = MagicMock(get=MagicMock(return_value=response))
    with pytest.raises(TickerNotFound):
        marketbeat.MarketBeatSource(session).fetch("ZZZZQ")


def test_marketbeat_source_end_to_end_with_fixture() -> None:
    response = MagicMock(
        url="https://www.marketbeat.com/stocks/NASDAQ/AAPL/forecast/",
        text=read_fixture("marketbeat_aapl.html"),
    )
    session = MagicMock(get=MagicMock(return_value=response))
    rating = marketbeat.MarketBeatSource(session).fetch("aapl")
    assert rating is not None and rating.source == "MarketBeat"
    session.get.assert_called_once_with(marketbeat.URL_TEMPLATE.format(ticker="AAPL"))


# --- StockAnalysis --------------------------------------------------------------------------


def test_stockanalysis_parses_sentence_and_trend_table() -> None:
    consensus = stockanalysis.parse_forecast_page(read_fixture("stockanalysis_jpm.html"))
    assert consensus is not None
    assert consensus.label_text == "Buy"
    assert consensus.analysts == 24
    assert consensus.price_target == 376.14
    assert consensus.counts == {"Strong Buy": 9, "Buy": 4, "Hold": 10, "Sell": 1, "Strong Sell": 0}


def test_stockanalysis_scores_from_latest_month_counts() -> None:
    consensus = stockanalysis.parse_forecast_page(read_fixture("stockanalysis_jpm.html"))
    rating = stockanalysis.to_rating(consensus, "StockAnalysis")
    assert rating.label is RatingLabel.BUY
    assert rating.score == pytest.approx((9 * 5 + 4 * 4 + 10 * 3 + 1 * 2) / 24, abs=1e-3)
    assert "9/4/10/1/0" in rating.raw


def test_stockanalysis_label_only_page() -> None:
    html = '<p>According to 3 analysts, X has a consensus rating of "Hold".</p>'
    consensus = stockanalysis.parse_forecast_page(html)
    rating = stockanalysis.to_rating(consensus, "StockAnalysis")
    assert rating.label is RatingLabel.HOLD and rating.score == 3.0 and rating.analysts == 3
    assert rating.price_target is None


def test_stockanalysis_unrelated_page_is_parse_error() -> None:
    with pytest.raises(ParseError):
        stockanalysis.parse_forecast_page("<html><body>Welcome to my blog</body></html>")


def test_stockanalysis_uses_dash_slug() -> None:
    response = MagicMock(text=read_fixture("stockanalysis_jpm.html"))
    session = MagicMock(get=MagicMock(return_value=response))
    stockanalysis.StockAnalysisSource(session).fetch("BRK.B")
    session.get.assert_called_once_with(stockanalysis.URL_TEMPLATE.format(ticker="brk-b"))


# --- Yahoo ----------------------------------------------------------------------------------

YAHOO_INFO = {
    "longName": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "currentPrice": 315.34,
    "marketCap": 4.6e12,
    "recommendationMean": 2.23,
    "recommendationKey": "buy",
    "numberOfAnalystOpinions": 38,
    "targetMeanPrice": 323.86,
    "trailingPE": 36.2,
    "priceToSalesTrailing12Months": 9.86,
    "priceToBook": 42.8,
    "enterpriseToRevenue": 9.9,
    "currentRatio": 1.003,
    "debtToEquity": 78.4,
}


def test_yahoo_rating_from_info() -> None:
    rating = yahoo.rating_from_info(YAHOO_INFO, "Yahoo Finance")
    assert rating is not None
    assert rating.label is RatingLabel.BUY
    assert rating.score == pytest.approx(6 - 2.23, abs=1e-3)
    assert rating.analysts == 38 and rating.price_target == 323.86


def test_yahoo_rating_absent_when_no_analysts() -> None:
    assert yahoo.rating_from_info({"longName": "Tiny Co"}, "Yahoo Finance") is None


def test_yahoo_profile_converts_debt_to_equity_percent() -> None:
    profile = yahoo.profile_from_info(YAHOO_INFO)
    assert profile.name == "Apple Inc." and profile.sector == "Technology"
    assert profile.fundamentals.debt_to_equity == pytest.approx(0.784)
    assert profile.fundamentals.pe == 36.2
    assert profile.market_cap == 4.6e12


def test_yahoo_source_caches_info_between_rating_and_profile(monkeypatch) -> None:
    calls = []

    def fake_load(ticker: str):
        calls.append(ticker)
        return YAHOO_INFO

    monkeypatch.setattr(yahoo, "_load_info", fake_load)
    source = yahoo.YahooSource()
    assert source.fetch("aapl") is not None
    assert source.fetch_profile("AAPL").name == "Apple Inc."
    assert calls == ["AAPL"]


# --- HTTP session ---------------------------------------------------------------------------


def _response(
    status: int, text: str = "x" * 30_000, url: str = "https://example.com/p"
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.ok = 200 <= status < 300
    resp.text = text
    resp.content = text.encode()
    resp.url = url
    return resp


def test_session_maps_statuses_to_errors() -> None:
    inner = MagicMock()
    session = PoliteSession(delay_s=0, max_retries=0, session=inner)

    inner.get.return_value = _response(404)
    with pytest.raises(TickerNotFound):
        session.get("https://example.com/a")

    inner.get.return_value = _response(403)
    with pytest.raises(SourceBlocked):
        session.get("https://example.com/b")

    inner.get.return_value = _response(200, text="<title>Pardon Our Interruption</title>")
    with pytest.raises(SourceBlocked):
        session.get("https://example.com/c")


def test_session_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr("stockchecker.sources.http.time.sleep", lambda *_: None)
    inner = MagicMock()
    inner.get.side_effect = [_response(503), _response(429), _response(200)]
    session = PoliteSession(delay_s=0, max_retries=3, session=inner)
    assert session.get("https://example.com/x").status_code == 200
    assert inner.get.call_count == 3


def test_session_enforces_per_host_delay(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("stockchecker.sources.http.time.sleep", lambda s: sleeps.append(s))
    inner = MagicMock()
    inner.get.return_value = _response(200)
    session = PoliteSession(delay_s=1.0, max_retries=0, session=inner)
    session.get("https://a.com/1")
    session.get("https://a.com/2")  # same host -> must wait
    session.get("https://b.com/1")  # different host -> no wait
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 1.0


# --- Live -----------------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.parametrize(
    "cls", [marketbeat.MarketBeatSource, stockanalysis.StockAnalysisSource, yahoo.YahooSource]
)
def test_live_sources_rate_apple(cls) -> None:
    rating = cls().fetch("AAPL")
    assert rating is not None
    assert 0 <= rating.score <= 5
    assert rating.analysts and rating.analysts > 5
