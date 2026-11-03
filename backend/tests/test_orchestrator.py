import pytest
from orchestrator import Orchestrator
from schemas import FeeSettings
import build.backtest_core as backtest_core

@pytest.fixture
def orchestrator():
    return Orchestrator()

def test_parse_strategy_valid(orchestrator):
    strategy_class = orchestrator.parse_strategy("SMA")
    assert strategy_class == backtest_core.SMAStrategy

def test_parse_strategy_invalid(orchestrator):
    with pytest.raises(ValueError, match="Unknown strategy type: INVALID"):
        orchestrator.parse_strategy("INVALID")

def test_parse_fee_percentage(orchestrator):
    fee_settings = FeeSettings(type="Percentage", rate=0.01, min=1.0, max=100.0)
    fee_class = orchestrator.parse_fee(fee_settings)
    assert backtest_core.PercentageFee.called

def test_parse_fee_share_flat(orchestrator):
    fee_settings = FeeSettings(type="ShareFlat", rate=0.05, min=0.0, max=0.0)
    fee_class = orchestrator.parse_fee(fee_settings)
    assert backtest_core.ShareFlatFee.called

def test_parse_fee_order_flat(orchestrator):
    fee_settings = FeeSettings(type="OrderFlat", rate=2.0, min=0.0, max=0.0)
    fee_class = orchestrator.parse_fee(fee_settings)
    assert backtest_core.OrderFlatFee.called

def test_parse_fee_invalid(orchestrator):
    fee_settings = FeeSettings(type="INVALID", rate=2.0, min=0.0, max=0.0)
    with pytest.raises(ValueError, match="Unknown fee type: INVALID"):
        orchestrator.parse_fee(fee_settings)
