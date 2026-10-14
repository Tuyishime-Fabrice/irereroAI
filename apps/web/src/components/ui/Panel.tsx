import type { HTMLAttributes, ReactNode } from "react";

export function Panel({ className = "", ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={`rounded-md border border-line bg-surface ${className}`} {...props} />;
}

export function PanelHeader({ title, action }: { title: ReactNode; action?: ReactNode }) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-line px-4 py-3">
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      {action}
    </header>
  );
}
