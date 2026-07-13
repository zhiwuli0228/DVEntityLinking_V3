// Workbench shell: the dark cohesive frame that replaces the old white-card
// stack. Desktop uses a 3-column grid (command/catalog · result · detail/explain);
// narrow screens collapse to a single column with a stable context order.

import type { ReactNode } from "react";

export function Shell({
  statusBand,
  llmConfig,
  left,
  center,
  right,
  debug,
}: {
  statusBand: ReactNode;
  llmConfig: ReactNode;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  debug: ReactNode;
}) {
  return (
    <main className="min-h-full w-full max-w-[1500px] mx-auto p-3 flex flex-col gap-2" data-testid="visual-workbench-shell">
      <header className="rounded-xl border border-shell-border bg-shell-panel px-3 py-2.5 flex items-end justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-base font-bold text-shell-ink leading-tight">DVEntityLinking Workbench</h1>
          <p className="text-[11px] text-shell-muted">Multi-mention entity linking · developer console</p>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {["Ops density", "Inline spans", "Generative explain"].map((p) => (
            <span key={p} className="rounded-full border border-shell-border bg-shell-panelSoft px-2 py-0.5 text-[10px] text-shell-muted">
              {p}
            </span>
          ))}
        </div>
      </header>
      {statusBand}
      <div className="grid gap-2 lg:grid-cols-[minmax(260px,0.9fr)_minmax(360px,1.35fr)_minmax(320px,1fr)] items-start">
        <div className="flex flex-col gap-2 min-w-0">
          {left}
          {llmConfig}
        </div>
        <div className="min-w-0">{center}</div>
        <div className="flex flex-col gap-2 min-w-0">
          {right}
        </div>
      </div>
      {debug}
    </main>
  );
}
