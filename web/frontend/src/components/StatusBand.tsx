// SigNoz-inspired status band: a dense, dark strip at the top summarizing
// runtime, catalog, LLM and current-query status. This replaces the old
// single-line status with metric tiles the eye can scan instantly.

import type { LinkResult, RuntimeStatus, LlmConfig } from "../api/client";
import { Metric, StatusBadge } from "./ui";

export function StatusBand({
  runtime,
  result,
  llmConfig,
}: {
  runtime: RuntimeStatus | null;
  result: LinkResult | null;
  llmConfig: LlmConfig | null;
}) {
  const typeText = runtime ? Object.entries(runtime.type_counts).map(([k, v]) => `${k}:${v}`).join("  ") : "-";
  const llmText = runtime?.llm_enabled
    ? `${llmConfig?.model || "enabled"}`
    : "offline";
  return (
    <div className="rounded-xl border border-shell-border bg-shell-panelSoft p-3" data-testid="status-band">
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-accent-teal">Status band</div>
          <div className="text-sm font-semibold text-shell-ink">运行状态</div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={runtime?.mode || "offline_demo"} />
          {result && <StatusBadge status={result.status} />}
        </div>
      </div>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Metric label="catalog" value={runtime ? String(runtime.catalog_loaded) : "-"} />
        <Metric label="entity_count" value={runtime?.entity_count ?? "-"} />
        <Metric label="type_counts" value={typeText} />
        <Metric label="LLM" value={llmText} />
      </dl>
    </div>
  );
}
