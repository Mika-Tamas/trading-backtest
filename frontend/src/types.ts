export interface Trade {
    ticker: string;
    entry_time: number;
    exit_time: number;
    entry_price: number;
    exit_price: number;
    quantity: number;
    side: number; // 1 for Long, -1 for Short
    realized_pnl: number;
    fee_paid: number;
}

export interface BacktestMetrics {
    total_return: number;
    annualized_return: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    maximum_drawdown: number;
    calmar_ratio: number;
    profit_factor: number;
    win_rate: number;
    information_ratio: number;
    beta: number;
    alpha: number;
}

export interface BacktestResponse {
    initial_cash: number;
    final_cash: number;
    fees_paid: number;
    timestamps: number[];
    equity_curve: number[];
    trades: Trade[];
    comparison_curve: number[];
    market_curve: number[];
    metrics: BacktestMetrics;
}

export type StrategyType = 'SMA';

export interface BacktestRequest {
    ticker: string;
    risk_free_ticker: string;
    market_ticker: string;
    visual_comparison_ticker: string;
    start_date: string;
    end_date: string;
    initial_cash: number;
    base_currency: string;
    strategy_name: StrategyType;
    strategy_params: number[];
    fee_model: FeeSettings;
}

export type FeeType = 'Percentage' | 'ShareFlat' | 'OrderFlat';

export interface FeeSettings {
    type: FeeType;
    rate: number;
    min: number;
    max: number;
}