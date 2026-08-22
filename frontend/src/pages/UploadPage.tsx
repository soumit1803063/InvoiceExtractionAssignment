import { useRef, useState } from 'react';
import { uploadDocument } from '../api/documents';
import { MessageBanner } from '../components/MessageBanner';
import { navigateTo } from '../hooks/useHashRoute';
import { useWords } from '../i18n';
import type { InvoiceDocument } from '../types/contract';

const ACCEPTED_TYPES = '.pdf,.jpg,.jpeg,.png';

interface UploadPageProps {
  onDocumentAccepted: (document: InvoiceDocument) => void;
}

export function UploadPage({ onDocumentAccepted }: UploadPageProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [accepted, setAccepted] = useState<InvoiceDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const words = useWords();

  async function upload(fileList: FileList | null) {
    const files = Array.from(fileList ?? []);
    if (fileInput.current) {
      fileInput.current.value = '';
    }
    if (files.length === 0) {
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      for (const file of files) {
        const document = await uploadDocument(file);
        onDocumentAccepted(document);
        setAccepted((current) => [...current, document]);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="page page--upload">
      <section className="dropzone">
        <h2 className="dropzone__title">{words.uploadInvoices}</h2>
        <input
          ref={fileInput}
          type="file"
          className="dropzone__input"
          accept={ACCEPTED_TYPES}
          multiple
          onChange={(event) => upload(event.target.files)}
        />
        <button
          type="button"
          className="button button--primary"
          disabled={isUploading}
          onClick={() => fileInput.current?.click()}
        >
          {isUploading ? words.uploading : words.chooseInvoices}
        </button>
        <p className="dropzone__hint">
          {words.pdfJpgOrPngEach}
        </p>
      </section>

      {error ? (
        <MessageBanner tone="danger" title={words.invoiceNotAccepted}>
          <p>{error}</p>
        </MessageBanner>
      ) : null}

      {accepted.length > 0 ? (
        <section className="panel">
          <header className="panel__header">
            <h2 className="panel__title">
              {words.acceptedSession}
            </h2>
            <button type="button" className="button button--ghost" onClick={() => navigateTo('/queue')}>
              {words.goQueue}
            </button>
          </header>
          <ul className="accepted">
            {accepted.map((document) => (
              <li key={document.document_id} className="accepted__item">
                <span className="accepted__name">{document.source_name}</span>
                <code className="accepted__id">{document.document_id}</code>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
