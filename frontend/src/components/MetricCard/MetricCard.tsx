import React from "react";
import styles from "./MetricCard.module.css";

interface MetricCardProps {
    label: string;
    value: string;
    icon: React.ReactNode;
}

export default function MetricCard({ label, value, icon }: MetricCardProps) {
    return (
        <div className={styles.metricsCard}>
            <div className={styles.metricCardHeader}>
                <h3>{label}</h3>
                {icon}
            </div>
            <p className={styles.metricsValue}>{value}</p>
        </div>
    );
}
