import pandas as pd
from cache_manager import CacheManager
import polars as pl
import yfinance as yf
from datetime import datetime, date


class DataProvider:
    def __init__(self, cache: CacheManager | None = None):
        self.cache = cache if cache is not None else CacheManager()

    @staticmethod
    def _pandas_to_polars(pandas_df: pd.DataFrame | None, ticker: str) -> pl.DataFrame:
        if pandas_df is None or pandas_df.empty:
            raise ValueError(f"Ticker '{ticker}' is invalid or has no data for the selected period/interval.")

        df_copy = pandas_df.copy()
        if isinstance(df_copy.columns, pd.MultiIndex):
            df_copy.columns = df_copy.columns.get_level_values(0)
        df_copy = df_copy.reset_index()

        if "Date" not in df_copy.columns:
            if "Datetime" in df_copy.columns:
                df_copy = df_copy.rename(columns={"Datetime": "Date"})
            else:
                raise ValueError(f"Downloaded data for '{ticker}' is missing 'Date' timestamps.")

        data = pl.from_pandas(df_copy)
        if "Date" not in data.columns:
            raise ValueError(f"Downloaded data for '{ticker}' is missing 'Date' timestamps.")

        data = data.with_columns(pl.col("Date").cast(pl.Date))
        if data["Date"].null_count() > 0:
            raise ValueError(f"Downloaded data for '{ticker}' contains missing or invalid timestamps.")

        return data

    def load_ticker(self, ticker, start_date, end_date) -> pl.DataFrame:

        try:
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD ISO format.")
        if start_dt >= end_dt:
            raise ValueError("Start date must be strictly before end date.")
        if end_dt > date.today():
            raise ValueError("End date cannot be in the future.")

        use_cache = False
        cached_df, cached_start, cached_end = self.cache.from_local_cache(ticker)
        if cached_df is not None:
            try:
                dfs_to_concat = []

                # Past data missing
                if cached_start > start_dt:
                    left_df = yf.download(ticker, start=start_date, end=cached_start)
                    if left_df is not None and not left_df.empty:
                        left_pl = self._pandas_to_polars(left_df, ticker)
                        dfs_to_concat.append(left_pl)
                        cached_start = start_dt

                # Present data
                dfs_to_concat.append(cached_df)

                # Future data missing
                if cached_end < end_dt:
                    right_df = yf.download(ticker, start=cached_end, end=end_date)
                    if right_df is not None and not right_df.empty:
                        right_pl = self._pandas_to_polars(right_df, ticker)
                        dfs_to_concat.append(right_pl)
                        cached_end = end_dt

                if len(dfs_to_concat) > 1:
                    print(f"Updating cache for {ticker}...")
                    data = pl.concat(dfs_to_concat)
                    data = data.unique(subset=["Date"]).sort("Date")
                    self.cache.save_to_csv(ticker, data)
                    self.cache.update_cache_metadata(ticker, start=cached_start, end=cached_end)
                else:
                    data = cached_df
                    self.cache.update_cache_metadata(ticker)

                print(f"Loading {ticker} from local cache...")
                data = data.filter((pl.col("Date") >= start_dt) & (pl.col("Date") <= end_dt))
                use_cache = True

            except Exception as e:
                use_cache = False
                print(f"Error while handling cache: {e}\nFalling back to full download.")

        if not use_cache:
            pandas_df = yf.download(ticker, start=start_date, end=end_date)
            data = self._pandas_to_polars(pandas_df, ticker)

            print(f"Creating cache for ticker {ticker}")
            self.cache.save_to_csv(ticker, data)
            self.cache.update_cache_metadata(ticker, start=start_date, end=end_date)

        self.cache.enforce_cache_lifecycle()
        return data

    def load_ticker_with_fx(self,ticker,start_date,end_date, currency):
        df = self.load_ticker(ticker, start_date, end_date)
        ticker_native_currency = self.get_ticker_currency(ticker)
        if (ticker_native_currency != None):
            if ticker_native_currency == currency:
                pass
            else:
                exchange_rate_ticker = f"{ticker_native_currency}{currency}=X"
                fx_df = self.load_ticker(exchange_rate_ticker,start_date,end_date)
                fx_df = fx_df.rename({"Close": "FX_Rate"})
                print(f"Converting {ticker} from {ticker_native_currency} to {currency}...")

                df = df.join(fx_df.select(["Date","FX_Rate"]), on="Date", how="left")
                df = df.with_columns(pl.col("FX_Rate").forward_fill().backward_fill())
                df = df.with_columns([
                    (pl.col("Open") * pl.col("FX_Rate")).alias("Open"),
                    (pl.col("High") * pl.col("FX_Rate")).alias("High"),
                    (pl.col("Low") * pl.col("FX_Rate")).alias("Low"),
                    (pl.col("Close") * pl.col("FX_Rate")).alias("Close"),])
                df = df.drop("FX_Rate")
        else:
            print(f"Warning: yfinance did not return currency for {ticker}. Skipping FX conversion...")

        return df
   
    def get_ticker_currency(self, ticker) -> str | None:
        try:
            ticker_info = yf.Ticker(ticker).info
            if not isinstance(ticker_info, dict):
                return None
            return ticker_info.get("currency", None)
        except Exception:
            return None










