import type { ReactNode } from "react";

import { PublicFooter } from "@/components/shell/PublicFooter";
import { PublicHeader } from "@/components/shell/PublicHeader";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PublicHeader />
      <main id="main" className="mx-auto max-w-6xl px-4 py-8">
        {children}
      </main>
      <PublicFooter />
    </>
  );
}
