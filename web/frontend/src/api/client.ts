// Typed API client mirroring the Flask safe projection in src/dv_entity_linking/web.py.
// The backend is the single source of truth for the contract; these types are a
// minimal hand-maintained projection used by the workbench UI.

export type Status =
  | "linked"
  | "partial"
  | "ambiguous"
  | "no_match"
  | "not_required"
  | "dependency_failed"
  | "invalid_input";

export type RunMode = "offline_demo" | "llm_enabled_demo";

export interface ApiErrorItem {
  error_code: string;
  message: string;
  field?: string;
}

export interface SafeEntity {
  entity_id: string;
  entity_type: string;
  canonical_name: string;
  aliases: string[];
  description: string;
  source: string;
  data_layer: string;
  attributes_safe?: { key: string; value: unknown; source: string }[];
  omitted_attribute_count?: number;
}

export interface SafeCandidate {
  entity_id: string;
  candidate_id: string;
  canonical_name: string;
  entity_type: string;
  confidence: number;
  score: number;
  match_reason: string;
  rank: number | null;
}

export interface SafeMention {
  text: string;
  span: [number, number] | null;
  predicted_type: string | null;
  entity_type: string | null;
  source: string;
}

export interface SafeMentionResult {
  mention_index: number;
  mention: SafeMention;
  status: Status;
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

export interface LlmExplanation {
  context_type: "global" | "mention" | "candidate";
  mention_index?: number;
  candidate_id?: string;
  entity_id?: string;
  stage: string;
  stage_status: string;
  safe_summary: string;
  fallback_reason?: string;
  error_code?: string;
  redaction_note?: string;
}

export interface StageStatus {
  stage: string;
  attempted: boolean;
  succeeded: boolean;
  fallback_used: boolean;
  stage_status: string;
  safe_summary?: string;
  error_code?: string;
}

export interface ModeStatus {
  requested_mode: RunMode;
  effective_mode: RunMode | null;
  allow_fallback: boolean;
  llm_enabled: boolean;
  llm_used: boolean;
  fallback_used: boolean;
  degraded: boolean;
  result_source: string;
  stage_statuses: StageStatus[];
  error_code?: string | null;
}

export interface LinkResult {
  query: string;
  status: Status;
  mentions: SafeMention[];
  mention_results: SafeMentionResult[];
  linked_entity: SafeEntity | null;
  candidates: SafeCandidate[];
  confidence: number | null;
  disambiguation_reason: string;
  no_match_reason: string;
  bypass_reason: string;
  degraded: boolean;
  error_code: string | null;
  data_layer: string;
  source: string;
  stage_trace?: unknown;
  mode_status: ModeStatus;
  result_source: string;
  safe_summary: string;
  llm_explanations: LlmExplanation[];
}

export interface RuntimeStatus {
  mode: RunMode;
  mode_status: ModeStatus;
  catalog_loaded: boolean;
  entity_count: number;
  type_counts: Record<string, number>;
  llm_enabled: boolean;
  llm_config: LlmConfig;
}

export interface LlmConfig {
  enabled: boolean;
  provider: string;
  model: string;
  base_url_configured: boolean;
  api_key_configured: boolean;
  api_key_env: string;
  timeout_seconds: number;
  runtime_configurable: boolean;
}

export interface EntityListItem extends SafeEntity {}

export interface EntitiesResponse {
  items: EntityListItem[];
  entity_count: number;
  type_counts: Record<string, number>;
  selected_entity_type: string;
}

export interface RetrievalItem {
  entity_id: string;
  canonical_name: string;
  entity_type: string;
  score: number;
  similarity_reason: string;
  source: string;
  data_layer: string;
}

export interface RetrievalResult {
  status: Status;
  query_entity_id: string;
  k: number;
  items: RetrievalItem[];
  no_match_reason: string;
}

export interface QuerySample {
  id: string;
  query: string;
  expected_status: string;
}

export interface SamplesResponse {
  metadata?: Record<string, unknown>;
  queries: QuerySample[];
}

export interface LinkRequest {
  query: string;
  mode: RunMode;
  allow_fallback: boolean;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  const data = (await res.json().catch(() => ({}))) as T & { errors?: ApiErrorItem[]; error_code?: string };
  if (!res.ok) {
    const msg = data?.errors?.[0]?.message || data?.error_code || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data as T;
}

export const api = {
  async status(): Promise<RuntimeStatus> {
    const res = await fetch("/api/status");
    return jsonOrThrow<RuntimeStatus>(res);
  },
  async link(req: LinkRequest): Promise<LinkResult> {
    const res = await fetch("/api/link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    return jsonOrThrow<LinkResult>(res);
  },
  async entities(params: { q?: string; entity_type?: string; limit?: number } = {}): Promise<EntitiesResponse> {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.entity_type) qs.set("entity_type", params.entity_type);
    if (params.limit) qs.set("limit", String(params.limit));
    const res = await fetch(`/api/entities?${qs.toString()}`);
    return jsonOrThrow<EntitiesResponse>(res);
  },
  async entity(entityId: string): Promise<SafeEntity> {
    const res = await fetch(`/api/entities/${encodeURIComponent(entityId)}`);
    return jsonOrThrow<SafeEntity>(res);
  },
  async retrieve(entityId: string, k = 5): Promise<RetrievalResult> {
    const res = await fetch("/api/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_id: entityId, k }),
    });
    return jsonOrThrow<RetrievalResult>(res);
  },
  async getLlmConfig(): Promise<LlmConfig> {
    const res = await fetch("/api/llm/config");
    return jsonOrThrow<LlmConfig>(res);
  },
  async updateLlmConfig(payload: {
    enabled: boolean;
    model?: string;
    base_url?: string;
    api_key?: string;
    timeout_seconds?: number;
  }): Promise<LlmConfig> {
    const res = await fetch("/api/llm/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return jsonOrThrow<LlmConfig>(res);
  },
  async samples(): Promise<SamplesResponse> {
    const res = await fetch("/api/samples");
    return jsonOrThrow<SamplesResponse>(res);
  },
};
