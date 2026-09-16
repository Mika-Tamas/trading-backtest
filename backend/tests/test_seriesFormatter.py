import pytest
import polars as pl
from datetime import datetime, date, timezone
from seriesFormatter import SeriesFormatter

@pytest.fixture
def formatter():
    return SeriesFormatter()

def test_convert_to_bar_curve(formatter):
    df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 2)],
        "Open": [10.0, 11.0],
        "High": [12.0, 13.0],
        "Low": [9.0, 10.0],
        "Close": [11.0, 12.0],
        "Volume": [100.0, 200.0]
    })

    bars = formatter.convert_to_bar_curve("AAPL", df)
    
    assert len(bars) == 2
    
    bar1 = bars[0]
    assert bar1.ticker == "AAPL"
    assert bar1.open == 10.0
    assert bar1.high == 12.0
    assert bar1.low == 9.0
    assert bar1.close == 11.0
    assert bar1.volume == 100.0
    assert bar1.timestamp == int(datetime(2023, 1, 1).timestamp())

def test_build_normalized_curve(formatter):
    df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)],
        "Close": [100.0, 110.0, 90.0]
    })
    
    timestamps = [
        int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 2, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 3, tzinfo=timezone.utc).timestamp())
    ]
    
    curve = formatter.build_normalized_curve(1000.0, df, timestamps)
    
    assert len(curve) == 3
    assert curve == [1000.0, 1100.0, 900.0]

def test_get_price_curve(formatter):
    df = pl.DataFrame({
        "Date": [date(2023, 1, 1), date(2023, 1, 2)],
        "Close": [100.0, 110.0]
    })
    
    timestamps = [
        int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 2, tzinfo=timezone.utc).timestamp())
    ]
    
    curve = formatter.get_price_curve(df, timestamps)
    assert curve == [100.0, 110.0]

def test_align_curves_forward_backward_fill(formatter):
    df = pl.DataFrame({
        "Date": [date(2023, 1, 2)],
        "Close": [110.0]
    })
    
    timestamps = [
        int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 2, tzinfo=timezone.utc).timestamp()),
        int(datetime(2023, 1, 3, tzinfo=timezone.utc).timestamp())
    ]
    
    aligned = formatter.align_curves(df, timestamps)
    
    assert len(aligned) == 3
    assert aligned["Close"].to_list() == [110.0, 110.0, 110.0]
