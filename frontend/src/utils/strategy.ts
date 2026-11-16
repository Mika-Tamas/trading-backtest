import type { StrategyType } from '../types';

export interface StrategyParamSpec {
    id: string;
    label: string;
    defaultValue: number;
    min?: number;
    step?: number | 'any';
}

export interface StrategySpec {
    type: StrategyType;
    label: string;
    params: StrategyParamSpec[];
}

export const SUPPORTED_STRATEGIES: readonly StrategySpec[] = [
    {
        type: 'SMA',
        label: 'SMA Crossover',
        params: [
            { id: 'fastPeriod', label: 'Short Window (SMA)', defaultValue: 20, min: 1, step: 1 },
            { id: 'slowPeriod', label: 'Long Window (SMA)', defaultValue: 50, min: 1, step: 1 },
        ],
    },
];

export function getStrategySpec(strategyName: StrategyType): StrategySpec {
    return (
        SUPPORTED_STRATEGIES.find((s) => s.type === strategyName) ??
        SUPPORTED_STRATEGIES[0]
    );
}

export function getDefaultStrategyParams(strategyName: StrategyType): number[] {
    return getStrategySpec(strategyName).params.map((p) => p.defaultValue);
}

export function validateStrategyParams(
    strategyName: StrategyType,
    params: number[]
): string | null {
    const spec = getStrategySpec(strategyName);
    if (params.length !== spec.params.length) {
        return `${spec.label} requires ${spec.params.length} parameters.`;
    }
    for (let i = 0; i < spec.params.length; i++) {
        const value = params[i];
        const min = spec.params[i].min ?? 1;
        if (!Number.isFinite(value) || value < min) {
            return `${spec.params[i].label} must be at least ${min}.`;
        }
    }
    return null;
}

export function buildStrategyParams(
    strategyName: StrategyType,
    params: number[]
): number[] {
    const spec = getStrategySpec(strategyName);
    return spec.params.map((p, idx) => {
        const val = params[idx];
        return Number.isFinite(val) ? val : p.defaultValue;
    });
}
