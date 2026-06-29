import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { DollarSign, Calendar, TrendingUp, AlertCircle, Play, Activity, List } from 'lucide-react';
import type { BacktestResponse, Trade } from './types';
import './App.css';

export default function App() {
  const [ticker, setTicker] = useState<string>('AAPL');
  const [startDate, setStartDate] = useState<string>('2023-01-01');
  const [endDate, setEndDate] = useState<string>('2024-01-01');
  const [initialCapital, setinitialCapital] = useState<number>(10000);

  const [strategyName, setStrategyName] = useState<string>('SMA');
  const [fastPeriod, setFastPeriod] = useState<number>(50);
  const [slowPeriod, setSlowPeriod] = useState<number>(100);


  const [results, setResults] = useState<BacktestResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const chartData = React.useMemo(() => {
    if (!results) return [];

    return results.timestamps.map((timestamp, index) => {
      const dateObj = new Date(timestamp * 1000);
      return { // return {date, equity, benchmark}
        date: dateObj.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          year: '2-digit'
        }),
        equity: results.equity_curve[index],
        benchmark: results.benchmark_curve[index],
      };
    });
  }, [results]);


  const executeBacktest = async (e: React.SyntheticEvent) => {
    e.preventDefault();

    setLoadingStatus(true);
    setErrorMessage(null);

    try {
      const response = await fetch('http://127.0.0.1:8000/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: ticker,
          start_date: startDate,
          end_date: endDate,
          initial_cash: initialCapital,
          strategy_name: strategyName,
          strategy_params: [fastPeriod, slowPeriod]
        }),
      });
      if (!response.ok) {
        throw new Error(`Server returned status: ${response.status}`);
      }

      const data: BacktestResponse = await response.json();
      setResults(data);
      console.log("Backtest executed successfully.")

    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to connect to backend.');
      console.error(errorMessage);
    } finally {
      setLoadingStatus(false);

    }
  };

  return (
    <>
      <div className="container-title">
        <h1>Trading Backtest System</h1>
      </div>

      <div className="container-dashboard">
        <aside className="sidebar-config">
          <h2>Configuration</h2>
          <form onSubmit={executeBacktest}>
            <div className="input-group">
              <label htmlFor="ticker">Ticker Symbol</label>
              <input
                id="ticker"
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
              />
            </div>

            <div className="input-group">
              <label htmlFor="startDate">Start Date</label>
              <input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label htmlFor="endDate">End Date</label>
              <input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label htmlFor="strategy">Strategy</label>
              <select
                id="strategy"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
              >
                <option value="SMA">SMA Crossover</option>
              </select>
            </div>

            <div className="input-group">
              <label htmlFor="fastPeriod">Short Window (SMA)</label>
              <input
                id="fastPeriod"
                type="number"
                value={fastPeriod}
                onChange={(e) => setFastPeriod(parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="input-group">
              <label htmlFor="slowPeriod">Long Window (SMA)</label>
              <input
                id="slowPeriod"
                type="number"
                value={slowPeriod}
                onChange={(e) => setSlowPeriod(parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="input-group">
              <label htmlFor="initialCapital">Initial Capital ($)</label>
              <input
                id="initialCapital"
                type="number"
                value={initialCapital}
                onChange={(e) => setinitialCapital(parseFloat(e.target.value) || 0)}
              />
            </div>

            <button type="submit" className="btn-submit" disabled={loadingStatus}>
              {loadingStatus ? 'Running...' : 'Run Backtest'}
            </button>
          </form>

        </aside>

        <main className='main-content'>
          <div className="metrics-grid">

            <div className="metrics-card">
              <h3>Total return</h3>
              <p className="metrics-value">
                {results ? `${(((results.final_cash - results.initial_cash) / results.initial_cash) * 100).toFixed(2)}%` : "-"}
              </p>
            </div>

            <div className="metrics-card">
              <h3>Final Capital</h3>
              <p className="metrics-value">
                {results ? (
                  <>
                    <DollarSign size={20} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                    {results.final_cash.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </>
                ) : (
                  "-"
                )}
              </p>
            </div>

            <div className="metrics-card">
              <h3>Win rate</h3>
              <p className="metrics-value">
                {results ? `${((results.trades.filter(trade => trade.realized_pnl > 0).length / results.trades.length) * 100).toFixed(2)}%` : "-"}
              </p>
            </div>

            <div className="metrics-card">
              <h3>Sharpe ratio</h3>
              <p className="metrics-value">
                {"-"} {/*placeholder*/}
              </p>
            </div>
          </div>

          {/**/}

          <div className='container-chart'>
            <h3>Equity Curve</h3>
            <div className='chart-box'>
              {results ? (
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />

                    <XAxis
                      dataKey="date"
                      stroke="var(--text)"
                      tickLine={false}
                    />
                    <YAxis
                      stroke="var(--text)"
                      tickLine={false}
                      domain={['auto', 'auto']}
                      tickFormatter={(tick) => `$${tick.toLocaleString()}`}
                    />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        `$${parseFloat(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                        name
                      ]}

                      contentStyle={{
                        backgroundColor: 'var(--code-bg)',
                        borderColor: 'var(--border)',
                        borderRadius: '8px',
                        boxShadow: 'var(--shadow)'
                      }}
                    />

                    <Line
                      name="Strategy Equity"
                      type="monotone"
                      dataKey="equity"
                      stroke="var(--accent)"
                      strokeWidth={2}
                      dot={false}
                    />

                    <Line
                      name="Buy & Hold"
                      type="monotone"
                      dataKey="benchmark"
                      stroke="#b4f2a0"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>

              ) : (
                <div className='chart-placeholder'>
                  Run a backtest to view the performance graph
                </div>
              )}
            </div>
          </div >
        </main >
      </div >
    </>
  )
}