from datetime import timedelta, datetime, date
import json
import os
from pathlib import Path
from urllib.parse import quote
import polars as pl
from schemas import normalize_ticker

WINDOWS_RESERVED_NAMES = frozenset({
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(10)),
    *(f"LPT{i}" for i in range(10)),
})


class CacheManager:
    def __init__(self, storage_path: str | None = None, metadata_file: str | None = None):
        if storage_path is None and metadata_file is None:
            try:
                with open("../config.json", "r") as cfg:
                    config_data = json.load(cfg)
                    storage_path = config_data["paths"]["stored_tickers"]
                    metadata_file = os.path.join(storage_path, "cache_metadata.json")
            except Exception:
                print("Config not found. Loading default file paths...")

        if storage_path is None:
            storage_path = "./backend/data/"
        if metadata_file is None:
            metadata_file = os.path.join(storage_path, "cache_metadata.json")

        os.makedirs(storage_path, exist_ok=True)
        self.storage_path = storage_path
        self.storage_root = Path(storage_path).resolve()
        self.metadata_path = metadata_file

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

    def _load_metadata(self) -> dict:
        if not os.path.exists(self.metadata_path):
            return {}
        try:
            with open(self.metadata_path, "r") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError, ValueError):
            return {}

    def from_local_cache(self, ticker: str) -> tuple[pl.DataFrame | None, date | None, date | None]:
        normalized = normalize_ticker(ticker)
        path = self.ticker_path(normalized)
        if not os.path.exists(path):
            return None, None, None
        try:
            data = pl.read_csv(path)
            if data.is_empty() or "Date" not in data.columns:
                return None, None, None
            if data.schema["Date"] != pl.Date:
                data = data.with_columns(pl.col("Date").str.to_date("%Y-%m-%d"))
            if data["Date"].null_count() > 0:
                return None, None, None

            start, end = self.get_cache_bounds(normalized)

            if start is None or end is None:
                start = data["Date"].min()
                end = data["Date"].max()

            return data, start, end
        except Exception:
            return None, None, None

    def save_to_csv(self, ticker: str, df: pl.DataFrame):
        path = self.ticker_path(ticker)
        df.write_csv(path)
        print(f"Data successfully saved to {path}")

    def get_cache_bounds(self, ticker: str) -> tuple[date | None, date | None]:
        normalized = normalize_ticker(ticker)
        try:
            metadata = self._load_metadata()
            start = date.fromisoformat(metadata[normalized]["start"])
            end = date.fromisoformat(metadata[normalized]["end"])
            return start, end
        except Exception:
            return None, None

    def update_cache_metadata(self, ticker, start=None, end=None):
        normalized = normalize_ticker(ticker)
        cached = self._load_metadata()

        ticker_data = cached.get(normalized, {})
        if not isinstance(ticker_data, dict):
            ticker_data = {}
        if start is not None:
            ticker_data["start"] = start.isoformat() if hasattr(start, "isoformat") else str(start)
        if end is not None:
            ticker_data["end"] = end.isoformat() if hasattr(end, "isoformat") else str(end)

        ticker_data["last_accessed"] = datetime.now().isoformat()

        cached[normalized] = ticker_data

        with open(self.metadata_path, "w") as f:
            json.dump(cached, f, indent=4)

    def remove_cached_ticker(self, ticker):
        normalized = normalize_ticker(ticker)
        path = self.ticker_path(normalized)
        if os.path.exists(path):
            os.remove(path)

        cached = self._load_metadata()

        if normalized in cached:
            cached.pop(normalized)
            with open(self.metadata_path, "w") as f:
                json.dump(cached, f, indent=4)
        else:
            print(f"{normalized} didn't have metadata.")

    def _drop_invalid_metadata_key(self, raw_key: str):
        cached = self._load_metadata()
        if raw_key in cached:
            cached.pop(raw_key)
            with open(self.metadata_path, "w") as f:
                json.dump(cached, f, indent=4)

    def enforce_cache_lifecycle(self, cutoff_date=None):
        if cutoff_date is None:
            cutoff_date = datetime.now() - timedelta(days=30)

        metadata = self._load_metadata()
        for ticker, data in list(metadata.items()):
            try:
                last_accessed = datetime.fromisoformat(data["last_accessed"])
            except (KeyError, TypeError, ValueError):
                try:
                    self.remove_cached_ticker(ticker)
                except ValueError:
                    self._drop_invalid_metadata_key(ticker)
                continue
            if last_accessed < cutoff_date:
                try:
                    self.remove_cached_ticker(ticker)
                except ValueError:
                    self._drop_invalid_metadata_key(ticker)
