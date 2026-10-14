import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AppShell roles={["admin"]}>{children}</AppShell>;
}
