"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "@/lib/api/client";

type Workspace = {
  weeks: string[];
  currentWeek: string;
  week: string;
  setWeek: (week: string) => void;
  area: string | null;
  setArea: (area: string | null) => void;
  demoMode: boolean;
};

const WorkspaceContext = createContext<Workspace | null>(null);

/** The reporting calendar and the area being looked at, shared by every staff page. */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [calendar, setCalendar] = useState<{
    weeks: string[];
    current: string;
    demo: boolean;
  } | null>(null);
  const [chosenWeek, setWeek] = useState<string | null>(null);
  const [area, setArea] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/calendar").then(({ data }) => {
      if (data)
        setCalendar({ weeks: data.weeks, current: data.current_week, demo: data.demo_mode });
    });
  }, []);

  const value = useMemo<Workspace | null>(
    () =>
      calendar && {
        weeks: calendar.weeks,
        currentWeek: calendar.current,
        week: chosenWeek ?? calendar.current,
        setWeek,
        area,
        setArea,
        demoMode: calendar.demo,
      },
    [calendar, chosenWeek, area],
  );
  if (!value) return null;
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): Workspace {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("useWorkspace outside WorkspaceProvider");
  return workspace;
}
