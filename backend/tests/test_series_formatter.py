from datetime import date, datetime, timezone
import json
import polars as pl
import pytest
import build.backtest_core as backtest_core
from series_formatter import SeriesFormatter


@pytest.fixture
def formatter():
    return SeriesFormatter()


def test_convert_to_bar_curve_produces_real_cpp_bars(formatter):
    df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 2)],
        "Open": [10.0, 11.0],
        "High": [12.0, 13.0],
        "Low": [9.0, 10.0],
        "Close": [11.0, 12.0],
        "Volume": [100.0, 200.0],
    })

    bars = formatter.convert_to_bar_curve("AAPL", df)

    assert len(bars) == 2
    assert isinstance(bars[0], backtest_core.Bar)
    assert bars[0].ticker == "AAPL"
    assert bars[0].open == 10.0
    assert bars[0].high == 12.0
    assert bars[0].low == 9.0
    assert bars[0].close == 11.0
    assert bars[0].volume == 100.0
    assert bars[0].timestamp == int(datetime(2023, 1, 1).timestamp())


def test_convert_to_bar_curve_rejects_nan_or_null_ohlcv(formatter):
    nan_df = pl.DataFrame({
        "Date": [date(2023, 1, 1)],
        "Open": [10.0],
        "High": [12.0],
        "Low": [9.0],
        "Close": [float("nan")],
        "Volume": [100.0],
    })
    with pytest.raises(ValueError, match="non-finite"):
        formatter.convert_to_bar_curve("AAPL", nan_df)


def test_mismatched_series_lengths_and_duplicate_dates(formatter):
    df = pl.DataFrame({
        "Date": [date(2022, 12, 31), date(2023, 1, 2), date(2023, 1, 2), date(2023, 1, 5)],
        "Close": [95.0, 105.0, 110.0, 130.0],
    })

    timestamps = [
        int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 2, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 3, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 4, tzinfo=timezone.utc).timestamp()),
    ]

    curve = formatter.build_normalized_curve(1000.0, df, timestamps)
    price_curve = formatter.get_price_curve(df, timestamps)

    assert len(curve) == len(timestamps)
    assert len(price_curve) == len(timestamps)
    # Backfills 01-01 from latest 01-02 (110.0); forward-fills 03 & 04
    assert price_curve == [110.0, 110.0, 110.0, 110.0]
    assert curve == [1000.0, 1000.0, 1000.0, 1000.0]


def test_nan_and_null_values_are_filled_for_json_serialization(formatter):
    df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4)],
        "Close": [float("nan"), 100.0, None, 120.0],
    })

    timestamps = [
        int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 2, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 3, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 4, tzinfo=timezone.utc).timestamp()),
    ]

    curve = formatter.build_normalized_curve(1000.0, df, timestamps)
    assert curve == [1000.0, 1000.0, 1000.0, 1200.0]
    serialized = json.dumps(curve, allow_nan=False)
    assert serialized == "[1000.0, 1000.0, 1000.0, 1200.0]"


def test_empty_timestamps_empty_df_and_zero_starting_price(formatter):
    df = pl.DataFrame({"Date": [date(2023, 1, 1)], "Close": [100.0]})
    assert formatter.build_normalized_curve(1000.0, df, []) == []
    assert formatter.get_price_curve(df, []) == []

    ts = [int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())]
    empty_df = pl.DataFrame(schema={"Date": pl.Date, "Close": pl.Float64})
    with pytest.raises(ValueError, match="empty or all-null"):
        formatter.build_normalized_curve(1000.0, empty_df, ts)

    zero_df = pl.DataFrame({"Date": [date(2023, 1, 1)], "Close": [0.0]})
    with pytest.raises(ValueError, match="finite and non-zero"):
        formatter.build_normalized_curve(1000.0, zero_df, ts)
