from cacheManager import CacheManager
import polars as pl
import yfinance as yf
from datetime import datetime, date


class DataProvider():
    def __init__(self):
        self.cache = CacheManager()
        

    def load_ticker(self,ticker,start_date,end_date) -> pl.DataFrame:
        
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
        cached_df,cached_start,cached_end = self.cache.from_local_cache(ticker)
        if cached_df is not None:
            try:             

                dfs_to_concat = []

                #Past data missing
                if cached_start > start_dt:
                    left_df = yf.download(ticker,start=start_date,end=cached_start)
                    if not left_df.empty:
                        left_df.columns = left_df.columns.get_level_values(0)
                        left_df = left_df.reset_index()

                        left_pl = pl.from_pandas(left_df)
                        left_pl = left_pl.with_columns(pl.col("Date").cast(pl.Date))
                        dfs_to_concat.append(left_pl)
                        cached_start = start_dt
                
                #Present data
                dfs_to_concat.append(cached_df)

                #Future data missing
                if cached_end < end_dt:
                    right_df = yf.download(ticker,start=cached_end,end=end_date)
                    if not right_df.empty:
                        right_df.columns = right_df.columns.get_level_values(0)
                        right_df = right_df.reset_index()

                        right_pl = pl.from_pandas(right_df)
                        right_pl = right_pl.with_columns(pl.col("Date").cast(pl.Date))
                        dfs_to_concat.append(right_pl)
                        cached_end = end_dt

                if(len(dfs_to_concat) > 1):
                    print(f"Updating cache for {ticker}...")
                    data = pl.concat(dfs_to_concat)                    
                    data = data.unique(subset=["Date"]).sort("Date")
                    self.cache.save_to_csv(ticker,data)
                    self.cache.update_cache_metadata(ticker,start=cached_start,end=cached_end)
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
        
            if pandas_df.empty:
                raise ValueError(f"Ticker '{ticker}' is invalid or has no data for the selected period/interval.")

            pandas_df.columns = pandas_df.columns.get_level_values(0)
            pandas_df = pandas_df.reset_index()
            data = pl.from_pandas(pandas_df)

            data = data.with_columns(pl.col("Date").cast(pl.Date)) # 2020-01-01 format

            print(f"Creating cache for ticker {ticker}")
            self.cache.save_to_csv(ticker,data)
            self.cache.update_cache_metadata(ticker,start=start_date, end=end_date)


        self.cache.enforce_cache_lifecycle()
        return data


   











