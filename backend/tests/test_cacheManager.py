import pytest
import os
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, mock_open
import polars as pl
from cacheManager import CacheManager

@pytest.fixture
def mock_config():
    with patch("builtins.open", mock_open(read_data='{"paths": {"stored_tickers": "./mock_data/"}}')):
        yield

@pytest.fixture
def cache_manager(mock_config):
    return CacheManager()

def test_init_creates_directory(mock_config):
    with patch("os.makedirs") as mock_makedirs:
        cm = CacheManager()
        mock_makedirs.assert_called_once_with("./mock_data/", exist_ok=True)

def test_ticker_path(cache_manager):
    assert cache_manager.ticker_path("AAPL") == "./mock_data/AAPL.csv"

def test_from_local_cache_not_exists(cache_manager):
    with patch("os.path.exists", return_value=False):
        df, start, end = cache_manager.from_local_cache("AAPL")
        assert df is None
        assert start is None
        assert end is None

def test_from_local_cache_exists(cache_manager):
    mock_df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 2)],
        "Close": [100.0, 101.0]
    })
    
    with patch("os.path.exists", return_value=True), \
         patch("polars.read_csv", return_value=mock_df), \
         patch.object(cache_manager, "get_cache_bounds", return_value=(date(2023, 1, 1), date(2023, 1, 2))):
        
        df, start, end = cache_manager.from_local_cache("AAPL")
        
        assert df is not None
        assert len(df) == 2
        assert start == date(2023, 1, 1)
        assert end == date(2023, 1, 2)

def test_from_local_cache_exists_no_metadata(cache_manager):
    mock_df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 5)],
        "Close": [100.0, 101.0]
    })
    
    with patch("os.path.exists", return_value=True), \
         patch("polars.read_csv", return_value=mock_df), \
         patch.object(cache_manager, "get_cache_bounds", return_value=(None, None)):
        
        df, start, end = cache_manager.from_local_cache("AAPL")
        
        assert start == date(2023, 1, 1)
        assert end == date(2023, 1, 5)

def test_update_cache_metadata_new(cache_manager):
    m_open = mock_open()
    with patch("builtins.open", m_open):
        with patch("os.path.exists", return_value=False):
            m_open.side_effect = [FileNotFoundError, m_open.return_value]
            cache_manager.update_cache_metadata("AAPL", start=date(2023,1,1), end=date(2023,1,10))
            
            m_open.assert_called_with("./mock_data/cache_metadata.json", "w")
            
            handle = m_open.return_value
            written = "".join(call.args[0] for call in handle.write.call_args_list)
            data = json.loads(written)
            assert "AAPL" in data
            assert data["AAPL"]["start"] == "2023-01-01"
            assert data["AAPL"]["end"] == "2023-01-10"
            assert "last_accessed" in data["AAPL"]

def test_remove_cached_ticker(cache_manager):
    mock_metadata = {"AAPL": {"start": "2023-01-01"}, "MSFT": {"start": "2023-01-01"}}
    m_open = mock_open(read_data=json.dumps(mock_metadata))
    
    with patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove, \
         patch("builtins.open", m_open):
        
        cache_manager.remove_cached_ticker("AAPL")
        
        mock_remove.assert_called_once_with("./mock_data/AAPL.csv")
        
        handle = m_open()
        write_calls = [c.args[0] for c in handle.write.call_args_list if c.args]
        if write_calls:
            written = "".join(write_calls)
            data = json.loads(written)
            assert "AAPL" not in data
            assert "MSFT" in data

def test_enforce_cache_lifecycle(cache_manager):
    old_date = (datetime.now() - timedelta(days=40)).isoformat()
    new_date = (datetime.now() - timedelta(days=10)).isoformat()
    
    mock_metadata = {
        "OLD_TICKER": {"last_accessed": old_date},
        "NEW_TICKER": {"last_accessed": new_date}
    }
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_metadata))), \
         patch.object(cache_manager, "remove_cached_ticker") as mock_remove:
        
        cache_manager.enforce_cache_lifecycle()
        
        mock_remove.assert_called_once_with("OLD_TICKER")
