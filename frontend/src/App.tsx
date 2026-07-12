import React, { useState } from 'react';
import { DollarSign, Calendar, TrendingUp, AlertCircle, Play, Activity, List } from 'lucide-react';
import type { BacktestResponse, BacktestRequest } from './types';
import EquityChart from './components/EquityChart/EquityChart';
import MetricCard from './components/MetricCard/MetricCard';
import SidebarConfig from './components/SidebarConfig/SidebarConfig';
import './App.css';

export default function App() {
  const [ticker, setTicker] = useState<string>('AAPL');
  const [sameAsTraded, setSameAsTraded] = useState<boolean>(true);
  const [visualComparisonTicker, setVisualComparisonTicker] = useState<string>('AAPL');
  const [riskFreeTicker, setRiskFreeTicker] = useState<string>('^IRX');
  const [marketTicker, setMarketTicker] = useState<string>('SPY');
  const [startDate, setStartDate] = useState<string>('2022-01-01');
  const [endDate, setEndDate] = useState<string>('2023-01-01');
  const [initialCapital, setinitialCapital] = useState<number>(10000);

  const [strategyName, setStrategyName] = useState<string>('SMA');
  const [fastPeriod, setFastPeriod] = useState<number>(20);
  const [slowPeriod, setSlowPeriod] = useState<number>(50);


  const [results, setResults] = useState<BacktestResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);


  const executeBacktest = async (e: React.SyntheticEvent) => {
    e.preventDefault();

    setLoadingStatus(true);
    setErrorMessage(null);

    try {
      const payload: BacktestRequest = {
        ticker: ticker,
        risk_free_ticker: riskFreeTicker,
        market_ticker: marketTicker,
        visual_comparison_ticker: visualComparisonTicker,
        start_date: startDate,
        end_date: endDate,
        initial_cash: initialCapital,
        strategy_name: strategyName,
        strategy_params: [fastPeriod, slowPeriod]
      };
      const response = await fetch('http://127.0.0.1:8000/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
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

  const renderMetricCard = (key: keyof typeof metricsRegistry) => {
    const metric = metricsRegistry[key];
    return (<MetricCard
      key={key}
      label={metric.label}
      value={metric.value}
      icon={metric.icon}
    />
    );
  };

  const metricsRegistry = {
    total_return: { label: "Total Return", value: results ? `${results.metrics.total_return.toFixed(2)}%` : "-", icon: <TrendingUp /> },
    final_cash: { label: "Final Capital", value: results ? `$${results.final_cash.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "-", icon: <DollarSign /> },
    win_rate: { label: "Win Rate", value: results ? `${results.metrics.win_rate.toFixed(2)}%` : "-", icon: <Activity /> },
    sharpe_ratio: { label: "Sharpe Ratio", value: results ? results.metrics.sharpe_ratio.toFixed(2) : "-", icon: <Activity /> },
    sortino_ratio: { label: "Sortino Ratio", value: results ? results.metrics.sortino_ratio.toFixed(2) : "-", icon: <Activity /> },
    information_ratio: { label: "Information Ratio", value: results ? results.metrics.information_ratio.toFixed(2) : "-", icon: <Activity /> },
    max_drawdown: { label: "Max Drawdown", value: results ? `${results.metrics.maximum_drawdown.toFixed(2)}%` : "-", icon: <AlertCircle /> },
    annualized_return: { label: "Annualized Return", value: results ? `${results.metrics.annualized_return.toFixed(2)}%` : "-", icon: <TrendingUp /> },
    alpha: { label: "Alpha", value: results ? `${results.metrics.alpha.toFixed(2)}%` : "-", icon: <TrendingUp /> },
    beta: { label: "Beta", value: results ? results.metrics.beta.toFixed(2) : "-", icon: <Activity /> },
  };

  const topLayout = ['total_return', 'annualized_return', 'final_cash', 'alpha', 'beta'] as const;
  const sideLayout = ['sharpe_ratio', 'sortino_ratio', 'information_ratio', 'win_rate', 'max_drawdown'] as const;


  return (
    <>
      <div className="container-title">
        <h1>Trading Backtest System</h1>
      </div>

      <div className="container-dashboard">
        <SidebarConfig
          ticker={ticker}
          setTicker={setTicker}
          sameAsTraded={sameAsTraded}
          setSameAsTraded={setSameAsTraded}
          visualComparisonTicker={visualComparisonTicker}
          setVisualComparisonTicker={setVisualComparisonTicker}
          startDate={startDate}
          setStartDate={setStartDate}
          endDate={endDate}
          setEndDate={setEndDate}
          strategyName={strategyName}
          setStrategyName={setStrategyName}
          fastPeriod={fastPeriod}
          setFastPeriod={setFastPeriod}
          slowPeriod={slowPeriod}
          setSlowPeriod={setSlowPeriod}
          initialCapital={initialCapital}
          setinitialCapital={setinitialCapital}
          loadingStatus={loadingStatus}
          executeBacktest={executeBacktest}
        />

        <main className='main-content'>
          <div className="center-column">
            <div className="metrics-grid">
              {topLayout.map(renderMetricCard)}
            </div>

            {/**/}

            <EquityChart results={results} />
          </div>
          <div className="rightside-column">
            {sideLayout.map(renderMetricCard)}
          </div>
        </main >
      </div >
    </>
  )
}