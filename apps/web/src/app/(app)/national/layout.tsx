import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";

export default function NationalLayout({ children }: { children: ReactNode }) {
  return <AppShell roles={["national_analyst", "admin"]}>{children}</AppShell>;
}
