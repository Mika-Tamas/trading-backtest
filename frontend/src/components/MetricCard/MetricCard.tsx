import React from 'react';
import styles from './MetricCard.module.css';

export type MetricTone = 'neutral' | 'positive' | 'negative' | 'accent';
export type MetricVariant = 'primary' | 'compact';

interface MetricCardProps {
    label: string;
    value: string;
    icon: React.ReactNode;
    tone?: MetricTone;
    variant?: MetricVariant;
    highlightValue?: boolean;
}

export default function MetricCard({
    label,
    value,
    icon,
    tone = 'neutral',
    variant = 'primary',
    highlightValue = false,
}: MetricCardProps) {
    const toneClass =
        tone === 'positive'
            ? styles.tonePositive
            : tone === 'negative'
              ? styles.toneNegative
              : tone === 'accent'
                ? styles.toneAccent
                : styles.toneNeutral;

    const variantClass = variant === 'compact' ? styles.variantCompact : styles.variantPrimary;
    const valueClass = `${styles.metricsValue} ${highlightValue ? styles.valueToned : ''}`;

    return (
        <div className={`${styles.metricsCard} ${toneClass} ${variantClass}`}>
            <div className={styles.metricCardHeader}>
                <h3>{label}</h3>
                <span className={styles.iconBadge} aria-hidden="true">
                    {icon}
                </span>
            </div>
            <p className={valueClass}>{value}</p>
        </div>
    );
}
