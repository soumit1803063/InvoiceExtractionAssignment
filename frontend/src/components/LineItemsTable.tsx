import { useRef } from 'react';
import type { EditableInvoiceLine } from '../model/invoiceDraft';
import { fill, useWords } from '../i18n';
import type { TaxCode } from '../types/contract';
import { formatCurrency } from '../utils/formatting';
import { isIntegerInputValid, parseIntegerOrNull, sumDefined } from '../utils/parsing';

interface LineItemsTableProps {
  lines: EditableInvoiceLine[];
  subtotalText: string;
  isDisabled: boolean;
  onLineFieldChange: (lineIndex: number, fieldKey: keyof EditableInvoiceLine, nextValue: string) => void;
  onAddLine: () => void;
  onRemoveLine: (lineIndex: number) => void;
}

const TAX_CODE_OPTIONS: Array<{ value: TaxCode | ''; label: string }> = [
  { value: '', label: '—' },
  { value: 'T10', label: 'T10 (10%)' },
  { value: 'T08', label: 'T08 (8%)' }
];

export function LineItemsTable({
  lines,
  subtotalText,
  isDisabled,
  onLineFieldChange,
  onAddLine,
  onRemoveLine
}: LineItemsTableProps) {
  const words = useWords();
  const unitInputRefs = useRef<Array<HTMLInputElement | null>>([]);

  const indexOfFirstMissingUnit = lines.findIndex((line) => line.unit.trim() === '');
  const missingUnitCount = lines.filter((line) => line.unit.trim() === '').length;
  const linesTotal = sumDefined(lines.map((line) => parseIntegerOrNull(line.amount)));
  const subtotalValue = parseIntegerOrNull(subtotalText);
  const isCrossfootMatching = subtotalValue !== null && subtotalValue === linesTotal;

  function focusFirstMissingUnit() {
    if (indexOfFirstMissingUnit < 0) {
      return;
    }
    unitInputRefs.current[indexOfFirstMissingUnit]?.focus();
  }

  return (
    <section className="panel">
      <header className="panel__header">
        <h2 className="panel__title">
          {words.lineItems}

        </h2>
        <span className="panel__summary">{lines.length} lines</span>
      </header>

      {missingUnitCount > 0 ? (
        <div className="unit-alert" role="alert">
          <div>
            <p className="unit-alert__title">
              {missingUnitCount} {words.linesHaveNoUnit}
            </p>
            <p className="unit-alert__detail">
              {words.accountingSystemRequiresUnitEvery}
            </p>
          </div>
          <button type="button" className="button button--ghost" onClick={focusFirstMissingUnit} disabled={isDisabled}>
            {words.goFirstMissingUnit}
          </button>
        </div>
      ) : null}

      <div className="table-scroll">
        <table className="line-items">
          <thead>
            <tr>
              <th className="line-items__index-column">#</th>
              <th>{words.description}</th>
              <th className="line-items__number-column">{words.qty}</th>
              <th className="line-items__unit-column">{words.unit}</th>
              <th className="line-items__number-column">{words.unitPrice}</th>
              <th className="line-items__number-column">{words.amount}</th>
              <th className="line-items__tax-column">{words.tax}</th>
              <th className="line-items__action-column" />
            </tr>
          </thead>
          <tbody>
            {lines.map((line, lineIndex) => {
              const isUnitMissing = line.unit.trim() === '';
              return (
                <tr key={lineIndex} className={isUnitMissing ? 'line-items__row--needs-unit' : undefined}>
                  <td className="line-items__index-column">{lineIndex + 1}</td>
                  <td>
                    <input
                      className="cell-input"
                      value={line.description}
                      disabled={isDisabled}
                      aria-label={fill(words.ariaDescription, String(lineIndex + 1))}
                      onChange={(event) => onLineFieldChange(lineIndex, 'description', event.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className={`cell-input cell-input--end${isIntegerInputValid(line.quantity) ? '' : ' cell-input--invalid'}`}
                      value={line.quantity}
                      inputMode="numeric"
                      disabled={isDisabled}
                      aria-label={fill(words.ariaQuantity, String(lineIndex + 1))}
                      onChange={(event) => onLineFieldChange(lineIndex, 'quantity', event.target.value)}
                    />
                  </td>
                  <td
                    className={
                      isUnitMissing ? 'line-items__unit-cell line-items__unit-cell--missing' : 'line-items__unit-cell'
                    }
                  >
                    <input
                      ref={(element) => {
                        unitInputRefs.current[lineIndex] = element;
                      }}
                      className={`cell-input${isUnitMissing ? ' cell-input--missing' : ''}`}
                      value={line.unit}
                      placeholder="{words.required}"
                      disabled={isDisabled}
                      aria-label={fill(words.ariaUnit, String(lineIndex + 1))}
                      aria-invalid={isUnitMissing}
                      onChange={(event) => onLineFieldChange(lineIndex, 'unit', event.target.value)}
                    />
                    {isUnitMissing ? <span className="line-items__unit-hint">must be filled in</span> : null}
                  </td>
                  <td>
                    <input
                      className={`cell-input cell-input--end${isIntegerInputValid(line.unit_price) ? '' : ' cell-input--invalid'}`}
                      value={line.unit_price}
                      inputMode="numeric"
                      disabled={isDisabled}
                      aria-label={fill(words.ariaUnitPrice, String(lineIndex + 1))}
                      onChange={(event) => onLineFieldChange(lineIndex, 'unit_price', event.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className={`cell-input cell-input--end${isIntegerInputValid(line.amount) ? '' : ' cell-input--invalid'}`}
                      value={line.amount}
                      inputMode="numeric"
                      disabled={isDisabled}
                      aria-label={fill(words.ariaAmount, String(lineIndex + 1))}
                      onChange={(event) => onLineFieldChange(lineIndex, 'amount', event.target.value)}
                    />
                  </td>
                  <td>
                    <select
                      className="cell-input"
                      value={line.tax_code}
                      disabled={isDisabled}
                      aria-label={fill(words.ariaTaxCode, String(lineIndex + 1))}
                      onChange={(event) => onLineFieldChange(lineIndex, 'tax_code', event.target.value)}
                    >
                      {TAX_CODE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="line-items__action-column">
                    <button
                      type="button"
                      className="button button--icon"
                      disabled={isDisabled}
                      aria-label={fill(words.ariaRemoveLine, String(lineIndex + 1))}
                      onClick={() => onRemoveLine(lineIndex)}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
            {lines.length === 0 ? (
              <tr>
                <td colSpan={8} className="line-items__empty">
                  {words.noLineItemsExtracted}
                </td>
              </tr>
            ) : null}
          </tbody>
          <tfoot>
            <tr className={isCrossfootMatching ? undefined : 'line-items__footer--mismatch'}>
              <td colSpan={5} className="line-items__footer-label">
                {words.linesAddUp}
              </td>
              <td className="line-items__number-column line-items__footer-value">{formatCurrency(linesTotal)}</td>
              <td colSpan={2} className="line-items__footer-note">
                {subtotalValue === null
                  ? words.noSubtotalToCompare
                  : isCrossfootMatching
                    ? fill(words.matchesSubtotal, formatCurrency(subtotalValue))
                    : fill(words.doesNotMatchSubtotal, formatCurrency(subtotalValue))}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="panel__footer-actions">
        <button type="button" className="button button--ghost" onClick={onAddLine} disabled={isDisabled}>
          {words.addLine}
        </button>
      </div>
    </section>
  );
}
