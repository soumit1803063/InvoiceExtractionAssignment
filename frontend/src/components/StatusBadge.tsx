import { useWords } from '../i18n';
import type { Words } from '../i18n';
import type { DocumentStatus } from '../types/contract';

const STATUS_PRESENTATION: Record<DocumentStatus, { word: keyof Words; modifier: string }> = {
  processing: { word: 'reading', modifier: 'badge--processing' },
  needs_review: { word: 'needsReview', modifier: 'badge--warning' },
  ready: { word: 'readyRegister', modifier: 'badge--ready' },
  registered: { word: 'statusRegistered', modifier: 'badge--registered' },
  rejected: { word: 'rejected', modifier: 'badge--danger' }
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const presentation = STATUS_PRESENTATION[status];
  const words = useWords();
  return (
    <span className={`badge ${presentation.modifier}`}>
      {words[presentation.word]}
    </span>
  );
}
