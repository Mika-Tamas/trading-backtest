from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import json
import os
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

import cache_manager as cache_manager_module
from cache_manager import (
    BARS_COLLECTION,
    METADATA_COLLECTION,
    CacheManager,
    LocalCacheManager,
    MongoCacheManager,
    close_cached_clients,
    create_cache_manager,
)
from tests.fake_mongo import FakeDatabase


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def local_cache(cache_dir):
    return LocalCacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
        ttl_days=30,
        max_tickers=500,
    )


@pytest.fixture
def fake_db():
    return FakeDatabase()


@pytest.fixture
def mongo_cache(fake_db):
    return MongoCacheManager(db=fake_db, ttl_days=30, max_tickers=500)


@pytest.fixture(params=["local", "mongo"])
def cache_manager(request, tmp_path):
    if request.param == "local":
        d = tmp_path / "poly_cache"
        return LocalCacheManager(
            storage_path=str(d),
            metadata_file=str(d / "cache_metadata.json"),
            ttl_days=30,
            max_tickers=500,
        )
    return MongoCacheManager(db=FakeDatabase(), ttl_days=30, max_tickers=500)


def _sample_ohlcv(dates: list[date], closes: list[float]) -> pl.DataFrame:
    return pl.DataFrame({
        "Date": dates,
        "Open": closes,
        "High": [c + 1.0 for c in closes],
        "Low": [c - 1.0 for c in closes],
        "Close": closes,
        "Volume": [10000.0] * len(dates),
    })


def test_is_cache_manager_subclass(cache_manager):
    assert isinstance(cache_manager, CacheManager)


def test_cannot_instantiate_abstract_base_class():
    with pytest.raises(TypeError):
        CacheManager()  # type: ignore[abstract]


def test_from_cache_missing_ticker(cache_manager):
    df, start, end = cache_manager.from_cache("MISSING")
    assert df is None
    assert start is None
    assert end is None
    assert cache_manager.has_bars("MISSING") is False


def test_save_and_load_round_trip_with_metadata_and_date_range(cache_manager):
    sample = _sample_ohlcv(
        [date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4), date(2023, 1, 5)],
        [100.0, 102.5, 101.0, 105.0],
    )
    saved_count = cache_manager.save_bars("AAPL", sample)
    assert saved_count == 4
    assert cache_manager.has_bars("AAPL") is True

    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 6))

    loaded, start, end = cache_manager.from_cache("AAPL")
    assert loaded is not None
    assert loaded.columns == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert loaded["Date"].to_list() == [date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4), date(2023, 1, 5)]
    assert loaded["Close"].to_list() == [100.0, 102.5, 101.0, 105.0]
    assert start == date(2023, 1, 1)
    assert end == date(2023, 1, 6)

    sliced = cache_manager.get_bars("AAPL", start_date=date(2023, 1, 3), end_date=date(2023, 1, 4))
    assert sliced is not None
    assert sliced["Date"].to_list() == [date(2023, 1, 3), date(2023, 1, 4)]
    assert sliced["Close"].to_list() == [102.5, 101.0]


def test_save_bars_upserts_and_deduplicates_by_ticker_and_date(cache_manager):
    first = _sample_ohlcv([date(2023, 1, 2), date(2023, 1, 3)], [100.0, 101.0])
    second = _sample_ohlcv([date(2023, 1, 3), date(2023, 1, 4)], [101.5, 103.0])

    cache_manager.save_bars("AAPL", first)
    cache_manager.save_bars("AAPL", second)

    loaded = cache_manager.get_bars("AAPL")
    assert loaded is not None
    assert loaded["Date"].to_list() == [date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4)]
    assert loaded["Close"].to_list() == [100.0, 101.5, 103.0]


def test_save_bars_handles_empty_and_rejects_invalid_dataframes(cache_manager):
    empty_df = pl.DataFrame(schema={"Date": pl.Date, "Close": pl.Float64})
    assert cache_manager.save_bars("AAPL", empty_df) == 0

    no_date_df = pl.DataFrame({"Close": [100.0]})
    with pytest.raises(ValueError, match="Date"):
        cache_manager.save_bars("AAPL", no_date_df)

    null_date_df = pl.DataFrame({"Date": [date(2023, 1, 1), None], "Close": [100.0, 101.0]})
    with pytest.raises(ValueError, match="null"):
        cache_manager.save_bars("AAPL", null_date_df)


def test_from_cache_falls_back_to_bar_bounds_when_metadata_missing(cache_manager):
    sample = pl.DataFrame({
        "Date": [date(2023, 2, 1), date(2023, 2, 10)],
        "Close": [150.0, 155.0],
    })
    cache_manager.save_bars("MSFT", sample)

    loaded, start, end = cache_manager.from_cache("MSFT")
    assert loaded is not None
    assert start == date(2023, 2, 1)
    assert end == date(2023, 2, 10)


def test_update_cache_metadata_expands_bounds_monotonically(cache_manager):
    cache_manager.save_bars("AAPL", _sample_ohlcv([date(2023, 1, 5)], [100.0]))
    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 5), end=date(2023, 1, 10))
    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 8))
    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 4), end=date(2023, 1, 20))

    assert cache_manager.get_cache_bounds("AAPL") == (date(2023, 1, 1), date(2023, 1, 20))


def test_currency_caching_persists_preserves_case_and_clears_on_remove(cache_manager):
    assert cache_manager.get_cached_currency("AAPL") is None

    cache_manager.update_cache_metadata(" aapl ", currency=" USD ")
    assert cache_manager.get_cached_currency("AAPL") == "USD"

    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 10))
    assert cache_manager.get_cached_currency("AAPL") == "USD"
    assert cache_manager.get_cache_bounds("AAPL") == (date(2023, 1, 1), date(2023, 1, 10))

    cache_manager.update_cache_metadata("LLOY.L", currency="GBp")
    assert cache_manager.get_cached_currency("LLOY.L") == "GBp"

    cache_manager.update_cache_metadata("AAPL", currency="   ")
    assert cache_manager.get_cached_currency("AAPL") == "USD"

    cache_manager.remove_cached_ticker("AAPL")
    assert cache_manager.get_cached_currency("AAPL") is None


def test_concurrent_metadata_and_bar_updates_do_not_lose_keys(cache_manager):
    tickers = [f"TKR{i}" for i in range(8)]

    def worker(sym: str) -> None:
        for day in range(1, 11):
            d = date(2023, 1, day)
            cache_manager.save_bars(sym, _sample_ohlcv([d], [100.0 + day]))
            cache_manager.update_cache_metadata(sym, start=d, end=d)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, tickers))

    for sym in tickers:
        loaded, start, end = cache_manager.from_cache(sym)
        assert loaded is not None
        assert len(loaded) == 10
        assert start == date(2023, 1, 1)
        assert end == date(2023, 1, 10)


def test_remove_cached_ticker_deletes_bars_and_metadata(cache_manager):
    df = _sample_ohlcv([date(2023, 1, 1)], [100.0])
    cache_manager.save_bars("AAPL", df)
    cache_manager.save_bars("MSFT", df)
    cache_manager.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 2))
    cache_manager.update_cache_metadata("MSFT", start=date(2023, 1, 1), end=date(2023, 1, 2))

    cache_manager.remove_cached_ticker("AAPL")

    assert cache_manager.has_bars("AAPL") is False
    assert cache_manager.get_cache_bounds("AAPL") == (None, None)
    assert cache_manager.has_bars("MSFT") is True
    assert cache_manager.get_cache_bounds("MSFT") == (date(2023, 1, 1), date(2023, 1, 2))


@pytest.mark.parametrize(
    "bad_ticker",
    [
        "",
        "   ",
        ".",
        "..",
        "A..B",
        ".AAPL",
        "AAPL.",
        "../../target",
        "..\\target",
        "BRK/B",
        "NASDAQ:AAPL",
        "AAPL*",
        "AAPL?",
        "A" * 13,
    ],
)
def test_invalid_and_traversal_tickers_raise_value_error(cache_manager, bad_ticker):
    df = _sample_ohlcv([date(2023, 1, 1)], [100.0])

    with pytest.raises(ValueError):
        cache_manager.from_cache(bad_ticker)
    with pytest.raises(ValueError):
        cache_manager.get_bars(bad_ticker)
    with pytest.raises(ValueError):
        cache_manager.save_bars(bad_ticker, df)
    with pytest.raises(ValueError):
        cache_manager.get_cache_bounds(bad_ticker)
    with pytest.raises(ValueError):
        cache_manager.get_cached_currency(bad_ticker)
    with pytest.raises(ValueError):
        cache_manager.update_cache_metadata(bad_ticker, start=date(2023, 1, 1), end=date(2023, 1, 2))
    with pytest.raises(ValueError):
        cache_manager.remove_cached_ticker(bad_ticker)


@pytest.mark.parametrize(
    "ticker",
    [
        " aapl ",
        "^irx",
        "USDEUR=X",
        "BRK.B",
        "BRK-B",
        "CON",
        "NUL",
        "PRN",
        "COM1",
        "LPT1",
        "CON.DE",
    ],
)
def test_round_trip_for_special_and_reserved_tickers(cache_manager, ticker):
    sample = pl.DataFrame({"Date": [date(2023, 3, 1)], "Close": [42.0]})
    cache_manager.save_bars(ticker, sample)
    cache_manager.update_cache_metadata(ticker, start=date(2023, 3, 1), end=date(2023, 3, 2))

    loaded, start, end = cache_manager.from_cache(ticker)
    assert loaded is not None
    assert loaded["Close"].to_list() == [42.0]
    assert start == date(2023, 3, 1)
    assert end == date(2023, 3, 2)

    cache_manager.remove_cached_ticker(ticker)
    assert cache_manager.has_bars(ticker) is False


def test_create_cache_manager_selection(monkeypatch, tmp_path):
    monkeypatch.delenv("CACHE_BACKEND", raising=False)
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.delenv("MONGO_URI", raising=False)

    auto_local = create_cache_manager(storage_path=str(tmp_path / "auto_local"))
    assert isinstance(auto_local, LocalCacheManager)

    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://user:pass@example.mongodb.net/")
    auto_mongo = create_cache_manager()
    assert isinstance(auto_mongo, MongoCacheManager)

    monkeypatch.setenv("CACHE_BACKEND", "local")
    forced_local = create_cache_manager(storage_path=str(tmp_path / "forced_local"))
    assert isinstance(forced_local, LocalCacheManager)

    explicit_mongo = create_cache_manager(backend="mongo", db=FakeDatabase())
    assert isinstance(explicit_mongo, MongoCacheManager)

    with pytest.raises(ValueError, match="Unknown cache backend"):
        create_cache_manager(backend="redis")


def test_local_init_creates_storage_directory(cache_dir):
    assert not cache_dir.exists()
    cm = LocalCacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
    )
    assert cache_dir.is_dir()
    assert cm.ticker_path("AAPL") == os.path.join(str(cache_dir.resolve()), "AAPL.csv")


@pytest.mark.parametrize(
    "ticker,expected_filename",
    [
        (" aapl ", "AAPL.csv"),
        ("^irx", "%5EIRX.csv"),
        ("USDEUR=X", "USDEUR%3DX.csv"),
        ("BRK.B", "BRK.B.csv"),
        ("BRK-B", "BRK-B.csv"),
        ("CON", "%43ON.csv"),
        ("NUL", "%4EUL.csv"),
        ("PRN", "%50RN.csv"),
        ("COM1", "%43OM1.csv"),
        ("LPT1", "%4CPT1.csv"),
        ("CON.DE", "%43ON.DE.csv"),
    ],
)
def test_local_safe_filename_encoding(local_cache, cache_dir, ticker, expected_filename):
    assert local_cache.ticker_path(ticker) == str((cache_dir / expected_filename).resolve())


def test_local_handles_corrupted_csv_and_missing_date_column(local_cache, cache_dir):
    (cache_dir / "EMPTY.csv").write_text("", encoding="utf-8")
    assert local_cache.from_cache("EMPTY") == (None, None, None)

    (cache_dir / "BADDATE.csv").write_text("Date,Close\nnot-a-date,100.0\n", encoding="utf-8")
    assert local_cache.from_cache("BADDATE") == (None, None, None)

    (cache_dir / "NODATE.csv").write_text("Ticker,Close\nAAPL,100.0\n", encoding="utf-8")
    assert local_cache.from_cache("NODATE") == (None, None, None)


def test_local_corrupted_metadata_json_recovery_and_no_tmp_leftovers(local_cache, cache_dir):
    meta_path = cache_dir / "cache_metadata.json"
    meta_path.write_text("{corrupted json!!!", encoding="utf-8")

    assert local_cache.get_cache_bounds("AAPL") == (None, None)

    local_cache.save_bars("AAPL", _sample_ohlcv([date(2023, 1, 1)], [100.0]))
    local_cache.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 10))
    recovered = json.loads(meta_path.read_text(encoding="utf-8"))
    assert recovered["AAPL"]["start"] == "2023-01-01"
    assert recovered["AAPL"]["end"] == "2023-01-10"
    assert "last_accessed" in recovered["AAPL"]

    tmp_files = list(cache_dir.glob("*.tmp"))
    assert tmp_files == []


def test_local_lifecycle_evicts_expired_corrupted_and_protects_outside_files(local_cache, cache_dir, tmp_path):
    outside = tmp_path / "escaped.csv"
    outside.write_text("safe", encoding="utf-8")

    df = _sample_ohlcv([date(2023, 1, 1)], [100.0])
    for sym in ("EXPIRED", "FRESH", "CORRUPT_TS"):
        local_cache.save_bars(sym, df)

    old_ts = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    fresh_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    metadata = {
        "EXPIRED": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": old_ts},
        "FRESH": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": fresh_ts},
        "CORRUPT_TS": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": "bad-timestamp"},
        "../escaped": {"start": "2023-01-01", "end": "2023-01-02", "last_accessed": old_ts},
    }
    (cache_dir / "cache_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    evicted = local_cache.enforce_cache_lifecycle()

    assert set(evicted) == {"EXPIRED", "CORRUPT_TS", "../escaped"}
    assert outside.read_text(encoding="utf-8") == "safe"
    assert not (cache_dir / "EXPIRED.csv").exists()
    assert not (cache_dir / "CORRUPT_TS.csv").exists()
    assert (cache_dir / "FRESH.csv").exists()
    remaining = json.loads((cache_dir / "cache_metadata.json").read_text(encoding="utf-8"))
    assert list(remaining.keys()) == ["FRESH"]


def test_local_lifecycle_enforces_lru_max_tickers_and_max_cache_bytes(cache_dir):
    cm = LocalCacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
        ttl_days=30,
        max_tickers=2,
        max_cache_bytes=None,
    )
    df = _sample_ohlcv([date(2023, 1, 1)], [100.0])
    now = datetime.now(timezone.utc)
    meta = {}
    for idx, sym in enumerate(("OLDEST", "MIDDLE", "NEWEST", "LATEST")):
        cm.save_bars(sym, df)
        meta[sym] = {
            "start": "2023-01-01",
            "end": "2023-01-02",
            "last_accessed": (now - timedelta(hours=10 - idx)).isoformat(),
        }
    (cache_dir / "cache_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    evicted = cm.enforce_cache_lifecycle()
    assert evicted == ["OLDEST", "MIDDLE"]
    assert cm.has_bars("NEWEST") is True
    assert cm.has_bars("LATEST") is True

    single_size = os.path.getsize(cm.ticker_path("LATEST"))
    cm_bytes = LocalCacheManager(
        storage_path=str(cache_dir),
        metadata_file=str(cache_dir / "cache_metadata.json"),
        ttl_days=30,
        max_tickers=100,
        max_cache_bytes=single_size + 5,
    )
    evicted_by_bytes = cm_bytes.enforce_cache_lifecycle()
    assert evicted_by_bytes == ["NEWEST"]
    assert cm_bytes.has_bars("NEWEST") is False
    assert cm_bytes.has_bars("LATEST") is True


def test_mongo_init_is_lazy_and_missing_uri_raises_on_first_use(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.delenv("MONGO_URI", raising=False)

    cm = MongoCacheManager()
    with pytest.raises(RuntimeError, match="MONGODB_URI"):
        cm.get_cache_bounds("AAPL")


def test_invalid_ttl_days_raises_value_error(fake_db, cache_dir):
    with pytest.raises(ValueError, match="ttl_days"):
        MongoCacheManager(db=fake_db, ttl_days=0)
    with pytest.raises(ValueError, match="ttl_days"):
        LocalCacheManager(storage_path=str(cache_dir), ttl_days=0)


def test_mongo_shared_client_is_reused_for_same_uri():
    close_cached_clients()
    mock_client = MagicMock()
    mock_db = FakeDatabase("shared_db")
    mock_client.__getitem__.return_value = mock_db

    with patch.object(cache_manager_module, "MongoClient", return_value=mock_client) as client_cls:
        cm1 = MongoCacheManager(mongo_uri="mongodb+srv://user:pass@example.mongodb.net/", db_name="shared_db")
        cm2 = MongoCacheManager(mongo_uri="mongodb+srv://user:pass@example.mongodb.net/", db_name="shared_db")

        assert cm1.get_cache_bounds("AAPL") == (None, None)
        assert cm2.get_cache_bounds("MSFT") == (None, None)
        assert client_cls.call_count == 1

    close_cached_clients()
    mock_client.close.assert_called_once()


def test_mongo_indexes_created_and_ttl_conflict_is_tolerated(fake_db):
    cm = MongoCacheManager(db=fake_db, ttl_days=30)
    assert cm.from_cache("MISSING") == (None, None, None)

    bars_indexes = fake_db[BARS_COLLECTION].index_information()
    meta_indexes = fake_db[METADATA_COLLECTION].index_information()

    assert bars_indexes["ticker_date_unique"] == {
        "key": [("ticker", 1), ("Date", 1)],
        "unique": True,
    }
    assert bars_indexes["bars_ttl"] == {
        "key": [("last_accessed", 1)],
        "expireAfterSeconds": 30 * 86400,
    }
    assert meta_indexes["metadata_ttl"] == {
        "key": [("last_accessed", 1)],
        "expireAfterSeconds": 30 * 86400,
    }

    cache_manager_module._INDEXED_DBS.clear()
    cm_new_ttl = MongoCacheManager(db=fake_db, ttl_days=15)
    assert cm_new_ttl.get_cache_bounds("MISSING") == (None, None)


def test_mongo_handles_corrupted_bar_and_metadata_documents(mongo_cache, fake_db):
    fake_db[BARS_COLLECTION].insert_one({"ticker": "BADDATE", "Date": "not-a-date", "Close": 100.0})
    assert mongo_cache.from_cache("BADDATE") == (None, None, None)

    fake_db[BARS_COLLECTION].insert_one({"ticker": "NODATE", "Close": 100.0})
    assert mongo_cache.from_cache("NODATE") == (None, None, None)

    fake_db[METADATA_COLLECTION].insert_one({
        "_id": "AAPL",
        "ticker": "AAPL",
        "start": "not-a-date",
        "end": None,
        "last_accessed": "bad-ts",
    })
    assert mongo_cache.get_cache_bounds("AAPL") == (None, None)

    mongo_cache.update_cache_metadata("AAPL", start=date(2023, 1, 1), end=date(2023, 1, 10))
    assert mongo_cache.get_cache_bounds("AAPL") == (date(2023, 1, 1), date(2023, 1, 10))


def test_mongo_throttles_bar_ttl_touches(mongo_cache, fake_db):
    mongo_cache.save_bars("AAPL", _sample_ohlcv([date(2023, 1, 5)], [100.0]))
    mongo_cache.update_cache_metadata("AAPL", start=date(2023, 1, 5), end=date(2023, 1, 10))
    mongo_cache.update_cache_metadata("AAPL")
    assert fake_db[BARS_COLLECTION].update_many_calls == 0

    old_ts = datetime.now(timezone.utc) - timedelta(days=5)
    fake_db[METADATA_COLLECTION].update_one({"_id": "AAPL"}, {"$set": {"last_accessed": old_ts}})
    mongo_cache.update_cache_metadata("AAPL")
    assert fake_db[BARS_COLLECTION].update_many_calls == 1


def test_mongo_lifecycle_enforces_lru_max_tickers_only(fake_db):
    cm = MongoCacheManager(db=fake_db, ttl_days=30, max_tickers=2)
    df = _sample_ohlcv([date(2023, 1, 1)], [100.0])
    now = datetime.now(timezone.utc)

    for idx, sym in enumerate(("OLDEST", "MIDDLE", "LATEST")):
        cm.save_bars(sym, df)
        fake_db[METADATA_COLLECTION].insert_one({
            "_id": sym,
            "ticker": sym,
            "last_accessed": now - timedelta(hours=5 - idx),
        })

    evicted = cm.enforce_cache_lifecycle()

    assert evicted == ["OLDEST"]
    assert cm.has_bars("OLDEST") is False
    assert cm.has_bars("MIDDLE") is True
    assert cm.has_bars("LATEST") is True
    assert fake_db[METADATA_COLLECTION].count_documents({}) == 2

    # When within max_tickers, enforce_cache_lifecycle does not scan/evict by TTL (delegated to MongoDB).
    fake_db[METADATA_COLLECTION].update_one(
        {"_id": "MIDDLE"},
        {"$set": {"last_accessed": now - timedelta(days=60)}},
    )
    assert cm.enforce_cache_lifecycle() == []
    assert cm.has_bars("MIDDLE") is True
