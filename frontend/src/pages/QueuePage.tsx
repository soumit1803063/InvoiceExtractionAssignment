import { useState } from 'react';
import { clearDocuments } from '../api/documents';
import { DocumentList } from '../components/DocumentList';
import { MessageBanner } from '../components/MessageBanner';
import { navigateTo } from '../hooks/useHashRoute';
import { useWords } from '../i18n';
import type { InvoiceDocument } from '../types/contract';

interface QueuePageProps {
  documents: InvoiceDocument[];
  tab: 'reading' | 'queue' | 'logged';
  isLoading: boolean;
  onCleared: () => void;
}

export function QueuePage({ documents, tab, isLoading, onCleared }: QueuePageProps) {
  const words = useWords();
  const [isConfirming, setIsConfirming] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [clearError, setClearError] = useState<string | null>(null);

  async function clearEverything() {
    setIsClearing(true);
    setClearError(null);
    try {
      await clearDocuments();
      setIsConfirming(false);
      onCleared();
    } catch (cause) {
      setClearError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setIsClearing(false);
    }
  }

  const logged = documents.filter((candidate) => candidate.status === 'registered');
  const readingNow = documents.filter((candidate) => candidate.status === 'processing');
  const queued = documents.filter(
    (candidate) => candidate.status !== 'registered' && candidate.status !== 'processing'
  );
  const visible = tab === 'logged' ? logged : tab === 'reading' ? readingNow : queued;
  const passedCount = queued.filter((candidate) => candidate.blocking_reasons.length === 0).length;
  const failedCount = queued.length - passedCount;

  return (
    <div className="page">
      <div className="queue-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'reading'}
          className={`queue-tabs__tab${tab === 'reading' ? ' queue-tabs__tab--active' : ''}`}
          onClick={() => navigateTo('/reading')}
        >
          {words.readingTab} <span className="queue-tabs__count">{readingNow.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'queue'}
          className={`queue-tabs__tab${tab === 'queue' ? ' queue-tabs__tab--active' : ''}`}
          onClick={() => navigateTo('/queue')}
        >
          {words.queue} <span className="queue-tabs__count">{queued.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'logged'}
          className={`queue-tabs__tab${tab === 'logged' ? ' queue-tabs__tab--active' : ''}`}
          onClick={() => navigateTo('/logged')}
        >
          {words.logged} <span className="queue-tabs__count">{logged.length}</span>
        </button>
        <button
          type="button"
          className="button button--ghost queue-tabs__clear"
          onClick={() => setIsConfirming(true)}
          disabled={documents.length === 0 || isClearing}
        >
          {isClearing ? words.clearing : words.clearEverything}
        </button>
      </div>

      {isConfirming ? (
        <MessageBanner
          tone="warning"
          title={words.clearEverythingConfirm}
          action={
            <>
              <button type="button" className="button button--ghost" onClick={() => setIsConfirming(false)}>
                {words.cancel}
              </button>
              <button type="button" className="button button--danger" onClick={clearEverything} disabled={isClearing}>
                {isClearing ? words.clearing : words.yesClearEverything}
              </button>
            </>
          }
        >
          <p>{words.clearEverythingExplained}</p>
        </MessageBanner>
      ) : null}

      {clearError ? (
        <MessageBanner tone="danger" title={words.clearingFailed}>
          <p>{clearError}</p>
        </MessageBanner>
      ) : null}

      <section className="app__queue">
        <div className="app__queue-header">
          <p className="app__queue-counts">
            {tab === 'logged'
              ? words.loggedIntoAccountingSystemThese
              : tab === 'reading'
                ? `${readingNow.length} ${words.reading}`
                : `${passedCount} ${words.passed} · ${failedCount} ${words.failed}`}
          </p>
        </div>

        {isLoading ? <p className="app__placeholder">{words.loading}</p> : null}

        {!isLoading && visible.length === 0 ? (
          <div className="app__placeholder app__placeholder--empty">
            {tab === 'logged' ? (
              <>
                <p className="app__placeholder-title">
                  {words.nothingLoggedYet}
                </p>
                <p>{words.invoicesAppearHereOnceAccounting}</p>
              </>
            ) : tab === 'reading' ? (
              <>
                <p className="app__placeholder-title">{words.nothingBeingReadNow}</p>
                <p>{words.uploadedInvoicesAppearHereWhileRead}</p>
              </>
            ) : (
              <>
                <p className="app__placeholder-title">{words.noInvoicesYet}</p>
                <p>{words.uploadInvoiceFillQueue}</p>
              </>
            )}
          </div>
        ) : null}

        {visible.length > 0 ? (
          <DocumentList
            documents={visible}
            showRegistration={tab === 'logged'}
            onSelectDocument={(documentId) =>
              navigateTo(`/${tab === 'logged' ? 'log' : tab}/documents/${documentId}`)
            }
          />
        ) : null}
      </section>
    </div>
  );
}
