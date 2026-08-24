import { useCallback } from 'react';
import { fetchHealth, fetchReferenceData } from '../api/documents';
import { MessageBanner } from '../components/MessageBanner';
import { useAsyncData } from '../hooks/useAsyncData';
import { useWords } from '../i18n';
import type { HealthResponse, ReferenceData } from '../types/contract';

export function DashboardPage() {
  const words = useWords();
  const loadHealth = useCallback((signal: AbortSignal) => fetchHealth(signal), []);
  const loadReference = useCallback((signal: AbortSignal) => fetchReferenceData(signal), []);
  const health = useAsyncData<HealthResponse>(loadHealth);
  const reference = useAsyncData<ReferenceData>(loadReference);

  const partners = reference.data?.partners ?? [];
  const taxRates = reference.data?.tax_rates ?? [];
  const isReachable = health.data?.accounting_api_reachable === true;
  const isBusy = health.isLoading || reference.isLoading;

  function reloadAll() {
    health.reload();
    reference.reload();
  }

  return (
    <div className="page">
      <section className="panel">
        <div className="panel__header">
          <h2 className="panel__title">{words.whatTheAccountingSystemAccepts}</h2>
          <button
            type="button"
            className="button button--ghost"
            onClick={reloadAll}
            disabled={isBusy}
          >
            {isBusy ? words.loading : words.refresh}
          </button>
        </div>
        <p className="panel__note">{words.readLiveFromTheAccountingSystem}</p>

        {reference.error || reference.data?.lookup_failure_reason ? (
          <MessageBanner tone="danger" title={words.referenceCouldNotBeRead}>
            <p>{reference.error ?? reference.data?.lookup_failure_reason}</p>
          </MessageBanner>
        ) : null}

        <div className="tiles">
          <div className="tile">
            <span className="tile__label">{words.livenessCheck}</span>
            <span className="tile__value">
              {health.isLoading ? words.loading : isReachable ? words.reachable : words.unreachable}
            </span>
            <span className="tile__note">{words.livenessCheckEndpoint}</span>
          </div>
          <div className="tile">
            <span className="tile__label">{words.suppliersRegisterable}</span>
            <span className="tile__value">{partners.length}</span>
            <span className="tile__note">{words.supplierMasterEndpoint}</span>
          </div>
          <div className="tile">
            <span className="tile__label">{words.taxCodesAccepted}</span>
            <span className="tile__value">{taxRates.length}</span>
            <span className="tile__note">{words.taxCodeListEndpoint}</span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2 className="panel__title">{words.supplierMaster}</h2>
          <span className="panel__summary">{words.supplierMasterEndpoint}</span>
        </div>
        {partners.length === 0 ? (
          <div className="app__placeholder">
            <p className="app__placeholder-title">
              {reference.isLoading ? words.loading : words.noSuppliersReturned}
            </p>
          </div>
        ) : (
          <table className="queue">
            <thead>
              <tr>
                <th scope="col">{words.partnerCode}</th>
                <th scope="col">{words.supplierName}</th>
                <th scope="col">{words.registrationNumber}</th>
                <th scope="col">{words.aliases}</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((partner) => (
                <tr key={partner.partner_code} className="queue__row queue__row--reading">
                  <td className="queue__cell queue__cell--id">
                    <code>{partner.partner_code}</code>
                  </td>
                  <td className="queue__cell">{partner.name}</td>
                  <td className="queue__cell queue__cell--id">
                    <code>{partner.registration_no}</code>
                  </td>
                  <td className="queue__cell">{partner.aliases.join(' / ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2 className="panel__title">{words.taxCodeList}</h2>
          <span className="panel__summary">{words.taxCodeListEndpoint}</span>
        </div>
        {taxRates.length === 0 ? (
          <div className="app__placeholder">
            <p className="app__placeholder-title">
              {reference.isLoading ? words.loading : words.noTaxCodesReturned}
            </p>
          </div>
        ) : (
          <table className="queue">
            <thead>
              <tr>
                <th scope="col">{words.taxCode}</th>
                <th scope="col">{words.rate}</th>
              </tr>
            </thead>
            <tbody>
              {taxRates.map((taxRate) => (
                <tr key={taxRate.code} className="queue__row queue__row--reading">
                  <td className="queue__cell queue__cell--id">
                    <code>{taxRate.code}</code>
                  </td>
                  <td className="queue__cell queue__cell--checks">
                    {`${Math.round(taxRate.rate * 100)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
