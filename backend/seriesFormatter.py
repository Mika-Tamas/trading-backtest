import polars as pl
from datetime import datetime, date
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
from build import backtest_core

class SeriesFormatter:

    # for market, visual bm
    def build_normalized_curve(self,initial_cash, df: pl.DataFrame, backtest_timestamps) -> list[float]:
        df = self.align_curves(df,backtest_timestamps)
        starting_price = df['Close'][0]
        normalized_curve = ((df['Close'] / starting_price) * initial_cash).to_list()
        return normalized_curve

    # for risk free
    def get_price_curve(self, df: pl.DataFrame, backtest_timestamps: list[int]) -> list[float]: 
        aligned_df = self.align_curves(df, backtest_timestamps)
        price_curve = aligned_df['Close'].to_list()
        return price_curve

    def convert_to_bar_curve(self,ticker:str,df:pl.DataFrame):
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

    def align_curves(self,df : pl.DataFrame, timestamps: list[int]) -> pl.DataFrame:
        target_df = pl.DataFrame({"timestamp": timestamps})
        target_df = target_df.with_columns(pl.from_epoch(pl.col("timestamp"), time_unit="s").cast(pl.Date).alias("Date"))

        aligned_df = target_df.join(df, on="Date", how="left")

        aligned_df = aligned_df.with_columns(pl.col("Close").forward_fill().backward_fill())

        return aligned_df

    