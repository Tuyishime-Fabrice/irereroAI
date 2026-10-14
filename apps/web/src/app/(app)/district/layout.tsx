import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";

export default function DistrictLayout({ children }: { children: ReactNode }) {
  return <AppShell roles={["district_planner", "national_analyst", "admin"]}>{children}</AppShell>;
}
