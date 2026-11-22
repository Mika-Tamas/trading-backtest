from __future__ import annotations

from abc import ABC, abstractmethod
import atexit
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any
from urllib.parse import quote

from dotenv import load_dotenv
import polars as pl
from pymongo import ASCENDING, MongoClient, ReturnDocument, UpdateOne
from pymongo.errors import OperationFailure

from schemas import normalize_ticker

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)
load_dotenv(_BACKEND_DIR / ".env", override=False)

DEFAULT_DB_NAME = "trading_backtest"
BARS_COLLECTION = "ticker_bars"
METADATA_COLLECTION = "ticker_metadata"
DEFAULT_TTL_DAYS = 30
DEFAULT_MAX_TICKERS = 500
DEFAULT_MAX_CACHE_BYTES = 256 * 1024 * 1024
BAR_TOUCH_INTERVAL = timedelta(hours=24)
BULK_WRITE_BATCH_SIZE = 1000
STANDARD_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")

WINDOWS_RESERVED_NAMES = frozenset({
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(10)),
    *(f"LPT{i}" for i in range(10)),
})

_CLIENT_LOCK = threading.Lock()
_CLIENTS: dict[str, MongoClient] = {}
_INDEXED_DBS: set[tuple[int, str]] = set()
_INDEX_LOCK = threading.Lock()

_LOCAL_LOCKS_GUARD = threading.Lock()
_LOCAL_DIR_LOCKS: dict[Path, threading.RLock] = {}


def _get_local_dir_lock(storage_root: Path) -> threading.RLock:
    with _LOCAL_LOCKS_GUARD:
        lock = _LOCAL_DIR_LOCKS.get(storage_root)
        if lock is None:
            lock = threading.RLock()
            _LOCAL_DIR_LOCKS[storage_root] = lock
        return lock


def _get_shared_client(mongo_uri: str) -> MongoClient:
    with _CLIENT_LOCK:
        client = _CLIENTS.get(mongo_uri)
        if client is None:
            client = MongoClient(
                mongo_uri,
                tz_aware=True,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
            _CLIENTS[mongo_uri] = client
        return client


def close_cached_clients() -> None:
    """Close all shared MongoClient instances and clear index tracking."""
    with _CLIENT_LOCK:
        clients = list(_CLIENTS.values())
        _CLIENTS.clear()
    with _INDEX_LOCK:
        _INDEXED_DBS.clear()
    for client in clients:
        try:
            client.close()
        except Exception:
            pass


atexit.register(close_cached_clients)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_iso_date(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return date.fromisoformat(value.strip()).isoformat()
    raise ValueError(f"Unsupported date value: {value!r}")


def _parse_optional_iso_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


def _normalize_currency(value: Any) -> str | None:
    """Strip non-empty currency codes while preserving case (e.g. 'USD', 'GBp')."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _parse_int_env(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def _atomic_write_csv(path: Path, df: pl.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            df.write_csv(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


class CacheManager(ABC):
    """Abstract base class for polymorphic market-data cache backends."""

    def __init__(
        self,
        ttl_days: int | None = None,
        max_tickers: int | None = DEFAULT_MAX_TICKERS,
    ):
        if ttl_days is None:
            env_ttl = _parse_int_env("CACHE_TTL_DAYS", DEFAULT_TTL_DAYS)
            ttl_days = env_ttl if (env_ttl is not None and env_ttl > 0) else DEFAULT_TTL_DAYS
        if ttl_days <= 0:
            raise ValueError("ttl_days must be a positive integer.")
        self.ttl_days = ttl_days
        self.ttl_seconds = ttl_days * 86400

        if max_tickers is DEFAULT_MAX_TICKERS:
            env_max = _parse_int_env("CACHE_MAX_TICKERS", DEFAULT_MAX_TICKERS)
            max_tickers = env_max if (env_max is None or env_max > 0) else None
        elif max_tickers is not None and max_tickers <= 0:
            max_tickers = None
        self.max_tickers = max_tickers

    @staticmethod
    def _validate_bars_df(df: pl.DataFrame) -> None:
        if "Date" not in df.columns:
            raise ValueError("DataFrame must contain a 'Date' column.")
        if df["Date"].null_count() > 0:
            raise ValueError("DataFrame contains null values in 'Date'.")

    @staticmethod
    def _normalize_bars_df(df: pl.DataFrame) -> pl.DataFrame | None:
        try:
            if df.is_empty() or "Date" not in df.columns:
                return None

            if df.schema["Date"] != pl.Date:
                df = df.with_columns(
                    pl.col("Date").cast(pl.Utf8).str.to_date("%Y-%m-%d", strict=False)
                )
            if df["Date"].null_count() > 0:
                return None

            ordered_cols = ["Date"]
            for col in STANDARD_OHLCV_COLUMNS:
                if col in df.columns:
                    ordered_cols.append(col)
            remaining = sorted(set(df.columns) - set(ordered_cols))
            ordered_cols.extend(remaining)
            df = df.select(ordered_cols)

            float_casts = [
                pl.col(col).cast(pl.Float64)
                for col in STANDARD_OHLCV_COLUMNS
                if col in df.columns
            ]
            if float_casts:
                df = df.with_columns(float_casts)

            return df.sort("Date")
        except Exception:
            return None

    def from_cache(
        self,
        ticker: str,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
    ) -> tuple[pl.DataFrame | None, date | None, date | None]:
        normalized = normalize_ticker(ticker)
        data = self.get_bars(normalized, start_date=start_date, end_date=end_date)
        if data is None or data.is_empty():
            return None, None, None

        start, end = self.get_cache_bounds(normalized)
        if start is None or end is None:
            start = data["Date"].min()
            end = data["Date"].max()

        return data, start, end

    @abstractmethod
    def has_bars(self, ticker: str) -> bool:
        """Return True if at least one cached bar exists for ticker."""

    @abstractmethod
    def get_bars(
        self,
        ticker: str,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
    ) -> pl.DataFrame | None:
        """Load cached bars for ticker, optionally filtered to [start_date, end_date]."""

    @abstractmethod
    def save_bars(self, ticker: str, df: pl.DataFrame) -> int:
        """Upsert bars for ticker (merging by Date) and return number of bars written."""

    @abstractmethod
    def get_cache_bounds(self, ticker: str) -> tuple[date | None, date | None]:
        """Return cached (start, end) date bounds from metadata, or (None, None)."""

    @abstractmethod
    def get_cached_currency(self, ticker: str) -> str | None:
        """Return cached native currency code for ticker, or None if not cached."""

    @abstractmethod
    def update_cache_metadata(
        self,
        ticker: str,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        currency: str | None = None,
    ) -> None:
        """Atomically expand metadata bounds, optionally store currency, and refresh last_accessed."""

    @abstractmethod
    def remove_cached_ticker(self, ticker: str) -> None:
        """Remove all cached bars and metadata for ticker."""

    @abstractmethod
    def enforce_cache_lifecycle(self, cutoff_date: datetime | None = None) -> list[str]:
        """Evict expired/corrupted entries and enforce capacity limits; return evicted keys."""


class LocalCacheManager(CacheManager):
    """Thread-safe, atomic local CSV + JSON metadata cache implementation."""

    def __init__(
        self,
        storage_path: str | None = None,
        metadata_file: str | None = None,
        ttl_days: int | None = None,
        max_tickers: int | None = DEFAULT_MAX_TICKERS,
        max_cache_bytes: int | None = DEFAULT_MAX_CACHE_BYTES,
    ):
        super().__init__(ttl_days=ttl_days, max_tickers=max_tickers)

        if max_cache_bytes is DEFAULT_MAX_CACHE_BYTES:
            env_bytes = _parse_int_env("CACHE_MAX_BYTES", DEFAULT_MAX_CACHE_BYTES)
            max_cache_bytes = env_bytes if (env_bytes is None or env_bytes > 0) else None
        elif max_cache_bytes is not None and max_cache_bytes <= 0:
            max_cache_bytes = None
        self.max_cache_bytes = max_cache_bytes

        if storage_path is None and metadata_file is None:
            try:
                config_path = _PROJECT_ROOT / "config.json"
                with open(config_path, "r", encoding="utf-8") as cfg:
                    config_data = json.load(cfg)
                    configured_dir = config_data["paths"]["stored_tickers"]
                    resolved_dir = Path(configured_dir)
                    if not resolved_dir.is_absolute():
                        resolved_dir = (_BACKEND_DIR / resolved_dir).resolve()
                    storage_path = str(resolved_dir)
                    metadata_file = os.path.join(storage_path, "cache_metadata.json")
            except Exception:
                print("Config not found. Loading default file paths...")

        if storage_path is None:
            storage_path = str((_BACKEND_DIR / "data").resolve())
        if metadata_file is None:
            metadata_file = os.path.join(storage_path, "cache_metadata.json")

        os.makedirs(storage_path, exist_ok=True)
        self.storage_path = storage_path
        self.storage_root = Path(storage_path).resolve()
        self.metadata_path = metadata_file
        self._lock = _get_local_dir_lock(self.storage_root)

    @staticmethod
    def _safe_cache_filename(ticker: str) -> str:
        normalized = normalize_ticker(ticker)
        encoded = quote(normalized, safe="._-")
        stem = normalized.split(".", 1)[0]
        if stem in WINDOWS_RESERVED_NAMES:
            encoded = f"%{ord(encoded[0]):02X}{encoded[1:]}"
        return f"{encoded}.csv"

    def ticker_path(self, ticker: str) -> str:
        filename = self._safe_cache_filename(ticker)
        resolved = (self.storage_root / filename).resolve()
        if not resolved.is_relative_to(self.storage_root):
            raise ValueError(f"Resolved cache path escapes storage root for ticker: {ticker!r}")
        return str(resolved)

    def _load_metadata_unlocked(self) -> dict[str, Any]:
        if not os.path.exists(self.metadata_path):
            return {}
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError, ValueError):
            return {}

    def _save_metadata_unlocked(self, metadata: dict[str, Any]) -> None:
        _atomic_write_text(Path(self.metadata_path), json.dumps(metadata, indent=4))

    def has_bars(self, ticker: str) -> bool:
        normalized = normalize_ticker(ticker)
        path = self.ticker_path(normalized)
        with self._lock:
            return os.path.exists(path) and os.path.getsize(path) > 0

    def get_bars(
        self,
        ticker: str,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
    ) -> pl.DataFrame | None:
        normalized = normalize_ticker(ticker)
        start_dt = date.fromisoformat(_to_iso_date(start_date)) if start_date is not None else None
        end_dt = date.fromisoformat(_to_iso_date(end_date)) if end_date is not None else None
        path = self.ticker_path(normalized)

        with self._lock:
            if not os.path.exists(path):
                return None
            try:
                raw_df = pl.read_csv(path)
            except Exception:
                return None

        data = self._normalize_bars_df(raw_df)
        if data is None:
            return None

        if start_dt is not None:
            data = data.filter(pl.col("Date") >= start_dt)
        if end_dt is not None:
            data = data.filter(pl.col("Date") <= end_dt)

        return None if data.is_empty() else data

    def save_bars(self, ticker: str, df: pl.DataFrame) -> int:
        normalized = normalize_ticker(ticker)
        self._validate_bars_df(df)
        if df.is_empty():
            return 0

        incoming = self._normalize_bars_df(df)
        if incoming is None or incoming.is_empty():
            raise ValueError("DataFrame contains invalid values in 'Date'.")

        path = Path(self.ticker_path(normalized))
        with self._lock:
            existing: pl.DataFrame | None = None
            if path.exists():
                try:
                    existing = self._normalize_bars_df(pl.read_csv(path))
                except Exception:
                    existing = None

            if existing is not None and not existing.is_empty():
                merged = (
                    pl.concat([existing, incoming], how="diagonal_relaxed")
                    .unique(subset=["Date"], keep="last")
                    .sort("Date")
                )
            else:
                merged = incoming.unique(subset=["Date"], keep="last").sort("Date")

            merged = self._normalize_bars_df(merged)
            if merged is None:
                raise ValueError("Failed to normalize bars DataFrame before saving.")

            _atomic_write_csv(path, merged)

        return len(incoming)

    def get_cache_bounds(self, ticker: str) -> tuple[date | None, date | None]:
        normalized = normalize_ticker(ticker)
        with self._lock:
            metadata = self._load_metadata_unlocked()
        try:
            entry = metadata[normalized]
            start = date.fromisoformat(entry["start"])
            end = date.fromisoformat(entry["end"])
            return start, end
        except Exception:
            return None, None

    def get_cached_currency(self, ticker: str) -> str | None:
        normalized = normalize_ticker(ticker)
        with self._lock:
            metadata = self._load_metadata_unlocked()
        entry = metadata.get(normalized)
        if not isinstance(entry, dict):
            return None
        return _normalize_currency(entry.get("currency"))

    def update_cache_metadata(
        self,
        ticker: str,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        currency: str | None = None,
    ) -> None:
        normalized = normalize_ticker(ticker)
        start_iso = _to_iso_date(start) if start is not None else None
        end_iso = _to_iso_date(end) if end is not None else None
        normalized_currency = _normalize_currency(currency)
        now_iso = _utc_now().isoformat()

        with self._lock:
            cached = self._load_metadata_unlocked()
            ticker_data = cached.get(normalized, {})
            if not isinstance(ticker_data, dict):
                ticker_data = {}

            if start_iso is not None:
                existing_start = _parse_optional_iso_date(ticker_data.get("start"))
                ticker_data["start"] = (
                    min(existing_start, start_iso) if existing_start is not None else start_iso
                )
            if end_iso is not None:
                existing_end = _parse_optional_iso_date(ticker_data.get("end"))
                ticker_data["end"] = (
                    max(existing_end, end_iso) if existing_end is not None else end_iso
                )
            if normalized_currency is not None:
                ticker_data["currency"] = normalized_currency

            ticker_data["last_accessed"] = now_iso
            cached[normalized] = ticker_data
            self._save_metadata_unlocked(cached)

    def remove_cached_ticker(self, ticker: str) -> None:
        normalized = normalize_ticker(ticker)
        path = self.ticker_path(normalized)
        with self._lock:
            if os.path.exists(path):
                os.remove(path)
            cached = self._load_metadata_unlocked()
            if normalized in cached:
                cached.pop(normalized)
                self._save_metadata_unlocked(cached)

    def _safe_delete_csv_unlocked(self, raw_key: str) -> int:
        try:
            path = self.ticker_path(raw_key)
        except ValueError:
            return 0
        if os.path.exists(path):
            try:
                size = os.path.getsize(path)
                os.remove(path)
                return size
            except OSError:
                return 0
        return 0

    def _safe_csv_size_unlocked(self, raw_key: str) -> int:
        try:
            path = self.ticker_path(raw_key)
        except ValueError:
            return 0
        if os.path.exists(path):
            try:
                return os.path.getsize(path)
            except OSError:
                return 0
        return 0

    def enforce_cache_lifecycle(self, cutoff_date: datetime | None = None) -> list[str]:
        cutoff = _utc_now() - timedelta(days=self.ttl_days) if cutoff_date is None else _as_utc(cutoff_date)
        evicted: list[str] = []

        with self._lock:
            metadata = self._load_metadata_unlocked()
            if not metadata:
                return evicted

            parsed_access_times: dict[str, datetime] = {}

            for raw_key, data in list(metadata.items()):
                is_valid_key = True
                try:
                    normalize_ticker(raw_key)
                except ValueError:
                    is_valid_key = False

                is_expired = False
                parsed_ts: datetime | None = None
                if not isinstance(data, dict):
                    is_expired = True
                else:
                    raw_ts = data.get("last_accessed")
                    if isinstance(raw_ts, str):
                        try:
                            parsed_ts = _as_utc(datetime.fromisoformat(raw_ts))
                            is_expired = parsed_ts < cutoff
                        except ValueError:
                            is_expired = True
                    else:
                        is_expired = True

                if is_expired or not is_valid_key:
                    if is_valid_key:
                        self._safe_delete_csv_unlocked(raw_key)
                    metadata.pop(raw_key, None)
                    evicted.append(str(raw_key))
                elif parsed_ts is not None:
                    parsed_access_times[raw_key] = parsed_ts

            if self.max_tickers is not None and self.max_tickers > 0:
                excess = len(metadata) - self.max_tickers
                if excess > 0:
                    oldest_keys = sorted(
                        metadata.keys(),
                        key=lambda k: parsed_access_times.get(k, datetime.min.replace(tzinfo=timezone.utc)),
                    )[:excess]
                    for key in oldest_keys:
                        self._safe_delete_csv_unlocked(key)
                        metadata.pop(key, None)
                        parsed_access_times.pop(key, None)
                        evicted.append(str(key))

            if self.max_cache_bytes is not None and self.max_cache_bytes > 0 and metadata:
                sizes = {key: self._safe_csv_size_unlocked(key) for key in metadata}
                total_bytes = sum(sizes.values())
                if total_bytes > self.max_cache_bytes:
                    lru_order = sorted(
                        metadata.keys(),
                        key=lambda k: parsed_access_times.get(k, datetime.min.replace(tzinfo=timezone.utc)),
                    )
                    for key in lru_order:
                        if total_bytes <= self.max_cache_bytes:
                            break
                        self._safe_delete_csv_unlocked(key)
                        metadata.pop(key, None)
                        total_bytes -= sizes.get(key, 0)
                        evicted.append(str(key))

            if evicted:
                self._save_metadata_unlocked(metadata)

        return evicted


class MongoCacheManager(CacheManager):
    """MongoDB-backed market data cache with atomic upserts, TTL, and LRU eviction."""

    def __init__(
        self,
        mongo_uri: str | None = None,
        db_name: str | None = None,
        db: Any = None,
        ttl_days: int | None = None,
        max_tickers: int | None = DEFAULT_MAX_TICKERS,
    ):
        super().__init__(ttl_days=ttl_days, max_tickers=max_tickers)
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._db = db
        self._indexes_ready = False

    def _get_db(self) -> Any:
        if self._db is not None:
            return self._db

        uri = self._mongo_uri
        if uri is None:
            uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        if not uri or not uri.strip():
            raise RuntimeError(
                "MONGODB_URI environment variable is not set. "
                "Set MONGODB_URI in your environment or .env file."
            )

        db_name = self._db_name or os.getenv("MONGODB_DB_NAME") or DEFAULT_DB_NAME
        client = _get_shared_client(uri.strip())
        self._db = client[db_name]
        return self._db

    def _ensure_indexes(self, db: Any) -> None:
        if self._indexes_ready:
            return

        db_key = (id(db), getattr(db, "name", ""))
        with _INDEX_LOCK:
            if db_key in _INDEXED_DBS:
                self._indexes_ready = True
                return

            bars_col = db[BARS_COLLECTION]
            meta_col = db[METADATA_COLLECTION]

            bars_col.create_index(
                [("ticker", ASCENDING), ("Date", ASCENDING)],
                unique=True,
                name="ticker_date_unique",
            )
            self._ensure_ttl_index(bars_col, "bars_ttl")
            self._ensure_ttl_index(meta_col, "metadata_ttl")

            _INDEXED_DBS.add(db_key)
            self._indexes_ready = True

    def _ensure_ttl_index(self, collection: Any, index_name: str) -> None:
        try:
            collection.create_index(
                [("last_accessed", ASCENDING)],
                expireAfterSeconds=self.ttl_seconds,
                name=index_name,
            )
        except OperationFailure as exc:
            # IndexOptionsConflict (code 85) if TTL changed on an existing index.
            if getattr(exc, "code", None) != 85:
                raise

    def _collections(self) -> tuple[Any, Any]:
        db = self._get_db()
        self._ensure_indexes(db)
        return db[BARS_COLLECTION], db[METADATA_COLLECTION]

    def has_bars(self, ticker: str) -> bool:
        normalized = normalize_ticker(ticker)
        bars_col, _ = self._collections()
        return bars_col.find_one({"ticker": normalized}, {"_id": 1}) is not None

    def get_bars(
        self,
        ticker: str,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
    ) -> pl.DataFrame | None:
        normalized = normalize_ticker(ticker)
        bars_col, _ = self._collections()

        query: dict[str, Any] = {"ticker": normalized}
        if start_date is not None or end_date is not None:
            date_filter: dict[str, str] = {}
            if start_date is not None:
                date_filter["$gte"] = _to_iso_date(start_date)
            if end_date is not None:
                date_filter["$lte"] = _to_iso_date(end_date)
            query["Date"] = date_filter

        projection = {"_id": 0, "ticker": 0, "last_accessed": 0}
        docs = list(bars_col.find(query, projection).sort("Date", ASCENDING))
        if not docs:
            return None

        return self._docs_to_polars(docs)

    @classmethod
    def _docs_to_polars(cls, docs: list[dict[str, Any]]) -> pl.DataFrame | None:
        try:
            all_keys: set[str] = set()
            for doc in docs:
                all_keys.update(doc.keys())

            if "Date" not in all_keys:
                return None

            columnar: dict[str, list[Any]] = {col: [] for col in all_keys}
            for doc in docs:
                for col in all_keys:
                    columnar[col].append(doc.get(col))

            return cls._normalize_bars_df(pl.DataFrame(columnar))
        except Exception:
            return None

    def save_bars(self, ticker: str, df: pl.DataFrame) -> int:
        normalized = normalize_ticker(ticker)
        self._validate_bars_df(df)
        if df.is_empty():
            return 0

        bars_col, _ = self._collections()
        now = _utc_now()

        operations: list[UpdateOne] = []
        for row in df.iter_rows(named=True):
            date_iso = _to_iso_date(row["Date"])
            doc: dict[str, Any] = {
                "ticker": normalized,
                "Date": date_iso,
                "last_accessed": now,
            }
            for col, val in row.items():
                if col in ("Date", "_id", "ticker", "last_accessed"):
                    continue
                if col in STANDARD_OHLCV_COLUMNS and val is not None:
                    doc[col] = float(val)
                else:
                    doc[col] = val

            operations.append(
                UpdateOne(
                    {"ticker": normalized, "Date": date_iso},
                    {"$set": doc},
                    upsert=True,
                )
            )

        for i in range(0, len(operations), BULK_WRITE_BATCH_SIZE):
            batch = operations[i : i + BULK_WRITE_BATCH_SIZE]
            bars_col.bulk_write(batch, ordered=False)

        return len(operations)

    def get_cache_bounds(self, ticker: str) -> tuple[date | None, date | None]:
        normalized = normalize_ticker(ticker)
        _, meta_col = self._collections()
        try:
            doc = meta_col.find_one({"_id": normalized})
            if not isinstance(doc, dict):
                return None, None
            start = date.fromisoformat(doc["start"])
            end = date.fromisoformat(doc["end"])
            return start, end
        except Exception:
            return None, None

    def get_cached_currency(self, ticker: str) -> str | None:
        normalized = normalize_ticker(ticker)
        _, meta_col = self._collections()
        try:
            doc = meta_col.find_one({"_id": normalized}, {"currency": 1})
            if not isinstance(doc, dict):
                return None
            return _normalize_currency(doc.get("currency"))
        except Exception:
            return None

    def update_cache_metadata(
        self,
        ticker: str,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        currency: str | None = None,
    ) -> None:
        normalized = normalize_ticker(ticker)
        bars_col, meta_col = self._collections()
        now = _utc_now()

        set_fields: dict[str, Any] = {
            "ticker": normalized,
            "last_accessed": now,
        }
        normalized_currency = _normalize_currency(currency)
        if normalized_currency is not None:
            set_fields["currency"] = normalized_currency

        update_doc: dict[str, Any] = {"$set": set_fields}
        if start is not None:
            update_doc["$min"] = {"start": _to_iso_date(start)}
        if end is not None:
            update_doc["$max"] = {"end": _to_iso_date(end)}

        prev = meta_col.find_one_and_update(
            {"_id": normalized},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.BEFORE,
        )

        # Keep bar TTL fresh without hitting update_many on every single read.
        should_touch_bars = False
        if isinstance(prev, dict):
            prev_ts = prev.get("last_accessed")
            if not isinstance(prev_ts, datetime):
                should_touch_bars = True
            elif (now - _as_utc(prev_ts)) >= BAR_TOUCH_INTERVAL:
                should_touch_bars = True

        if should_touch_bars:
            bars_col.update_many(
                {"ticker": normalized},
                {"$set": {"last_accessed": now}},
            )

    def remove_cached_ticker(self, ticker: str) -> None:
        normalized = normalize_ticker(ticker)
        bars_col, meta_col = self._collections()
        bars_col.delete_many({"ticker": normalized})
        meta_col.delete_one({"_id": normalized})

    def enforce_cache_lifecycle(self, cutoff_date: datetime | None = None) -> list[str]:
        if self.max_tickers is None or self.max_tickers <= 0:
            return []

        bars_col, meta_col = self._collections()
        total = meta_col.count_documents({})
        excess = total - self.max_tickers
        if excess <= 0:
            return []

        evicted: list[str] = []
        oldest_docs = list(
            meta_col.find({}).sort("last_accessed", ASCENDING).limit(excess)
        )
        for doc in oldest_docs:
            raw_id = doc.get("_id")
            raw_ticker = doc.get("ticker", raw_id)
            if raw_ticker is not None:
                bars_col.delete_many({"ticker": raw_ticker})
            meta_col.delete_one({"_id": raw_id})
            evicted.append(str(raw_ticker))

        return evicted


def create_cache_manager(backend: str | None = None, **kwargs: Any) -> CacheManager:
    selected = (backend if backend is not None else os.getenv("CACHE_BACKEND", "")).strip().lower()

    if selected == "local":
        return LocalCacheManager(**kwargs)
    if selected == "mongo":
        return MongoCacheManager(**kwargs)
    if selected == "":
        has_uri = bool((os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "").strip())
        if has_uri:
            return MongoCacheManager(**kwargs)
        return LocalCacheManager(**kwargs)

    raise ValueError(f"Unknown cache backend: {selected!r}. Expected 'local' or 'mongo'.")
