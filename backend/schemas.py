from pydantic import BaseModel

class BacktestRequest(BaseModel):
    ticker:str
    start_date:str
    end_date:str
    initial_cash:float
    strategy_name:str
    strategy_params:list[float]

class TradeResponse(BaseModel):
    symbol: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    quantity: float
    side: int
    realized_pnl: float

class BacktestMetrics(BaseModel):
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    maximum_drawdown: float
    calmar_ratio: float
    profit_ratio: float
    win_rate: float
    information_ratio: float
    beta: float
    alpha: float

class BacktestResponse(BaseModel):
    initial_cash: float
    final_cash: float
    timestamps: list[int]
    equity_curve: list[float]
    trades: list[TradeResponse]
    benchmark_curve: list[float]
    metrics: BacktestMetrics
