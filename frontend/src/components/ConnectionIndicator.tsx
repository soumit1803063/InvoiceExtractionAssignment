import { useCallback } from 'react';
import { fetchHealth } from '../api/documents';
import { useAsyncData } from '../hooks/useAsyncData';
import { useWords } from '../i18n';
import type { HealthResponse } from '../types/contract';

export function ConnectionIndicator() {
  const loadHealth = useCallback((signal: AbortSignal) => fetchHealth(signal), []);
  const health = useAsyncData<HealthResponse>(loadHealth);
  const words = useWords();

  if (health.isLoading) {
    return <p className="connection connection--unknown">{words.checkingConnections}</p>;
  }

  if (health.error || !health.data) {
    return <p className="connection connection--down">
        {words.screenCannotReachItsOwn}
      </p>;
  }

  return health.data.accounting_api_reachable ? (
    <p className="connection connection--up">
      {words.accountingSystemReachableRegistrationPossible}
    </p>
  ) : (
    <p className="connection connection--down">
      {words.accountingSystemUnreachableReviewingWorks}
    </p>
  );
}
