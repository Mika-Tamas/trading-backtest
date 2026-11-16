import React, { useState } from 'react';
import { DollarSign, Euro, PoundSterling, JapaneseYen, Banknote, TrendingUp, AlertCircle, Activity } from 'lucide-react';
import type { BacktestResponse, BacktestRequest, FeeType, StrategyType } from './types';
import { formatCurrency } from './utils/currency';
import { buildFeeSettings, validateFeeSettings } from './utils/fee';
import { buildStrategyParams, getDefaultStrategyParams, validateStrategyParams } from './utils/strategy';
import EquityChart from './components/EquityChart/EquityChart';
import MetricCard from './components/MetricCard/MetricCard';
import SidebarConfig from './components/SidebarConfig/SidebarConfig';
import './App.css';

function getCurrencyIcon(currency: string) {
  switch (currency) {
    case 'USD':
    case 'CAD':
    case 'AUD':
      return <DollarSign />;
    case 'EUR':
      return <Euro />;
    case 'GBP':
      return <PoundSterling />;
    case 'JPY':
      return <JapaneseYen />;
    default:
      return <Banknote />;
  }
}

export default function App() {
  const [ticker, setTicker] = useState<string>('AAPL');
  const [sameAsTraded, setSameAsTraded] = useState<boolean>(true);
  const [visualComparisonTicker, setVisualComparisonTicker] = useState<string>('AAPL');
  const [riskFreeTicker] = useState<string>('^IRX');
  const [marketTicker] = useState<string>('SPY');
  const [startDate, setStartDate] = useState<string>('2022-01-01');
  const [endDate, setEndDate] = useState<string>('2023-01-01');
  const [initialCapital, setInitialCapital] = useState<number>(10000);
  const [baseCurrency, setBaseCurrency] = useState<string>('EUR');
  const [resultCurrency, setResultCurrency] = useState<string>('EUR');

  const [strategyName, setStrategyName] = useState<StrategyType>('SMA');
  const [strategyParams, setStrategyParams] = useState<number[]>(() =>
    getDefaultStrategyParams('SMA')
  );

  const [feeType, setFeeType] = useState<FeeType>('Percentage');
  const [feeRate, setFeeRate] = useState<number>(0.1);
  const [minFee, setMinFee] = useState<number | null>(null);
  const [maxFee, setMaxFee] = useState<number | null>(null);


  const [results, setResults] = useState<BacktestResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);


  const executeBacktest = async (e: React.SyntheticEvent) => {
    e.preventDefault();

    const validationError =
      validateStrategyParams(strategyName, strategyParams) ??
      validateFeeSettings(feeType, feeRate, minFee, maxFee);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setLoadingStatus(true);
    setErrorMessage(null);

    try {
      const requestCurrency = baseCurrency;
      const payload: BacktestRequest = {
        ticker: ticker,
        risk_free_ticker: riskFreeTicker,
        market_ticker: marketTicker,
        visual_comparison_ticker: visualComparisonTicker,
        start_date: startDate,
        end_date: endDate,
        initial_cash: initialCapital,
        base_currency: requestCurrency,
        strategy_name: strategyName,
        strategy_params: buildStrategyParams(strategyName, strategyParams),
        fee_model: buildFeeSettings(feeType, feeRate, minFee, maxFee),
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
      setResultCurrency(requestCurrency);
      console.log("Backtest executed successfully.")

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to backend.';
      setErrorMessage(message);
      console.error(err);
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

  const currencyIcon = getCurrencyIcon(results ? resultCurrency : baseCurrency);

  const metricsRegistry = {
    total_return: { label: "Total Return", value: results ? `${results.metrics.total_return.toFixed(2)}%` : "-", icon: <TrendingUp /> },
    final_cash: { label: "Final Capital", value: results ? formatCurrency(results.final_cash, resultCurrency, { maximumFractionDigits: 0 }) : "-", icon: currencyIcon },
    fees_paid: { label: "Total Fees", value: results ? formatCurrency(results.fees_paid, resultCurrency, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "-", icon: currencyIcon },
    win_rate: { label: "Win Rate", value: results ? `${results.metrics.win_rate.toFixed(2)}%` : "-", icon: <Activity /> },
    sharpe_ratio: { label: "Sharpe Ratio", value: results ? results.metrics.sharpe_ratio.toFixed(2) : "-", icon: <Activity /> },
    sortino_ratio: { label: "Sortino Ratio", value: results ? results.metrics.sortino_ratio.toFixed(2) : "-", icon: <Activity /> },
    information_ratio: { label: "Information Ratio", value: results ? results.metrics.information_ratio.toFixed(2) : "-", icon: <Activity /> },
    max_drawdown: { label: "Max Drawdown", value: results ? `${results.metrics.maximum_drawdown.toFixed(2)}%` : "-", icon: <AlertCircle /> },
    annualized_return: { label: "Annualized Return", value: results ? `${results.metrics.annualized_return.toFixed(2)}%` : "-", icon: <TrendingUp /> },
    alpha: { label: "Alpha", value: results ? `${results.metrics.alpha.toFixed(2)}%` : "-", icon: <TrendingUp /> },
    beta: { label: "Beta", value: results ? results.metrics.beta.toFixed(2) : "-", icon: <Activity /> },
  };

  const topLayout = ['total_return', 'annualized_return', 'fees_paid', 'final_cash', 'alpha', 'beta'] as const;
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
          strategyParams={strategyParams}
          setStrategyParams={setStrategyParams}
          initialCapital={initialCapital}
          setInitialCapital={setInitialCapital}
          baseCurrency={baseCurrency}
          setBaseCurrency={setBaseCurrency}
          feeType={feeType}
          setFeeType={setFeeType}
          feeRate={feeRate}
          setFeeRate={setFeeRate}
          minFee={minFee}
          setMinFee={setMinFee}
          maxFee={maxFee}
          setMaxFee={setMaxFee}
          loadingStatus={loadingStatus}
          executeBacktest={executeBacktest}
        />

        <main className='main-content'>
          <div className="center-column">
            {errorMessage && (
              <div className="error-banner" role="alert">
                <AlertCircle size={18} />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="metrics-grid">
              {topLayout.map(renderMetricCard)}
            </div>

            {/**/}

            <EquityChart results={results} currency={resultCurrency} />
          </div>
          <div className="rightside-column">
            {sideLayout.map(renderMetricCard)}
          </div>
        </main >
      </div >
    </>
  )
}