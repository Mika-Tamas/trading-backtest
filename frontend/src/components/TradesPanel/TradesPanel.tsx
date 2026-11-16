import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDownRight, ArrowUpDown, ArrowUpRight, Inbox, List, X } from 'lucide-react';
import type { Trade } from '../../types';
import { formatCurrency } from '../../utils/currency';
import styles from './TradesPanel.module.css';

type TradeFilter = 'all' | 'wins' | 'losses';
type SortOrder = 'newest' | 'oldest';

interface TradesPanelProps {
    trades: Trade[] | null;
    currency: string;
    isOpen: boolean;
    onClose: () => void;
}

const SECONDS_PER_DAY = 86_400;

function formatDate(unixSeconds: number): string {
    return new Date(unixSeconds * 1000).toLocaleDateString(undefined, {
        year: '2-digit',
        month: 'short',
        day: 'numeric',
    });
}

function formatQuantity(quantity: number): string {
    return quantity.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function getReturnPct(trade: Trade): number {
    if (trade.entry_price === 0) return 0;
    return ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100 * trade.side;
}

function getHoldingDays(trade: Trade): number {
    return Math.max(0, Math.round((trade.exit_time - trade.entry_time) / SECONDS_PER_DAY));
}

export default function TradesPanel({ trades, currency, isOpen, onClose }: TradesPanelProps) {
    const [filter, setFilter] = useState<TradeFilter>('all');
    const [sortOrder, setSortOrder] = useState<SortOrder>('newest');
    const closeButtonRef = useRef<HTMLButtonElement>(null);

    useEffect(() => {
        if (!isOpen) return;
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKey);
        closeButtonRef.current?.focus({ preventScroll: true });
        return () => window.removeEventListener('keydown', handleKey);
    }, [isOpen, onClose]);

    const summary = useMemo(() => {
        const list = trades ?? [];
        const wins = list.filter((t) => t.realized_pnl > 0).length;
        const netPnl = list.reduce((sum, t) => sum + t.realized_pnl, 0);
        return { total: list.length, wins, losses: list.length - wins, netPnl };
    }, [trades]);

    const visibleTrades = useMemo(() => {
        const list = (trades ?? []).filter((t) => {
            if (filter === 'wins') return t.realized_pnl > 0;
            if (filter === 'losses') return t.realized_pnl <= 0;
            return true;
        });
        return [...list].sort((a, b) =>
            sortOrder === 'newest' ? b.exit_time - a.exit_time : a.exit_time - b.exit_time
        );
    }, [trades, filter, sortOrder]);

    const money = (value: number, fractionDigits = 2) =>
        formatCurrency(value, currency, {
            minimumFractionDigits: fractionDigits,
            maximumFractionDigits: fractionDigits,
        });

    const signedMoney = (value: number) => `${value > 0 ? '+' : ''}${money(value)}`;

    const hasResults = trades !== null;

    return (
        <>
            <div
                className={`${styles.backdrop} ${isOpen ? styles.backdropVisible : ''}`}
                onClick={onClose}
                aria-hidden="true"
            />

            <aside
                id="trades-panel"
                className={`${styles.panel} ${isOpen ? styles.panelOpen : ''}`}
                aria-label="Executed trades"
            >
                <div className={styles.panelHeader}>
                    <div className={styles.titleGroup}>
                        <List size={16} className={styles.headerIcon} />
                        <h2>Trade Log</h2>
                        {hasResults && <span className={styles.countBadge}>{summary.total}</span>}
                    </div>
                    <button
                        ref={closeButtonRef}
                        type="button"
                        className={styles.closeButton}
                        onClick={onClose}
                        aria-label="Close trade log"
                    >
                        <X size={16} />
                    </button>
                </div>

                {hasResults && summary.total > 0 && (
                    <>
                        <div className={styles.summaryGrid}>
                            <div className={styles.summaryItem}>
                                <span className={styles.summaryLabel}>Net P&amp;L</span>
                                <span
                                    className={`${styles.summaryValue} ${
                                        summary.netPnl > 0
                                            ? styles.positive
                                            : summary.netPnl < 0
                                              ? styles.negative
                                              : ''
                                    }`}
                                >
                                    {signedMoney(summary.netPnl)}
                                </span>
                            </div>
                            <div className={styles.summaryItem}>
                                <span className={styles.summaryLabel}>Wins / Losses</span>
                                <span className={styles.summaryValue}>
                                    <span className={styles.positive}>{summary.wins}</span>
                                    <span className={styles.summarySep}>/</span>
                                    <span className={styles.negative}>{summary.losses}</span>
                                </span>
                            </div>
                        </div>

                        <div className={styles.toolbar}>
                            <div className={styles.segmented} role="tablist" aria-label="Filter trades">
                                {(['all', 'wins', 'losses'] as const).map((key) => (
                                    <button
                                        key={key}
                                        type="button"
                                        role="tab"
                                        aria-selected={filter === key}
                                        className={`${styles.segment} ${filter === key ? styles.segmentActive : ''}`}
                                        onClick={() => setFilter(key)}
                                    >
                                        {key === 'all' ? 'All' : key === 'wins' ? 'Wins' : 'Losses'}
                                    </button>
                                ))}
                            </div>
                            <button
                                type="button"
                                className={styles.sortButton}
                                onClick={() => setSortOrder((s) => (s === 'newest' ? 'oldest' : 'newest'))}
                                title="Toggle sort order"
                            >
                                <ArrowUpDown size={13} />
                                <span>{sortOrder === 'newest' ? 'Newest' : 'Oldest'}</span>
                            </button>
                        </div>
                    </>
                )}

                <div className={styles.listArea}>
                    {!hasResults && (
                        <div className={styles.emptyState}>
                            <Inbox size={22} />
                            <p>Run a backtest to see the trades executed by the engine.</p>
                        </div>
                    )}

                    {hasResults && summary.total === 0 && (
                        <div className={styles.emptyState}>
                            <Inbox size={22} />
                            <p>The strategy did not close any trades in this period.</p>
                        </div>
                    )}

                    {hasResults && summary.total > 0 && visibleTrades.length === 0 && (
                        <div className={styles.emptyState}>
                            <p>No trades match this filter.</p>
                        </div>
                    )}

                    {visibleTrades.length > 0 && (
                        <ul className={styles.tradeList}>
                            {visibleTrades.map((trade, index) => {
                                const isLong = trade.side >= 0;
                                const pnlClass =
                                    trade.realized_pnl > 0
                                        ? styles.positive
                                        : trade.realized_pnl < 0
                                          ? styles.negative
                                          : '';
                                const returnPct = getReturnPct(trade);
                                const days = getHoldingDays(trade);

                                return (
                                    <li
                                        key={`${trade.entry_time}-${trade.exit_time}-${index}`}
                                        className={styles.tradeCard}
                                    >
                                        <div className={styles.tradeTop}>
                                            <div className={styles.tradeIdentity}>
                                                <span
                                                    className={`${styles.sideBadge} ${
                                                        isLong ? styles.sideLong : styles.sideShort
                                                    }`}
                                                >
                                                    {isLong ? (
                                                        <ArrowUpRight size={12} />
                                                    ) : (
                                                        <ArrowDownRight size={12} />
                                                    )}
                                                    {isLong ? 'Long' : 'Short'}
                                                </span>
                                                <span className={styles.ticker}>{trade.ticker}</span>
                                            </div>
                                            <div className={styles.pnlGroup}>
                                                <span className={`${styles.pnl} ${pnlClass}`}>
                                                    {signedMoney(trade.realized_pnl)}
                                                </span>
                                                <span className={`${styles.returnPct} ${pnlClass}`}>
                                                    {returnPct > 0 ? '+' : ''}
                                                    {returnPct.toFixed(2)}%
                                                </span>
                                            </div>
                                        </div>

                                        <div className={styles.tradeRoute}>
                                            <div className={styles.routeLeg}>
                                                <span className={styles.routeLabel}>Entry</span>
                                                <span className={styles.routeDate}>
                                                    {formatDate(trade.entry_time)}
                                                </span>
                                                <span className={styles.routePrice}>
                                                    {money(trade.entry_price)}
                                                </span>
                                            </div>
                                            <span className={styles.routeArrow} aria-hidden="true">
                                                →
                                            </span>
                                            <div className={`${styles.routeLeg} ${styles.routeLegEnd}`}>
                                                <span className={styles.routeLabel}>Exit</span>
                                                <span className={styles.routeDate}>
                                                    {formatDate(trade.exit_time)}
                                                </span>
                                                <span className={styles.routePrice}>
                                                    {money(trade.exit_price)}
                                                </span>
                                            </div>
                                        </div>

                                        <div className={styles.tradeMeta}>
                                            <span>
                                                Qty <strong>{formatQuantity(trade.quantity)}</strong>
                                            </span>
                                            <span>
                                                Fee <strong>{money(trade.fee_paid)}</strong>
                                            </span>
                                            <span>
                                                <strong>{days}</strong> {days === 1 ? 'day' : 'days'}
                                            </span>
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </div>
            </aside>
        </>
    );
}
