export const SUPPORTED_CURRENCIES = [
    { code: 'USD', label: 'USD ($)' },
    { code: 'EUR', label: 'EUR (€)' },
    { code: 'GBP', label: 'GBP (£)' },
    { code: 'JPY', label: 'JPY (¥)' },
    { code: 'CHF', label: 'CHF' },
    { code: 'CAD', label: 'CAD (CA$)' },
    { code: 'AUD', label: 'AUD (A$)' },
    { code: 'HUF', label: 'HUF (Ft)' },
] as const;

export function getCurrencySymbol(currency: string): string {
    try {
        const parts = new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency,
            currencyDisplay: 'narrowSymbol',
        }).formatToParts(0);
        return parts.find((part) => part.type === 'currency')?.value ?? currency;
    } catch {
        return currency;
    }
}

export function formatCurrency(
    value: number,
    currency: string,
    options?: { minimumFractionDigits?: number; maximumFractionDigits?: number }
): string {
    const minimumFractionDigits = options?.minimumFractionDigits ?? 0;
    const maximumFractionDigits = options?.maximumFractionDigits ?? 0;

    try {
        return new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency,
            currencyDisplay: 'narrowSymbol',
            minimumFractionDigits,
            maximumFractionDigits,
        }).format(value);
    } catch {
        const formatted = value.toLocaleString(undefined, {
            minimumFractionDigits,
            maximumFractionDigits,
        });
        return `${currency} ${formatted}`;
    }
}
