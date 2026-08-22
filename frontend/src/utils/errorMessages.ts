import { fill } from '../i18n';
import type { Words } from '../i18n';

const ERROR_CODE_DESCRIPTIONS: Record<string, keyof Words> = {
  DUPLICATE_INVOICE: 'errorDuplicateInvoice',
  PARTNER_NOT_FOUND: 'errorPartnerNotFound',
  AMOUNT_MISMATCH: 'errorAmountMismatch',
  VALIDATION_ERROR: 'errorValidation',
  UNKNOWN_TAX_CODE: 'errorUnknownTaxCode',
  DUE_DATE_BEFORE_ISSUE_DATE: 'errorDueBeforeIssue',
  UNAUTHORIZED: 'errorUnauthorized',
  NOT_FOUND: 'errorNotFound'
};

const ERROR_CODE_TITLES: Record<string, keyof Words> = {
  DUPLICATE_INVOICE: 'titleDuplicateInvoice',
  PARTNER_NOT_FOUND: 'titlePartnerNotFound',
  AMOUNT_MISMATCH: 'titleAmountMismatch',
  VALIDATION_ERROR: 'titleValidation',
  UNKNOWN_TAX_CODE: 'titleUnknownTaxCode',
  DUE_DATE_BEFORE_ISSUE_DATE: 'titleDueBeforeIssue',
  UNAUTHORIZED: 'titleUnauthorized',
  NOT_FOUND: 'titleNotFound'
};

export function describeErrorCode(
  code: string | null | undefined,
  detail: string | null | undefined,
  words: Words
): string {
  if (!code) {
    return detail?.trim() || words.errorUnstated;
  }
  const word = ERROR_CODE_DESCRIPTIONS[code];
  if (!word) {
    return detail?.trim() || fill(words.errorWithCode, code);
  }
  const description = words[word];
  const trimmedDetail = detail?.trim();
  return trimmedDetail && trimmedDetail !== description ? `${description} (${trimmedDetail})` : description;
}

export function describeErrorCodeTitle(code: string | null | undefined, words: Words): string {
  const word = code ? ERROR_CODE_TITLES[code] : undefined;
  return word ? words[word] : words.titleRegistrationFailed;
}
