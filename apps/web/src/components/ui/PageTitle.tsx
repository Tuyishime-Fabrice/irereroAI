import type { ReactNode } from "react";

import { ZigzagBand } from "@/components/brand/ZigzagBand";

export function PageTitle({
  title,
  lead,
  actions,
}: {
  title: ReactNode;
  lead?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6">
      <ZigzagBand className="mb-4 max-w-24 rounded-sm" />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink">{title}</h1>
          {lead && <p className="mt-1 max-w-2xl text-ink-muted">{lead}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}
