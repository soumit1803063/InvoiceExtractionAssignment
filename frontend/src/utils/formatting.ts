const integerCurrencyFormatters = new Map<string, Intl.NumberFormat>();

function currencyFormatterFor(currency: string): Intl.NumberFormat {
  const cached = integerCurrencyFormatters.get(currency);
  if (cached) {
    return cached;
  }
  const formatter = new Intl.NumberFormat('ja-JP', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
    minimumFractionDigits: 0
  });
  integerCurrencyFormatters.set(currency, formatter);
  return formatter;
}

export function formatCurrency(value: number | null | undefined, currency = 'JPY'): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return currencyFormatterFor(currency).format(value);
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString('ja-JP', { hour12: false });
}

export function humanizeIdentifier(value: string): string {
  return value
    .replace(/\[(\d+)\]/g, ' $1')
    .replace(/[._]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^./, (character) => character.toUpperCase());
}


