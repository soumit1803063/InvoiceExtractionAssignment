import { useCallback } from 'react';
import { buildDocumentPreviewUrl, fetchDocumentPreview } from '../api/documents';
import { useAsyncData } from '../hooks/useAsyncData';
import { useObjectUrl } from '../hooks/useObjectUrl';
import { fill, useWords } from '../i18n';

interface SourcePreviewProps {
  documentId: string;
  sourceName: string;
}

export function SourcePreview({ documentId, sourceName }: SourcePreviewProps) {
  const words = useWords();
  const loadPreview = useCallback((signal: AbortSignal) => fetchDocumentPreview(documentId, signal), [documentId]);
  const preview = useAsyncData<Blob>(loadPreview);
  const objectUrl = useObjectUrl(preview.data);
  const isPortableDocument = preview.data?.type.includes('pdf') ?? false;

  return (
    <section className="panel panel--preview">
      <header className="panel__header">
        <h2 className="panel__title">
          {words.sourcePage}
        </h2>
        {objectUrl ? (
          <a className="panel__summary panel__summary--link" href={objectUrl} target="_blank" rel="noreferrer">
            {words.openFullSize}
          </a>
        ) : null}
      </header>

      <div className="preview__frame">
        {preview.isLoading ? (
          <p className="preview__message">{words.loadingSourcePage}</p>
        ) : null}

        {!preview.isLoading && preview.error ? (
          <div className="preview__message preview__message--error">
            <p>{words.sourcePageCouldNotLoaded}</p>
            <p className="preview__message-detail">{preview.error}</p>
            <button type="button" className="button button--ghost" onClick={preview.reload}>
              {words.tryAgain}
            </button>
          </div>
        ) : null}

        {objectUrl && !preview.error ? (
          isPortableDocument ? (
            <object className="preview__object" data={objectUrl} type="application/pdf" aria-label={sourceName}>
              <p className="preview__message">
                {words.browserWillNotDisplayPdf}{' '}
                <a href={buildDocumentPreviewUrl(documentId)} target="_blank" rel="noreferrer">
                  {words.openInNewTab}
                </a>
                .
              </p>
            </object>
          ) : (
            <img className="preview__image" src={objectUrl} alt={fill(words.scannedPageOf, sourceName)} />
          )
        ) : null}
      </div>
    </section>
  );
}
