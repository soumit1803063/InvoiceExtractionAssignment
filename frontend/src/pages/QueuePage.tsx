import { DocumentList } from '../components/DocumentList';
import { navigateTo } from '../hooks/useHashRoute';
import { useWords } from '../i18n';
import type { InvoiceDocument } from '../types/contract';

interface QueuePageProps {
  documents: InvoiceDocument[];
  tab: 'reading' | 'queue' | 'logged';
  isLoading: boolean;
}

export function QueuePage({ documents, tab, isLoading }: QueuePageProps) {
  const words = useWords();

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
      </div>

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
