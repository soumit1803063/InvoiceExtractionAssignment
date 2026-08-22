import { DocumentList } from '../components/DocumentList';
import { navigateTo } from '../hooks/useHashRoute';
import { useWords } from '../i18n';
import type { InvoiceDocument } from '../types/contract';

interface QueuePageProps {
  documents: InvoiceDocument[];
  tab: 'queue' | 'logged';
  isLoading: boolean;
}

export function QueuePage({ documents, tab, isLoading }: QueuePageProps) {
  const words = useWords();
  const logged = documents.filter((candidate) => candidate.status === 'registered');
  const queued = documents.filter((candidate) => candidate.status !== 'registered');
  const visible = tab === 'logged' ? logged : queued;
  const processingCount = queued.filter((candidate) => candidate.status === 'processing').length;
  const passedCount = queued.filter(
    (candidate) => candidate.status !== 'processing' && candidate.blocking_reasons.length === 0
  ).length;
  const failedCount = queued.length - processingCount - passedCount;

  return (
    <div className="page">
      <div className="queue-tabs" role="tablist">
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
      </div>

      <section className="app__queue">
        <div className="app__queue-header">
          <p className="app__queue-counts">
            {tab === 'logged'
              ? words.loggedIntoAccountingSystemThese
              : `${processingCount > 0 ? `${processingCount} ${words.reading} · ` : ''}${passedCount} ${words.passed} · ${failedCount} ${words.failed}`}
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
            onSelectDocument={(documentId) => navigateTo(`/documents/${documentId}`)}
          />
        ) : null}
      </section>
    </div>
  );
}
