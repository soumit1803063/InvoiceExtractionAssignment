import { useState } from 'react';
import type { InvoiceDocument } from '../types/contract';
import { formatTimestamp, humanizeIdentifier } from '../utils/formatting';
import { fill, useWords } from '../i18n';
import type { Words } from '../i18n';
import { describeErrorCode, describeErrorCodeTitle } from '../utils/errorMessages';
import { MessageBanner } from './MessageBanner';

interface RegisterPanelProps {
  document: InvoiceDocument;
  hasUnsavedChanges: boolean;
  isRegistering: boolean;
  transportError: string | null;
  onRegister: () => void;
}

function collectReasonsRegistrationIsBlocked(
  document: InvoiceDocument,
  hasUnsavedChanges: boolean,
  words: Words
): string[] {
  const reasons: string[] = [];
  if (hasUnsavedChanges) {
    reasons.push(words.unsavedCorrectionsSaveFirst);
  }
  for (const reason of document.blocking_reasons) {
    reasons.push(humanizeIdentifier(reason));
  }
  if (document.status === 'rejected') {
    reasons.push(words.markedAsRejected);
  }
  if (document.status === 'needs_review' && document.blocking_reasons.length === 0) {
    reasons.push(words.serverStillNeedsReview);
  }
  return reasons;
}

export function RegisterPanel({
  document,
  hasUnsavedChanges,
  isRegistering,
  transportError,
  onRegister
}: RegisterPanelProps) {
  const words = useWords();
  const [isConfirmationOpen, setIsConfirmationOpen] = useState(false);

  const registration = document.registration;
  const isAlreadyRegistered = document.status === 'registered' || Boolean(registration?.accounting_id);
  const blockingReasons = collectReasonsRegistrationIsBlocked(document, hasUnsavedChanges, words);
  const canRegister = !isAlreadyRegistered && document.status === 'ready' && blockingReasons.length === 0;

  if (isAlreadyRegistered) {
    return (
      <section className="panel panel--register">
        <MessageBanner tone="success" title={words.registeredAccountingSystem}>
          <p>
            {words.accountingRecord}: <strong>{registration?.accounting_id ?? words.unknownId}</strong>
          </p>
          <p>{fill(words.registeredAt, formatTimestamp(registration?.attempted_at))}</p>
          <p>
            {words.recordCannotBeChanged}
          </p>
        </MessageBanner>
      </section>
    );
  }

  return (
    <section className="panel panel--register">
      <header className="panel__header">
        <h2 className="panel__title">
          {words.registration}
        </h2>
      </header>

      <div className="irreversible-notice">
        <p className="irreversible-notice__title">{words.registrationCannotUndone}</p>
        <p>
          {words.sendingInvoiceWritesIntoAccounting}
        </p>
      </div>

      {registration && registration.error_code ? (
        <MessageBanner tone="danger" title={describeErrorCodeTitle(registration.error_code, words)}>
          <p>{describeErrorCode(registration.error_code, registration.error_message, words)}</p>
          <p className="banner__meta">
            {words.lastAttempt} {formatTimestamp(registration.attempted_at)} ·{' '}
            {words.accountingSystemReplied} {registration.http_status}
          </p>
        </MessageBanner>
      ) : null}

      {transportError ? (
        <MessageBanner tone="danger" title={words.registrationRequestDidNotComplete}>
          <p>{transportError}</p>
        </MessageBanner>
      ) : null}

      {blockingReasons.length > 0 ? (
        <div className="register-blocked">
          <p className="register-blocked__title">{words.notRegisterableYet}</p>
          <ul>
            {blockingReasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {isConfirmationOpen ? (
        <div className="confirm-box" role="alertdialog" aria-label={words.confirmRegistration}>
          <p className="confirm-box__title">{fill(words.registerPermanently, document.source_name)}</p>
          <p>
            {words.writesInvoiceForGood}
          </p>
          <div className="confirm-box__actions">
            <button
              type="button"
              className="button button--danger"
              disabled={isRegistering}
              onClick={() => {
                setIsConfirmationOpen(false);
                onRegister();
              }}
            >
              {isRegistering ? words.registering : words.yesRegisterPermanently}
            </button>
            <button
              type="button"
              className="button button--ghost"
              disabled={isRegistering}
              onClick={() => setIsConfirmationOpen(false)}
            >
              {words.cancel}
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="button button--primary button--wide"
          disabled={!canRegister || isRegistering}
          onClick={() => setIsConfirmationOpen(true)}
        >
          {isRegistering ? words.registering : words.register}
        </button>
      )}
    </section>
  );
}
