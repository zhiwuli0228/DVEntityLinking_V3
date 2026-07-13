"""Optional Flask web/API boundary for the demo."""

from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path
from typing import Any

from .catalog import CatalogError
from .llm import LLMConfig, OpenAICompatibleLLMClient
from .models import (
    ApiError,
    EntityLinkResult,
    EntityRecord,
    ErrorCode,
    LinkCandidate,
    MentionLinkResult,
    ModeRequest,
    ModeStatus,
    RetrievalItem,
    RunMode,
    Status,
    to_plain,
)
from .service import EntityLinkingService


WEB_LLM_API_KEY_ENV = "DVEL_WEB_LLM_API_KEY"
SAFE_ATTRIBUTE_KEYS = {
    "severity",
    "category",
    "domain",
    "vendor",
    "unit",
    "task_type",
    "measurement_type",
    "object_type",
    "ne_type",
    "source_type",
    "lifecycle_state",
}
FORBIDDEN_ATTRIBUTE_FRAGMENTS = {
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
    "base_url",
    "url",
    "host",
    "raw_request",
    "raw_response",
    "prompt",
    "llm",
}


def create_app(
    service: EntityLinkingService | None = None,
    *,
    samples_path: str | Path = "samples/mock/query_samples.json",
    default_mode: RunMode | str = RunMode.OFFLINE_DEMO,
    frontend_dist: str | Path | None = None,
):
    try:
        from flask import Flask, jsonify, request, send_file, send_from_directory
    except ImportError as exc:  # pragma: no cover - depends on optional runtime install
        raise RuntimeError("Flask is required to run the web demo") from exc

    app = Flask(__name__)
    app.config["entity_linking_service"] = service or EntityLinkingService.from_catalog_path()
    app.config["default_run_mode"] = RunMode(default_mode)
    # React SPA build output. Defaults to <repo_root>/web/frontend/dist.
    repo_root = Path(__file__).resolve().parents[2]
    app.config["frontend_dist"] = Path(frontend_dist) if frontend_dist else repo_root / "web" / "frontend" / "dist"

    @app.get("/")
    def index():
        index_html = app.config["frontend_dist"] / "index.html"
        if not index_html.exists():
            return (
                "Frontend build not found. Run `npm install && npm run build` in web/frontend first.",
                503,
                {"Content-Type": "text/plain; charset=utf-8"},
            )
        return send_file(index_html)

    @app.get("/assets/<path:filename>")
    def frontend_assets(filename: str):
        assets_dir = app.config["frontend_dist"] / "assets"
        return send_from_directory(assets_dir, filename)

    @app.get("/classic")
    def classic():
        # Legacy server-rendered page kept as a compat surface for the existing
        # acceptance smokes, which assert on SSR HTML markers. The React SPA at
        # "/" is the primary frontend; new visual evidence is browser-based.
        default_query = request.args.get("query", "") or _default_query(samples_path)
        preloaded = _preloaded_sections(
            app.config["entity_linking_service"],
            default_query,
            app.config["default_run_mode"],
        )
        html = _index_html(default_query, app.config["default_run_mode"])
        for section_id, value in preloaded.items():
            html = _replace_section(html, section_id, value)
        return html

    @app.get("/api/status")
    def status():
        current = app.config["entity_linking_service"]
        try:
            load_result = current.catalog.load()
            run_mode = app.config["default_run_mode"]
            mode_status = ModeStatus(
                requested_mode=run_mode,
                effective_mode=run_mode,
                allow_fallback=True,
                llm_enabled=current.llm_client is not None,
                llm_used=False,
                fallback_used=False,
                degraded=False,
                stage_statuses=_default_stage_statuses(run_mode, current.llm_client is not None),
            )
            return jsonify(
                {
                    "mode": run_mode.value,
                    "mode_status": to_plain(mode_status),
                    "catalog_loaded": True,
                    "entity_count": load_result.entity_count,
                    "type_counts": load_result.type_counts,
                    "llm_enabled": current.llm_client is not None,
                    "llm_config": _safe_llm_config(current),
                }
            )
        except CatalogError as exc:
            return jsonify(_error_payload(exc.error_code, str(exc))), 503

    @app.post("/api/link")
    def link():
        current = app.config["entity_linking_service"]
        payload = request.get_json(silent=True) or {}
        default_run_mode = app.config["default_run_mode"]
        mode_request, error_payload = _parse_mode_request(payload, default_run_mode)
        if error_payload is not None:
            return jsonify(error_payload), 400
        try:
            result = current.link_query(
                mode_request.query,
                mode=mode_request.mode,
                allow_fallback=mode_request.allow_fallback,
            )
        except CatalogError as exc:
            return jsonify(_error_payload(exc.error_code, str(exc))), 503

        mode_status = _build_mode_status(
            mode_request,
            current.llm_client is not None,
            result.status,
            result.source,
            result.degraded,
            result.error_code,
            stage_trace=result.stage_trace,
        )
        return jsonify(_safe_link_result(result, mode_status))

    @app.get("/api/entities")
    def entities():
        current = app.config["entity_linking_service"]
        query = request.args.get("q", "")
        entity_type = request.args.get("entity_type")
        limit = _parse_int(request.args.get("limit"), default=20, minimum=1, maximum=200)
        current.ensure_catalog_loaded()
        if query.strip():
            items = current.retriever.search_entities(
                query,
                entity_type=entity_type,
                limit=limit,
            )
        else:
            items = current.catalog.entities
            if entity_type:
                items = [item for item in items if item.entity_type.value == entity_type]
            items = items[:limit]
        type_counts = _type_counts(current.catalog.entities)
        return jsonify(
            {
                "items": [_safe_entity(item) for item in items],
                "entity_count": len(current.catalog.entities),
                "type_counts": type_counts,
                "selected_entity_type": entity_type or "",
            }
        )

    @app.get("/api/entities/<entity_id>")
    def entity(entity_id: str):
        current = app.config["entity_linking_service"]
        record = current.retriever.get_entity(entity_id)
        if not record:
            return jsonify({"status": "no_match", "no_match_reason": "entity not found"}), 404
        return jsonify(_safe_entity(record, include_attributes=True))

    @app.post("/api/retrieve")
    def retrieve():
        current = app.config["entity_linking_service"]
        payload = request.get_json(silent=True) or {}
        result = current.retriever.similar_entities(
            str(payload.get("entity_id", "")),
            _parse_int(payload.get("k"), default=5, minimum=1, maximum=20),
        )
        return jsonify(_safe_retrieval_result(result))

    @app.get("/api/llm/config")
    def get_llm_config():
        current = app.config["entity_linking_service"]
        return jsonify(_safe_llm_config(current))

    @app.post("/api/llm/config")
    def update_llm_config():
        current = app.config["entity_linking_service"]
        payload = request.get_json(silent=True) or {}
        enabled = payload.get("enabled", False)
        if not isinstance(enabled, bool):
            return (
                jsonify(_error_payload(ErrorCode.INVALID_INPUT, "enabled must be a JSON boolean", field="enabled")),
                400,
            )
        if not enabled:
            current.configure_llm_client(None)
            app.config["default_run_mode"] = RunMode.OFFLINE_DEMO
            return jsonify(_safe_llm_config(current))

        existing_config = getattr(current.llm_client, "config", None)
        provider = str(payload.get("provider") or getattr(existing_config, "provider", "openai_compatible"))
        model = str(payload.get("model") or getattr(existing_config, "model", "qwen3.6-27b")).strip()
        base_url = str(payload.get("base_url") or getattr(existing_config, "base_url", "")).strip()
        api_key = str(payload.get("api_key") or "")
        timeout_seconds = _parse_timeout_seconds(
            payload.get("timeout_seconds", getattr(existing_config, "timeout_seconds", 20.0))
        )
        if timeout_seconds is None:
            return (
                jsonify(
                    _error_payload(
                        ErrorCode.INVALID_INPUT,
                        "timeout_seconds must be a number between 1 and 120",
                        field="timeout_seconds",
                    )
                ),
                400,
            )
        if not model:
            return jsonify(_error_payload(ErrorCode.INVALID_INPUT, "model is required", field="model")), 400
        if not base_url:
            return jsonify(_error_payload(ErrorCode.INVALID_INPUT, "base_url is required", field="base_url")), 400

        api_key_env = getattr(existing_config, "api_key_env", WEB_LLM_API_KEY_ENV)
        if api_key:
            os.environ[WEB_LLM_API_KEY_ENV] = api_key
            api_key_env = WEB_LLM_API_KEY_ENV
        config = LLMConfig(
            provider=provider,
            enabled=True,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
        )
        if not config.api_key:
            return (
                jsonify(
                    _error_payload(
                        ErrorCode.INVALID_INPUT,
                        "api_key is required when enabling LLM",
                        field="api_key",
                    )
                ),
                400,
            )
        current.configure_llm_client(OpenAICompatibleLLMClient(config))
        app.config["default_run_mode"] = RunMode.LLM_ENABLED_DEMO
        return jsonify(_safe_llm_config(current))

    @app.get("/api/samples")
    def samples():
        payload = json.loads(Path(samples_path).read_text(encoding="utf-8-sig"))
        return jsonify(payload)

    return app


def _index_html(default_query: str, default_run_mode: RunMode) -> str:
    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DVEntityLinking V2 Workbench</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #edf1f4;
      --shell: #172026;
      --shell-soft: #22313a;
      --panel: #ffffff;
      --panel-alt: #f7fafb;
      --ink: #18212a;
      --muted: #5f6f7a;
      --border: #cbd5dd;
      --border-strong: #93a4b1;
      --blue: #2563eb;
      --green: #18794e;
      --amber: #a15c00;
      --red: #b42318;
      --teal: #0f766e;
      --chip: #eef3f6;
    }
    * { box-sizing: border-box; min-width: 0; }
    html { background: var(--bg); }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    main.visual-shell {
      width: min(1500px, 100%);
      margin: 0 auto;
      padding: 14px;
      display: grid;
      gap: 10px;
    }
    h1, h2, h3, p { margin-top: 0; }
    h1 { margin-bottom: 2px; font-size: 1.45rem; line-height: 1.15; }
    h2 { margin-bottom: 8px; font-size: .98rem; line-height: 1.25; }
    h3 { margin-bottom: 6px; font-size: .84rem; line-height: 1.25; text-transform: uppercase; color: var(--muted); }
    section, details {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 1px 0 rgba(23, 32, 38, .04);
    }
    button, input, select {
      min-height: 36px;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 7px 10px;
      font: inherit;
      max-width: 100%;
    }
    input, select { background: #fff; color: var(--ink); }
    button { background: var(--blue); color: #fff; border-color: var(--blue); cursor: pointer; }
    button.secondary { background: #fff; color: var(--ink); border-color: var(--border); }
    button.ghost { background: var(--chip); color: var(--ink); border-color: transparent; }
    button[aria-pressed="true"], .item.is-active {
      border-color: var(--teal);
      outline: 2px solid rgba(15, 118, 110, .22);
      outline-offset: 1px;
    }
    label { color: var(--muted); }
    .app-header {
      display: flex;
      gap: 12px;
      justify-content: space-between;
      align-items: end;
      flex-wrap: wrap;
      color: #f6fafc;
      background: var(--shell);
      border: 1px solid #0d1419;
      border-radius: 8px;
      padding: 14px;
    }
    .app-header .muted { color: #b8c5ce; margin-bottom: 0; }
    .prototype-pills { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
    .prototype-pill {
      border: 1px solid rgba(255,255,255,.22);
      border-radius: 999px;
      color: #dce8ee;
      padding: 4px 8px;
      font-size: .74rem;
      white-space: nowrap;
    }
    .muted { color: var(--muted); }
    .visual-frame {
      display: grid;
      gap: 10px;
      background: #dfe6eb;
      border: 1px solid #c6d0d8;
      border-radius: 8px;
      padding: 10px;
    }
    .status-band {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(260px, .58fr);
      gap: 10px;
      align-items: stretch;
      background: var(--shell-soft);
      border: 1px solid #10181d;
      border-radius: 8px;
      padding: 10px;
    }
    .status-band #runtime-status,
    .status-band #llm-config-panel {
      background: rgba(255,255,255,.06);
      border-color: rgba(255,255,255,.14);
      color: #f5f8fa;
      box-shadow: none;
    }
    .status-band #llm-config-panel summary { cursor: pointer; font-weight: 700; }
    .status-band label, .status-band .muted, .status-band .metric dt { color: #c2ced6; }
    .status-band .metric {
      background: rgba(255,255,255,.08);
      border-color: rgba(255,255,255,.14);
    }
    .status-band .metric dd { color: #ffffff; }
    .status-band input { background: #f7fafb; color: var(--ink); }
    .visual-layout {
      display: grid;
      grid-template-columns: minmax(260px, .9fr) minmax(360px, 1.35fr) minmax(320px, 1fr);
      gap: 10px;
      align-items: start;
    }
    .query-command-zone,
    .result-stream,
    .right-rail,
    .entity-detail-zone,
    .catalog-filter-zone,
    .llm-explanation-component {
      display: grid;
      gap: 10px;
      align-content: start;
    }
    .panel-title { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .panel-kicker { margin: 0 0 4px; color: var(--teal); font-size: .72rem; font-weight: 800; text-transform: uppercase; }
    .runtime-grid, .summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
    .metric { border: 1px solid var(--border); border-radius: 6px; padding: 8px; min-width: 0; background: var(--panel-alt); }
    .metric dt { color: var(--muted); font-size: .76rem; }
    .metric dd { margin: 3px 0 0; font-weight: 750; overflow-wrap: anywhere; }
    .query-form, .llm-config-form { display: grid; gap: 8px; align-items: end; }
    .query-form { grid-template-columns: minmax(0, 1fr); }
    .query-controls { display: grid; grid-template-columns: minmax(0, 1fr) minmax(120px, .72fr); gap: 8px; align-items: center; }
    .llm-config-form { grid-template-columns: 110px minmax(130px, 1fr); }
    .field { display: grid; gap: 4px; font-size: .78rem; }
    .status {
      display: inline-flex;
      min-height: 24px;
      align-items: center;
      max-width: 100%;
      border-radius: 999px;
      padding: 3px 9px;
      background: var(--chip);
      color: var(--ink);
      font-weight: 800;
      overflow-wrap: anywhere;
    }
    .status.linked { background: #e5f4ec; color: var(--green); }
    .status.partial, .status.ambiguous { background: #fff2d8; color: var(--amber); }
    .status.no_match, .status.invalid_input, .status.dependency_failed { background: #fde9e7; color: var(--red); }
    .status.not_required { background: #edf1f4; color: var(--muted); }
    .list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
    .item {
      border: 1px solid var(--border);
      border-left: 4px solid var(--border-strong);
      border-radius: 6px;
      padding: 9px;
      min-width: 0;
      background: #fff;
      color: var(--ink);
      overflow-wrap: anywhere;
    }
    .item button { margin-top: 6px; }
    .mention-card, .candidate-card, .catalog-card { width: 100%; text-align: left; display: block; }
    .mention-card.is-active, .candidate-card.is-active, .catalog-card.is-active { border-left-color: var(--teal); background: #f4fbfa; }
    .meta { color: var(--muted); font-size: .8rem; overflow-wrap: anywhere; }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
    .type-filters { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
    .filter-chip { min-height: 30px; padding: 5px 9px; }
    .filter-chip.is-active { background: #e8f5f2; border-color: var(--teal); color: var(--teal); font-weight: 800; }
    .split-list { display: grid; gap: 8px; max-height: 360px; overflow: auto; padding-right: 2px; }
    .explanation-list .item { border-left-color: var(--blue); }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 28rem; overflow: auto; }
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
    @media (max-width: 1120px) {
      .status-band, .visual-layout { grid-template-columns: 1fr; }
      .right-rail { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
    }
    @media (max-width: 760px) {
      main.visual-shell { padding: 10px; }
      .runtime-grid, .summary-grid { grid-template-columns: 1fr 1fr; }
      .right-rail { grid-template-columns: 1fr; }
      .llm-config-form, .query-controls { grid-template-columns: 1fr; }
      .app-header { align-items: start; }
      .prototype-pills { justify-content: flex-start; }
      section, details { padding: 10px; }
    }
    @media (max-width: 520px) {
      .runtime-grid, .summary-grid { grid-template-columns: 1fr; }
      .visual-frame { padding: 8px; }
      .status-band { padding: 8px; }
    }
  </style>
</head>
<body>
  <main id="visual-workbench-shell" data-testid="visual-workbench-shell" class="visual-shell">
    <header class="app-header">
      <div>
        <h1>DVEntityLinking V2 Workbench</h1>
        <p class="muted">Multi-mention entity linking demo</p>
      </div>
      <div class="prototype-pills" aria-label="absorbed prototype principles">
        <span class="prototype-pill">Ops status density</span>
        <span class="prototype-pill">Generative explanation component</span>
        <span class="prototype-pill">Schema-driven state</span>
      </div>
    </header>

    <div class="visual-frame">
      <div id="status-band" data-testid="status-band" class="status-band">
        <section id="runtime-status" data-testid="runtime-status"></section>

        <details id="llm-config-panel">
          <summary>LLM 配置</summary>
          <form id="llm-config-form" class="llm-config-form">
            <label><input name="enabled" type="checkbox"> enabled</label>
            <label class="field">model<input name="model" value="qwen3.6-27b"></label>
            <label class="field">base_url<input name="base_url" placeholder="https://.../v1"></label>
            <label class="field">api_key<input name="api_key" type="password" autocomplete="off" placeholder="不落盘"></label>
            <label class="field">timeout<input name="timeout_seconds" type="number" min="1" max="120" value="20"></label>
            <button type="submit">保存</button>
          </form>
          <p id="llm-config-status" class="muted"></p>
        </details>
      </div>

      <div class="visual-layout" aria-label="V2 visual workbench layout">
        <div id="query-command-zone" data-testid="query-command-zone" class="query-command-zone">
          <section id="query-panel" data-testid="query-panel">
            <p class="panel-kicker">Command zone</p>
            <h2>Query</h2>
            <form id="query-form" class="query-form">
              <input name="query" value="__DEFAULT_QUERY__">
              <div class="query-controls">
                <select name="mode">
                  <option value="offline_demo">offline_demo</option>
                  <option value="llm_enabled_demo">llm_enabled_demo</option>
                </select>
                <label><input name="allow_fallback" type="checkbox" checked> allow_fallback</label>
              </div>
              <button type="submit">Link</button>
            </form>
          </section>

          <div id="catalog-filter-zone" data-testid="catalog-filter-zone" class="catalog-filter-zone">
            <section id="entity-catalog" data-testid="catalog-panel"></section>
          </div>
        </div>

        <div id="result-stream" data-testid="result-stream" class="result-stream">
          <section id="result-summary" data-testid="result-summary"></section>
          <section id="mention-summary" data-testid="mention-strip"></section>
          <section id="candidate-list" data-testid="candidate-detail-panel"></section>
        </div>

        <div class="right-rail">
          <div id="entity-detail-zone" data-testid="entity-detail-zone" class="entity-detail-zone">
            <section id="entity-detail" data-testid="entity-detail-panel"></section>
            <section id="retrieval-result" data-testid="retrieval-result"></section>
          </div>
          <div id="llm-explanation-component" data-testid="llm-explanation-component" class="llm-explanation-component">
            <section id="llm-safe-explanation-panel" data-testid="llm-safe-explanation-panel"></section>
          </div>
        </div>
      </div>
    </div>

    <details id="debug-details" data-testid="debug-panel">
      <summary>调试详情</summary>
      <pre id="debug-json"></pre>
    </details>
  </main>
  <script>
    const defaultMode = "__DEFAULT_RUN_MODE__";
    const state = {
      status: null,
      catalog: {items: [], type_counts: {}},
      result: null,
      selectedMentionIndex: null,
      selectedCandidateId: null,
      selectedEntityId: null,
      activeEntityType: "",
      entityRequestToken: 0,
      llmPanelContext: "global"
    };
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]));
    const statusClass = (status) => `status ${String(status || "")}`;
    const setDebug = (value) => {
      document.getElementById("debug-json").textContent = JSON.stringify(value, null, 2);
    };
    const mentionReason = (item) =>
      item?.disambiguation_reason || item?.no_candidate_reason || item?.no_match_reason ||
      item?.bypass_reason || item?.status || "-";
    const linkedEntity = (payload) => {
      if (payload?.linked_entity?.entity_id) return payload.linked_entity;
      const found = (payload?.mention_results || [])
        .find((item) => item.linked_entity && item.linked_entity.entity_id);
      return found?.linked_entity || null;
    };
    const selectedMention = () => {
      if (!state.result || state.selectedMentionIndex === null) return null;
      return (state.result.mention_results || [])[state.selectedMentionIndex] || null;
    };
    const currentExplanations = (contextType, mentionIndex, candidateId, entityId) => {
      const items = state.result?.llm_explanations || [];
      return items.filter((item) => {
        if (item.context_type !== contextType) return false;
        if (mentionIndex !== undefined && item.mention_index !== mentionIndex) return false;
        if (candidateId && item.candidate_id && item.candidate_id !== candidateId) return false;
        if (entityId && item.entity_id && item.entity_id !== entityId) return false;
        return true;
      });
    };
    const renderRuntimeStatus = (payload) => {
      state.status = payload;
      const typeCounts = payload.type_counts || {};
      const typeText = Object.entries(typeCounts).map(([key, value]) => `${key}: ${value}`).join(", ");
      const llmConfig = payload.llm_config || {};
      const llmText = payload.llm_enabled ? `${llmConfig.model || "enabled"}` : "offline";
      document.getElementById("runtime-status").innerHTML = `
        <div class="panel-title">
          <div>
            <p class="panel-kicker">Status band</p>
            <h2>运行状态</h2>
          </div>
          <span class="${statusClass(payload.mode || defaultMode)}">${esc(payload.mode || defaultMode)}</span>
        </div>
        <dl class="runtime-grid">
          <div class="metric"><dt>catalog loaded</dt><dd>${esc(payload.catalog_loaded)}</dd></div>
          <div class="metric"><dt>entity_count</dt><dd>${esc(payload.entity_count || 0)}</dd></div>
          <div class="metric"><dt>type_counts</dt><dd>${esc(typeText || "-")}</dd></div>
          <div class="metric"><dt>LLM overview</dt><dd>${esc(llmText)}</dd></div>
        </dl>`;
    };
    const renderLlmConfig = (payload) => {
      const form = document.getElementById("llm-config-form");
      form.elements.enabled.checked = Boolean(payload.enabled);
      form.elements.model.value = payload.model || "qwen3.6-27b";
      form.elements.timeout_seconds.value = payload.timeout_seconds || 20;
      const parts = [
        payload.enabled ? "enabled" : "offline",
        payload.base_url_configured ? "base_url configured" : "base_url empty",
        payload.api_key_configured ? "api_key configured" : "api_key empty",
        payload.api_key_env || "DVEL_WEB_LLM_API_KEY"
      ];
      document.getElementById("llm-config-status").textContent = parts.join(" · ");
    };
    const renderResultSummary = (payload) => {
      state.result = payload;
      const entity = linkedEntity(payload);
      const mentionCount = (payload.mention_results || []).length;
      const linkedCount = (payload.mention_results || []).filter((item) => item.linked_entity).length;
      const reason = payload.disambiguation_reason || payload.no_match_reason || payload.bypass_reason || payload.safe_summary || payload.status || "";
      const title = entity ? `${entity.entity_id} · ${entity.canonical_name}` : "-";
      document.getElementById("result-summary").innerHTML = `
        <div class="panel-title">
          <div>
            <p class="panel-kicker">Result stream</p>
            <h2>实体链接结果</h2>
          </div>
          <span class="${statusClass(payload.status)}">${esc(payload.status || "unknown")}</span>
        </div>
        <dl class="summary-grid">
          <div class="metric"><dt>mention_count</dt><dd>${esc(mentionCount)}</dd></div>
          <div class="metric"><dt>linked_count</dt><dd>${esc(linkedCount)}</dd></div>
          <div class="metric"><dt>linked_entity</dt><dd>${esc(title)}</dd></div>
          <div class="metric"><dt>reason</dt><dd>${esc(reason || "-")}</dd></div>
        </dl>`;
    };
    const renderMentions = (payload) => {
      const rows = (payload.mention_results || []).map((item, index) => {
        const mention = item.mention || {};
        const span = Array.isArray(mention.span) ? `[${mention.span.join(", ")}]` : "-";
        const type = mention.entity_type || mention.predicted_type || "-";
        const linked = item.linked_entity?.entity_id || "-";
        const candidateText = item.candidates?.length ? `${item.candidates.length} candidates` : (item.no_candidate_reason || "no candidates");
        const active = state.selectedMentionIndex === index ? " is-active" : "";
        return `<li>
          <button class="item mention-card${active}" type="button" data-testid="mention-result-card" data-mention-index="${index}" aria-pressed="${state.selectedMentionIndex === index}">
            <strong>${esc(mention.text || "-")}</strong>
            <br><span class="${statusClass(item.status)}">${esc(item.status || "-")}</span>
            <span class="meta"> type ${esc(type)} · span ${esc(span)} · linked ${esc(linked)} · ${esc(candidateText)}</span>
            <br><span class="meta">${esc(mentionReason(item))}</span>
          </button>
        </li>`;
      }).join("");
      const body = rows ? `<ul class="list">${rows}</ul>` : '<p class="muted">No mention needed for this query.</p>';
      document.getElementById("mention-summary").innerHTML = `
        <p class="panel-kicker">Multi-mention stream</p>
        <h2>Mention 简要信息</h2>
        ${body}`;
      document.querySelectorAll("[data-mention-index]").forEach((button) => {
        button.addEventListener("click", async () => {
          state.selectedMentionIndex = Number(button.dataset.mentionIndex);
          state.selectedCandidateId = null;
          state.llmPanelContext = "mention";
          const mention = selectedMention();
          renderMentions(state.result);
          renderCandidates(mention?.candidates || []);
          const entityId = mention?.linked_entity?.entity_id || mention?.candidates?.[0]?.entity_id;
          if (entityId) {
            await showEntity(entityId);
          } else {
            state.entityRequestToken += 1;
            renderEntity(null);
            renderRetrieval({items: []});
          }
          renderLlmPanel();
        });
      });
    };
    const renderCandidates = (items) => {
      const rows = (items || []).map((item) => {
        const active = state.selectedCandidateId === item.entity_id ? " is-active" : "";
        return `
        <li>
          <button class="item candidate-card${active}" type="button" data-testid="candidate-card" data-candidate-id="${esc(item.entity_id)}" aria-pressed="${state.selectedCandidateId === item.entity_id}">
            <strong>${esc(item.entity_id)}</strong><br>
            ${esc(item.canonical_name)}<br>
            <span class="meta">${esc(item.entity_type)} · score ${esc(item.confidence ?? item.score ?? "-")} · ${esc(item.match_reason || "")}</span>
          </button>
        </li>`;
      }).join("");
      document.getElementById("candidate-list").innerHTML = `
        <p class="panel-kicker">Candidate stack</p>
        <h2>候选实体</h2>
        ${rows ? `<ul class="list">${rows}</ul>` : '<p class="muted">No candidate for selected mention.</p>'}`;
      document.querySelectorAll("[data-candidate-id]").forEach((button) => {
        button.addEventListener("click", async () => {
          state.selectedCandidateId = button.dataset.candidateId;
          state.llmPanelContext = "candidate";
          renderCandidates(items || []);
          await showEntity(state.selectedCandidateId);
          renderLlmPanel();
        });
      });
    };
    const renderEntityCatalog = (payload) => {
      const items = Array.isArray(payload) ? payload : (payload.items || []);
      const typeCounts = Array.isArray(payload) ? state.catalog.type_counts : (payload.type_counts || {});
      const selectedType = Array.isArray(payload) ? state.activeEntityType : (payload.selected_entity_type || "");
      state.activeEntityType = selectedType;
      state.catalog = {items, type_counts: typeCounts};
      const filters = [''].concat(Object.keys(typeCounts)).map((type) => `
        <button class="secondary filter-chip ${selectedType === type ? "is-active" : ""}" type="button" data-entity-type="${esc(type)}" aria-pressed="${selectedType === type}">${esc(type || "all")}</button>`).join("");
      const rows = items.map((item) => `
        <li>
          <button class="item catalog-card${state.selectedEntityId === item.entity_id ? " is-active" : ""}" type="button" data-testid="catalog-entity-card" data-entity-id="${esc(item.entity_id)}">
            <strong>${esc(item.entity_id)}</strong> ${esc(item.canonical_name)}
            <br><span class="meta">${esc(item.entity_type)} · aliases ${esc((item.aliases || []).length)}</span>
          </button>
        </li>`).join("");
      document.getElementById("entity-catalog").innerHTML = `
        <div class="panel-title">
          <div>
            <p class="panel-kicker">Catalog filter zone</p>
            <h2>样例实体目录</h2>
          </div>
          <button class="secondary" id="show-entities" type="button">查看全部样例实体</button>
        </div>
        <div class="type-filters" data-testid="catalog-type-filter">${filters}</div>
        ${rows ? `<ul class="list split-list">${rows}</ul>` : '<p class="muted">点击查看全部样例实体</p>'}`;
      document.querySelectorAll("#entity-catalog [data-entity-id]").forEach((button) => {
        button.addEventListener("click", () => showEntity(button.dataset.entityId));
      });
      document.querySelectorAll("#entity-catalog [data-entity-type]").forEach((button) => {
        button.addEventListener("click", () => loadEntities(button.dataset.entityType));
      });
      const showButton = document.getElementById("show-entities");
      if (showButton) showButton.addEventListener("click", () => loadEntities(""));
    };
    const renderEntity = (payload) => {
      if (!payload || !payload.entity_id) {
        document.getElementById("entity-detail").innerHTML = '<p class="panel-kicker">Entity detail zone</p><h2>实体详情</h2><p class="muted">No linked entity.</p>';
        return;
      }
      const attrs = (payload.attributes_safe || []).map((item) => `
        <li class="item"><strong>${esc(item.key)}</strong>: ${esc(item.value)} <span class="meta">${esc(item.source || "")}</span></li>`).join("");
      document.getElementById("entity-detail").innerHTML = `
        <p class="panel-kicker">Entity detail zone</p>
        <h2>实体详情</h2>
        <dl class="summary-grid">
          <div class="metric"><dt>entity_id</dt><dd>${esc(payload.entity_id)}</dd></div>
          <div class="metric"><dt>entity_type</dt><dd>${esc(payload.entity_type)}</dd></div>
          <div class="metric"><dt>canonical_name</dt><dd>${esc(payload.canonical_name)}</dd></div>
          <div class="metric"><dt>aliases</dt><dd>${esc((payload.aliases || []).join(", ") || "-")}</dd></div>
        </dl>
        <p class="muted">${esc(payload.description || "")}</p>
        <h3>safe attributes</h3>
        ${attrs ? `<ul class="list">${attrs}</ul>` : '<p class="muted">No safe attributes.</p>'}
        <p class="meta">omitted_attribute_count: ${esc(payload.omitted_attribute_count || 0)}</p>`;
    };
    const renderRetrieval = (payload) => {
      const rows = (payload.items || []).map((item) => `
        <li class="item">
          <strong>${esc(item.entity_id)}</strong> ${esc(item.canonical_name)}
          <br><span class="meta">${esc(item.entity_type)} · ${esc(item.similarity_reason)}</span>
        </li>`).join("");
      document.getElementById("retrieval-result").innerHTML = `
        <p class="panel-kicker">Related context</p>
        <h2>相似实体</h2>
        ${rows ? `<ul class="list">${rows}</ul>` : '<p class="muted">No related entities.</p>'}`;
    };
    const renderLlmPanel = () => {
      const status = state.result?.mode_status || state.status?.mode_status || {};
      const mention = selectedMention();
      const candidateId = state.selectedCandidateId;
      const context = state.llmPanelContext || "global";
      const explanations = context === "candidate"
        ? currentExplanations("candidate", state.selectedMentionIndex, candidateId, state.selectedEntityId)
        : context === "mention"
          ? currentExplanations("mention", state.selectedMentionIndex)
          : currentExplanations("global");
      const stageRows = (status.stage_statuses || []).map((item) => `
        <li class="item"><strong>${esc(item.stage)}</strong>
          <br><span class="meta">${esc(item.stage_status || (item.succeeded ? "used" : "not_used"))} · ${esc(item.safe_summary || item.error_code || "")}</span>
        </li>`).join("");
      const explanationRows = explanations.map((item) => `
        <li class="item"><strong>${esc(item.context_type)} · ${esc(item.stage)}</strong>
          <br><span class="meta">mention ${esc(item.mention_index ?? "-")} · candidate ${esc(item.candidate_id || "-")} · ${esc(item.stage_status)}</span>
          <p class="muted">${esc(item.safe_summary)}</p>
        </li>`).join("");
      const empty = context === "global" ? "No global LLM explanation in current mode." : "No LLM explanation for this item in current mode.";
      document.getElementById("llm-safe-explanation-panel").innerHTML = `
        <div class="panel-title">
          <div>
            <p class="panel-kicker">Generative UI component</p>
            <h2>LLM 交互式安全解释</h2>
          </div>
          <button class="ghost" id="llm-global-status" type="button">global status</button>
        </div>
        <dl class="summary-grid">
          <div class="metric"><dt>enabled</dt><dd>${esc(status.llm_enabled ?? state.status?.llm_enabled ?? false)}</dd></div>
          <div class="metric"><dt>used</dt><dd>${esc(status.llm_used ?? false)}</dd></div>
          <div class="metric"><dt>fallback</dt><dd>${esc(status.fallback_used ?? false)}</dd></div>
          <div class="metric"><dt>context</dt><dd>${esc(context)} ${mention ? "· " + esc(mention.mention?.text || "") : ""}</dd></div>
        </dl>
        <h3>stage summary</h3>
        ${stageRows ? `<ul class="list">${stageRows}</ul>` : '<p class="muted">No stage summary.</p>'}
        <h3>safe explanation</h3>
        ${explanationRows ? `<ul class="list explanation-list">${explanationRows}</ul>` : `<p class="muted">${esc(empty)}</p>`}`;
      const globalButton = document.getElementById("llm-global-status");
      if (globalButton) globalButton.addEventListener("click", () => {
        state.llmPanelContext = "global";
        renderLlmPanel();
      });
    };
    async function loadStatus() {
      const response = await fetch("/api/status");
      const payload = await response.json();
      renderRuntimeStatus(payload);
      renderLlmConfig(payload.llm_config || {});
      renderLlmPanel();
      setDebug({status: payload});
    }
    async function loadEntities(entityType = "") {
      const suffix = entityType ? `&entity_type=${encodeURIComponent(entityType)}` : "";
      const response = await fetch(`/api/entities?limit=200${suffix}`);
      const payload = await response.json();
      renderEntityCatalog(payload);
      setDebug({entities: payload});
    }
    async function showEntity(entityId) {
      if (!entityId) return {};
      state.selectedEntityId = entityId;
      if (state.catalog.items.length) {
        renderEntityCatalog({
          items: state.catalog.items,
          type_counts: state.catalog.type_counts,
          selected_entity_type: state.activeEntityType
        });
      }
      const requestToken = ++state.entityRequestToken;
      const response = await fetch(`/api/entities/${encodeURIComponent(entityId)}`);
      const payload = await response.json();
      if (requestToken !== state.entityRequestToken) return {};
      renderEntity(payload);
      const retrieval = await fetch("/api/retrieve", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({entity_id: entityId, k: 5})
      });
      const retrievalPayload = await retrieval.json();
      if (requestToken !== state.entityRequestToken) return {};
      renderRetrieval(retrievalPayload);
      return {entity: payload, retrieval: retrievalPayload};
    }
    document.getElementById("query-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const query = form.get("query");
      const mode = form.get("mode") || defaultMode;
      const allow_fallback = form.get("allow_fallback") === "on";
      const response = await fetch("/api/link", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query, mode, allow_fallback})
      });
      const payload = await response.json();
      state.selectedMentionIndex = payload.mention_results?.length ? 0 : null;
      state.selectedCandidateId = null;
      state.selectedEntityId = null;
      state.llmPanelContext = "global";
      renderResultSummary(payload);
      renderMentions(payload);
      renderCandidates(selectedMention()?.candidates || payload.candidates || []);
      renderLlmPanel();
      const entity = linkedEntity(payload);
      const entityId = entity?.entity_id || payload.candidates?.[0]?.entity_id;
      let detail = {};
      if (entityId) {
        detail = await showEntity(entityId);
      } else {
        renderEntity(null);
        renderRetrieval({items: []});
      }
      setDebug({link: payload, ...detail});
    });
    document.getElementById("llm-config-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const payload = {
        enabled: form.get("enabled") === "on",
        model: String(form.get("model") || ""),
        base_url: String(form.get("base_url") || ""),
        api_key: String(form.get("api_key") || ""),
        timeout_seconds: Number(form.get("timeout_seconds") || 20)
      };
      const response = await fetch("/api/llm/config", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) {
        document.getElementById("llm-config-status").textContent = result.errors?.[0]?.message || result.error_code || "配置失败";
        setDebug({llm_config_error: result});
        return;
      }
      event.currentTarget.elements.api_key.value = "";
      renderLlmConfig(result);
      await loadStatus();
      setDebug({llm_config: result});
    });
    renderEntityCatalog([]);
    renderEntity(null);
    renderRetrieval({items: []});
    renderLlmPanel();
    loadStatus();
    loadEntities("");
    document.getElementById("query-form").requestSubmit();
  </script>
</body>
</html>"""
    html = html.replace("__DEFAULT_RUN_MODE__", default_run_mode.value)
    html = html.replace("__DEFAULT_QUERY__", escape(default_query, quote=True))
    return html


def _parse_mode_request(payload: dict, default_run_mode: RunMode) -> tuple[ModeRequest | None, dict | None]:
    raw_mode = payload.get("mode", default_run_mode.value)
    try:
        mode = RunMode(raw_mode)
    except ValueError:
        return None, _error_payload(
            ErrorCode.INVALID_MODE,
            f"invalid mode: {raw_mode!r}",
            field="mode",
        )
    raw_allow_fallback = payload.get("allow_fallback", True)
    if not isinstance(raw_allow_fallback, bool):
        return None, _error_payload(
            ErrorCode.INVALID_ALLOW_FALLBACK,
            "allow_fallback must be a JSON boolean",
            field="allow_fallback",
        )
    return ModeRequest(
        query=str(payload.get("query", "")),
        mode=mode,
        allow_fallback=raw_allow_fallback,
    ), None


def _build_mode_status(
    mode_request: ModeRequest,
    llm_enabled: bool,
    result_status: Status,
    result_source: str,
    degraded: bool,
    error_code: ErrorCode | None,
    stage_trace: list[dict[str, Any]] | None = None,
) -> ModeStatus:
    fallback_used = (
        mode_request.mode == RunMode.LLM_ENABLED_DEMO
        and mode_request.allow_fallback
        and degraded
        and result_status != Status.DEPENDENCY_FAILED
    )
    if result_status == Status.DEPENDENCY_FAILED and not mode_request.allow_fallback:
        projected_source = "none"
    else:
        projected_source = result_source
    if stage_trace:
        stage_statuses = stage_trace
    elif error_code:
        stage_statuses = [
            {
                "stage": "llm" if mode_request.mode == RunMode.LLM_ENABLED_DEMO and llm_enabled else "linking",
                "attempted": mode_request.mode == RunMode.LLM_ENABLED_DEMO and llm_enabled,
                "succeeded": False,
                "fallback_used": fallback_used,
                "stage_status": "fallback_used" if fallback_used else "failed",
                "error_code": error_code.value,
                "safe_summary": "fallback used" if fallback_used else "dependency failed",
            }
        ]
    else:
        stage_statuses = _default_stage_statuses(mode_request.mode, llm_enabled)
    if stage_trace:
        llm_used = any(
            item.get("stage") == "llm"
            and (
                item.get("succeeded") is True
                or item.get("stage_status") == "used"
                or item.get("status") == "used"
            )
            for item in stage_trace
        )
    else:
        llm_used = mode_request.mode == RunMode.LLM_ENABLED_DEMO and llm_enabled
    return ModeStatus(
        requested_mode=mode_request.mode,
        effective_mode=RunMode.OFFLINE_DEMO if fallback_used else mode_request.mode,
        allow_fallback=mode_request.allow_fallback,
        llm_enabled=llm_enabled,
        llm_used=llm_used,
        fallback_used=fallback_used,
        degraded=degraded,
        result_source=projected_source,
        stage_statuses=stage_statuses,
        error_code=error_code,
    )


def _default_stage_statuses(mode: RunMode, llm_enabled: bool) -> list[dict[str, Any]]:
    llm_active = mode == RunMode.LLM_ENABLED_DEMO and llm_enabled
    return [
        {
            "stage": "need_linking",
            "attempted": True,
            "succeeded": True,
            "fallback_used": False,
            "stage_status": "used",
            "safe_summary": "query analyzed for entity-linking intent",
        },
        {
            "stage": "llm",
            "attempted": llm_active,
            "succeeded": llm_active,
            "fallback_used": False,
            "stage_status": "used" if llm_active else "not_used",
            "safe_summary": "LLM enabled path" if llm_active else "offline deterministic path",
        },
        {
            "stage": "retrieve_candidates",
            "attempted": True,
            "succeeded": True,
            "fallback_used": False,
            "stage_status": "used",
            "safe_summary": "catalog candidates retrieved from safe projection",
        },
    ]


def _safe_link_result(result: EntityLinkResult, mode_status: ModeStatus) -> dict:
    payload = {
        "query": result.query,
        "status": result.status.value,
        "mentions": [_safe_mention(mention) for mention in result.mentions],
        "mention_results": [
            _safe_mention_result(item, index)
            for index, item in enumerate(result.mention_results)
        ],
        "linked_entity": _safe_entity(result.linked_entity) if result.linked_entity else None,
        "candidates": [_safe_candidate(item) for item in result.candidates],
        "confidence": result.confidence,
        "disambiguation_reason": result.disambiguation_reason,
        "no_match_reason": result.no_match_reason,
        "bypass_reason": result.bypass_reason,
        "degraded": result.degraded,
        "error_code": result.error_code.value if result.error_code else None,
        "data_layer": result.data_layer.value,
        "source": result.source,
        "stage_trace": result.stage_trace,
        "mode_status": to_plain(mode_status),
        "result_source": mode_status.result_source,
        "safe_summary": _result_safe_summary(result),
    }
    payload["llm_explanations"] = _build_llm_explanations(payload)
    return payload


def _safe_mention_result(item: MentionLinkResult, index: int) -> dict:
    no_candidate_reason = item.no_match_reason or item.bypass_reason
    if not item.candidates and not item.linked_entity and not no_candidate_reason:
        no_candidate_reason = f"no candidate for mention '{item.mention.text}'"
    payload = {
        "mention_index": index,
        "mention": _safe_mention(item.mention),
        "status": item.status.value,
        "linked_entity": _safe_entity(item.linked_entity) if item.linked_entity else None,
        "candidates": [_safe_candidate(candidate) for candidate in item.candidates],
        "confidence": item.confidence,
        "disambiguation_reason": item.disambiguation_reason,
        "no_match_reason": item.no_match_reason,
        "bypass_reason": item.bypass_reason,
        "no_candidate_reason": no_candidate_reason,
        "degraded": item.degraded,
        "error_code": item.error_code.value if item.error_code else None,
        "source": item.source,
        "data_layer": item.data_layer.value,
        "storage_lookup": item.storage_lookup,
    }
    return payload


def _safe_mention(mention) -> dict:
    return {
        "text": mention.text,
        "span": list(mention.span) if mention.span else None,
        "predicted_type": mention.predicted_type.value if mention.predicted_type else None,
        "entity_type": mention.predicted_type.value if mention.predicted_type else None,
        "source": mention.source.value,
    }


def _safe_candidate(candidate: LinkCandidate) -> dict:
    return {
        "entity_id": candidate.entity_id,
        "candidate_id": candidate.entity_id,
        "canonical_name": candidate.canonical_name,
        "entity_type": candidate.entity_type.value,
        "confidence": candidate.confidence,
        "score": candidate.confidence,
        "match_reason": candidate.match_reason,
        "rank": candidate.rank,
    }


def _safe_entity(entity: EntityRecord | None, *, include_attributes: bool = False) -> dict:
    if entity is None:
        return {}
    payload = {
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type.value,
        "canonical_name": entity.canonical_name,
        "aliases": list(entity.aliases),
        "description": entity.description,
        "source": entity.source,
        "data_layer": entity.data_layer.value,
    }
    if include_attributes:
        safe_attributes, omitted_count = _safe_attributes(entity.attributes)
        payload["attributes_safe"] = safe_attributes
        payload["omitted_attribute_count"] = omitted_count
    return payload


def _safe_attributes(attributes: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    safe_items: list[dict[str, Any]] = []
    omitted_count = 0
    for key, value in attributes.items():
        normalized_key = str(key).lower()
        if (
            normalized_key not in SAFE_ATTRIBUTE_KEYS
            or any(fragment in normalized_key for fragment in FORBIDDEN_ATTRIBUTE_FRAGMENTS)
        ):
            omitted_count += 1
            continue
        if not _is_safe_attribute_value(value):
            omitted_count += 1
            continue
        safe_items.append(
            {
                "key": str(key),
                "value": _safe_attribute_value(value),
                "source": "catalog",
            }
        )
    return safe_items, omitted_count


def _is_safe_attribute_value(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        if len(value) > 300:
            return False
        return not any(fragment in lowered for fragment in FORBIDDEN_ATTRIBUTE_FRAGMENTS)
    if isinstance(value, bool | int | float):
        return True
    if isinstance(value, list):
        return all(isinstance(item, str) and len(item) <= 120 for item in value)
    return False


def _safe_attribute_value(value: Any) -> Any:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return value


def _safe_retrieval_item(item: RetrievalItem) -> dict:
    return {
        "entity_id": item.entity_id,
        "canonical_name": item.canonical_name,
        "entity_type": item.entity_type.value,
        "score": item.score,
        "similarity_reason": item.similarity_reason,
        "source": item.source,
        "data_layer": item.data_layer.value,
    }


def _safe_retrieval_result(result) -> dict:
    return {
        "status": result.status.value,
        "query_entity_id": result.query_entity_id,
        "k": result.k,
        "items": [_safe_retrieval_item(item) for item in result.items],
        "no_match_reason": result.no_match_reason,
    }


def _build_llm_explanations(payload: dict) -> list[dict[str, Any]]:
    mode_status = payload.get("mode_status") or {}
    explanations: list[dict[str, Any]] = [
        {
            "context_type": "global",
            "stage": "linking",
            "stage_status": "degraded" if payload.get("degraded") else "used",
            "safe_summary": payload.get("safe_summary") or "link result generated from safe projection",
            "fallback_reason": payload.get("no_match_reason") or payload.get("bypass_reason") or "",
            "error_code": payload.get("error_code") or "",
            "redaction_note": "redacted",
        }
    ]
    for item in payload.get("mention_results", []):
        mention = item.get("mention") or {}
        mention_index = item.get("mention_index", 0)
        explanations.append(
            {
                "context_type": "mention",
                "mention_index": mention_index,
                "stage": "extract_mention",
                "stage_status": "degraded" if item.get("degraded") else "used",
                "safe_summary": (
                    f"Mention '{mention.get('text', '-')}' status {item.get('status', '-')}; "
                    f"{item.get('disambiguation_reason') or item.get('no_candidate_reason') or 'safe deterministic summary'}"
                ),
                "fallback_reason": item.get("no_match_reason") or "",
                "error_code": item.get("error_code") or "",
                "redaction_note": "redacted",
            }
        )
        for candidate in item.get("candidates", []):
            explanations.append(
                {
                    "context_type": "candidate",
                    "mention_index": mention_index,
                    "candidate_id": candidate.get("candidate_id") or candidate.get("entity_id"),
                    "entity_id": candidate.get("entity_id"),
                    "stage": "retrieve_candidates",
                    "stage_status": "used",
                    "safe_summary": (
                        f"Candidate {candidate.get('entity_id')} matched by "
                        f"{candidate.get('match_reason', 'safe candidate retrieval')}"
                    ),
                    "fallback_reason": "",
                    "error_code": "",
                    "redaction_note": "redacted",
                }
            )
    if mode_status.get("fallback_used"):
        explanations[0]["stage_status"] = "fallback_used"
        explanations[0]["fallback_reason"] = "LLM path degraded and offline fallback was used"
    return explanations


def _result_safe_summary(result: EntityLinkResult) -> str:
    if result.status == Status.NOT_REQUIRED:
        return result.bypass_reason or "entity linking is not required"
    if result.status == Status.NO_MATCH:
        return result.no_match_reason or "no entity candidate found"
    if result.status == Status.PARTIAL:
        return "partial result: at least one mention linked and at least one mention unresolved"
    if result.status == Status.LINKED:
        return result.disambiguation_reason or "all detected mentions linked"
    return result.no_match_reason or result.status.value


def _error_payload(error_code: ErrorCode, message: str, *, field: str = "") -> dict:
    api_error = ApiError(error_code=error_code, message=message, field=field)
    return {
        "status": "dependency_failed"
        if error_code == ErrorCode.DEPENDENCY_FAILED
        else "invalid_input",
        "error_code": error_code.value,
        "result_source": "none",
        "candidates": [],
        "linked_entity": None,
        "mention_results": [],
        "llm_explanations": [],
        "errors": [to_plain(api_error)],
    }


def _parse_timeout_seconds(value) -> float | None:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        return None
    if timeout < 1 or timeout > 120:
        return None
    return timeout


def _parse_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _safe_llm_config(service: EntityLinkingService) -> dict:
    config = getattr(service.llm_client, "config", None)
    return {
        "enabled": service.llm_client is not None,
        "provider": str(getattr(config, "provider", "openai_compatible")),
        "model": str(getattr(config, "model", "qwen3.6-27b" if service.llm_client is None else "")),
        "base_url_configured": bool(getattr(config, "base_url", "")),
        "api_key_configured": bool(getattr(config, "api_key", "")),
        "api_key_env": str(getattr(config, "api_key_env", WEB_LLM_API_KEY_ENV)),
        "timeout_seconds": float(getattr(config, "timeout_seconds", 20.0)),
        "runtime_configurable": True,
    }


def _default_query(samples_path: str | Path) -> str:
    try:
        payload = json.loads(Path(samples_path).read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "RAN-A1 的 ASR 最近如何"
    queries = payload.get("queries") if isinstance(payload, dict) else None
    if isinstance(queries, list) and queries:
        first_query = queries[0].get("query") if isinstance(queries[0], dict) else None
        if isinstance(first_query, str) and first_query:
            return first_query
    return "RAN-A1 的 ASR 最近如何"


def _replace_section(html: str, section_id: str, value) -> str:
    replacements = {
        "runtime-status": _render_runtime_status,
        "result-summary": _render_result_summary,
        "mention-summary": _render_mention_summary,
        "llm-safe-explanation-panel": _render_llm_panel,
        "entity-catalog": _render_entity_catalog,
        "candidate-list": _render_candidate_list,
        "entity-detail": _render_entity_detail,
        "retrieval-result": _render_retrieval_result,
    }
    renderer = replacements.get(section_id)
    if renderer is None:
        return html
    marker = f'<section id="{section_id}"'
    start = html.find(marker)
    if start == -1:
        return html
    close = html.find("</section>", start)
    if close == -1:
        return html
    end = close + len("</section>")
    return f"{html[:start]}{renderer(value)}{html[end:]}"


def _render_runtime_status(value: dict) -> str:
    type_counts = value.get("type_counts") or {}
    type_text = ", ".join(f"{key}: {count}" for key, count in type_counts.items()) or "-"
    config = value.get("llm_config") or {}
    llm_status = str(config.get("model") or "enabled") if value.get("llm_enabled") else "offline"
    return (
        '<section id="runtime-status" data-testid="runtime-status"><div class="panel-title">'
        '<div><p class="panel-kicker">Status band</p><h2>运行状态</h2></div>'
        f'<span class="status">{escape(str(value.get("mode", "")))}</span></div>'
        '<dl class="runtime-grid">'
        f'<div class="metric"><dt>catalog loaded</dt><dd>{escape(str(value.get("catalog_loaded", True)))}</dd></div>'
        f'<div class="metric"><dt>entity_count</dt><dd>{escape(str(value.get("entity_count", 0)))}</dd></div>'
        f'<div class="metric"><dt>type_counts</dt><dd>{escape(type_text)}</dd></div>'
        f'<div class="metric"><dt>LLM overview</dt><dd>{escape(llm_status)}</dd></div>'
        "</dl></section>"
    )


def _render_result_summary(value: dict) -> str:
    entity = _linked_entity(value) or {}
    mention_count = len(value.get("mention_results", []))
    linked_count = sum(1 for item in value.get("mention_results", []) if item.get("linked_entity"))
    title = "-"
    if entity.get("entity_id"):
        title = f'{entity.get("entity_id")} · {entity.get("canonical_name", "")}'
    reason = (
        value.get("disambiguation_reason")
        or value.get("no_match_reason")
        or value.get("bypass_reason")
        or value.get("safe_summary")
        or value.get("status")
        or ""
    )
    return (
        '<section id="result-summary" data-testid="result-summary"><div class="panel-title">'
        '<div><p class="panel-kicker">Result stream</p><h2>实体链接结果</h2></div>'
        f'<span class="status {escape(str(value.get("status", "")))}">{escape(str(value.get("status", "unknown")))}</span></div>'
        '<dl class="summary-grid">'
        f'<div class="metric"><dt>mention_count</dt><dd>{escape(str(mention_count))}</dd></div>'
        f'<div class="metric"><dt>linked_count</dt><dd>{escape(str(linked_count))}</dd></div>'
        f'<div class="metric"><dt>linked_entity</dt><dd>{escape(title)}</dd></div>'
        f'<div class="metric"><dt>reason</dt><dd>{escape(str(reason or "-"))}</dd></div>'
        "</dl></section>"
    )


def _render_mention_summary(value: dict) -> str:
    rows = "".join(
        (
            '<li><button class="item mention-card'
            f'{" is-active" if index == 0 else ""}" type="button" data-testid="mention-result-card" data-mention-index="'
            f'{index}" aria-pressed="{str(index == 0).lower()}"><strong>{escape(str((item.get("mention") or {}).get("text") or "-"))}</strong><br>'
            f'<span class="status {escape(str(item.get("status", "")))}">{escape(str(item.get("status") or "-"))}</span> '
            f'<span class="meta">type {escape(str((item.get("mention") or {}).get("predicted_type") or "-"))} · '
            f'span {escape(str((item.get("mention") or {}).get("span") or "-"))} · '
            f'linked {escape(str((item.get("linked_entity") or {}).get("entity_id") or "-"))} · '
            f'{escape(str(item.get("no_candidate_reason") or ""))}</span></button></li>'
        )
        for index, item in enumerate(value.get("mention_results", []))
    )
    body = f'<ul class="list">{rows}</ul>' if rows else '<p class="muted">No mention needed for this query.</p>'
    return (
        '<section id="mention-summary" data-testid="mention-strip">'
        '<p class="panel-kicker">Multi-mention stream</p><h2>Mention 简要信息</h2>'
        f"{body}</section>"
    )


def _render_llm_panel(value: dict) -> str:
    explanations = value.get("llm_explanations") or []
    rows = "".join(
        (
            '<li class="item">'
            f'<strong>{escape(str(item.get("context_type", "")))} · {escape(str(item.get("stage", "")))}</strong>'
            f'<br><span class="meta">{escape(str(item.get("stage_status", "")))}</span>'
            f'<p class="muted">{escape(str(item.get("safe_summary", "")))}</p>'
            "</li>"
        )
        for item in explanations[:4]
    )
    body = f'<ul class="list">{rows}</ul>' if rows else '<p class="muted">No LLM explanation for this item in current mode.</p>'
    return (
        '<section id="llm-safe-explanation-panel" data-testid="llm-safe-explanation-panel">'
        '<div class="panel-title"><div><p class="panel-kicker">Generative UI component</p>'
        '<h2>LLM 交互式安全解释</h2></div>'
        '<button class="ghost" id="llm-global-status" type="button">global status</button></div>'
        f"{body}</section>"
    )


def _render_entity_catalog(value: list[dict]) -> str:
    rows = "".join(
        (
            '<li><button class="item catalog-card" type="button" data-entity-id="'
            f'{escape(str(item.get("entity_id", "")), quote=True)}">'
            f'<strong>{escape(str(item.get("entity_id", "")))}</strong> '
            f'{escape(str(item.get("canonical_name", "")))}'
            f'<br><span class="meta">{escape(str(item.get("entity_type", "")))}</span>'
            "</button></li>"
        )
        for item in value
    )
    body = f'<ul class="list split-list">{rows}</ul>' if rows else '<p class="muted">点击查看全部样例实体</p>'
    return (
        '<section id="entity-catalog" data-testid="catalog-panel"><div class="panel-title">'
        '<div><p class="panel-kicker">Catalog filter zone</p><h2>样例实体目录</h2></div>'
        '<button class="secondary" id="show-entities" type="button">查看全部样例实体</button></div>'
        '<div class="type-filters" data-testid="catalog-type-filter"></div>'
        f"{body}</section>"
    )


def _render_candidate_list(value: list[dict]) -> str:
    rows = "".join(
        (
            '<li><button class="item candidate-card" type="button" data-testid="candidate-card" data-candidate-id="'
            f'{escape(str(item.get("entity_id", "")), quote=True)}">'
            f'<strong>{escape(str(item.get("entity_id", "")))}</strong><br>'
            f'{escape(str(item.get("canonical_name", "")))}<br>'
            f'<span class="meta">{escape(str(item.get("match_reason", "")))}</span>'
            "</button></li>"
        )
        for item in value[:5]
    )
    body = f'<ul class="list">{rows}</ul>' if rows else '<p class="muted">No candidate for selected mention.</p>'
    return (
        '<section id="candidate-list" data-testid="candidate-detail-panel">'
        '<p class="panel-kicker">Candidate stack</p><h2>候选实体</h2>'
        f"{body}</section>"
    )


def _render_entity_detail(value: dict) -> str:
    if not value or not value.get("entity_id"):
        return (
            '<section id="entity-detail" data-testid="entity-detail-panel">'
            '<p class="panel-kicker">Entity detail zone</p><h2>实体详情</h2>'
            '<p class="muted">No linked entity.</p></section>'
        )
    attrs = "".join(
        (
            '<li class="item">'
            f'<strong>{escape(str(item.get("key", "")))}</strong>: {escape(str(item.get("value", "")))}'
            "</li>"
        )
        for item in value.get("attributes_safe", [])
    )
    attr_body = f'<ul class="list">{attrs}</ul>' if attrs else '<p class="muted">No safe attributes.</p>'
    return (
        '<section id="entity-detail" data-testid="entity-detail-panel">'
        '<p class="panel-kicker">Entity detail zone</p><h2>实体详情</h2><dl class="summary-grid">'
        f'<div class="metric"><dt>实体ID</dt><dd>{escape(str(value.get("entity_id", "")))}</dd></div>'
        f'<div class="metric"><dt>实体类型</dt><dd>{escape(str(value.get("entity_type", "")))}</dd></div>'
        f'<div class="metric"><dt>标准名称</dt><dd>{escape(str(value.get("canonical_name", "")))}</dd></div>'
        f'<div class="metric"><dt>别名</dt><dd>{escape(", ".join(value.get("aliases", [])) or "-")}</dd></div>'
        "</dl>"
        f'<p class="muted">{escape(str(value.get("description", "")))}</p>'
        f"<h3>safe attributes</h3>{attr_body}"
        f'<p class="meta">omitted_attribute_count: {escape(str(value.get("omitted_attribute_count", 0)))}</p></section>'
    )


def _render_retrieval_result(value: dict) -> str:
    rows = "".join(
        (
            '<li class="item">'
            f'<strong>{escape(str(item.get("entity_id", "")))}</strong> '
            f'{escape(str(item.get("canonical_name", "")))}'
            f'<br><span class="meta">{escape(str(item.get("similarity_reason", "")))}</span>'
            "</li>"
        )
        for item in (value.get("items") or [])
    )
    body = f'<ul class="list">{rows}</ul>' if rows else '<p class="muted">No related entities.</p>'
    return (
        '<section id="retrieval-result" data-testid="retrieval-result">'
        '<p class="panel-kicker">Related context</p><h2>相似实体</h2>'
        f"{body}</section>"
    )


def _preloaded_sections(service: EntityLinkingService, query: str, mode: RunMode = RunMode.OFFLINE_DEMO) -> dict:
    if not query.strip():
        return {}
    sections = {}
    try:
        load_result = service.catalog.load()
        mode_status = ModeStatus(
            requested_mode=mode,
            effective_mode=mode,
            allow_fallback=True,
            llm_enabled=service.llm_client is not None,
            stage_statuses=_default_stage_statuses(mode, service.llm_client is not None),
        )
        sections["runtime-status"] = {
            "mode": mode.value,
            "mode_status": to_plain(mode_status),
            "catalog_loaded": True,
            "entity_count": load_result.entity_count,
            "type_counts": load_result.type_counts,
            "llm_enabled": service.llm_client is not None,
            "llm_config": _safe_llm_config(service),
        }
    except CatalogError as exc:
        sections["runtime-status"] = _error_payload(exc.error_code, str(exc))
        return sections

    result = service.link_query(query, mode=mode)
    mode_status = _build_mode_status(
        ModeRequest(query=query, mode=mode, allow_fallback=True),
        service.llm_client is not None,
        result.status,
        result.source,
        result.degraded,
        result.error_code,
        stage_trace=result.stage_trace,
    )
    payload = _safe_link_result(result, mode_status)
    sections["result-summary"] = payload
    sections["mention-summary"] = payload
    sections["llm-safe-explanation-panel"] = payload
    sections["entity-catalog"] = []
    first_mention = payload.get("mention_results", [{}])[0] if payload.get("mention_results") else {}
    sections["candidate-list"] = first_mention.get("candidates", payload.get("candidates", []))

    entity_id = _first_linked_or_candidate_id(payload)
    if entity_id:
        entity = service.retriever.get_entity(entity_id)
        if entity:
            sections["entity-detail"] = _safe_entity(entity, include_attributes=True)
        sections["retrieval-result"] = _safe_retrieval_result(service.retriever.similar_entities(entity_id, 5))
    return sections


def _linked_entity(payload: dict) -> dict | None:
    linked_entity = payload.get("linked_entity") or {}
    if linked_entity.get("entity_id"):
        return linked_entity
    for result in payload.get("mention_results", []):
        entity = result.get("linked_entity") or {}
        if entity.get("entity_id"):
            return entity
    return None


def _first_linked_or_candidate_id(payload: dict) -> str:
    linked_entity = _linked_entity(payload) or {}
    if linked_entity.get("entity_id"):
        return linked_entity["entity_id"]
    for result in payload.get("mention_results", []):
        candidates = result.get("candidates") or []
        if candidates:
            return candidates[0].get("entity_id", "")
    candidates = payload.get("candidates") or []
    if candidates:
        return candidates[0].get("entity_id", "")
    return ""


def _type_counts(entities: list[EntityRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.entity_type.value] = counts.get(entity.entity_type.value, 0) + 1
    return dict(sorted(counts.items()))
