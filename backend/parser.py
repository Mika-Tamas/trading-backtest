import polars as pl
import yfinance as yf
import json
import os

class DataParser():
    def __init__(self):
        self.data = None
        with open("config.json", "r") as cfg:
            config_data = json.load(cfg)
            self.STORED_TICKERS_PATH = config_data["paths"]["stored_tickers"]
            os.makedirs(self.STORED_TICKERS_PATH, exist_ok=True)

    def load_ticker(self,ticker,start_date,end_date):
        
        file_path = self.STORED_TICKERS_PATH + ticker + ".csv"

        if os.path.exists(file_path):
            print(f"Loading {ticker} from local cache...")
            self.data = pl.read_csv(file_path)
        else:
            tckr = yf.Ticker(ticker)
            pandas_df = yf.download(ticker, start=start_date, end=end_date)
        
            if pandas_df.empty:
                raise ValueError(f"Ticker '{ticker}' is invalid or has no data for the selected period/interval.")

            pandas_df = pandas_df.reset_index()
            self.data = pl.from_pandas(pandas_df)

            print(f"Creating cache for ticker {ticker}")
            self.save_to_csv(file_path)

        return self.data

    def load_last(self):
        return self.data

    def convert_to_bar():
        

    def save_to_csv(self, file_path : str):
        if self.data is not None:
            self.data.write_csv(file_path)
            print(f"Data successfully saved to {file_path}")
        else:
            print("No data available to save.")






