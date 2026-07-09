import { useCallback, useEffect, useState } from "react";

/**
 * Data fetching every converted page shares: runs `fetcher` on mount (and
 * whenever `deps` change), exposes { data, loading, error, reload }.
 * `reload()` refetches in place — used after deletes/promotions the way the
 * Django pages used a redirect-and-rerender.
 */
export default function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refreshIndex]);

  const reload = useCallback(() => setRefreshIndex((i) => i + 1), []);

  return { data, loading, error, reload };
}
