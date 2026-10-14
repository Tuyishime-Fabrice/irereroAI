"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Origin, Provenance } from "@/lib/api/client";

type Registry = {
  origins: Origin[];
  register: (key: string, origins: Origin[]) => void;
  unregister: (key: string) => void;
};

const ProvenanceContext = createContext<Registry | null>(null);

/** Collects the origins of everything on screen so the shell can label simulated data. */
export function ProvenanceProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Record<string, Origin[]>>({});
  const register = useCallback(
    (key: string, origins: Origin[]) => setEntries((current) => ({ ...current, [key]: origins })),
    [],
  );
  const unregister = useCallback(
    (key: string) =>
      setEntries((current) => {
        const next = { ...current };
        delete next[key];
        return next;
      }),
    [],
  );
  const value = useMemo(
    () => ({ origins: [...new Set(Object.values(entries).flat())], register, unregister }),
    [entries, register, unregister],
  );
  return <ProvenanceContext.Provider value={value}>{children}</ProvenanceContext.Provider>;
}

/** Call with the provenance of data a component shows. */
export function useProvenance(provenance: Provenance | null | undefined) {
  const registry = useContext(ProvenanceContext);
  const key = useId();
  const origins = provenance?.origins.join(",");
  useEffect(() => {
    if (!registry || !origins) return;
    registry.register(key, origins.split(",") as Origin[]);
    return () => registry.unregister(key);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- registry functions are stable
  }, [key, origins]);
}

export function useVisibleOrigins(): Origin[] {
  return useContext(ProvenanceContext)?.origins ?? [];
}
