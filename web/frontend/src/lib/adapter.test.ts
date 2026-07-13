// Adapter unit tests: assert /api/link mention_results[] -> UI mentions[] field
// sources, default selection (first linked mention) and storage_lookup passthrough.

import { describe, expect, it } from "vitest";
import { adaptLinkResult } from "./adapter";
import type { LinkResult } from "../api/client";

function baseResult(over: Partial<LinkResult> = {}): LinkResult {
  return {
    query: "Check ALM-51020 and CPU Usage.",
    status: "linked",
    mentions: [],
    mention_results: [],
    linked_entity: null,
    candidates: [],
    confidence: null,
    disambiguation_reason: "",
    no_match_reason: "",
    bypass_reason: "",
    degraded: false,
    error_code: null,
    data_layer: "L0_SYNTHETIC",
    source: "offline_deterministic",
    mode_status: {
      requested_mode: "offline_demo",
      effective_mode: "offline_demo",
      allow_fallback: true,
      llm_enabled: false,
      llm_used: false,
      fallback_used: false,
      degraded: false,
      result_source: "offline_deterministic",
      stage_statuses: [],
    },
    result_source: "offline_deterministic",
    safe_summary: "",
    llm_explanations: [],
    ...over,
  };
}

describe("adaptLinkResult", () => {
  it("maps mention_results fields to UI mentions and preserves index", () => {
    const result = baseResult({
      mention_results: [
        {
          mention_index: 0,
          mention: { text: "ALM-51020", span: [6, 16], predicted_type: "alarm", entity_type: "alarm", source: "deterministic" },
          status: "linked",
          linked_entity: { entity_id: "DV-ALM-002", entity_type: "alarm", canonical_name: "cert expire", aliases: [], description: "", source: "catalog", data_layer: "L1_SANITIZED" },
          candidates: [],
          confidence: 0.99,
          disambiguation_reason: "canonical alarm name match",
          no_match_reason: "",
          bypass_reason: "",
          no_candidate_reason: "",
          degraded: false,
          error_code: null,
          source: "offline_deterministic",
          data_layer: "L1_SANITIZED",
        },
      ],
    });
    const { mentions, defaultMentionIndex, defaultEntityId } = adaptLinkResult(result);
    expect(mentions).toHaveLength(1);
    expect(mentions[0].text).toBe("ALM-51020");
    expect(mentions[0].predicted_type).toBe("alarm");
    expect(mentions[0].status).toBe("linked");
    expect(mentions[0].linked_entity?.entity_id).toBe("DV-ALM-002");
    expect(defaultMentionIndex).toBe(0);
    expect(defaultEntityId).toBe("DV-ALM-002");
  });

  it("defaults to first linked mention, otherwise first mention", () => {
    const result = baseResult({
      mention_results: [
        {
          mention_index: 0,
          mention: { text: "Unknown", span: [0, 7], predicted_type: null, entity_type: null, source: "deterministic" },
          status: "no_match",
          linked_entity: null,
          candidates: [],
          confidence: null,
          disambiguation_reason: "",
          no_match_reason: "no candidate",
          bypass_reason: "",
          no_candidate_reason: "no candidate",
          degraded: false,
          error_code: null,
          source: "offline_deterministic",
          data_layer: "L0_SYNTHETIC",
        },
        {
          mention_index: 1,
          mention: { text: "CPU Usage", span: [21, 30], predicted_type: "kpi_meas_type_key", entity_type: "kpi_meas_type_key", source: "deterministic" },
          status: "linked",
          linked_entity: { entity_id: "DV-KPI-MTK-001", entity_type: "kpi_meas_type_key", canonical_name: "CPU Usage", aliases: [], description: "", source: "catalog", data_layer: "L0_SYNTHETIC" },
          candidates: [],
          confidence: 0.99,
          disambiguation_reason: "canonical name match",
          no_match_reason: "",
          bypass_reason: "",
          no_candidate_reason: "",
          degraded: false,
          error_code: null,
          source: "offline_deterministic",
          data_layer: "L0_SYNTHETIC",
        },
      ],
    });
    const { defaultMentionIndex, defaultEntityId } = adaptLinkResult(result);
    expect(defaultMentionIndex).toBe(1);
    expect(defaultEntityId).toBe("DV-KPI-MTK-001");
  });

  it("passes storage_lookup through when present (V3 mode)", () => {
    const result = baseResult({
      mention_results: [
        {
          mention_index: 0,
          mention: { text: "CBS_1", span: [0, 5], predicted_type: "ne_name", entity_type: "ne_name", source: "deterministic" },
          status: "linked",
          linked_entity: { entity_id: "DV-NE-NAME-001", entity_type: "ne_name", canonical_name: "CBS_1", aliases: [], description: "", source: "v3_gauss_mock", data_layer: "L2_SIMULATED_INTERFACE" },
          candidates: [],
          confidence: 0.95,
          disambiguation_reason: "name match",
          no_match_reason: "",
          bypass_reason: "",
          no_candidate_reason: "",
          degraded: false,
          error_code: null,
          source: "runtime_mock",
          data_layer: "L2_SIMULATED_INTERFACE",
          storage_lookup: { status: "hit", source: "gauss_mock" },
        },
      ],
    });
    const { mentions } = adaptLinkResult(result);
    expect(mentions[0].storage_lookup).toEqual({ status: "hit", source: "gauss_mock" });
  });
});
