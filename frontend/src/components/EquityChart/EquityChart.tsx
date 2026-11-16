import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import type { BacktestResponse } from '../../types';
import { formatCurrency } from '../../utils/currency';
import styles from './EquityChart.module.css';

interface EquityChartProps {
  results: BacktestResponse | null;
  currency: string;
}

export default function EquityChart({ results, currency }: EquityChartProps) {
  const chartData = React.useMemo(() => {
    if (!results) return [];

    return results.timestamps.map((timestamp, index) => {
      return {
        timestamp: timestamp * 1000,
        equity: results.equity_curve[index],
        comparison_curve: results.comparison_curve[index],
        market_curve: results.market_curve[index]
      };
    });
  }, [results]);

  return (
    <div className={styles.chartContainer}>
      <h3>Equity Curve</h3>
      <div className={styles.chartBox}>
        {results ? (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis
                dataKey="timestamp"
                stroke="var(--text-primary)"
                tickLine={false}
                minTickGap={40}
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                tickFormatter={(unixTime) =>
                  new Date(unixTime).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                  })
                }
              />
              <YAxis
                width={80}
                stroke="var(--text-primary)"
                tickLine={false}
                domain={['auto', 'auto']}
                tickFormatter={(tick) => formatCurrency(tick, currency, { maximumFractionDigits: 0 })}
              />
              <Tooltip
                itemSorter={(item) => -(Number(item.value) || 0)}
                labelFormatter={(unixTime) =>
                  new Date(unixTime).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })
                }
                formatter={(value, name) => [
                  formatCurrency(Number(value ?? 0), currency, { maximumFractionDigits: 0 }),
                  String(name ?? ''),
                ]}
                contentStyle={{
                  backgroundColor: 'var(--bg-input)',
                  borderColor: 'var(--border-color)',
                  borderRadius: '18px',
                  boxShadow: 'var(--shadow)',
                }}
              />
              <Legend
                itemSorter={(item) => {
                  const label = item.value;
                  if (label === 'Strategy Equity') return 1;
                  if (label === 'Buy & Hold') return 2;
                  return 3;
                }}
                verticalAlign="top"
                height={36}
                iconType="plainline"
                wrapperStyle={{ fontSize: "14px", color: "var(--text-secondary)" }}

              />

              <Line
                name="Broad Market"
                type="monotone"
                dataKey="market_curve"
                stroke="rgba(255, 255, 255, 0.5)"
                strokeWidth={0.8}
                strokeDasharray="2 2"
                dot={false}
              />
              <Line
                name="Buy & Hold"
                type="monotone"
                dataKey="comparison_curve"
                stroke="#b4f2a0"
                strokeWidth={0.8}
                strokeDasharray="2 2"
                dot={false}
              />
              <Line
                name="Strategy Equity"
                type="monotone"
                dataKey="equity"
                stroke="var(--text-accent)"
                strokeWidth={2.2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className={styles.chartPlaceholder}>
            Run a backtest to view the performance graph
          </div>
        )}
      </div>
    </div>
  );
}
