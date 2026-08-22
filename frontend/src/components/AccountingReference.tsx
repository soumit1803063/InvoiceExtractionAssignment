import { useCallback } from 'react';
import { fetchReferenceData } from '../api/documents';
import { useAsyncData } from '../hooks/useAsyncData';
import { useWords } from '../i18n';
import type { InvoiceFields, ReferenceData } from '../types/contract';

interface AccountingReferenceProps {
  fields: InvoiceFields;
}

export function AccountingReference({ fields }: AccountingReferenceProps) {
  const load = useCallback((signal: AbortSignal) => fetchReferenceData(signal), []);
  const reference = useAsyncData<ReferenceData>(load);
  const words = useWords();

  if (reference.isLoading || !reference.data) {
    return null;
  }

  const { partners, tax_rates, lookup_failure_reason } = reference.data;

  return (
    <section className="panel">
      <header className="panel__header">
        <h2 className="panel__title">{words.fromAccountingSystem}</h2>
        <span className="panel__summary">
          {words.readLiveFrom} GET /partners · /tax-codes
        </span>
      </header>

      {lookup_failure_reason ? <p className="reference__error">{lookup_failure_reason}</p> : null}

      <table className="reference">
        <thead>
          <tr>
            <th scope="col">{words.partnerCode}</th>
            <th scope="col">{words.registrationNumber}</th>
            <th scope="col">{words.supplier}</th>
          </tr>
        </thead>
        <tbody>
          {partners.map((partner) => {
            const isMatch =
              partner.partner_code === fields.partner_code ||
              partner.registration_no === fields.registration_number;
            return (
              <tr key={partner.partner_code} className={isMatch ? 'reference__row--match' : undefined}>
                <td>
                  <code>{partner.partner_code}</code>
                </td>
                <td>
                  <code>{partner.registration_no ?? '—'}</code>
                </td>
                <td>{partner.name ?? '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="reference__rates">
        {words.acceptedTaxCodes}:{' '}
        {tax_rates.map((rate) => `${rate.code} (${Math.round(rate.rate * 100)}%)`).join(' · ')}
      </p>
    </section>
  );
}
