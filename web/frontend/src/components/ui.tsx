// Small hand-rolled UI primitives (Tremor-inspired) styled with Tailwind.
// Kept intentionally minimal: this is a developer workbench, not a product.

import type { ReactNode } from "react";
import type { Status } from "../api/client";

export function Card({
  children,
  className = "",
  pad = true,
  testId,
}: {
  children: ReactNode;
  className?: string;
  pad?: boolean;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className={`rounded-xl border border-shell-border bg-shell-panel ${pad ? "p-3" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ kicker, title, right }: { kicker?: string; title: string; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-2 mb-2">
      <div>
        {kicker && <div className="text-[10px] font-bold uppercase tracking-wider text-accent-teal">{kicker}</div>}
        <h2 className="text-sm font-semibold text-shell-ink leading-tight">{title}</h2>
      </div>
      {right}
    </div>
  );
}

export function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-shell-border bg-shell-panelSoft px-2.5 py-2 min-w-0">
      <dt className="text-[11px] text-shell-muted truncate">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-shell-ink break-words">{value}</dd>
    </div>
  );
}

const STATUS_STYLES: Record<Status, string> = {
  linked: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  partial: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  ambiguous: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  no_match: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  not_required: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  dependency_failed: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  invalid_input: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

export function StatusBadge({ status, className = "" }: { status: Status | string; className?: string }) {
  const key = (status as Status) in STATUS_STYLES ? (status as Status) : "not_required";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold border ${STATUS_STYLES[key]} ${className}`}
    >
      {String(status)}
    </span>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "teal" | "blue" | "violet" }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-500/15 text-slate-300 border-slate-500/30",
    teal: "bg-teal-500/15 text-teal-300 border-teal-500/30",
    blue: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    violet: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function EmptyHint({ children }: { children: ReactNode }) {
  return <p className="text-xs text-shell-muted">{children}</p>;
}
