import copy
from datetime import date, timedelta
import json
from unittest.mock import patch
import polars as pl
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _valid_payload():
    return {
        "ticker": "AAPL",
        "risk_free_ticker": "^IRX",
        "market_ticker": "SPY",
        "visual_comparison_ticker": "AAPL",
        "start_date": "2023-01-10",
        "end_date": "2023-01-25",
        "initial_cash": 10000.0,
        "base_currency": "USD",
        "strategy_name": "SMA",
        "strategy_params": [4.0, 2.0],
        "fee_model": {
            "type": "Percentage",
            "rate": 0.001,
            "min": 1.0,
            "max": 100.0,
        },
    }


def _make_sample_df(start: date, days: int, prices: list[float]) -> pl.DataFrame:
    dates = [start + timedelta(days=i) for i in range(days)]
    return pl.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p + 1.0 for p in prices],
        "Low": [p - 1.0 for p in prices],
        "Close": prices,
        "Volume": [10000.0] * days,
    })


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p: p.pop("ticker"),
        lambda p: p.update({"ticker": "   "}),
        lambda p: p.update({"initial_cash": 0.0}),
        lambda p: p.update({"initial_cash": -500.0}),
        lambda p: p.update({"initial_cash": "not-a-float"}),
        lambda p: p.update({"start_date": "2023-99-99"}),
        lambda p: p.update({"start_date": "2023-01-25", "end_date": "2023-01-10"}),
        lambda p: p.update({"start_date": "2023-01-10", "end_date": "2023-01-10"}),
        lambda p: p.update({"strategy_name": "UNKNOWN"}),
        lambda p: p.update({"strategy_params": []}),
        lambda p: p.update({"strategy_params": [10.0]}),
        lambda p: p.update({"strategy_params": [-5.0, 10.0]}),
        lambda p: p["fee_model"].update({"type": "BogusFee"}),
        lambda p: p["fee_model"].update({"rate": -0.05}),
    ],
)
def test_run_backtest_malformed_payloads_return_422(mutator):
    payload = _valid_payload()
    mutator(payload)
    response = client.post("/backtest", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_run_backtest_end_to_end_with_real_engine():
    # Includes warmup before 2023-01-10
    prices = [
        100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
        100.0, 100.0, 110.0, 120.0, 130.0, 135.0,
        140.0, 130.0, 120.0, 115.0, 110.0, 105.0,
        100.0, 98.0, 95.0,
    ]
    asset_df = _make_sample_df(date(2023, 1, 4), len(prices), prices)
    rf_df = _make_sample_df(date(2023, 1, 10), 15, [4.0] * 15)
    spy_df = _make_sample_df(date(2023, 1, 10), 15, [400.0 + i for i in range(15)])

    def fake_load(ticker, start_date, end_date, currency):
        if ticker == "^IRX":
            return rf_df
        if ticker == "SPY":
            return spy_df
        return asset_df

    with patch("orchestrator.DataProvider.load_ticker_with_fx", side_effect=fake_load):
        response = client.post("/backtest", json=_valid_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["initial_cash"] == 10000.0
    assert len(data["timestamps"]) > 2
    assert len(data["equity_curve"]) == len(data["timestamps"])
    assert len(data["market_curve"]) == len(data["timestamps"])
    assert len(data["comparison_curve"]) == len(data["timestamps"])
    assert len(data["trades"]) >= 1
    assert data["fees_paid"] > 0.0
    json.dumps(data, allow_nan=False)
