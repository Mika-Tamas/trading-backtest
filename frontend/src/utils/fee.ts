import type { FeeSettings, FeeType } from '../types';

export const SUPPORTED_FEE_MODELS: ReadonlyArray<{ type: FeeType; label: string }> = [
    { type: 'Percentage', label: 'Percentage (%)' },
    { type: 'ShareFlat', label: 'Flat per Share' },
    { type: 'OrderFlat', label: 'Flat per Order' },
];

export function feeSupportsBounds(feeType: FeeType): boolean {
    return feeType !== 'OrderFlat';
}

export function getFeeRateLabel(feeType: FeeType, currencySymbol: string): string {
    switch (feeType) {
        case 'Percentage':
            return 'Fee Rate (%)';
        case 'ShareFlat':
            return `Fee per Share (${currencySymbol})`;
        case 'OrderFlat':
            return `Fee per Order (${currencySymbol})`;
    }
}

export function validateFeeSettings(
    feeType: FeeType,
    feeRate: number,
    minFee: number | null,
    maxFee: number | null
): string | null {
    if (!Number.isFinite(feeRate) || feeRate < 0) {
        return 'Fee rate must be a non-negative number.';
    }
    if (
        feeSupportsBounds(feeType) &&
        minFee !== null &&
        maxFee !== null &&
        minFee > 0 &&
        maxFee > 0 &&
        minFee > maxFee
    ) {
        return 'Minimum fee cannot be greater than maximum fee.';
    }
    return null;
}

export function buildFeeSettings(
    feeType: FeeType,
    feeRate: number,
    minFee: number | null,
    maxFee: number | null
): FeeSettings {
    const hasBounds = feeSupportsBounds(feeType);
    return {
        type: feeType,
        rate: feeType === 'Percentage' ? feeRate / 100 : feeRate,
        min: !hasBounds || minFee === null || minFee <= 0 ? -1.0 : minFee,
        max: !hasBounds || maxFee === null || maxFee <= 0 ? -1.0 : maxFee,
    };
}
