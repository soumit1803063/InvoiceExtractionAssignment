import { useCallback, useEffect, useState } from 'react';

export interface AsyncDataState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  reload: () => void;
  replaceData: (next: T) => void;
}

export function useAsyncData<T>(loader: (signal: AbortSignal) => Promise<T>): AsyncDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadCounter, setReloadCounter] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let isCurrent = true;
    setIsLoading(true);
    loader(controller.signal)
      .then((result) => {
        if (!isCurrent) {
          return;
        }
        setData(result);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!isCurrent || controller.signal.aborted) {
          return;
        }
        setError(cause instanceof Error ? cause.message : String(cause));
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });
    return () => {
      isCurrent = false;
      controller.abort();
    };
  }, [loader, reloadCounter]);

  const reload = useCallback(() => {
    setReloadCounter((current) => current + 1);
  }, []);

  const replaceData = useCallback((next: T) => {
    setData(next);
    setError(null);
  }, []);

  return { data, error, isLoading, reload, replaceData };
}
