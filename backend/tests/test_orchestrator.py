from datetime import date, timedelta
import json
from types import SimpleNamespace
from unittest.mock import patch
import polars as pl
from pydantic import ValidationError
import pytest
import build.backtest_core as backtest_core
from orchestrator import Orchestrator
from schemas import BacktestRequest, BacktestResponse, FeeSettings


@pytest.fixture
def orchestrator():
    return Orchestrator()


def _make_df(start: date, prices: list[float]) -> pl.DataFrame:
    dates = [start + timedelta(days=i) for i in range(len(prices))]
    return pl.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p + 1.0 for p in prices],
        "Low": [p - 1.0 for p in prices],
        "Close": prices,
        "Volume": [10000.0] * len(prices),
    })


def test_parse_strategy_returns_real_cpp_class(orchestrator):
    strategy_class = orchestrator.parse_strategy("SMA")
    assert strategy_class is backtest_core.SMAStrategy
    instance = strategy_class(1000, 10, 5)
    assert isinstance(instance, backtest_core.SMAStrategy)
    assert instance.get_warmup_days() == 10

    with pytest.raises(ValueError, match="Unknown strategy type: INVALID"):
        orchestrator.parse_strategy("INVALID")


def test_parse_fee_returns_real_cpp_instances(orchestrator):
    pct = orchestrator.parse_fee(FeeSettings(type="Percentage", rate=0.01, min=1.0, max=100.0))
    share = orchestrator.parse_fee(FeeSettings(type="ShareFlat", rate=0.05, min=0.0, max=0.0))
    order = orchestrator.parse_fee(FeeSettings(type="OrderFlat", rate=2.0, min=0.0, max=0.0))

    assert isinstance(pct, backtest_core.PercentageFee)
    assert isinstance(share, backtest_core.ShareFlatFee)
    assert isinstance(order, backtest_core.OrderFlatFee)

    with pytest.raises(ValidationError):
        FeeSettings(type="INVALID", rate=2.0, min=0.0, max=0.0)

    with pytest.raises(ValueError, match="Unknown fee type: INVALID"):
        orchestrator.parse_fee(SimpleNamespace(type="INVALID", rate=2.0, min=0.0, max=0.0))


@pytest.mark.parametrize(
    "fee_model",
    [
        FeeSettings(type="Percentage", rate=0.002, min=1.0, max=50.0),
        FeeSettings(type="ShareFlat", rate=0.05, min=1.0, max=50.0),
        FeeSettings(type="OrderFlat", rate=5.0, min=0.0, max=0.0),
    ],
)
def test_execute_end_to_end_cpp_binding_invocation(orchestrator, fee_model):
    asset_prices = [
        100.0, 100.0, 100.0, 100.0, 100.0, 100.0,  # warmup (Jan 4..9)
        100.0, 100.0, 120.0, 130.0, 135.0, 140.0,  # golden cross
        115.0, 100.0, 90.0, 85.0, 80.0,            # death cross + liquidation
    ]
    asset_df = _make_df(date(2023, 1, 4), asset_prices)
    market_df = _make_df(date(2023, 1, 10), [400.0 + i * 2.0 for i in range(11)])
    rf_df = _make_df(date(2023, 1, 10), [3.0] * 11)

    req = BacktestRequest(
        ticker="AAPL",
        risk_free_ticker="^IRX",
        market_ticker="SPY",
        visual_comparison_ticker="AAPL",
        start_date="2023-01-10",
        end_date="2023-01-20",
        initial_cash=10000.0,
        base_currency="USD",
        strategy_name="SMA",
        strategy_params=[4.0, 2.0],
        fee_model=fee_model,
    )

    def mock_load_ticker(ticker, start_date, end_date):
        if ticker == "^IRX":
            return rf_df
        raise AssertionError(f"Unexpected load_ticker call for {ticker}")

    def mock_load(ticker, start_date, end_date, currency):
        if ticker == "SPY":
            return market_df
        return asset_df

    with patch.object(orchestrator.data_provider, "load_ticker", side_effect=mock_load_ticker), \
         patch.object(orchestrator.data_provider, "load_ticker_with_fx", side_effect=mock_load):
        res = orchestrator.execute(req)

    assert isinstance(res, BacktestResponse)
    assert res.initial_cash == 10000.0
    assert len(res.timestamps) == len(res.equity_curve)
    assert len(res.timestamps) == len(res.market_curve)
    assert len(res.timestamps) == len(res.comparison_curve)
    assert len(res.trades) >= 1
    assert res.fees_paid > 0.0

    total_pnl = sum(t.realized_pnl for t in res.trades)
    assert res.final_cash == pytest.approx(res.initial_cash + total_pnl - res.fees_paid, abs=1e-6)

    json.dumps(res.model_dump(), allow_nan=False)


def test_execute_non_usd_base_currency_does_not_scale_risk_free_rate(orchestrator):
    asset_prices = [
        100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
        100.0, 100.0, 120.0, 130.0, 135.0, 140.0,
        115.0, 100.0, 90.0, 85.0, 80.0,
    ]
    asset_df = _make_df(date(2023, 1, 4), asset_prices)
    market_df = _make_df(date(2023, 1, 10), [400.0 + i * 2.0 for i in range(11)])
    rf_df = _make_df(date(2023, 1, 10), [3.0] * 11)

    req = BacktestRequest(
        ticker="AAPL",
        risk_free_ticker="^IRX",
        market_ticker="SPY",
        visual_comparison_ticker="AAPL",
        start_date="2023-01-10",
        end_date="2023-01-20",
        initial_cash=1000000.0,
        base_currency="HUF",
        strategy_name="SMA",
        strategy_params=[4.0, 2.0],
        fee_model=FeeSettings(type="Percentage", rate=0.001, min=1.0, max=100.0),
    )

    def mock_load_ticker(ticker, start_date, end_date):
        if ticker == "^IRX":
            return rf_df
        raise AssertionError(f"Unexpected load_ticker call for {ticker}")

    def mock_load_ticker_with_fx(ticker, start_date, end_date, currency):
        if ticker == "SPY":
            return market_df
        return asset_df

    with patch.object(orchestrator.data_provider, "load_ticker", side_effect=mock_load_ticker) as spy_load_ticker, \
         patch.object(orchestrator.data_provider, "load_ticker_with_fx", side_effect=mock_load_ticker_with_fx) as spy_load_fx:
        orchestrator.execute(req)

    assert any(call.args[0] == "^IRX" for call in spy_load_ticker.call_args_list)
    assert all(call.args[0] != "^IRX" for call in spy_load_fx.call_args_list)
