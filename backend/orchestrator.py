from dataProvider import DataProvider
from seriesFormatter import SeriesFormatter
from schemas import BacktestRequest, BacktestMetrics, TradeResponse, BacktestResponse, FeeSettings
import sys
import os
from datetime import timedelta, datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
from build import backtest_core

class Orchestrator():
    def __init__(self):
        self.parser = DataProvider()
        self.formatter = SeriesFormatter()
        self.BUFFER_SCALE = 1.5

    def execute(self,req : BacktestRequest):

        #init strategy
        warmup_over_timestamp = int(datetime.fromisoformat(req.start_date).timestamp())
        strategy_type = self.parse_strategy(req.strategy_name)
        int_args = [int(arg) for arg in req.strategy_params]
        strategy_instance = strategy_type(warmup_over_timestamp,*int_args)

        warmup_days = strategy_instance.get_warmup_days() * self.BUFFER_SCALE
        buffered_start_dt = datetime.fromisoformat(req.start_date) - timedelta(days=int(warmup_days))
        buffered_start_date = buffered_start_dt.date().isoformat()
        
        #get ticker curve
        df = self.parser.load_ticker_with_fx(req.ticker,buffered_start_date,req.end_date,req.base_currency)
        bars = self.formatter.convert_to_bar_curve(req.ticker,df)

        #init fee
        fee_instance = self.parse_fee(req.fee_model)
        
        

#---------------------------run backtest---------------------------
        backtester = backtest_core.Backtester(req.initial_cash,strategy_instance, warmup_over_timestamp,fee_instance)
        backtester.run(bars)

        portfolio = backtester.get_portfolio()
        equity_curve = backtester.get_equity_curve()
        timestamps = backtester.get_timestamps()
        trade_history = portfolio.get_trade_history()
        
        #get curves for benchmark    
        risk_free_data = self.parser.load_ticker_with_fx(req.risk_free_ticker,req.start_date,req.end_date,req.base_currency)
        market_data = self.parser.load_ticker_with_fx(req.market_ticker,req.start_date,req.end_date,req.base_currency)
        if req.visual_comparison_ticker == req.ticker:
            comparison_data = df
        else:
            comparison_data = self.parser.load_ticker_with_fx(req.visual_comparison_ticker,req.start_date,req.end_date,req.base_currency)

        market_curve = self.formatter.build_normalized_curve(req.initial_cash,market_data,timestamps)
        risk_free_curve = self.formatter.get_price_curve(risk_free_data,timestamps)
        comparison_curve = self.formatter.build_normalized_curve(req.initial_cash,comparison_data,timestamps)

        

#---------------------------calculate metrics, formulate response---------------------------
        metrics = backtest_core.Metrics(equity_curve, trade_history, market_curve, risk_free_curve)
        metrics_struct = BacktestMetrics(
            total_return=metrics.get_total_return(),
            annualized_return=metrics.get_annualized_return(),
            sharpe_ratio=metrics.get_sharpe_ratio(),
            sortino_ratio=metrics.get_sortino_ratio(),
            maximum_drawdown=metrics.get_maximum_drawdown(),
            calmar_ratio=metrics.get_calmar_ratio(),
            profit_ratio=metrics.get_profit_factor(),
            win_rate=metrics.get_win_rate(),
            information_ratio=metrics.get_information_ratio(),
            beta=metrics.get_beta(),
            alpha=metrics.get_alpha(),
        )

        trades_struct = [TradeResponse(
            symbol=t.symbol,
            entry_time=int(t.entry_time),
            exit_time=int(t.exit_time),
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            quantity=t.quantity,
            side=t.side,
            realized_pnl=t.realized_pnl,
            fee_paid = t.fee_paid
        ) for t in trade_history]
        
        total_fees_paid = sum(t.fee_paid for t in trade_history)

        return BacktestResponse(
            initial_cash=req.initial_cash,
            final_cash=portfolio.get_cash(),
            fees_paid = total_fees_paid,
            timestamps=timestamps,
            equity_curve=equity_curve,
            trades=trades_struct,
            comparison_curve=comparison_curve,
            market_curve=market_curve,
            metrics=metrics_struct
        )
        

    def parse_strategy(self,strategy_name):
        match(strategy_name):
            case("SMA"):
                return backtest_core.SMA_strategy
            case _:
                raise ValueError(f"Unknown strategy type: {strategy_name}")
    
    def parse_fee(self, fee_settings):
        match(fee_settings.type):
            case "Percentage":
                return backtest_core.Percentage_fee(fee_settings.rate, fee_settings.min, fee_settings.max)
            case "ShareFlat":
                return backtest_core.Share_flat_fee(fee_settings.rate, fee_settings.min, fee_settings.max)
            case "OrderFlat":
                return backtest_core.Order_flat_fee(fee_settings.rate)
            case _:
                raise ValueError(f"Unknown fee type: {fee_settings.type}")
