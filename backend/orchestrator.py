from parser import DataParser
from schemas import BacktestRequest, BacktestMetrics, TradeResponse, BacktestResponse
import sys
import os


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
from build import backtest_core

class Orchestrator():
    def __init__(self):
        self.parser = DataParser()

    def execute(self,req : BacktestRequest):
        
        df = self.parser.load_ticker(req.ticker,req.start_date,req.end_date)
        bars = self.parser.convert_to_bar(df, req.ticker)
        
        strategy_type = self.parse_strategy(req.strategy_name)

        int_args = [int(arg) for arg in req.strategy_params]
        strategy_instance = strategy_type(*int_args)
        backtester = backtest_core.Backtester(req.initial_cash,strategy_instance)
        backtester.run(bars)

        portfolio = backtester.get_portfolio()
        equity_curve = backtester.get_equity_curve()
        benchmark_curve = backtester.get_benchmark_curve()
        timestamps = backtester.get_timestamps()
        trade_history = portfolio.get_trade_history()

        # Empty list for risk free rate until SOFR integration
        risk_free_rate_curve = []
        metrics = backtest_core.Metrics(equity_curve, trade_history, benchmark_curve, risk_free_rate_curve)

        metrics_struct = BacktestMetrics(
            total_return=metrics.get_total_return(),
            annualized_return=metrics.get_annualized_return(),
            sharpe_ratio=metrics.get_sharpe_ratio(),
            sortino_ratio=metrics.get_sortino_ratio(),
            maximum_drawdown=metrics.get_maximum_drawdown(),
            calmar_ratio=metrics.get_calmar_ratio(),
            profit_ratio=metrics.get_profit_factor(),
            win_rate=metrics.get_win_rate()
        )


        trades_struct = [TradeResponse(
            symbol=t.symbol,
            entry_time=int(t.entry_time),
            exit_time=int(t.exit_time),
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            quantity=t.quantity,
            side=t.side,
            realized_pnl=t.realized_pnl
        ) for t in trade_history]

        return BacktestResponse(
            initial_cash=req.initial_cash,
            final_cash=portfolio.get_cash(),
            timestamps=timestamps,
            equity_curve=equity_curve,
            trades=trades_struct,
            benchmark_curve=benchmark_curve,
            metrics=metrics_struct
        )
        


    def parse_strategy(self,strategy_name):
        match(strategy_name):
            case("SMA"):
                return backtest_core.SMA_strategy
            case _:
                raise ValueError(f"Unknown strategy type: {strategy_name}")
        