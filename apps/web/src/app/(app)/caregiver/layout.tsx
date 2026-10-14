import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";
import { RegisterServiceWorker } from "@/components/shell/RegisterServiceWorker";

export default function CaregiverLayout({ children }: { children: ReactNode }) {
  return (
    <AppShell roles={["caregiver"]}>
      <RegisterServiceWorker />
      {children}
    </AppShell>
  );
}
