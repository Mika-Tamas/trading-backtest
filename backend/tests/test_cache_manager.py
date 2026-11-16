import json
import os
from datetime import date, datetime, timedelta
import polars as pl
import pytest
from cache_manager import CacheManager


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def cache_manager(cache_dir):
    return CacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
    )


def test_init_creates_storage_directory(cache_dir):
    assert not cache_dir.exists()
    cm = CacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
    )
    assert cache_dir.is_dir()
    assert cm.ticker_path("AAPL") == os.path.join(str(cache_dir), "AAPL.csv")


def test_from_local_cache_missing_file(cache_manager):
    df, start, end = cache_manager.from_local_cache("MISSING")
    assert df is None
    assert start is None
    assert end is None


def test_save_and_load_round_trip_with_metadata(cache_manager):
    sample = pl.DataFrame({
        "Date": [date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4)],
        "Close": [100.0, 102.5, 101.0],
    })
    cache_manager.save_to_csv("AAPL", sample)
    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 5))

    loaded, start, end = cache_manager.from_local_cache("AAPL")
    assert loaded is not None
    assert len(loaded) == 3
    assert loaded["Close"].to_list() == [100.0, 102.5, 101.0]
    assert start == date(2023, 1, 1)
    assert end == date(2023, 1, 5)


def test_from_local_cache_falls_back_to_csv_bounds_when_metadata_missing(cache_manager):
    sample = pl.DataFrame({
        "Date": [date(2023, 2, 1), date(2023, 2, 10)],
        "Close": [150.0, 155.0],
    })
    cache_manager.save_to_csv("MSFT", sample)

    loaded, start, end = cache_manager.from_local_cache("MSFT")
    assert loaded is not None
    assert start == date(2023, 2, 1)
    assert end == date(2023, 2, 10)


def test_from_local_cache_handles_corrupted_csv_and_missing_date_column(cache_manager, cache_dir):
    (cache_dir / "EMPTY.csv").write_text("", encoding="utf-8")
    assert cache_manager.from_local_cache("EMPTY") == (None, None, None)

    (cache_dir / "BADDATE.csv").write_text("Date,Close\nnot-a-date,100.0\n", encoding="utf-8")
    assert cache_manager.from_local_cache("BADDATE") == (None, None, None)

    (cache_dir / "NODATE.csv").write_text("Ticker,Close\nAAPL,100.0\n", encoding="utf-8")
    assert cache_manager.from_local_cache("NODATE") == (None, None, None)


def test_corrupted_metadata_json_recovery(cache_manager, cache_dir):
    meta_path = cache_dir / "cache_metadata.json"
    meta_path.write_text("{corrupted json!!!", encoding="utf-8")

    assert cache_manager.get_cache_bounds("AAPL") == (None, None)

    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 10))
    recovered = json.loads(meta_path.read_text(encoding="utf-8"))
    assert recovered["AAPL"]["start"] == "2023-01-01"
    assert recovered["AAPL"]["end"] == "2023-01-10"
    assert "last_accessed" in recovered["AAPL"]


def test_remove_cached_ticker_deletes_csv_and_metadata(cache_manager, cache_dir):
    df = pl.DataFrame({"Date": [date(2023, 1, 1)], "Close": [100.0]})
    cache_manager.save_to_csv("AAPL", df)
    cache_manager.save_to_csv("MSFT", df)
    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 2))
    cache_manager.update_cache_metadata("MSFT", start=date(2023, 1, 1), end=date(2023, 1, 2))

    cache_manager.remove_cached_ticker("AAPL")

    assert not (cache_dir / "AAPL.csv").exists()
    assert (cache_dir / "MSFT.csv").exists()
    metadata = json.loads((cache_dir / "cache_metadata.json").read_text(encoding="utf-8"))
    assert "AAPL" not in metadata
    assert "MSFT" in metadata


def test_enforce_cache_lifecycle_evicts_expired_and_corrupted_entries(cache_manager, cache_dir):
    df = pl.DataFrame({"Date": [date(2023, 1, 1)], "Close": [100.0]})
    for sym in ("EXPIRED", "FRESH", "CORRUPT_TS"):
        cache_manager.save_to_csv(sym, df)

    old_ts = (datetime.now() - timedelta(days=45)).isoformat()
    fresh_ts = (datetime.now() - timedelta(days=5)).isoformat()

    metadata = {
        "EXPIRED": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": old_ts},
        "FRESH": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": fresh_ts},
        "CORRUPT_TS": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": "bad-timestamp"},
    }
    (cache_dir / "cache_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    cache_manager.enforce_cache_lifecycle()

    assert not (cache_dir / "EXPIRED.csv").exists()
    assert not (cache_dir / "CORRUPT_TS.csv").exists()
    assert (cache_dir / "FRESH.csv").exists()
    remaining = json.loads((cache_dir / "cache_metadata.json").read_text(encoding="utf-8"))
    assert list(remaining.keys()) == ["FRESH"]
