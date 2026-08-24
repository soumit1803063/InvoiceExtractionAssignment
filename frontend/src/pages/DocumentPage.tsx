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
  onDocumentsReplaced: (documents: InvoiceDocument[]) => void;
}

export function DocumentPage({
  document,
  documents,
  isLoading,
  onDocumentUpdated,
  onDocumentsReplaced
}: DocumentPageProps) {
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

  const duplicateSourceName = document.verification.duplicate_of
    ? (documents.find((candidate) => candidate.document_id === document.verification.duplicate_of)
        ?.source_name ?? null)
    : null;


  return (
    <div className="page">
      <nav className="breadcrumb">
        <button
          type="button"
          className="button button--ghost"
          onClick={() =>
            navigateTo(
              document.status === 'registered'
                ? '/logged'
                : document.status === 'processing'
                  ? '/reading'
                  : '/queue'
            )
          }
        >
          ← {document.status === 'registered' ? words.backLoggedList : words.backQueue}
        </button>
      </nav>


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
          onDocumentsReplaced={onDocumentsReplaced}
        />
      )}
    </div>
  );
}
