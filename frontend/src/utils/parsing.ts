const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function parseIntegerOrNull(text: string): number | null {
  const trimmed = text.trim().replace(/[,\s￥¥]/g, '');
  if (trimmed === '' || trimmed === '-') {
    return null;
  }
  if (!/^-?\d+$/.test(trimmed)) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function isIntegerInputValid(text: string): boolean {
  const trimmed = text.trim().replace(/[,\s￥¥]/g, '');
  return trimmed === '' || /^-?\d+$/.test(trimmed);
}

export function isIsoDateValid(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed === '') {
    return true;
  }
  if (!ISO_DATE_PATTERN.test(trimmed)) {
    return false;
  }
  const parsed = new Date(`${trimmed}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === trimmed;
}

export function textToNullableString(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === '' ? null : trimmed;
}

export function nullableToText(value: string | number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value);
}

export function sumDefined(values: Array<number | null | undefined>): number {
  return values.reduce<number>((total, value) => total + (typeof value === 'number' ? value : 0), 0);
}
