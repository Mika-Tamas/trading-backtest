from datetime import timedelta, datetime, date
import polars as pl
import json
import os

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
        self.metadata_path = metadata_file

    def ticker_path(self, ticker: str) -> str:
        return os.path.join(self.storage_path, f"{ticker}.csv")

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
        path = self.ticker_path(ticker)
        if not os.path.exists(path):
            return None, None, None
        try:
            data = pl.read_csv(path)
            if data.is_empty() or "Date" not in data.columns:
                return None, None, None
            data = data.with_columns(pl.col("Date").cast(pl.Date))
            if data["Date"].null_count() > 0:
                return None, None, None

            start, end = self.get_cache_bounds(ticker)

            if start is None or end is None:
                start = data["Date"].min()
                end = data["Date"].max()

            return data, start, end
        except Exception:
            return None, None, None

    def save_to_csv(self, ticker: str, df: pl.DataFrame):
        df.write_csv(self.ticker_path(ticker))
        print(f"Data successfully saved to {self.ticker_path(ticker)}")

    def get_cache_bounds(self, ticker: str) -> tuple[date | None, date | None]:
        try:
            metadata = self._load_metadata()
            start = date.fromisoformat(metadata[ticker]["start"])
            end = date.fromisoformat(metadata[ticker]["end"])
            return start, end
        except Exception:
            return None, None

    def update_cache_metadata(self, ticker, start=None, end=None):
        cached = self._load_metadata()

        ticker_data = cached.get(ticker, {})
        if not isinstance(ticker_data, dict):
            ticker_data = {}
        if start is not None:
            ticker_data["start"] = start.isoformat() if hasattr(start, "isoformat") else str(start)
        if end is not None:
            ticker_data["end"] = end.isoformat() if hasattr(end, "isoformat") else str(end)

        ticker_data["last_accessed"] = datetime.now().isoformat()

        cached[ticker] = ticker_data

        with open(self.metadata_path, "w") as f:
            json.dump(cached, f, indent=4)

    def remove_cached_ticker(self, ticker):
        path = self.ticker_path(ticker)
        if os.path.exists(path):
            os.remove(path)

        cached = self._load_metadata()

        if ticker in cached:
            cached.pop(ticker)
            with open(self.metadata_path, "w") as f:
                json.dump(cached, f, indent=4)
        else:
            print(f"{ticker} didn't have metadata.")

    def enforce_cache_lifecycle(self, cutoff_date=None):
        if cutoff_date is None:
            cutoff_date = datetime.now() - timedelta(days=30)

        metadata = self._load_metadata()
        for ticker, data in list(metadata.items()):
            try:
                last_accessed = datetime.fromisoformat(data["last_accessed"])
            except (KeyError, TypeError, ValueError):
                self.remove_cached_ticker(ticker)
                continue
            if last_accessed < cutoff_date:
                self.remove_cached_ticker(ticker)
