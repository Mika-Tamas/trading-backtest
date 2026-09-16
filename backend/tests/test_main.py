import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch
from schemas import BacktestResponse, BacktestMetrics, TradeResponse

client = TestClient(app)

def test_run_backtest_invalid_schema():
    payload = {
        "start_date": "2023-01-01",
        "end_date": "2023-01-02",
        "initial_cash": 1000.0,
    }
    response = client.post("/backtest", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_run_backtest_valid():
    valid_payload = {
        "ticker": "AAPL",
        "risk_free_ticker": "^IRX",
        "market_ticker": "SPY",
        "visual_comparison_ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-01-02",
        "initial_cash": 10000.0,
        "base_currency": "USD",
        "strategy_name": "SMA",
        "strategy_params": [10.0, 20.0],
        "fee_model": {
            "type": "Percentage",
            "rate": 0.01,
            "min": 0.0,
            "max": 0.0
        }
    }

    mock_metrics = BacktestMetrics(
        total_return=0.1,
        annualized_return=0.1,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        maximum_drawdown=0.05,
        calmar_ratio=2.0,
        profit_ratio=1.5,
        win_rate=0.6,
        information_ratio=0.5,
        beta=1.0,
        alpha=0.01
    )

    mock_response = BacktestResponse(
        initial_cash=10000.0,
        final_cash=11000.0,
        fees_paid=10.0,
        timestamps=[1672531200, 1672617600],
        equity_curve=[10000.0, 11000.0],
        trades=[],
        comparison_curve=[10000.0, 10500.0],
        market_curve=[10000.0, 10100.0],
        metrics=mock_metrics
    )

    with patch('main.Orchestrator') as mock_orchestrator_class:
        mock_instance = mock_orchestrator_class.return_value
        mock_instance.execute.return_value = mock_response

        response = client.post("/backtest", json=valid_payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["initial_cash"] == 10000.0
        assert data["final_cash"] == 11000.0
        assert data["fees_paid"] == 10.0
        assert len(data["equity_curve"]) == 2
        assert "metrics" in data
        assert data["metrics"]["sharpe_ratio"] == 1.5
