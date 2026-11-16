from datetime import date, timedelta
from unittest.mock import patch
import pandas as pd
import polars as pl
import pytest
from cache_manager import CacheManager
from data_provider import DataProvider


@pytest.fixture
def data_provider(tmp_path):
    cache_dir = tmp_path / "dp_cache"
    cm = CacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
    )
    return DataProvider(cache=cm)


def _make_yf_df(dates, closes, ticker="AAPL"):
    df = pd.DataFrame({
        "Date": [pd.Timestamp(d) for d in dates],
        "Open": closes,
        "High": [c + 2.0 for c in closes],
        "Low": [c - 2.0 for c in closes],
        "Close": closes,
        "Volume": [1000] * len(dates),
    }).set_index("Date")
    df.columns = pd.MultiIndex.from_product([df.columns, [ticker]])
    return df


def test_load_ticker_rejects_invalid_dates(data_provider):
    with pytest.raises(ValueError, match="YYYY-MM-DD ISO format"):
        data_provider.load_ticker("AAPL", "2023/01/01", "2023-01-10")

    with pytest.raises(ValueError, match="Start date must be strictly before end date"):
        data_provider.load_ticker("AAPL", "2023-01-10", "2023-01-01")

    with pytest.raises(ValueError, match="Start date must be strictly before end date"):
        data_provider.load_ticker("AAPL", "2023-01-05", "2023-01-05")

    future_date = (date.today() + timedelta(days=30)).isoformat()
    with pytest.raises(ValueError, match="End date cannot be in the future"):
        data_provider.load_ticker("AAPL", "2023-01-01", future_date)


def test_load_ticker_populates_and_reuses_real_cache(data_provider):
    yf_df = _make_yf_df(["2023-01-02", "2023-01-03"], [101.0, 102.0])

    with patch("yfinance.download", return_value=yf_df) as mock_yf:
        first = data_provider.load_ticker("AAPL", "2023-01-02", "2023-01-03")
        assert mock_yf.call_count == 1
        assert isinstance(first, pl.DataFrame)
        assert first["Close"].to_list() == [101.0, 102.0]

        second = data_provider.load_ticker("AAPL", "2023-01-02", "2023-01-03")
        assert mock_yf.call_count == 1
        assert second["Close"].to_list() == [101.0, 102.0]


def test_load_ticker_upstream_timeout_and_empty_responses(data_provider):
    with patch("yfinance.download", side_effect=TimeoutError("upstream timed out")):
        with pytest.raises(TimeoutError, match="upstream timed out"):
            data_provider.load_ticker("AAPL", "2023-01-01", "2023-01-10")

    with patch("yfinance.download", return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="invalid or has no data"):
            data_provider.load_ticker("BADTICKER", "2023-01-01", "2023-01-10")

    with patch("yfinance.download", return_value=None):
        with pytest.raises(ValueError, match="invalid or has no data"):
            data_provider.load_ticker("NONETICKER", "2023-01-01", "2023-01-10")


def test_load_ticker_missing_or_null_timestamps_raise_value_error(data_provider):
    no_date_df = pd.DataFrame({"Close": [100.0, 101.0]})
    with patch("yfinance.download", return_value=no_date_df):
        with pytest.raises(ValueError, match="missing 'Date' timestamps"):
            data_provider.load_ticker("AAPL", "2023-01-01", "2023-01-10")

    nat_df = pd.DataFrame({
        "Date": [pd.Timestamp("2023-01-02"), pd.NaT],
        "Open": [100.0, 101.0],
        "High": [102.0, 103.0],
        "Low": [99.0, 100.0],
        "Close": [101.0, 102.0],
        "Volume": [1000, 1100],
    }).set_index("Date")
    with patch("yfinance.download", return_value=nat_df):
        with pytest.raises(ValueError, match="missing or invalid timestamps"):
            data_provider.load_ticker("AAPL", "2023-01-01", "2023-01-10")


def test_load_ticker_cache_extension_fallback_on_timeout(data_provider):
    initial_df = _make_yf_df(["2023-01-05", "2023-01-06"], [105.0, 106.0])
    full_df = _make_yf_df(["2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06"], [103.0, 104.0, 105.0, 106.0])

    with patch("yfinance.download", return_value=initial_df):
        data_provider.load_ticker("AAPL", "2023-01-05", "2023-01-06")

    # Partial fetch timeout falls back to full download
    with patch("yfinance.download", side_effect=[TimeoutError("partial timeout"), full_df]):
        extended = data_provider.load_ticker("AAPL", "2023-01-03", "2023-01-06")
        assert extended["Close"].to_list() == [103.0, 104.0, 105.0, 106.0]


def test_load_ticker_with_fx_conversion_and_info_timeout_fallback(data_provider):
    asset_df = _make_yf_df(["2023-01-02", "2023-01-03"], [100.0, 110.0], ticker="AAPL")
    fx_df = _make_yf_df(["2023-01-02", "2023-01-03"], [1.5, 1.6], ticker="USDEUR=X")

    with patch("yfinance.download", side_effect=[asset_df, fx_df]), \
         patch.object(data_provider, "get_ticker_currency", return_value="USD"):
        converted = data_provider.load_ticker_with_fx("AAPL", "2023-01-02", "2023-01-03", "EUR")
        assert converted["Close"].to_list() == [150.0, 176.0]
        assert converted["Open"].to_list() == [150.0, 176.0]

    with patch("yfinance.Ticker", side_effect=TimeoutError("info timeout")):
        assert data_provider.get_ticker_currency("AAPL") is None
