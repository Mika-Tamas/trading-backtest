
import polars as pl
import yfinance as yf
import json
import os
import sys
from datetime import datetime, date

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
from build import backtest_core


class DataParser():
    def __init__(self):
        with open("../config.json", "r") as cfg:
            config_data = json.load(cfg)
            self.STORED_TICKERS_PATH = config_data["paths"]["stored_tickers"]
            os.makedirs(self.STORED_TICKERS_PATH, exist_ok=True)

    def load_ticker(self,ticker,start_date,end_date):
        
        try:
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD ISO format.")
        if start_dt >= end_dt:
            raise ValueError("Start date must be strictly before end date.")
        if end_dt > date.today():
            raise ValueError("End date cannot be in the future.")


        file_path = self.STORED_TICKERS_PATH + ticker + ".csv"
        use_cache = False

        if os.path.exists(file_path):
            try:
                
                cached_df = pl.read_csv(file_path)
                cached_df = cached_df.with_columns(pl.col("Date").cast(pl.Date))                
                cached_start = cached_df["Date"].min()
                cached_end = cached_df["Date"].max()

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

                if(len(dfs_to_concat) > 1):
                    print(f"Updating cache for {ticker}...")
                    data = pl.concat(dfs_to_concat)                    
                    data = data.unique(subset=["Date"]).sort("Date")
                    self.save_to_csv(data, file_path)
                else:
                    data = cached_df

                print(f"Loading {ticker} from local cache...")
                data = data.filter((pl.col("Date") >= start_dt) & (pl.col("Date") <= end_dt))
                use_cache = True

            except Exception as e:
                use_cache = False
                os.remove(file_path)
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
            self.save_to_csv(data,file_path)

        return data


    def convert_to_bar(self, df:pl.DataFrame, ticker:str):
        bars = []
        for row in df.iter_rows(named=True):
            date_val = row["Date"]
            if isinstance(date_val, datetime):
                timestamp = int(date_val.timestamp())
            elif isinstance(date_val, date):
                timestamp = int(datetime.combine(date_val, datetime.min.time()).timestamp())
            else: # str
                timestamp = int(datetime.fromisoformat(str(date_val)).timestamp())

            bar = backtest_core.Bar(
                ticker,
                timestamp,
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(row["Volume"]))
            bars.append(bar)

        return bars

    def save_to_csv(self, df : pl.DataFrame,file_path : str):
        df.write_csv(file_path)
        print(f"Data successfully saved to {file_path}")






