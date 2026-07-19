from pydantic import BaseModel

class FeeSettings(BaseModel):
    type: str
    rate: float
    min: float
    max: float

class BacktestRequest(BaseModel):
    ticker:str
    risk_free_ticker: str
    market_ticker: str
    visual_comparison_ticker: str
    start_date:str
    end_date:str
    initial_cash:float
    base_currency: str
    strategy_name:str
    strategy_params:list[float]
    fee_model : FeeSettings

class TradeResponse(BaseModel):
    symbol: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    quantity: float
    side: int
    realized_pnl: float
    fee_paid: float

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
    fees_paid: float
    timestamps: list[int]
    equity_curve: list[float]
    trades: list[TradeResponse]
    comparison_curve: list[float]
    market_curve: list[float]
    metrics: BacktestMetrics

