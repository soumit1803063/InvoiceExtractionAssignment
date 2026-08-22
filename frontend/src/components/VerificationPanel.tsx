import type { InvoiceFields, Verification } from '../types/contract';
import { formatCurrency, humanizeIdentifier } from '../utils/formatting';
import { sumDefined } from '../utils/parsing';
import { fill, useWords } from '../i18n';
import type { Words } from '../i18n';

interface VerificationPanelProps {
  verification: Verification;
  blockingReasons: string[];
  fields: InvoiceFields;
  duplicateSourceName: string | null;
}

interface CheckRow {
  key: string;
  label: string;
  passed: boolean;
  explanation: string;
  detail: string;
}

function buildCheckRows(
  verification: Verification,
  fields: InvoiceFields,
  duplicateSourceName: string | null,
  words: Words
): CheckRow[] {
  const lineTotal = sumDefined((fields.lines ?? []).map((line) => line.amount));
  const subtotalPlusTax =
    fields.subtotal !== null && fields.tax_amount !== null ? fields.subtotal + fields.tax_amount : null;

  return [
    {
      key: 'crossfoot',
      label: words.checkCrossfoot,
      passed: verification.crossfoot_ok,
      explanation: words.everyLineAmountAddedUp,
      detail: fill(words.detailLinesAddUp, formatCurrency(lineTotal), formatCurrency(fields.subtotal))
    },
    {
      key: 'tax',
      label: words.checkTax,
      passed: verification.tax_ok,
      explanation: words.taxRecalculatedPerTaxCode,
      detail: fill(words.detailTaxDeclared, formatCurrency(fields.tax_amount))
    },
    {
      key: 'total',
      label: words.checkTotal,
      passed: verification.total_ok,
      explanation: words.arithmeticInvoiceItselfMustHold,
      detail:
        subtotalPlusTax === null
          ? words.subtotalOrTaxMissingSo
          : fill(
              words.detailTotalSum,
              formatCurrency(fields.subtotal),
              formatCurrency(fields.tax_amount),
              formatCurrency(subtotalPlusTax),
              formatCurrency(fields.total_amount)
            )
    },
    {
      key: 'printed_total',
      label: words.checkPrintedTotal,
      passed: verification.printed_total_ok,
      explanation: words.guardsAgainstReadingErrorComputed,
      detail: fill(
        words.detailPrintedTotal,
        formatCurrency(fields.printed_total),
        formatCurrency(fields.total_amount)
      )
    },
    {
      key: 'partner',
      label: words.checkPartner,
      passed: verification.partner_matched,
      explanation: words.onlySuppliersAlreadyAccountingSystem,
      detail: fields.partner_code
        ? fill(words.detailPartnerCode, fields.partner_code)
        : words.detailNoPartnerCode
    },
    {
      key: 'duplicate',
      label: words.checkDuplicate,
      passed: verification.duplicate_of === null,
      explanation: words.sameInvoiceNumberSameSupplier,
      detail:
        verification.duplicate_of === null
          ? words.detailNoDuplicate
          : fill(words.detailDuplicateOf, duplicateSourceName ?? verification.duplicate_of)
    },
    {
      key: 'missing_required',
      label: words.checkRequired,
      passed: verification.missing_required.length === 0,
      explanation: words.accountingSystemRejectsRecordOutright,
      detail:
        verification.missing_required.length === 0
          ? words.detailNothingMissing
          : fill(words.detailStillMissing, verification.missing_required.map(humanizeIdentifier).join(', '))
    }
  ];
}

export function VerificationPanel({
  verification,
  blockingReasons,
  fields,
  duplicateSourceName
}: VerificationPanelProps) {
  const words = useWords();
  const rows = buildCheckRows(verification, fields, duplicateSourceName, words);
  const passedRatio =
    verification.checks_total > 0 ? Math.round((verification.checks_passed / verification.checks_total) * 100) : 0;

  return (
    <section className="panel">
      <header className="panel__header">
        <h2 className="panel__title">{words.verification}</h2>
        <span className="panel__summary">
          {fill(words.checksPassedOf, String(verification.checks_passed), String(verification.checks_total))}
        </span>
      </header>

      <div className="verification__progress" aria-hidden="true">
        <div className="verification__progress-fill" style={{ width: `${passedRatio}%` }} />
      </div>

      <ul className="verification__list">
        {rows.map((row) => (
          <li key={row.key} className={`verification__row verification__row--${row.passed ? 'pass' : 'fail'}`}>
            <span className="verification__mark" aria-hidden="true">
              {row.passed ? '✓' : '✕'}
            </span>
            <div className="verification__text">
              <p className="verification__label">
                <span className="verification__label-text">{row.label}</span>
                <span className="verification__outcome">{row.passed ? words.passed : words.failed}</span>
              </p>
              <p className="verification__explanation">{row.explanation}</p>
              <p className="verification__detail">{row.detail}</p>
            </div>
          </li>
        ))}
      </ul>

      {blockingReasons.length > 0 ? (
        <div className="verification__blocking">
          <p className="verification__blocking-title">{words.blockingRegistration}</p>
          <ul>
            {blockingReasons.map((reason) => (
              <li key={reason}>{humanizeIdentifier(reason)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
