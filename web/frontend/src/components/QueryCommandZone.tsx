// Query/filter command zone (SigNoz-style filter rail). Holds the query input,
// mode/fallback controls, sample picker and the Link action. Lives in the left
// column of the workbench grid.

import type { RunMode, QuerySample } from "../api/client";
import { Card, SectionTitle } from "./ui";

export function QueryCommandZone({
  query,
  mode,
  allowFallback,
  samples,
  loading,
  onQueryChange,
  onModeChange,
  onFallbackChange,
  onSamplePick,
  onSubmit,
}: {
  query: string;
  mode: RunMode;
  allowFallback: boolean;
  samples: QuerySample[];
  loading: boolean;
  onQueryChange: (v: string) => void;
  onModeChange: (v: RunMode) => void;
  onFallbackChange: (v: boolean) => void;
  onSamplePick: (q: string) => void;
  onSubmit: () => void;
}) {
  return (
    <Card testId="query-command-zone">
      <SectionTitle kicker="Command zone" title="Query" />
      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <input
          className="w-full rounded-lg border border-shell-border bg-shell-panelSoft px-3 py-2 text-sm text-shell-ink placeholder:text-shell-muted focus:outline-none focus:ring-2 focus:ring-accent-teal/60"
          placeholder="输入 Query，例如 Check ALM-51020 and CPU Usage."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          data-testid="query-input"
        />
        <div className="grid grid-cols-2 gap-2">
          <select
            className="rounded-lg border border-shell-border bg-shell-panelSoft px-2 py-2 text-sm text-shell-ink"
            value={mode}
            onChange={(e) => onModeChange(e.target.value as RunMode)}
            aria-label="run mode"
          >
            <option value="offline_demo">offline_demo</option>
            <option value="llm_enabled_demo">llm_enabled_demo</option>
          </select>
          <label className="flex items-center gap-2 text-xs text-shell-muted px-1">
            <input
              type="checkbox"
              checked={allowFallback}
              onChange={(e) => onFallbackChange(e.target.checked)}
            />
            allow_fallback
          </label>
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 rounded-lg bg-accent-teal text-shell-bg font-semibold text-sm px-3 py-2 hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Linking…" : "Link"}
          </button>
        </div>
        {samples.length > 0 && (
          <select
            className="rounded-lg border border-shell-border bg-shell-panelSoft px-2 py-2 text-xs text-shell-muted"
            value=""
            onChange={(e) => e.target.value && onSamplePick(e.target.value)}
            aria-label="sample queries"
          >
            <option value="">— sample queries —</option>
            {samples.map((s) => (
              <option key={s.id} value={s.query}>
                {s.id} · {s.query.length > 48 ? s.query.slice(0, 48) + "…" : s.query}
              </option>
            ))}
          </select>
        )}
      </form>
    </Card>
  );
}
