export interface Trade {
    symbol: string;
    entry_time: number;
    exit_time: number;
    entry_price: number;
    exit_price: number;
    quantity: number;
    side: number; // 1 for Long, -1 for Short
    realized_pnl: number;
}

export interface BacktestResponse {
    initial_cash: number;
    final_cash: number;
    timestamps: number[];
    equity_curve: number[];
    trades: Trade[];
}
