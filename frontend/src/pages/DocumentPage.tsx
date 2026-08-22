import { useState } from 'react';
import { reprocessDocument } from '../api/documents';
import { DocumentDetail } from '../components/DocumentDetail';
import { SourcePreview } from '../components/SourcePreview';
import { MessageBanner } from '../components/MessageBanner';
import { navigateTo } from '../hooks/useHashRoute';
import { useWords } from '../i18n';
import type { InvoiceDocument } from '../types/contract';

interface DocumentPageProps {
  document: InvoiceDocument | null;
  documents: InvoiceDocument[];
  isLoading: boolean;
  onDocumentUpdated: (document: InvoiceDocument) => void;
}

export function DocumentPage({ document, documents, isLoading, onDocumentUpdated }: DocumentPageProps) {
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [reprocessError, setReprocessError] = useState<string | null>(null);
  const words = useWords();

  if (!document) {
    return (
      <div className="page">
        <div className="app__placeholder app__placeholder--detail">
          <p className="app__placeholder-title">
            {isLoading ? words.loading : words.noDocumentWithProcessId}
          </p>
          {null}
        </div>
      </div>
    );
  }

  const activeDocument = document;
  const duplicateSourceName = document.verification.duplicate_of
    ? (documents.find((candidate) => candidate.document_id === document.verification.duplicate_of)
        ?.source_name ?? null)
    : null;

  async function reprocess() {
    setIsReprocessing(true);
    setReprocessError(null);
    try {
      onDocumentUpdated(await reprocessDocument(activeDocument.document_id));
    } catch (cause) {
      setReprocessError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setIsReprocessing(false);
    }
  }

  return (
    <div className="page">
      <nav className="breadcrumb">
        <button
          type="button"
          className="button button--ghost"
          onClick={() => navigateTo(document.status === 'registered' ? '/logged' : '/queue')}
        >
          ← {document.status === 'registered' ? words.backLoggedList : words.backQueue}
        </button>
        <button
          type="button"
          className="button button--ghost"
          disabled={isReprocessing || document.status === 'processing' || document.status === 'registered'}
          onClick={reprocess}
        >
          {isReprocessing ? words.reprocessing : words.reprocess}
        </button>
      </nav>

      {reprocessError ? (
        <MessageBanner tone="danger" title={words.reprocessingDidNotStart}>
          <p>{reprocessError}</p>
        </MessageBanner>
      ) : null}

      {document.status === 'processing' ? (
        <>
          <MessageBanner tone="info" title={words.stillReadingDocument}>
            <p>{words.fieldsAppearWhenReadingFinishes}</p>
          </MessageBanner>
          <SourcePreview documentId={document.document_id} sourceName={document.source_name} />
        </>
      ) : (
        <DocumentDetail
          key={document.document_id}
          document={document}
          duplicateSourceName={duplicateSourceName}
          onDocumentUpdated={onDocumentUpdated}
        />
      )}
    </div>
  );
}
