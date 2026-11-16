import React from 'react';
import type { FeeType, StrategyType } from '../../types';
import { SUPPORTED_CURRENCIES, getCurrencySymbol } from '../../utils/currency';
import { SUPPORTED_FEE_MODELS, feeSupportsBounds, getFeeRateLabel } from '../../utils/fee';
import { SUPPORTED_STRATEGIES, getDefaultStrategyParams, getStrategySpec } from '../../utils/strategy';
import styles from './SidebarConfig.module.css';

interface SidebarConfigProps {
    ticker: string;
    setTicker: (val: string) => void;
    sameAsTraded: boolean;
    setSameAsTraded: (val: boolean) => void;
    visualComparisonTicker: string;
    setVisualComparisonTicker: (val: string) => void;
    startDate: string;
    setStartDate: (val: string) => void;
    endDate: string;
    setEndDate: (val: string) => void;
    strategyName: StrategyType;
    setStrategyName: (val: StrategyType) => void;
    strategyParams: number[];
    setStrategyParams: (val: number[]) => void;
    initialCapital: number;
    setInitialCapital: (val: number) => void;
    baseCurrency: string;
    setBaseCurrency: (val: string) => void;
    feeType: FeeType;
    setFeeType: (val: FeeType) => void;
    feeRate: number;
    setFeeRate: (val: number) => void;
    minFee: number | null;
    setMinFee: (val: number | null) => void;
    maxFee: number | null;
    setMaxFee: (val: number | null) => void;
    loadingStatus: boolean;
    executeBacktest: (e: React.SyntheticEvent) => void;
}

export default function SidebarConfig({
    ticker,
    setTicker,
    sameAsTraded,
    setSameAsTraded,
    visualComparisonTicker,
    setVisualComparisonTicker,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    strategyName,
    setStrategyName,
    strategyParams,
    setStrategyParams,
    initialCapital,
    setInitialCapital,
    baseCurrency,
    setBaseCurrency,
    feeType,
    setFeeType,
    feeRate,
    setFeeRate,
    minFee,
    setMinFee,
    maxFee,
    setMaxFee,
    loadingStatus,
    executeBacktest,
}: SidebarConfigProps) {
    const currencySymbol = getCurrencySymbol(baseCurrency);
    const strategySpec = getStrategySpec(strategyName);
    const feeRateLabel = getFeeRateLabel(feeType, currencySymbol);

    const parseOptionalFee = (raw: string): number | null => {
        if (raw === '') return null;
        const parsed = parseFloat(raw);
        return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
    };

    const handleStrategyChange = (nextStrategy: StrategyType) => {
        setStrategyName(nextStrategy);
        setStrategyParams(getDefaultStrategyParams(nextStrategy));
    };

    const handleStrategyParamChange = (index: number, raw: string) => {
        const parsed = parseFloat(raw);
        const nextParams = [...strategyParams];
        nextParams[index] = Number.isFinite(parsed) ? parsed : 0;
        setStrategyParams(nextParams);
    };

    return (
        <aside className={styles.sidebarConfig}>
            <h2>Configuration</h2>
            <form onSubmit={executeBacktest}>
                <div className={styles.inputGroup}>
                    <label htmlFor="ticker">Ticker</label>
                    <input
                        id="ticker"
                        type="text"
                        value={ticker}
                        onChange={(e) => {
                            const newTicker = e.target.value.toUpperCase();
                            setTicker(newTicker);
                            if (sameAsTraded) {
                                setVisualComparisonTicker(newTicker);
                            }
                        }}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="visualComparisonTicker">Buy & Hold Ticker</label>
                    <div className={styles.checkboxGroup}>
                        <input
                            id="sameAsTraded"
                            type="checkbox"
                            checked={sameAsTraded}
                            onChange={(e) => {
                                const isChecked = e.target.checked;
                                setSameAsTraded(isChecked);
                                if (isChecked) {
                                    setVisualComparisonTicker(ticker);
                                }
                            }}
                        />
                        <label htmlFor="sameAsTraded">Same as Traded Ticker</label>
                    </div>
                    <input
                        id="visualComparisonTicker"
                        type="text"
                        value={visualComparisonTicker}
                        disabled={sameAsTraded}
                        onChange={(e) => setVisualComparisonTicker(e.target.value.toUpperCase())}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="startDate">Start Date</label>
                    <input
                        id="startDate"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="endDate">End Date</label>
                    <input
                        id="endDate"
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="strategy">Strategy</label>
                    <select
                        id="strategy"
                        value={strategyName}
                        onChange={(e) => handleStrategyChange(e.target.value as StrategyType)}
                    >
                        {SUPPORTED_STRATEGIES.map((strategy) => (
                            <option key={strategy.type} value={strategy.type}>
                                {strategy.label}
                            </option>
                        ))}
                    </select>
                </div>

                {strategySpec.params.map((param, index) => (
                    <div key={param.id} className={styles.inputGroup}>
                        <label htmlFor={param.id}>{param.label}</label>
                        <input
                            id={param.id}
                            type="number"
                            min={param.min}
                            step={param.step ?? 'any'}
                            value={strategyParams[index] ?? param.defaultValue}
                            onChange={(e) => handleStrategyParamChange(index, e.target.value)}
                        />
                    </div>
                ))}

                <div className={styles.inputGroup}>
                    <label htmlFor="baseCurrency">Currency</label>
                    <select
                        id="baseCurrency"
                        value={baseCurrency}
                        onChange={(e) => setBaseCurrency(e.target.value)}
                    >
                        {SUPPORTED_CURRENCIES.map((curr) => (
                            <option key={curr.code} value={curr.code}>
                                {curr.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="initialCapital">Initial Capital ({currencySymbol})</label>
                    <input
                        id="initialCapital"
                        type="number"
                        min={0}
                        step="any"
                        value={initialCapital}
                        onChange={(e) => setInitialCapital(parseFloat(e.target.value) || 0)}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="feeType">Fee Model</label>
                    <select
                        id="feeType"
                        value={feeType}
                        onChange={(e) => setFeeType(e.target.value as FeeType)}
                    >
                        {SUPPORTED_FEE_MODELS.map((model) => (
                            <option key={model.type} value={model.type}>
                                {model.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="feeRate">{feeRateLabel}</label>
                    <input
                        id="feeRate"
                        type="number"
                        min={0}
                        step="any"
                        value={feeRate}
                        onChange={(e) => {
                            const parsed = parseFloat(e.target.value);
                            setFeeRate(Number.isFinite(parsed) && parsed >= 0 ? parsed : 0);
                        }}
                    />
                </div>

                {feeSupportsBounds(feeType) && (
                    <div className={styles.rowGroup}>
                        <div className={styles.inputGroup}>
                            <label htmlFor="minFee">Min Fee ({currencySymbol})</label>
                            <input
                                id="minFee"
                                type="number"
                                min={0}
                                step="any"
                                placeholder="None"
                                value={minFee ?? ''}
                                onChange={(e) => setMinFee(parseOptionalFee(e.target.value))}
                            />
                        </div>
                        <div className={styles.inputGroup}>
                            <label htmlFor="maxFee">Max Fee ({currencySymbol})</label>
                            <input
                                id="maxFee"
                                type="number"
                                min={0}
                                step="any"
                                placeholder="None"
                                value={maxFee ?? ''}
                                onChange={(e) => setMaxFee(parseOptionalFee(e.target.value))}
                            />
                        </div>
                    </div>
                )}

                <button type="submit" className={styles.btnSubmit} disabled={loadingStatus}>
                    {loadingStatus ? 'Running...' : 'Run Backtest'}
                </button>
            </form>
        </aside>
    );
}
