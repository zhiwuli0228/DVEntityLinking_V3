// CopilotKit-inspired generative explanation component. Rather than a plain
// text list, it renders context header + stage chips + safe summary + redaction
// footer, and switches context (global/mention/candidate) as the user selects
// mentions or candidates. Stage trace / storage lookup are surfaced when present.

import type { LinkResult, LlmExplanation, StageStatus } from "../api/client";
import type { LlmContext } from "../state/workbench";
import { Card, SectionTitle, EmptyHint, Badge } from "./ui";

function stageChipTone(s: StageStatus): "slate" | "teal" | "blue" | "violet" {
  if (s.stage_status === "fallback_used") return "violet";
  if (s.succeeded) return "teal";
  if (s.attempted) return "blue";
  return "slate";
}

function contextExplanations(
  result: LinkResult,
  ctx: LlmContext,
  mentionIndex: number | null,
  candidateId: string | null,
): LlmExplanation[] {
  return result.llm_explanations.filter((e) => {
    if (ctx === "global") return e.context_type === "global";
    if (ctx === "mention") return e.context_type === "mention" && (e.mention_index ?? null) === (mentionIndex ?? null);
    if (ctx === "candidate")
      return (
        e.context_type === "candidate" &&
        (e.mention_index ?? null) === (mentionIndex ?? null) &&
        (!candidateId || !e.candidate_id || e.candidate_id === candidateId)
      );
    return false;
  });
}

export function LlmExplanationPanel({
  result,
  llmContext,
  activeMentionIndex,
  activeCandidateId,
  onGlobalClick,
}: {
  result: LinkResult | null;
  llmContext: LlmContext;
  activeMentionIndex: number | null;
  activeCandidateId: string | null;
  onGlobalClick: () => void;
}) {
  const stages = result?.mode_status?.stage_statuses ?? [];
  const explanations = result ? contextExplanations(result, llmContext, activeMentionIndex, activeCandidateId) : [];
  const ms = result?.mode_status;
  const ctxLabel =
    llmContext === "global"
      ? "global"
      : llmContext === "mention"
        ? `mention #${activeMentionIndex ?? "-"}`
        : `candidate ${activeCandidateId ?? "-"}`;

  return (
    <Card testId="llm-explanation-component">
      <SectionTitle
        kicker="Generative UI component"
        title="LLM 交互式安全解释"
        right={
          <button
            type="button"
            onClick={onGlobalClick}
            className="text-[10px] rounded border border-shell-border bg-shell-panelSoft px-2 py-1 text-shell-muted hover:text-shell-ink"
          >
            global
          </button>
        }
      />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2">
        <div className="rounded-lg border border-shell-border bg-shell-panelSoft px-2.5 py-2">
          <div className="text-[11px] text-shell-muted">enabled</div>
          <div className="text-sm font-semibold text-shell-ink">{String(ms?.llm_enabled ?? false)}</div>
        </div>
        <div className="rounded-lg border border-shell-border bg-shell-panelSoft px-2.5 py-2">
          <div className="text-[11px] text-shell-muted">used</div>
          <div className="text-sm font-semibold text-shell-ink">{String(ms?.llm_used ?? false)}</div>
        </div>
        <div className="rounded-lg border border-shell-border bg-shell-panelSoft px-2.5 py-2">
          <div className="text-[11px] text-shell-muted">fallback</div>
          <div className="text-sm font-semibold text-shell-ink">{String(ms?.fallback_used ?? false)}</div>
        </div>
        <div className="rounded-lg border border-shell-border bg-shell-panelSoft px-2.5 py-2">
          <div className="text-[11px] text-shell-muted">context</div>
          <div className="text-sm font-semibold text-shell-ink break-words">{ctxLabel}</div>
        </div>
      </div>

      <div className="text-[10px] font-bold uppercase tracking-wider text-shell-muted mb-1">stage chips</div>
      {stages.length === 0 ? (
        <EmptyHint>No stage summary.</EmptyHint>
      ) : (
        <div className="flex flex-wrap gap-1 mb-2">
          {stages.map((s) => (
            <Badge key={s.stage} tone={stageChipTone(s)}>
              {s.stage}: {s.stage_status}
            </Badge>
          ))}
        </div>
      )}

      <div className="text-[10px] font-bold uppercase tracking-wider text-shell-muted mb-1">safe explanation</div>
      {explanations.length === 0 ? (
        <EmptyHint>
          {llmContext === "global"
            ? "No global LLM explanation in current mode."
            : "No LLM explanation for this item in current mode."}
        </EmptyHint>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {explanations.map((e, i) => (
            <li key={i} className="rounded-lg border border-shell-border bg-shell-panelSoft px-2.5 py-2">
              <div className="text-xs font-semibold text-shell-ink">{e.stage} · {e.stage_status}</div>
              <p className="text-[11px] text-shell-muted mt-1 break-words">{e.safe_summary}</p>
              {e.error_code && <div className="text-[10px] text-rose-300 mt-0.5">{e.error_code}</div>}
              {e.redaction_note && <div className="text-[10px] text-shell-muted mt-0.5">redacted</div>}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
