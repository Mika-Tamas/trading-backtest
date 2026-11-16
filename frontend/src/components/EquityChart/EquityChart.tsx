import React from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { LineChart } from 'lucide-react';
import type { BacktestResponse } from '../../types';
import { formatCurrency } from '../../utils/currency';
import styles from './EquityChart.module.css';

interface EquityChartProps {
  results: BacktestResponse | null;
  currency: string;
  comparisonTicker?: string;
}

interface ChartPoint {
  timestamp: number;
  equity: number;
  comparison_curve: number;
  market_curve: number;
}

interface TooltipEntry {
  dataKey?: string | number;
  name?: string;
  value?: number | string;
  color?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: ReadonlyArray<TooltipEntry>;
  label?: number | string;
  currency: string;
}

function CustomTooltip({ active, payload, label, currency }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const timestamp = typeof label === 'number' ? label : Number(label);
  const formattedDate = Number.isFinite(timestamp)
    ? new Date(timestamp).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : String(label ?? '');

  const sortedPayload = [...payload].sort((a, b) => {
    const order = (key: string | number | undefined) => {
      if (key === 'equity') return 0;
      if (key === 'comparison_curve') return 1;
      return 2;
    };
    return order(a.dataKey) - order(b.dataKey);
  });

  return (
    <div className={styles.tooltipCard}>
      <div className={styles.tooltipDate}>{formattedDate}</div>
      <div className={styles.tooltipRows}>
        {sortedPayload.map((entry) => {
          const val = Number(entry.value ?? 0);
          return (
            <div key={String(entry.dataKey ?? entry.name)} className={styles.tooltipRow}>
              <span className={styles.tooltipLabelGroup}>
                <span
                  className={styles.tooltipDot}
                  style={{ backgroundColor: entry.color || 'var(--chart-strategy)' }}
                />
                <span className={styles.tooltipName}>{entry.name}</span>
              </span>
              <span className={styles.tooltipValue}>
                {formatCurrency(val, currency, {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                })}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function EquityChart({
  results,
  currency,
  comparisonTicker,
}: EquityChartProps) {
  const chartData: ChartPoint[] = React.useMemo(() => {
    if (!results) return [];

    return results.timestamps.map((timestamp, index) => ({
      timestamp: timestamp * 1000,
      equity: results.equity_curve[index],
      comparison_curve: results.comparison_curve[index],
      market_curve: results.market_curve[index],
    }));
  }, [results]);

  const buyHoldLabel = comparisonTicker ? `Buy & Hold (${comparisonTicker})` : 'Buy & Hold';

  return (
    <section className={styles.chartContainer}>
      <div className={styles.chartHeader}>
        <div className={styles.chartTitleGroup}>
          <h3>Equity Curve</h3>
          <span className={styles.chartSubtitle}>
            Portfolio performance vs. benchmarks ({currency})
          </span>
        </div>

        <div className={styles.legendGroup} aria-label="Chart series legend">
          <span className={styles.legendBadge}>
            <span className={`${styles.legendLine} ${styles.legendStrategy}`} />
            <span>Strategy Equity</span>
          </span>
          <span className={styles.legendBadge}>
            <span className={`${styles.legendLine} ${styles.legendBuyHold}`} />
            <span>{buyHoldLabel}</span>
          </span>
          <span className={styles.legendBadge}>
            <span className={`${styles.legendLine} ${styles.legendMarket}`} />
            <span>Broad Market (SPY)</span>
          </span>
        </div>
      </div>

      <div className={styles.chartBox}>
        {results ? (
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
              <defs>
                <linearGradient id="strategyAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-strategy)" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="var(--chart-strategy)" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--chart-grid)"
                vertical={false}
              />
              <XAxis
                dataKey="timestamp"
                axisLine={{ stroke: 'var(--border-color)' }}
                tickLine={false}
                minTickGap={44}
                dy={8}
                tick={{
                  fontSize: 11,
                  fill: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                }}
                tickFormatter={(unixTime) =>
                  new Date(unixTime).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                  })
                }
              />
              <YAxis
                width={76}
                axisLine={false}
                tickLine={false}
                tick={{
                  fontSize: 11,
                  fill: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                }}
                domain={['auto', 'auto']}
                tickFormatter={(tick) =>
                  formatCurrency(tick, currency, { maximumFractionDigits: 0 })
                }
              />
              <Tooltip
                cursor={{
                  stroke: 'var(--chart-cursor)',
                  strokeWidth: 1,
                  strokeDasharray: '4 4',
                }}
                content={<CustomTooltip currency={currency} />}
              />

              <Line
                name="Broad Market (SPY)"
                type="monotone"
                dataKey="market_curve"
                stroke="var(--chart-market)"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                dot={false}
                activeDot={{ r: 3.5, strokeWidth: 0 }}
              />
              <Line
                name={buyHoldLabel}
                type="monotone"
                dataKey="comparison_curve"
                stroke="var(--chart-buyhold)"
                strokeWidth={1.75}
                strokeDasharray="5 3"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
              <Area
                name="Strategy Equity"
                type="monotone"
                dataKey="equity"
                stroke="var(--chart-strategy)"
                strokeWidth={2.25}
                fill="url(#strategyAreaGrad)"
                fillOpacity={1}
                dot={false}
                activeDot={{ r: 4.5, strokeWidth: 2, stroke: 'var(--bg-card)' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className={styles.chartPlaceholder}>
            <div className={styles.placeholderIcon}>
              <LineChart size={22} />
            </div>
            <p className={styles.placeholderTitle}>No simulation data yet</p>
            <p className={styles.placeholderHint}>
              Configure your asset, strategy parameters, and capital settings on the left, then click{' '}
              <strong>Run Backtest</strong> to visualize performance.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
