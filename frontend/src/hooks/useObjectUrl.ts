import { useEffect, useState } from 'react';

export function useObjectUrl(source: Blob | null): string | null {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!source) {
      setObjectUrl(null);
      return;
    }
    const createdUrl = URL.createObjectURL(source);
    setObjectUrl(createdUrl);
    return () => {
      URL.revokeObjectURL(createdUrl);
    };
  }, [source]);

  return objectUrl;
}
