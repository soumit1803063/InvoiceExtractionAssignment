import { useEffect, useState } from 'react';

export const DEFAULT_ROUTE = '/queue';

function currentRoute(): string {
  return window.location.hash.replace(/^#/, '') || DEFAULT_ROUTE;
}

export function navigateTo(route: string): void {
  window.location.hash = route;
}

export function useHashRoute(): string {
  const [route, setRoute] = useState(currentRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(currentRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  return route;
}
