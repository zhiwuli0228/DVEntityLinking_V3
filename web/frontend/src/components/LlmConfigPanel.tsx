// LLM runtime config form (in-process only; never persisted server-side).
// Mirrors the old web demo form: enabled/model/base_url/api_key/timeout.

import { useState } from "react";
import type { LlmConfig } from "../api/client";
import { Card, EmptyHint } from "./ui";

export function LlmConfigPanel({
  config,
  onUpdate,
}: {
  config: LlmConfig | null;
  onUpdate: (payload: {
    enabled: boolean;
    model?: string;
    base_url?: string;
    api_key?: string;
    timeout_seconds?: number;
  }) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState(config?.enabled ?? false);
  const [model, setModel] = useState(config?.model || "qwen3.6-27b");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [timeout, setTimeout] = useState(config?.timeout_seconds ?? 20);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const summary = config
    ? [
        config.enabled ? "enabled" : "offline",
        config.base_url_configured ? "base_url configured" : "base_url empty",
        config.api_key_configured ? "api_key configured" : "api_key empty",
        config.api_key_env || "DVEL_WEB_LLM_API_KEY",
      ].join(" · ")
    : "-";

  return (
    <Card pad={false}>
      <button
        type="button"
        className="w-full flex items-center justify-between px-3 py-2"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-[10px] font-bold uppercase tracking-wider text-accent-teal">LLM 配置</span>
        <span className="text-[11px] text-shell-muted">{open ? "收起" : "展开"}</span>
      </button>
      {open && (
        <div className="border-t border-shell-border px-3 py-2 flex flex-col gap-2">
          <form
            className="grid grid-cols-[auto_1fr] gap-2 items-center"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setStatus("");
              try {
                await onUpdate({ enabled, model, base_url: baseUrl, api_key: apiKey, timeout_seconds: timeout });
                setStatus("saved");
                setApiKey("");
              } catch (err) {
                setStatus(String((err as Error).message || "config failed"));
              } finally {
                setBusy(false);
              }
            }}
          >
            <label className="text-[11px] text-shell-muted">enabled</label>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            <label className="text-[11px] text-shell-muted">model</label>
            <input className="rounded border border-shell-border bg-shell-panelSoft px-2 py-1 text-xs text-shell-ink" value={model} onChange={(e) => setModel(e.target.value)} />
            <label className="text-[11px] text-shell-muted">base_url</label>
            <input className="rounded border border-shell-border bg-shell-panelSoft px-2 py-1 text-xs text-shell-ink" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://.../v1" />
            <label className="text-[11px] text-shell-muted">api_key</label>
            <input type="password" autoComplete="off" className="rounded border border-shell-border bg-shell-panelSoft px-2 py-1 text-xs text-shell-ink" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="不落盘" />
            <label className="text-[11px] text-shell-muted">timeout</label>
            <input type="number" min={1} max={120} className="rounded border border-shell-border bg-shell-panelSoft px-2 py-1 text-xs text-shell-ink" value={timeout} onChange={(e) => setTimeout(Number(e.target.value))} />
            <div className="col-span-2 flex gap-2">
              <button type="submit" disabled={busy} className="rounded bg-accent-teal text-shell-bg text-xs font-semibold px-3 py-1.5 disabled:opacity-50">
                {busy ? "saving…" : "保存"}
              </button>
              {status && <span className="text-[11px] text-shell-muted self-center">{status}</span>}
            </div>
          </form>
          <EmptyHint>{summary}</EmptyHint>
        </div>
      )}
    </Card>
  );
}
