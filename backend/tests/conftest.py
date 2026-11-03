import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import sys
from unittest.mock import MagicMock

mock_backtest_core = MagicMock()

class MockBar:
    def __init__(self, ticker, timestamp, open, high, low, close, volume):
        self.ticker = ticker
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

mock_backtest_core.Bar = MockBar

mock_backtest_core.SMAStrategy = MagicMock
mock_backtest_core.PercentageFee = MagicMock
mock_backtest_core.ShareFlatFee = MagicMock
mock_backtest_core.OrderFlatFee = MagicMock
mock_backtest_core.Backtester = MagicMock
mock_backtest_core.Metrics = MagicMock

mock_build = MagicMock()
mock_build.backtest_core = mock_backtest_core
sys.modules['build'] = mock_build
sys.modules['build.backtest_core'] = mock_backtest_core
