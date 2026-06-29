from parser import DataParser
import sys
import os


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
from build import backtest_core

class Orchestrator():
    def __init__(self):
        self.parser = DataParser()

    def execute(self,ticker,start,end,initial_cash,strategy_name,*args):
        df = self.parser.load_ticker(ticker,start,end)
        bars = self.parser.convert_to_bar(df, ticker)
        
        strategy_type = self.parse_strategy(strategy_name)

        int_args = [int(arg) for arg in args]
        strategy_instance = strategy_type(*int_args)
        backtester = backtest_core.Backtester(initial_cash,strategy_instance)
        backtester.run(bars)

        portfolio = backtester.get_portfolio()
        equity_curve = backtester.get_equity_curve()
        timestamps = backtester.get_timestamps()

        trades = []
        for t in portfolio.get_trade_history():
            trades.append({
                "symbol": t.symbol,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "side": t.side,
                "realized_pnl": t.realized_pnl
            })

        return {
            "initial_cash": initial_cash,
            "final_cash": portfolio.get_cash(),
            "timestamps": timestamps,
            "equity_curve": equity_curve,
            "trades": trades,
            "benchmark_curve" : backtester.get_benchmark_curve()
        }
        


    def parse_strategy(self,strategy_name):
        match(strategy_name):
            case("SMA"):
                return backtest_core.SMA_strategy
            case _:
                raise ValueError(f"Unknown strategy type: {strategy_name}")
        