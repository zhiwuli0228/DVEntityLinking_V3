// VisualWorkbenchState: single source of truth for the workbench UI, updated via
// a reducer. Selection state (active mention/candidate/entity/llm context) is
// centralized so ResultStream, EntityDetailZone and LlmExplanation stay in sync.

import type {
  EntitiesResponse,
  LlmConfig,
  LinkResult,
  RetrievalResult,
  RuntimeStatus,
  RunMode,
  SafeEntity,
} from "../api/client";
import { adaptLinkResult, type UIMention } from "../lib/adapter";

export type LlmContext = "global" | "mention" | "candidate";

export interface WorkbenchState {
  runtime: RuntimeStatus | null;
  llmConfig: LlmConfig | null;
  catalog: EntitiesResponse | null;
  query: string;
  mode: RunMode;
  allowFallback: boolean;
  loading: boolean;
  error: string | null;
  result: LinkResult | null;
  mentions: UIMention[];
  activeMentionIndex: number | null;
  activeCandidateId: string | null;
  activeEntityId: string | null;
  activeTypeFilter: string;
  entityDetail: SafeEntity | null;
  retrieval: RetrievalResult | null;
  llmContext: LlmContext;
  debugCollapsed: boolean;
  selectionSeq: number;
}

export const initialState: WorkbenchState = {
  runtime: null,
  llmConfig: null,
  catalog: null,
  query: "",
  mode: "offline_demo",
  allowFallback: true,
  loading: false,
  error: null,
  result: null,
  mentions: [],
  activeMentionIndex: null,
  activeCandidateId: null,
  activeEntityId: null,
  activeTypeFilter: "",
  entityDetail: null,
  retrieval: null,
  llmContext: "global",
  debugCollapsed: true,
  selectionSeq: 0,
};

export type Action =
  | { type: "SET_RUNTIME"; runtime: RuntimeStatus; llmConfig: LlmConfig }
  | { type: "SET_CATALOG"; catalog: EntitiesResponse }
  | { type: "SET_TYPE_FILTER"; filter: string }
  | { type: "SET_QUERY"; query: string }
  | { type: "SET_MODE"; mode: RunMode }
  | { type: "SET_FALLBACK"; allow: boolean }
  | { type: "LINK_START" }
  | { type: "LINK_OK"; result: LinkResult }
  | { type: "LINK_FAIL"; error: string }
  | { type: "SET_LLM_CONFIG"; config: LlmConfig }
  | { type: "SELECT_MENTION"; index: number }
  | { type: "SELECT_CANDIDATE"; mentionIndex: number; candidateId: string }
  | { type: "SELECT_ENTITY"; entityId: string; from: "mention" | "catalog" }
  | { type: "SET_ENTITY_DETAIL"; entity: SafeEntity | null }
  | { type: "SET_RETRIEVAL"; retrieval: RetrievalResult | null }
  | { type: "SET_LLM_CONTEXT"; context: LlmContext }
  | { type: "TOGGLE_DEBUG"; collapsed: boolean }
  | { type: "SET_ERROR"; error: string | null };

export function reducer(state: WorkbenchState, action: Action): WorkbenchState {
  switch (action.type) {
    case "SET_RUNTIME":
      return { ...state, runtime: action.runtime, llmConfig: action.llmConfig };
    case "SET_CATALOG":
      return { ...state, catalog: action.catalog };
    case "SET_TYPE_FILTER":
      return { ...state, activeTypeFilter: action.filter };
    case "SET_QUERY":
      return { ...state, query: action.query };
    case "SET_MODE":
      return { ...state, mode: action.mode };
    case "SET_FALLBACK":
      return { ...state, allowFallback: action.allow };
    case "LINK_START":
      return { ...state, loading: true, error: null };
    case "LINK_OK": {
      const adapted = adaptLinkResult(action.result);
      return {
        ...state,
        loading: false,
        error: null,
        result: action.result,
        mentions: adapted.mentions,
        activeMentionIndex: adapted.defaultMentionIndex,
        activeCandidateId: adapted.defaultCandidateId,
        activeEntityId: adapted.defaultEntityId,
        llmContext: adapted.defaultMentionIndex === null ? "global" : "mention",
        entityDetail: null,
        retrieval: null,
      };
    }
    case "LINK_FAIL":
      return { ...state, loading: false, error: action.error, result: null, mentions: [] };
    case "SET_LLM_CONFIG":
      return { ...state, llmConfig: action.config };
    case "SELECT_MENTION": {
      const mention = state.mentions.find((m) => m.index === action.index) ?? null;
      const entityId = mention?.linked_entity?.entity_id ?? mention?.candidates?.[0]?.entity_id ?? null;
      const candidateId = mention?.linked_entity ? null : mention?.candidates?.[0]?.entity_id ?? null;
      return {
        ...state,
        activeMentionIndex: action.index,
        activeCandidateId: candidateId,
        activeEntityId: entityId,
        llmContext: "mention",
        entityDetail: null,
        retrieval: null,
        selectionSeq: state.selectionSeq + 1,
      };
    }
    case "SELECT_CANDIDATE":
      return {
        ...state,
        activeMentionIndex: action.mentionIndex,
        activeCandidateId: action.candidateId,
        activeEntityId: action.candidateId,
        llmContext: "candidate",
        entityDetail: null,
        retrieval: null,
        selectionSeq: state.selectionSeq + 1,
      };
    case "SELECT_ENTITY":
      return {
        ...state,
        activeEntityId: action.entityId,
        llmContext: action.from === "catalog" ? "global" : state.llmContext,
        entityDetail: null,
        retrieval: null,
        selectionSeq: state.selectionSeq + 1,
      };
    case "SET_ENTITY_DETAIL":
      return { ...state, entityDetail: action.entity };
    case "SET_RETRIEVAL":
      return { ...state, retrieval: action.retrieval };
    case "SET_LLM_CONTEXT":
      return { ...state, llmContext: action.context };
    case "TOGGLE_DEBUG":
      return { ...state, debugCollapsed: action.collapsed };
    case "SET_ERROR":
      return { ...state, error: action.error };
    default:
      return state;
  }
}
