// Workbench orchestration: holds the reducer, drives API side effects and
// wires selection state into the shell. Selection of a mention/candidate/entity
// triggers entity-detail + similar-entity fetches via an effect.

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api, type LlmConfig, type QuerySample, type RunMode } from "./api/client";
import { initialState, reducer } from "./state/workbench";
import { Shell } from "./components/Shell";
import { StatusBand } from "./components/StatusBand";
import { QueryCommandZone } from "./components/QueryCommandZone";
import { CatalogFilterZone } from "./components/CatalogFilterZone";
import { ResultStream } from "./components/ResultStream";
import { EntityDetailZone } from "./components/EntityDetailZone";
import { LlmExplanationPanel } from "./components/LlmExplanation";
import { LlmConfigPanel } from "./components/LlmConfigPanel";
import { DebugPanel } from "./components/DebugPanel";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [samples, setSamples] = useState<QuerySample[]>([]);
  const [loadingEntity, setLoadingEntity] = useState(false);
  const didInit = useRef(false);

  const loadCatalog = useCallback(async (typeFilter: string) => {
    try {
      const res = await api.entities({ entity_type: typeFilter || undefined, limit: 200 });
      dispatch({ type: "SET_CATALOG", catalog: res });
    } catch (e) {
      dispatch({ type: "SET_ERROR", error: String((e as Error).message) });
    }
  }, []);

  const fetchEntityAndRetrieval = useCallback(async (entityId: string | null) => {
    if (!entityId) {
      dispatch({ type: "SET_ENTITY_DETAIL", entity: null });
      dispatch({ type: "SET_RETRIEVAL", retrieval: null });
      return;
    }
    setLoadingEntity(true);
    try {
      const [entity, retrieval] = await Promise.all([
        api.entity(entityId).catch(() => null),
        api.retrieve(entityId, 5).catch(() => null),
      ]);
      dispatch({ type: "SET_ENTITY_DETAIL", entity: entity });
      dispatch({ type: "SET_RETRIEVAL", retrieval: retrieval });
    } finally {
      setLoadingEntity(false);
    }
  }, []);

  // React to active entity changes (mention/candidate/catalog selection).
  // selectionSeq forces a refetch even when entityId is unchanged (e.g. clicking
  // a candidate whose entity is already the active one).
  useEffect(() => {
    fetchEntityAndRetrieval(state.activeEntityId);
  }, [state.activeEntityId, state.selectionSeq, fetchEntityAndRetrieval]);

  // React to type filter changes.
  useEffect(() => {
    if (state.catalog) loadCatalog(state.activeTypeFilter);
  }, [state.activeTypeFilter, loadCatalog]); // eslint-disable-line react-hooks/exhaustive-deps

  const runLink = useCallback(
    async (query: string, mode: RunMode, allowFallback: boolean) => {
      if (!query.trim()) return;
      dispatch({ type: "LINK_START" });
      try {
        const result = await api.link({ query, mode, allow_fallback: allowFallback });
        dispatch({ type: "LINK_OK", result });
      } catch (e) {
        dispatch({ type: "LINK_FAIL", error: String((e as Error).message) });
      }
    },
    [],
  );

  // Mount: status + samples + catalog, then auto-run the first sample query.
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    (async () => {
      try {
        const [st, sm] = await Promise.all([api.status(), api.samples().catch(() => ({ queries: [] }))]);
        dispatch({ type: "SET_RUNTIME", runtime: st, llmConfig: st.llm_config });
        setSamples(sm.queries || []);
        const urlQuery = new URLSearchParams(window.location.search).get("query");
        const first = urlQuery || sm.queries?.[0]?.query || "Check ALM-51020 and CPU Usage.";
        dispatch({ type: "SET_QUERY", query: first });
        await loadCatalog("");
        await runLink(first, st.mode, true);
      } catch (e) {
        dispatch({ type: "SET_ERROR", error: String((e as Error).message) });
      }
    })();
  }, [loadCatalog, runLink]);

  const updateLlm = useCallback(async (payload: Parameters<typeof api.updateLlmConfig>[0]) => {
    const cfg: LlmConfig = await api.updateLlmConfig(payload);
    dispatch({ type: "SET_LLM_CONFIG", config: cfg });
    const st = await api.status().catch(() => null);
    if (st) dispatch({ type: "SET_RUNTIME", runtime: st, llmConfig: st.llm_config });
    if (payload.enabled) dispatch({ type: "SET_MODE", mode: "llm_enabled_demo" });
    else dispatch({ type: "SET_MODE", mode: "offline_demo" });
  }, []);

  return (
    <Shell
      statusBand={<StatusBand runtime={state.runtime} result={state.result} llmConfig={state.llmConfig} />}
      llmConfig={<LlmConfigPanel config={state.llmConfig} onUpdate={updateLlm} />}
      left={
        <>
          <QueryCommandZone
            query={state.query}
            mode={state.mode}
            allowFallback={state.allowFallback}
            samples={samples}
            loading={state.loading}
            onQueryChange={(q) => dispatch({ type: "SET_QUERY", query: q })}
            onModeChange={(m) => dispatch({ type: "SET_MODE", mode: m })}
            onFallbackChange={(a) => dispatch({ type: "SET_FALLBACK", allow: a })}
            onSamplePick={(q) => {
              dispatch({ type: "SET_QUERY", query: q });
              runLink(q, state.mode, state.allowFallback);
            }}
            onSubmit={() => runLink(state.query, state.mode, state.allowFallback)}
          />
          <CatalogFilterZone
            catalog={state.catalog}
            activeTypeFilter={state.activeTypeFilter}
            onSelectType={(t) => dispatch({ type: "SET_TYPE_FILTER", filter: t })}
            onSelectEntity={(id) => dispatch({ type: "SELECT_ENTITY", entityId: id, from: "catalog" })}
            activeEntityId={state.activeEntityId}
          />
        </>
      }
      center={
        <ResultStream
          result={state.result}
          mentions={state.mentions}
          activeMentionIndex={state.activeMentionIndex}
          activeCandidateId={state.activeCandidateId}
          onSelectMention={(i) => dispatch({ type: "SELECT_MENTION", index: i })}
          onSelectCandidate={(i, c) => dispatch({ type: "SELECT_CANDIDATE", mentionIndex: i, candidateId: c })}
        />
      }
      right={
        <>
          <EntityDetailZone entity={state.entityDetail} retrieval={state.retrieval} loadingEntity={loadingEntity} />
          <LlmExplanationPanel
            result={state.result}
            llmContext={state.llmContext}
            activeMentionIndex={state.activeMentionIndex}
            activeCandidateId={state.activeCandidateId}
            onGlobalClick={() => dispatch({ type: "SET_LLM_CONTEXT", context: "global" })}
          />
        </>
      }
      debug={
        <DebugPanel
          data={{ status: state.runtime, link: state.result, entity: state.entityDetail }}
          collapsed={state.debugCollapsed}
          onToggle={(c) => dispatch({ type: "TOGGLE_DEBUG", collapsed: c })}
        />
      }
    />
  );
}
