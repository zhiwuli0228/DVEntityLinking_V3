// LinkResultVisualAdapter: converts the /api/link safe projection into the
// UI-normalized mention list used by VisualWorkbenchState. This is a pure
// client-side adapter; the backend does NOT add a parallel top-level mentions[]
// field. Field sources are asserted in adapter.test.ts.

import type { LinkResult, SafeMentionResult, SafeCandidate, SafeEntity } from "../api/client";

export interface UIMention {
  index: number;
  text: string;
  span: [number, number] | null;
  predicted_type: string | null;
  entity_type: string | null;
  status: SafeMentionResult["status"];
  linked_entity: SafeEntity | null;
  candidates: SafeCandidate[];
  confidence: number | null;
  disambiguation_reason: string;
  no_match_reason: string;
  bypass_reason: string;
  no_candidate_reason: string;
  degraded: boolean;
  error_code: string | null;
  source: string;
  data_layer: string;
  storage_lookup?: Record<string, unknown> | null;
}

export interface AdapterResult {
  mentions: UIMention[];
  defaultMentionIndex: number | null;
  defaultCandidateId: string | null;
  defaultEntityId: string | null;
}

export function adaptLinkResult(result: LinkResult): AdapterResult {
  const mentions: UIMention[] = result.mention_results.map((m) => ({
    index: m.mention_index,
    text: m.mention.text,
    span: m.mention.span,
    predicted_type: m.mention.predicted_type ?? m.mention.entity_type,
    entity_type: m.mention.entity_type ?? m.mention.predicted_type,
    status: m.status,
    linked_entity: m.linked_entity,
    candidates: m.candidates,
    confidence: m.confidence,
    disambiguation_reason: m.disambiguation_reason,
    no_match_reason: m.no_match_reason,
    bypass_reason: m.bypass_reason,
    no_candidate_reason: m.no_candidate_reason,
    degraded: m.degraded,
    error_code: m.error_code,
    source: m.source,
    data_layer: m.data_layer,
    storage_lookup: m.storage_lookup ?? null,
  }));

  let defaultMentionIndex: number | null = null;
  if (mentions.length > 0) {
    const firstLinked = mentions.find((m) => m.linked_entity);
    defaultMentionIndex = (firstLinked ?? mentions[0]).index;
  }

  const active =
    mentions.find((m) => m.index === defaultMentionIndex) ?? null;
  const defaultEntityId =
    active?.linked_entity?.entity_id ??
    active?.candidates?.[0]?.entity_id ??
    result.linked_entity?.entity_id ??
    result.candidates?.[0]?.entity_id ??
    null;
  const defaultCandidateId = active?.candidates?.[0]?.entity_id ?? null;

  return { mentions, defaultMentionIndex, defaultCandidateId, defaultEntityId };
}
