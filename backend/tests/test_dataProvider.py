import pytest
from unittest.mock import patch, MagicMock
import polars as pl
import pandas as pd
from datetime import date
from dataProvider import DataProvider

@pytest.fixture
def data_provider():
    with patch('dataProvider.CacheManager'):
        dp = DataProvider()
        return dp

def test_load_ticker_invalid_dates(data_provider):
    with pytest.raises(ValueError, match="Start date must be strictly before end date"):
        data_provider.load_ticker("AAPL", "2023-01-10", "2023-01-01")
        
    future_date = date.today().replace(year=date.today().year + 1).isoformat()
    with pytest.raises(ValueError, match="End date cannot be in the future"):
        data_provider.load_ticker("AAPL", "2023-01-01", future_date)

def test_load_ticker_no_cache(data_provider):
    mock_df = pd.DataFrame({
        "Date": [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")],
        "Open": [100.0, 101.0],
        "High": [102.0, 103.0],
        "Low": [99.0, 100.0],
        "Close": [101.0, 102.0],
        "Volume": [1000, 1100]
    }).set_index("Date")
    mock_df.columns = pd.MultiIndex.from_product([mock_df.columns, ['AAPL']])
    
    data_provider.cache.from_local_cache.return_value = (None, None, None)
    
    with patch("yfinance.download", return_value=mock_df) as mock_yf:
        result = data_provider.load_ticker("AAPL", "2023-01-01", "2023-01-02")
        
        mock_yf.assert_called_once_with("AAPL", start="2023-01-01", end="2023-01-02")
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 2
        assert "Date" in result.columns
        assert data_provider.cache.save_to_csv.called
        assert data_provider.cache.update_cache_metadata.called

def test_load_ticker_with_fx(data_provider):
    mock_pl_df = pl.DataFrame({
        "Date": [date(2023, 1, 1)],
        "Open": [100.0],
        "High": [105.0],
        "Low": [95.0],
        "Close": [102.0],
    })
    
    mock_fx_df = pl.DataFrame({
        "Date": [date(2023, 1, 1)],
        "Close": [1.5]
    })

    with patch.object(data_provider, "load_ticker") as mock_load_ticker, \
         patch.object(data_provider, "get_ticker_currency", return_value="USD"):
        
        mock_load_ticker.side_effect = [mock_pl_df, mock_fx_df] # for with_fx
        result = data_provider.load_ticker_with_fx("AAPL", "2023-01-01", "2023-01-02", "EUR")
        
        # multiplied by 1.5
        assert result["Open"][0] == 150.0
        assert result["High"][0] == 157.5
        assert result["Low"][0] == 142.5
        assert result["Close"][0] == 153.0

def test_load_ticker_with_fx_same_currency(data_provider):
    mock_pl_df = pl.DataFrame({"Date": [date(2023, 1, 1)], "Close": [100.0]})
    
    with patch.object(data_provider, "load_ticker", return_value=mock_pl_df) as mock_load_ticker, \
         patch.object(data_provider, "get_ticker_currency", return_value="USD"):
        
        result = data_provider.load_ticker_with_fx("AAPL", "2023-01-01", "2023-01-02", "USD")
        
        assert mock_load_ticker.call_count == 1
        assert result["Close"][0] == 100.0
