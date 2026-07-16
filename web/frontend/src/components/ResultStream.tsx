// Result stream (center column): inline query highlight, query-level summary,
// multi-mention cards and the candidate stack for the active mention. Selection
// here propagates to the detail and explanation zones through shared state.

import type { LinkResult } from "../api/client";
import type { UIMention } from "../lib/adapter";
import { Card, SectionTitle, StatusBadge, Metric, EmptyHint } from "./ui";
import { QueryText } from "./QueryText";

export function ResultStream({
  result,
  mentions,
  activeMentionIndex,
  activeCandidateId,
  onSelectMention,
  onSelectCandidate,
}: {
  result: LinkResult | null;
  mentions: UIMention[];
  activeMentionIndex: number | null;
  activeCandidateId: string | null;
  onSelectMention: (index: number) => void;
  onSelectCandidate: (mentionIndex: number, candidateId: string) => void;
}) {
  const active = mentions.find((m) => m.index === activeMentionIndex) ?? null;
  return (
    <div className="flex flex-col gap-2 min-w-0" data-testid="result-stream">
      <Card>
        <SectionTitle
          kicker="Result stream"
          title="实体链接结果"
          right={result ? <StatusBadge status={result.status} /> : undefined}
        />
        {result ? (
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Metric label="mention_count" value={mentions.length} />
            <Metric label="linked_count" value={mentions.filter((m) => m.linked_entity).length} />
            <Metric
              label="linked_entity"
              value={result.linked_entity ? `${result.linked_entity.entity_id}` : "-"}
            />
            <Metric label="reason" value={result.disambiguation_reason || result.no_match_reason || result.bypass_reason || result.safe_summary || "-"} />
          </dl>
        ) : (
          <EmptyHint>Submit a query to see link results.</EmptyHint>
        )}
      </Card>

      {result && (
        <QueryText
          query={result.query}
          mentions={mentions}
          activeMentionIndex={activeMentionIndex}
          onSelect={onSelectMention}
        />
      )}

      <Card>
        <SectionTitle kicker="Multi-mention stream" title="Mention 简要信息" />
        {mentions.length === 0 ? (
          <EmptyHint>No mention needed for this query.</EmptyHint>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {mentions.map((m) => (
              <li key={m.index}>
                <button
                  type="button"
                  onClick={() => onSelectMention(m.index)}
                  className={`w-full text-left rounded-lg border px-2.5 py-2 transition-colors ${
                    activeMentionIndex === m.index
                      ? "border-accent-teal/70 bg-accent-teal/10"
                      : "border-shell-border bg-shell-panelSoft hover:border-shell-borderStrong"
                  }`}
                  data-testid="mention-result-card"
                  data-mention-index={m.index}
                  aria-pressed={activeMentionIndex === m.index}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-shell-ink">{m.text || "-"}</span>
                    <StatusBadge status={m.status} />
                    {m.predicted_type && (
                      <span className="text-[10px] text-shell-muted">{m.predicted_type}</span>
                    )}
                  </div>
                  <div className="text-[11px] text-shell-muted mt-1 break-words">
                    span {m.span ? `[${m.span.join(", ")}]` : "-"} · linked {m.linked_entity?.entity_id || "-"} ·{" "}
                    {m.candidates.length ? `${m.candidates.length} candidates` : m.no_candidate_reason || "no candidates"}
                    {m.storage_lookup ? " · storage" : ""}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <SectionTitle kicker="Candidate stack" title="候选实体" />
        {!active || active.candidates.length === 0 ? (
          <EmptyHint>No candidate for selected mention.</EmptyHint>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {active.candidates.map((c) => (
              <li key={c.entity_id}>
                <button
                  type="button"
                  onClick={() => onSelectCandidate(active.index, c.entity_id)}
                  className={`w-full text-left rounded-lg border px-2.5 py-2 transition-colors ${
                    activeCandidateId === c.entity_id
                      ? "border-accent-teal/70 bg-accent-teal/10"
                      : "border-shell-border bg-shell-panelSoft hover:border-shell-borderStrong"
                  }`}
                  data-testid="candidate-card"
                  data-candidate-id={c.entity_id}
                  aria-pressed={activeCandidateId === c.entity_id}
                >
                  <div className="text-sm font-semibold text-shell-ink">{c.entity_id}</div>
                  <div className="text-xs text-shell-ink break-words">{c.entity_name}</div>
                  <div className="text-[11px] text-shell-muted mt-0.5 break-words">
                    {c.entity_type} · score {c.confidence ?? c.score ?? "-"} · {c.match_reason}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
