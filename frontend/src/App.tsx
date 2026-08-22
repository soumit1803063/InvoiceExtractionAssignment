import { useCallback } from 'react';
import type { ReactNode } from 'react';
import { fetchDocuments } from './api/documents';
import { ConnectionIndicator } from './components/ConnectionIndicator';
import { MessageBanner } from './components/MessageBanner';
import { useAsyncData } from './hooks/useAsyncData';
import { LanguageProvider, useWords } from './i18n';
import { navigateTo, useHashRoute } from './hooks/useHashRoute';
import { useInterval } from './hooks/useInterval';
import { DocumentPage } from './pages/DocumentPage';
import { QueuePage } from './pages/QueuePage';
import { UploadPage } from './pages/UploadPage';
import type { InvoiceDocument } from './types/contract';

const REFRESH_INTERVAL_WHILE_READING = 2000;

const NAV_LINKS = [
  { route: '/upload', word: 'upload' },
  { route: '/queue', word: 'queue' },
  { route: '/logged', word: 'logged' }
] as const;

export function App() {
  return <LanguageProvider>{(toggle) => <Screen languageToggle={toggle} />}</LanguageProvider>;
}

function Screen({ languageToggle }: { languageToggle: ReactNode }) {
  const loadDocuments = useCallback((signal: AbortSignal) => fetchDocuments(signal), []);
  const documentsResource = useAsyncData<InvoiceDocument[]>(loadDocuments);
  const route = useHashRoute();
  const words = useWords();

  const documents = documentsResource.data ?? [];
  const { replaceData } = documentsResource;
  const isReading = documents.some((candidate) => candidate.status === 'processing');

  const refreshQuietly = useCallback(() => {
    fetchDocuments()
      .then(replaceData)
      .catch(() => undefined);
  }, [replaceData]);

  useInterval(refreshQuietly, isReading ? REFRESH_INTERVAL_WHILE_READING : null);

  const applyDocumentUpdate = useCallback(
    (updated: InvoiceDocument) => {
      const current = documentsResource.data ?? [];
      const isKnown = current.some((candidate) => candidate.document_id === updated.document_id);
      replaceData(
        isKnown
          ? current.map((candidate) =>
              candidate.document_id === updated.document_id ? updated : candidate
            )
          : [...current, updated]
      );
    },
    [documentsResource.data, replaceData]
  );

  const documentRoute = route.match(/^\/documents\/(.+)$/);
  const activeRoute = documentRoute ? '/queue' : route;

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1 className="app__title">{words.invoiceReview}</h1>
          <p className="app__subtitle">
            {words.checkEveryInvoiceBeforeLogged}
          </p>
          <ConnectionIndicator />
        </div>
        <div className="app__controls">
          {languageToggle}
          <nav className="app__nav">
            {NAV_LINKS.map((link) => (
              <button
                key={link.route}
                type="button"
                className={`app__nav-link${activeRoute === link.route ? ' app__nav-link--active' : ''}`}
                onClick={() => navigateTo(link.route)}
              >
                {words[link.word]}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {documentsResource.error && !documentsResource.isLoading ? (
        <MessageBanner
          tone="danger"
          title={words.queueCouldNotLoaded}
          action={
            <button type="button" className="button button--ghost" onClick={documentsResource.reload}>
              {words.tryAgain}
            </button>
          }
        >
          <p>{documentsResource.error}</p>
          <p>
            {words.nothingHasBeenSentAccounting}
          </p>
        </MessageBanner>
      ) : null}

      <main className="app__body">
        {documentRoute ? (
          <DocumentPage
            document={
              documents.find((candidate) => candidate.document_id === documentRoute[1]) ?? null
            }
            documents={documents}
            isLoading={documentsResource.isLoading}
            onDocumentUpdated={applyDocumentUpdate}
          />
        ) : route === '/upload' ? (
          <UploadPage onDocumentAccepted={applyDocumentUpdate} />
        ) : (
          <QueuePage
            documents={documents}
            tab={route === '/logged' ? 'logged' : 'queue'}
            isLoading={documentsResource.isLoading}
          />
        )}
      </main>
    </div>
  );
}
