import { useWords } from '../i18n';
import { isBlank } from '../utils/formatting';
import { MessageBanner } from './MessageBanner';

export function ExcludedNotesNotice({ notes }: { notes: string | null }) {
  const words = useWords();
  if (isBlank(notes)) {
    return null;
  }

  return (
    <MessageBanner tone="danger" title={words.handwrittenNotesWereFoundPage}>
      <p>
        {words.theseWereReadOffPage}
      </p>
      <blockquote className="excluded-notes">{notes}</blockquote>
    </MessageBanner>
  );
}
