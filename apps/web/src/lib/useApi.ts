"use client";

import { useCallback, useEffect, useState } from "react";

type State<T> = { key: string; data: T | null; error: boolean };

/**
 * Loads data for a key and reloads when the key changes. `reload` refetches the same key.
 * The loader resolves to null on failure.
 */
export function useApi<T>(key: string | null, load: () => Promise<T | null>) {
  const [state, setState] = useState<State<T> | null>(null);
  const [attempt, setAttempt] = useState(0);
  const fullKey = key === null ? null : `${key}#${attempt}`;

  useEffect(() => {
    if (fullKey === null) return;
    let active = true;
    load()
      .then((data) => active && setState({ key: fullKey, data, error: data === null }))
      .catch(() => active && setState({ key: fullKey, data: null, error: true }));
    return () => {
      active = false;
    };
    // The key identifies the request; `load` is recreated on every render by callers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullKey]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const current = state && fullKey !== null && state.key.split("#")[0] === key ? state : null;
  return {
    data: current?.data ?? null,
    loading: fullKey !== null && (!current || state?.key !== fullKey) && !current?.data,
    error: current?.error ?? false,
    reload,
  };
}
