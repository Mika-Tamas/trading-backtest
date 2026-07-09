import React from 'react';
import styles from './SidebarConfig.module.css';

interface SidebarConfigProps {
    ticker: string;
    setTicker: (val: string) => void;
    sameAsBenchmark: boolean;
    setSameAsBenchmark: (val: boolean) => void;
    benchmarkTicker: string;
    setBenchmarkTicker: (val: string) => void;
    startDate: string;
    setStartDate: (val: string) => void;
    endDate: string;
    setEndDate: (val: string) => void;
    strategyName: string;
    setStrategyName: (val: string) => void;
    fastPeriod: number;
    setFastPeriod: (val: number) => void;
    slowPeriod: number;
    setSlowPeriod: (val: number) => void;
    initialCapital: number;
    setinitialCapital: (val: number) => void;
    loadingStatus: boolean;
    executeBacktest: (e: React.SyntheticEvent) => void;
}

export default function SidebarConfig({
    ticker,
    setTicker,
    sameAsBenchmark,
    setSameAsBenchmark,
    benchmarkTicker,
    setBenchmarkTicker,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    strategyName,
    setStrategyName,
    fastPeriod,
    setFastPeriod,
    slowPeriod,
    setSlowPeriod,
    initialCapital,
    setinitialCapital,
    loadingStatus,
    executeBacktest,
}: SidebarConfigProps) {
    return (
        <aside className={styles.sidebarConfig}>
            <h2>Configuration</h2>
            <form onSubmit={executeBacktest}>
                <div className={styles.inputGroup}>
                    <label htmlFor="ticker">Ticker Symbol</label>
                    <input
                        id="ticker"
                        type="text"
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="benchmarkTicker">Buy & Hold Ticker</label>
                    <div className={styles.checkboxGroup}>
                        <input
                            id="sameAsBenchmark"
                            type="checkbox"
                            checked={sameAsBenchmark}
                            onChange={(e) => setSameAsBenchmark(e.target.checked)}
                        />
                        <label htmlFor="sameAsBenchmark">Same as Benchmark Ticker</label>
                    </div>
                    <input
                        id="benchmarkTicker"
                        type="text"
                        value={sameAsBenchmark ? ticker : benchmarkTicker}
                        disabled={sameAsBenchmark}
                        onChange={(e) => setBenchmarkTicker(e.target.value.toUpperCase())}
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
                        onChange={(e) => setStrategyName(e.target.value)}
                    >
                        <option value="SMA">SMA Crossover</option>
                    </select>
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="fastPeriod">Short Window (SMA)</label>
                    <input
                        id="fastPeriod"
                        type="number"
                        value={fastPeriod}
                        onChange={(e) => setFastPeriod(parseInt(e.target.value) || 0)}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="slowPeriod">Long Window (SMA)</label>
                    <input
                        id="slowPeriod"
                        type="number"
                        value={slowPeriod}
                        onChange={(e) => setSlowPeriod(parseInt(e.target.value) || 0)}
                    />
                </div>

                <div className={styles.inputGroup}>
                    <label htmlFor="initialCapital">Initial Capital ($)</label>
                    <input
                        id="initialCapital"
                        type="number"
                        value={initialCapital}
                        onChange={(e) => setinitialCapital(parseFloat(e.target.value) || 0)}
                    />
                </div>

                <button type="submit" className={styles.btnSubmit} disabled={loadingStatus}>
                    {loadingStatus ? 'Running...' : 'Run Backtest'}
                </button>
            </form>
        </aside>
    );
}
