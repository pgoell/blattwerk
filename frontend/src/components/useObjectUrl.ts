import { useEffect, useState } from "react";

// A URL for a blob, freed when the blob or the component goes away.
export function useObjectUrl(blob: Blob) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    const next = URL.createObjectURL(blob);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [blob]);
  return url;
}
