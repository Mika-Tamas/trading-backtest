from datetime import timedelta, datetime, date
import polars as pl
import json
import os

class CacheManager:
    def __init__(self, storage_path="./backend/data/", metadata_file ="./backend/data/cache_metadata.json"):
        try:
            with open("../config.json", "r") as cfg:
                config_data = json.load(cfg)
                storage_path = config_data["paths"]["stored_tickers"]
                metadata_file = storage_path + "cache_metadata.json"
                os.makedirs(storage_path, exist_ok=True)
        except Exception:
            print("Config not found. Loading default file paths...")

        self.storage_path = storage_path
        self.metadata_path = metadata_file

    def ticker_path(self,ticker:str) -> str:
        return self.storage_path + ticker + ".csv"

    def from_local_cache(self,ticker:str) -> tuple[pl.DataFrame | None, date | None, date | None]:
        if not(os.path.exists(self.ticker_path(ticker))):
            return None,None,None
        else:
            data = pl.read_csv(self.ticker_path(ticker))
            data = data.with_columns(pl.col("Date").cast(pl.Date))

            start, end = self.get_cache_bounds(ticker)

            if start is None or end is None:
                start = data["Date"].min()
                end = data["Date"].max()

            return data,start,end
        


    def save_to_csv(self, ticker:str, df : pl.DataFrame):
        df.write_csv(self.ticker_path(ticker))
        print(f"Data successfully saved to {self.ticker_path(ticker)}")


    def get_cache_bounds(self,ticker:str) -> tuple[date | None, date | None]:
        try:
            with open(self.metadata_path,"r") as f:
                metadata = json.load(f)
                start = date.fromisoformat(metadata[ticker]["start"])
                end = date.fromisoformat(metadata[ticker]["end"])
                return start,end
        except Exception:
            return None,None

    def update_cache_metadata(self, ticker, start=None, end=None):
        
        try:
            with open(self.metadata_path,"r") as f:
                cached = json.load(f)
        except FileNotFoundError:
            cached = {}

        start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
        end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)

        ticker_data = cached.get(ticker, {})
        if start is not None:
            ticker_data["start"] = start.isoformat() if hasattr(start,"isoformat") else str(start)
        if end is not None:
            ticker_data["end"] = end.isoformat() if hasattr(end,"isoformat") else str(end)

        ticker_data["last_accessed"] = datetime.now().isoformat()
        
        cached[ticker] = ticker_data
        
        with open(self.metadata_path, "w") as f:
            json.dump(cached,f, indent=4)

    def remove_cached_ticker(self, ticker):

        if os.path.exists(self.ticker_path(ticker)):
            os.remove(self.ticker_path(ticker))

        try:
            with open(self.metadata_path,"r") as f:
                cached = json.load(f)
        except FileNotFoundError:
            cached = {}
        
        
        if ticker in cached:
            cached.pop(ticker)
            with open(self.metadata_path, "w") as f:
                json.dump(cached,f, indent=4)
        else:
            print(f"{ticker} didn't have metadata.")

    def enforce_cache_lifecycle(self,cutoff_date=None):
        if cutoff_date is None:
            cutoff_date = datetime.now() - timedelta(days=30)
    
        if(os.path.exists(self.metadata_path)):
            with open(self.metadata_path,"r") as f:
                metadata = json.load(f)
            for ticker,data in metadata.items():
                last_accessed = datetime.fromisoformat(data["last_accessed"])
                if last_accessed < cutoff_date:
                    self.remove_cached_ticker(ticker)
