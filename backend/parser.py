
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
        with open("config.json", "r") as cfg:
            config_data = json.load(cfg)
            self.STORED_TICKERS_PATH = config_data["paths"]["stored_tickers"]
            os.makedirs(self.STORED_TICKERS_PATH, exist_ok=True)

    def load_ticker(self,ticker,start_date,end_date):
        
        file_path = self.STORED_TICKERS_PATH + ticker + ".csv"

        if os.path.exists(file_path):
            print(f"Loading {ticker} from local cache...")
            data = pl.read_csv(file_path)
        else:
            tckr = yf.Ticker(ticker)
            pandas_df = yf.download(ticker, start=start_date, end=end_date)
        
            if pandas_df.empty:
                raise ValueError(f"Ticker '{ticker}' is invalid or has no data for the selected period/interval.")

            pandas_df = pandas_df.reset_index()
            data = pl.from_pandas(pandas_df)

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
                timestamp = int(datetime.strptime(str(date_val), "%Y-%m-%d").timestamp())

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






