import { useWords } from '../i18n';
import type { Words } from '../i18n';
import type { InvoiceDocument } from '../types/contract';
import { formatTimestamp } from '../utils/formatting';
import { StatusBadge } from './StatusBadge';

interface DocumentListProps {
  documents: InvoiceDocument[];
  showRegistration: boolean;
  onSelectDocument: (documentId: string) => void;
}

function outcomeOf(
  document: InvoiceDocument,
  words: Words
): { label: string; modifier: string } {
  if (document.status === 'processing') {
    return { label: '—', modifier: 'outcome--pending' };
  }
  if (document.blocking_reasons.length > 0) {
    return { label: words.failed, modifier: 'outcome--failed' };
  }
  return { label: words.passed, modifier: 'outcome--passed' };
}

export function DocumentList({ documents, showRegistration, onSelectDocument }: DocumentListProps) {
  const words = useWords();
  return (
    <table className="queue">
      <thead>
        <tr>
          <th scope="col">{words.invoice}</th>
          <th scope="col">{words.processId}</th>
          <th scope="col">{words.created}</th>
          {showRegistration ? (
            <>
              <th scope="col">{words.accountingId}</th>
              <th scope="col">{words.registered}</th>
            </>
          ) : (
            <>
              <th scope="col">{words.checks}</th>
              <th scope="col">{words.result}</th>
            </>
          )}
        </tr>
      </thead>
      <tbody>
        {documents.map((document) => {
          const outcome = outcomeOf(document, words);
          const isProcessing = document.status === 'processing';
          return (
            <tr
              key={document.document_id}
              className="queue__row"
              tabIndex={0}
              onClick={() => onSelectDocument(document.document_id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onSelectDocument(document.document_id);
                }
              }}
            >
              <td className="queue__cell queue__cell--name">
                <span className="queue__name" title={document.source_name}>
                  {document.source_name}
                </span>
                <StatusBadge status={document.status} />
              </td>
              <td className="queue__cell queue__cell--id">
                <code title={document.document_id}>{document.document_id}</code>
              </td>
              <td className="queue__cell queue__cell--time">{formatTimestamp(document.created_at)}</td>
              {showRegistration ? (
                <>
                  <td className="queue__cell queue__cell--id">
                    <code>{document.registration?.accounting_id ?? '—'}</code>
                  </td>
                  <td className="queue__cell queue__cell--time">
                    {formatTimestamp(document.registration?.attempted_at)}
                  </td>
                </>
              ) : (
                <>
                  <td className="queue__cell queue__cell--checks">
                    {isProcessing
                      ? '—'
                      : `${document.verification.checks_passed}/${document.verification.checks_total}`}
                  </td>
                  <td className="queue__cell">
                    <span className={`outcome ${outcome.modifier}`}>{outcome.label}</span>
                  </td>
                </>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
