import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";

export default function SectorLayout({ children }: { children: ReactNode }) {
  return <AppShell roles={["sector_officer", "admin"]}>{children}</AppShell>;
}
