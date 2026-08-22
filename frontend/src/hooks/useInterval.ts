import { useEffect, useRef } from 'react';

export function useInterval(callback: () => void, delayMilliseconds: number | null): void {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delayMilliseconds === null) {
      return;
    }
    const timerId = window.setInterval(() => {
      savedCallback.current();
    }, delayMilliseconds);
    return () => {
      window.clearInterval(timerId);
    };
  }, [delayMilliseconds]);
}
