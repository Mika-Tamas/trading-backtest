from datetime import date, datetime
import pandas as pd
import polars as pl
import yfinance as yf

from cache_manager import CacheManager, create_cache_manager
from schemas import normalize_ticker


class DataProvider:
    def __init__(self, cache: CacheManager | None = None):
        self.cache: CacheManager = cache if cache is not None else create_cache_manager()

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

    def load_ticker(self, ticker: str, start_date: str, end_date: str) -> pl.DataFrame:
        normalized_ticker = normalize_ticker(ticker)

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
        try:
            cached_start, cached_end = self.cache.get_cache_bounds(normalized_ticker)
        except Exception as e:
            print(f"Error reading cache metadata for {normalized_ticker}: {e}\nFalling back to full download.")
            cached_start, cached_end = None, None

        if cached_start is not None and cached_end is not None:
            try:
                if not self.cache.has_bars(normalized_ticker):
                    raise RuntimeError(f"Metadata exists for {normalized_ticker} but no cached bars found.")

                new_slices: list[pl.DataFrame] = []
                updated_start = cached_start
                updated_end = cached_end

                # Past data missing
                if cached_start > start_dt:
                    left_df = yf.download(normalized_ticker, start=start_date, end=cached_start)
                    if left_df is not None and not left_df.empty:
                        left_pl = self._pandas_to_polars(left_df, normalized_ticker)
                        new_slices.append(left_pl)
                        updated_start = start_dt

                # Future data missing
                if cached_end < end_dt:
                    right_df = yf.download(normalized_ticker, start=cached_end, end=end_date)
                    if right_df is not None and not right_df.empty:
                        right_pl = self._pandas_to_polars(right_df, normalized_ticker)
                        new_slices.append(right_pl)
                        updated_end = end_dt

                cached_df = self.cache.get_bars(
                    normalized_ticker,
                    start_date=start_dt,
                    end_date=end_dt,
                )

                if new_slices:
                    print(f"Updating cache for {normalized_ticker}...")
                    combined_new = (
                        pl.concat(new_slices, how="diagonal_relaxed")
                        .unique(subset=["Date"])
                        .sort("Date")
                    )
                    self.cache.save_bars(normalized_ticker, combined_new)
                    self.cache.update_cache_metadata(
                        normalized_ticker,
                        start=updated_start,
                        end=updated_end,
                    )

                    parts = [df for df in (cached_df, combined_new) if df is not None and not df.is_empty()]
                    data = (
                        pl.concat(parts, how="diagonal_relaxed")
                        .unique(subset=["Date"])
                        .sort("Date")
                    )
                elif cached_df is not None and not cached_df.is_empty():
                    data = cached_df
                    self.cache.update_cache_metadata(normalized_ticker)
                else:
                    data = None

                if data is not None and not data.is_empty():
                    print(f"Loading {normalized_ticker} from cache...")
                    data = data.filter((pl.col("Date") >= start_dt) & (pl.col("Date") <= end_dt))
                    if not data.is_empty():
                        use_cache = True

            except Exception as e:
                use_cache = False
                print(f"Error while handling cache: {e}\nFalling back to full download.")

        if not use_cache:
            pandas_df = yf.download(normalized_ticker, start=start_date, end=end_date)
            data = self._pandas_to_polars(pandas_df, normalized_ticker)

            print(f"Creating cache for ticker {normalized_ticker}")
            try:
                self.cache.save_bars(normalized_ticker, data)
                self.cache.update_cache_metadata(
                    normalized_ticker,
                    start=start_dt,
                    end=end_dt,
                )
            except Exception as e:
                print(f"Warning: failed to save cache for {normalized_ticker}: {e}")

        try:
            self.cache.enforce_cache_lifecycle()
        except Exception as e:
            print(f"Warning: cache lifecycle enforcement failed: {e}")

        return data

    def load_ticker_with_fx(self, ticker: str, start_date: str, end_date: str, currency: str) -> pl.DataFrame:
        df = self.load_ticker(ticker, start_date, end_date)
        ticker_native_currency = self.get_ticker_currency(ticker)
        if ticker_native_currency is not None:
            if ticker_native_currency != currency:
                exchange_rate_ticker = f"{ticker_native_currency}{currency}=X"
                fx_df = self.load_ticker(exchange_rate_ticker, start_date, end_date)
                fx_df = fx_df.rename({"Close": "FX_Rate"})
                print(f"Converting {ticker} from {ticker_native_currency} to {currency}...")

                df = df.join(fx_df.select(["Date", "FX_Rate"]), on="Date", how="left")
                df = df.with_columns(pl.col("FX_Rate").forward_fill().backward_fill())
                df = df.with_columns([
                    (pl.col("Open") * pl.col("FX_Rate")).alias("Open"),
                    (pl.col("High") * pl.col("FX_Rate")).alias("High"),
                    (pl.col("Low") * pl.col("FX_Rate")).alias("Low"),
                    (pl.col("Close") * pl.col("FX_Rate")).alias("Close"),
                ])
                df = df.drop("FX_Rate")
        else:
            print(f"Warning: yfinance did not return currency for {ticker}. Skipping FX conversion...")

        return df

    def get_ticker_currency(self, ticker: str) -> str | None:
        normalized_ticker = normalize_ticker(ticker)

        try:
            cached_currency = self.cache.get_cached_currency(normalized_ticker)
            if cached_currency is not None:
                return cached_currency
        except Exception as e:
            print(f"Warning: failed to read cached currency for {normalized_ticker}: {e}")

        try:
            ticker_info = yf.Ticker(normalized_ticker).info
            if not isinstance(ticker_info, dict):
                return None
            raw_currency = ticker_info.get("currency", None)
        except Exception:
            return None

        if isinstance(raw_currency, str) and raw_currency.strip():
            currency = raw_currency.strip()
            try:
                self.cache.update_cache_metadata(normalized_ticker, currency=currency)
            except Exception as e:
                print(f"Warning: failed to cache currency for {normalized_ticker}: {e}")
            return currency

        return None
