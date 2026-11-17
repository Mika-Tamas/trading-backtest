import React, { useCallback, useEffect, useState } from 'react';
import {
  DollarSign,
  Euro,
  PoundSterling,
  JapaneseYen,
  Banknote,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Activity,
  Scale,
  Percent,
  Receipt,
  Sun,
  Moon,
  BarChart3,
  AlertCircle,
  List,
} from 'lucide-react';
import type { BacktestResponse, BacktestRequest, FeeType, StrategyType } from './types';
import { formatCurrency } from './utils/currency';
import { buildFeeSettings, validateFeeSettings } from './utils/fee';
import {
  buildStrategyParams,
  getDefaultStrategyParams,
  getStrategySpec,
  validateStrategyParams,
} from './utils/strategy';
import EquityChart from './components/EquityChart/EquityChart';
import MetricCard, { type MetricTone, type MetricVariant } from './components/MetricCard/MetricCard';
import SidebarConfig from './components/SidebarConfig/SidebarConfig';
import TradesPanel from './components/TradesPanel/TradesPanel';
import './App.css';

type ThemeMode = 'light' | 'dark';

const TRADES_DOCKED_QUERY = '(min-width: 1440px)';

function getInitialTheme(): ThemeMode {
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
  } catch {
    // Ignore storage errors
  }
  return 'light';
}

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

function getSignedTone(value: number | undefined): MetricTone {
  if (value === undefined) return 'neutral';
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return 'neutral';
}

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);

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
  const [resultTicker, setResultTicker] = useState<string | null>(null);
  const [resultComparisonTicker, setResultComparisonTicker] = useState<string | null>(null);
  const [resultStrategyLabel, setResultStrategyLabel] = useState<string | null>(null);
  const [resultPeriod, setResultPeriod] = useState<string | null>(null);

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
  const [tradesOpen, setTradesOpen] = useState<boolean>(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('theme', theme);
    } catch {
      // Ignore storage errors
    }
  }, [theme]);

  useEffect(() => {
    const mql = window.matchMedia(TRADES_DOCKED_QUERY);
    const handleChange = (e: MediaQueryListEvent) => {
      if (e.matches) setTradesOpen(false);
    };
    mql.addEventListener('change', handleChange);
    return () => mql.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    if (!tradesOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [tradesOpen]);

  const closeTrades = useCallback(() => setTradesOpen(false), []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

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
      const requestTicker = ticker;
      const requestComparison = visualComparisonTicker;
      const requestPeriod = `${startDate} → ${endDate}`;
      const requestStrategyLabel = getStrategySpec(strategyName).label;

      const payload: BacktestRequest = {
        ticker: requestTicker,
        risk_free_ticker: riskFreeTicker,
        market_ticker: marketTicker,
        visual_comparison_ticker: requestComparison,
        start_date: startDate,
        end_date: endDate,
        initial_cash: initialCapital,
        base_currency: requestCurrency,
        strategy_name: strategyName,
        strategy_params: buildStrategyParams(strategyName, strategyParams),
        fee_model: buildFeeSettings(feeType, feeRate, minFee, maxFee),
      };

      const apiBase =
        import.meta.env.VITE_API_URL ??
        (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

      const response = await fetch(`${apiBase}/backtest`, {
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
      setResultTicker(requestTicker);
      setResultComparisonTicker(requestComparison);
      setResultStrategyLabel(requestStrategyLabel);
      setResultPeriod(requestPeriod);
      console.log('Backtest executed successfully.');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to backend.';
      setErrorMessage(message);
      console.error(err);
    } finally {
      setLoadingStatus(false);
    }
  };

  const currencyIcon = getCurrencyIcon(results ? resultCurrency : baseCurrency);

  const metricsRegistry: Record<
    string,
    {
      label: string;
      value: string;
      icon: React.ReactNode;
      tone: MetricTone;
      highlightValue?: boolean;
    }
  > = {
    total_return: {
      label: 'Total Return',
      value: results ? `${results.metrics.total_return.toFixed(2)}%` : '—',
      icon: results && results.metrics.total_return < 0 ? <TrendingDown /> : <TrendingUp />,
      tone: getSignedTone(results?.metrics.total_return),
      highlightValue: true,
    },
    annualized_return: {
      label: 'Annualized Return',
      value: results ? `${results.metrics.annualized_return.toFixed(2)}%` : '—',
      icon: results && results.metrics.annualized_return < 0 ? <TrendingDown /> : <TrendingUp />,
      tone: getSignedTone(results?.metrics.annualized_return),
      highlightValue: true,
    },
    final_cash: {
      label: 'Final Capital',
      value: results
        ? formatCurrency(results.final_cash, resultCurrency, { maximumFractionDigits: 0 })
        : '—',
      icon: currencyIcon,
      tone: 'accent',
    },
    max_drawdown: {
      label: 'Max Drawdown',
      value: results ? `${results.metrics.maximum_drawdown.toFixed(2)}%` : '—',
      icon: <AlertTriangle />,
      tone: results && results.metrics.maximum_drawdown > 0 ? 'negative' : 'neutral',
      highlightValue: true,
    },
    sharpe_ratio: {
      label: 'Sharpe Ratio',
      value: results ? results.metrics.sharpe_ratio.toFixed(2) : '—',
      icon: <Activity />,
      tone: results && results.metrics.sharpe_ratio >= 1 ? 'positive' : 'accent',
    },
    sortino_ratio: {
      label: 'Sortino Ratio',
      value: results ? results.metrics.sortino_ratio.toFixed(2) : '—',
      icon: <Activity />,
      tone: results && results.metrics.sortino_ratio >= 1 ? 'positive' : 'accent',
    },
    information_ratio: {
      label: 'Information Ratio',
      value: results ? results.metrics.information_ratio.toFixed(2) : '—',
      icon: <Scale />,
      tone: 'neutral',
    },
    alpha: {
      label: 'Alpha',
      value: results ? `${results.metrics.alpha.toFixed(2)}%` : '—',
      icon: results && results.metrics.alpha < 0 ? <TrendingDown /> : <TrendingUp />,
      tone: getSignedTone(results?.metrics.alpha),
      highlightValue: true,
    },
    beta: {
      label: 'Beta',
      value: results ? results.metrics.beta.toFixed(2) : '—',
      icon: <Scale />,
      tone: 'neutral',
    },
    win_rate: {
      label: 'Win Rate',
      value: results ? `${results.metrics.win_rate.toFixed(2)}%` : '—',
      icon: <Percent />,
      tone: results && results.metrics.win_rate >= 50 ? 'positive' : 'neutral',
    },
    fees_paid: {
      label: 'Total Fees',
      value: results
        ? formatCurrency(results.fees_paid, resultCurrency, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
        : '—',
      icon: <Receipt />,
      tone: 'neutral',
    },
  };

  const primaryLayout = ['total_return', 'annualized_return', 'final_cash', 'max_drawdown'] as const;
  const secondaryLayout = [
    'alpha',
    'beta',
    'sharpe_ratio',
    'sortino_ratio',
    'information_ratio',
    'win_rate',
    'fees_paid',
  ] as const;

  const renderMetricCard = (
    key: (typeof primaryLayout)[number] | (typeof secondaryLayout)[number],
    variant: MetricVariant
  ) => {
    const metric = metricsRegistry[key];
    return (
      <MetricCard
        key={key}
        label={metric.label}
        value={metric.value}
        icon={metric.icon}
        tone={metric.tone}
        variant={variant}
        highlightValue={metric.highlightValue}
      />
    );
  };

  return (
    <>
      <header className="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <div className="brand-mark">
              <BarChart3 size={18} />
            </div>
            <div className="brand-copy">
              <h1 className="header-title">Trading Backtest System</h1>
              <p className="header-subtitle">Quantitative strategy simulation &amp; risk analytics</p>
            </div>
          </div>

          <div className="header-actions">
            {resultTicker && (
              <div className="status-pill" title="Active simulation parameters">
                <span className="status-dot" />
                <span className="status-ticker">{resultTicker}</span>
                {resultStrategyLabel && (
                  <>
                    <span className="status-sep">/</span>
                    <span className="status-meta">{resultStrategyLabel}</span>
                  </>
                )}
                {resultPeriod && (
                  <>
                    <span className="status-sep">·</span>
                    <span className="status-period">{resultPeriod}</span>
                  </>
                )}
                <span className="status-sep">·</span>
                <span className="status-currency">{resultCurrency}</span>
              </div>
            )}

            <button
              type="button"
              className="theme-toggle trades-toggle"
              onClick={() => setTradesOpen(true)}
              aria-label="Open trade log"
              aria-controls="trades-panel"
              aria-expanded={tradesOpen}
            >
              <List size={15} />
              <span className="trades-toggle-label">Trades</span>
              {results && <span className="trades-toggle-count">{results.trades.length}</span>}
            </button>

            <button
              type="button"
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            >
              {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
              <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
            </button>
          </div>
        </div>
      </header>

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

        <main className="main-content">
          {errorMessage && (
            <div className="error-banner" role="alert">
              <AlertCircle size={17} />
              <span>{errorMessage}</span>
            </div>
          )}

          <section aria-label="Primary performance summary">
            <div className="primary-metrics-grid">
              {primaryLayout.map((key) => renderMetricCard(key, 'primary'))}
            </div>
          </section>

          <EquityChart
            results={results}
            currency={resultCurrency}
            comparisonTicker={resultComparisonTicker ?? undefined}
          />

          <section className="secondary-section" aria-label="Risk and benchmark analytics">
            <div className="section-heading">
              <h2>Risk &amp; Benchmark Analytics</h2>
              <span>Benchmark sensitivity, risk-adjusted ratios &amp; execution metrics</span>
            </div>
            <div className="secondary-metrics-grid">
              {secondaryLayout.map((key) => renderMetricCard(key, 'compact'))}
            </div>
          </section>
        </main>

        <TradesPanel
          trades={results ? results.trades : null}
          currency={resultCurrency}
          isOpen={tradesOpen}
          onClose={closeTrades}
        />
      </div>
    </>
  );
}
