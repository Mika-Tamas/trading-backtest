import math
import polars as pl
from datetime import datetime, date, timezone
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
from build import backtest_core


class SeriesFormatter:

    # for market, visual bm
    def build_normalized_curve(self, initial_cash, df: pl.DataFrame, backtest_timestamps) -> list[float]:
        if not backtest_timestamps:
            return []
        aligned_df = self.align_curves(df, backtest_timestamps)
        if aligned_df.is_empty() or aligned_df["Close"].null_count() == len(aligned_df):
            raise ValueError("Cannot build normalized curve from empty or all-null price data.")
        starting_price = aligned_df["Close"][0]
        if starting_price is None or not math.isfinite(starting_price) or starting_price == 0.0:
            raise ValueError("Starting price must be finite and non-zero for normalization.")
        normalized_curve = ((aligned_df["Close"] / starting_price) * initial_cash).to_list()
        return normalized_curve

    # for risk free
    def get_price_curve(self, df: pl.DataFrame, backtest_timestamps: list[int]) -> list[float]:
        if not backtest_timestamps:
            return []
        aligned_df = self.align_curves(df, backtest_timestamps)
        if aligned_df.is_empty() or aligned_df["Close"].null_count() == len(aligned_df):
            raise ValueError("Cannot build price curve from empty or all-null price data.")
        price_curve = aligned_df["Close"].to_list()
        return price_curve

    def convert_to_bar_curve(self, ticker: str, df: pl.DataFrame):
        bars = []
        for row in df.iter_rows(named=True):
            date_val = row["Date"]
            if date_val is None:
                raise ValueError("Bar row contains null Date.")
            if isinstance(date_val, datetime):
                dt = date_val.replace(tzinfo=timezone.utc) if date_val.tzinfo is None else date_val
                timestamp = int(dt.timestamp())
            elif isinstance(date_val, date):
                timestamp = int(datetime.combine(date_val, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            else:  # str
                dt = datetime.fromisoformat(str(date_val))
                dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                timestamp = int(dt.timestamp())

            ohlcv = []
            for col in ("Open", "High", "Low", "Close", "Volume"):
                val = row[col]
                if val is None or not math.isfinite(float(val)):
                    raise ValueError(f"Bar row contains non-finite value in '{col}'.")
                ohlcv.append(float(val))

            bar = backtest_core.Bar(
                ticker,
                timestamp,
                ohlcv[0],
                ohlcv[1],
                ohlcv[2],
                ohlcv[3],
                ohlcv[4],
            )
            bars.append(bar)

        return bars

    def align_curves(self, df: pl.DataFrame, timestamps: list[int]) -> pl.DataFrame:
        if not timestamps:
            return pl.DataFrame(
                schema={"timestamp": pl.Int64, "Date": pl.Date, "Close": pl.Float64}
            )

        target_df = pl.DataFrame({"timestamp": timestamps})
        target_df = target_df.with_columns(
            pl.from_epoch(pl.col("timestamp"), time_unit="s").cast(pl.Date).alias("Date")
        )

        if df.is_empty():
            return target_df.with_columns(pl.lit(None, dtype=pl.Float64).alias("Close"))

        clean_df = (
            df.select(["Date", "Close"])
            .with_columns(pl.col("Close").cast(pl.Float64).fill_nan(None))
            .unique(subset=["Date"], keep="last")
        )

        aligned_df = target_df.join(clean_df, on="Date", how="left")
        aligned_df = aligned_df.with_columns(
            pl.col("Close").forward_fill().backward_fill()
        )

        return aligned_df

    