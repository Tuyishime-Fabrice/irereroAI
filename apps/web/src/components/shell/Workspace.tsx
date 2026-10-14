"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, type Schemas } from "@/lib/api/client";

type Workspace = {
  demoMode: boolean;
  catchmentSteps: number[];
  catchment: number;
  setCatchment: (minutes: number) => void;
};

const WorkspaceContext = createContext<Workspace | null>(null);

/** Settings every planner page shares, including the walking-time catchment being looked at. */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Schemas["AppSettings"] | null>(null);
  const [chosen, setCatchment] = useState<number | null>(null);

  useEffect(() => {
    api.GET("/settings").then(({ data }) => data && setSettings(data));
  }, []);

  const value = useMemo<Workspace | null>(
    () =>
      settings && {
        demoMode: settings.demo_mode,
        catchmentSteps: settings.catchment_steps,
        catchment: chosen ?? settings.catchment_minutes,
        setCatchment,
      },
    [settings, chosen],
  );
  if (!value) return null;
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): Workspace {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("useWorkspace outside WorkspaceProvider");
  return workspace;
}
