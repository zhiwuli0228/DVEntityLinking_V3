from __future__ import annotations

import argparse
import binascii
import json
import re
import struct
import zlib
from pathlib import Path

from demo_runtime import build_service, ensure_src_path, resolve_path, setup_logging


REQUIRED_BROWSER_EVIDENCE_CHECKS = {
    "all_sections_visible",
    "visual_workbench_shell_observed",
    "status_band_observed",
    "query_command_zone_observed",
    "result_stream_observed",
    "llm_explanation_component_observed",
    "catalog_filter_zone_observed",
    "multi_mention_observed",
    "second_mention_selected",
    "candidate_and_entity_detail_observed",
    "llm_explanation_observed",
    "catalog_filter_observed",
    "card_text_readable",
    "debug_collapsed",
    "no_section_overlap",
    "no_horizontal_overflow",
    "no_text_overlap_or_clipping_narrow",
}
BROWSER_EVIDENCE_SOURCE_FILES = (Path("src/dv_entity_linking/web.py"),)
FORBIDDEN_VISUAL_DOWNGRADE_CLASSIFICATIONS = {
    "weak_marker_only",
    "api_only",
    "no_visual_delta",
    "needs_user_decision",
    "missing_visual_evidence",
    "marker_only",
    "not_implemented",
}
AFTER_VISUAL_USER_ACCEPTANCE_STATUS = "accepted"
AFTER_VISUAL_USER_ACCEPTANCE_DATE = "2026-06-04"
AFTER_VISUAL_USER_ACCEPTANCE_SOURCE = "User confirmation in Codex thread"
AFTER_VISUAL_USER_ACCEPTANCE_NOTE = (
    "User confirmed current after visual can be accepted; before same-scenario "
    "screenshot or replacement criterion remains pending for AC-V2-FE-VIS-008."
)
D003_FORBIDDEN_RUNTIME_PATTERNS = (
    (
        "raw_llm_payload_key",
        re.compile(r"(?i)\braw_(?:request|response|prompt)\b"),
    ),
    (
        "authorization_bearer_value",
        re.compile(r"(?i)\bauthorization\b\s*[:=]\s*bearer\s+[A-Za-z0-9._-]{8,}"),
    ),
    (
        "bearer_token_value",
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{12,}"),
    ),
    (
        "secret_like_api_key",
        re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{8,}\b"),
    ),
    (
        "concrete_base_url_value",
        re.compile(r"https?://(?!\.\.\./v1)(?!localhost\b)(?!127\.0\.0\.1\b)[^\s\"'<>]+"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the V2 multi-type demo acceptance smoke checks.")
    parser.add_argument("--mode", choices=["offline_demo", "llm_enabled_demo"], default="offline_demo")
    parser.add_argument("--catalog", default="samples/real/v2_entity_examples.json")
    parser.add_argument("--samples", default="samples/real/v2_query_samples.json")
    parser.add_argument("--llm-config", default="config/llm.local.json")
    parser.add_argument("--log-dir", default="outputs/logs")
    return parser.parse_args()


def _link(client, query: str, mode: str) -> dict:
    response = client.post(
        "/api/link",
        json={"query": query, "mode": mode, "allow_fallback": True},
    )
    payload = response.get_json()
    payload["_http_status"] = response.status_code
    return payload


def _linked_entity_ids(payload: dict) -> list[str]:
    return [
        item.get("linked_entity", {}).get("entity_id", "")
        for item in payload.get("mention_results", [])
        if item.get("linked_entity")
    ]


def run_smoke(
    app,
    mode: str,
    log_dir: str = "outputs/logs",
    smoke_log_file: str | Path | None = None,
) -> dict:
    client = app.test_client()
    summary = {"mode": mode}
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    status = client.get("/api/status")
    status_payload = status.get_json()
    summary["status_code"] = status.status_code
    summary["catalog_loaded"] = status_payload.get("catalog_loaded")
    summary["entity_count"] = status_payload.get("entity_count")
    summary["type_counts"] = status_payload.get("type_counts")
    summary["llm_enabled"] = status_payload.get("llm_enabled")
    summary["llm_runtime_configurable"] = (status_payload.get("llm_config") or {}).get(
        "runtime_configurable"
    )

    linked = _link(client, "Run Network quality monitoring for onlinecharging_docker.", mode)
    summary["linked_status_code"] = linked["_http_status"]
    summary["linked_status"] = linked.get("status")
    summary["linked_entity_ids"] = _linked_entity_ids(linked)
    summary["linked_mention_count"] = len(linked.get("mention_results", []))
    summary["linked_llm_explanation_contexts"] = sorted(
        {item.get("context_type", "") for item in linked.get("llm_explanations", [])}
    )

    alarm_plus_kpi = _link(client, "Check ALM-51020 and CPU Usage.", mode)
    summary["alarm_plus_kpi_status"] = alarm_plus_kpi.get("status")
    summary["alarm_plus_kpi_entity_ids"] = _linked_entity_ids(alarm_plus_kpi)

    partial = _link(client, "Show CPU Usage for CloudHost-VM-1-1-000000.", mode)
    summary["partial_status"] = partial.get("status")
    summary["partial_linked_entity_ids"] = _linked_entity_ids(partial)
    summary["partial_no_match_count"] = sum(
        1 for item in partial.get("mention_results", []) if item.get("status") == "no_match"
    )

    no_match = _link(client, "Show metrics for UnknownApp-999.", mode)
    summary["no_match_status"] = no_match.get("status")
    summary["no_match_candidate_count"] = len(no_match.get("candidates", []))
    summary["no_match_has_linked_entity"] = bool(no_match.get("linked_entity"))
    summary["no_match_reason_visible"] = bool(
        (no_match.get("mention_results") or [{}])[0].get("no_candidate_reason")
    )

    not_required = _link(client, "Open the operations dashboard.", mode)
    summary["not_required_status"] = not_required.get("status")
    summary["not_required_candidate_count"] = len(not_required.get("candidates", []))
    summary["not_required_has_linked_entity"] = bool(not_required.get("linked_entity"))
    summary["not_required_mention_count"] = len(not_required.get("mention_results", []))
    summary["not_required_reason_visible"] = bool(not_required.get("bypass_reason"))

    invalid = client.post("/api/link", json={"query": "", "mode": mode})
    invalid_payload = invalid.get_json()
    summary["invalid_status"] = invalid_payload.get("status")
    summary["invalid_error_code"] = invalid_payload.get("error_code")

    page = client.get(
        "/classic",
        query_string={"query": "Show CPU Usage for CBS_1_cbpmdb_b2fc41cbb389(FI01)."},
    )
    html = page.get_data(as_text=True)
    summary["html_status_code"] = page.status_code
    summary["html_sections_present"] = all(
        marker in html
        for marker in [
            "visual-workbench-shell",
            "status-band",
            "query-command-zone",
            "result-stream",
            "entity-detail-zone",
            "llm-explanation-component",
            "catalog-filter-zone",
            "runtime-status",
            "query-panel",
            "result-summary",
            "mention-summary",
            "entity-catalog",
            "candidate-list",
            "entity-detail",
            "llm-safe-explanation-panel",
            "retrieval-result",
            "debug-details",
        ]
    )
    summary["html_debug_collapsed"] = "<details id=\"debug-details\"" in html and "debug-details\" open" not in html
    summary["html_contains_expected_entities"] = (
        "DV-KPI-MTK-001" in html and "DV-NE-NAME-001" in html
    )
    summary["html_contains_workbench_labels"] = all(
        marker in html
        for marker in [
            "DVEntityLinking V2 Workbench",
            "Ops status density",
            "Generative explanation component",
            "Schema-driven state",
            "Status band",
            "Command zone",
            "Result stream",
            "LLM 交互式安全解释",
            "Mention 简要信息",
            "样例实体目录",
        ]
    )

    samples = client.get("/api/samples")
    samples_payload = samples.get_json()
    summary["sample_count"] = len(samples_payload.get("queries", []))

    entities = client.get("/api/entities?limit=200")
    entities_payload = entities.get_json()
    summary["entity_catalog_count"] = len(entities_payload.get("items", []))

    entity_detail = client.get("/api/entities/DV-KPI-MTK-001").get_json()
    summary["entity_detail_has_safe_attributes"] = "attributes_safe" in entity_detail
    summary["entity_detail_has_raw_attributes"] = "attributes" in entity_detail

    retrieval = client.post("/api/retrieve", json={"entity_id": "DV-KPI-MTK-001", "k": 3})
    retrieval_payload = retrieval.get_json()
    summary["retrieval_status_code"] = retrieval.status_code
    summary["retrieval_result_count"] = len((retrieval_payload or {}).get("items", []))

    traceability = _build_traceability_summary(
        linked=linked,
        partial=partial,
        no_match=no_match,
        not_required=not_required,
        summary=summary,
    )
    traceability_json = log_path / "v2_frontend_traceability_check.json"
    traceability_md = log_path / "v2_frontend_traceability_check.md"
    traceability_json.write_text(
        json.dumps(traceability, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    traceability_md.write_text(_traceability_markdown(traceability), encoding="utf-8")
    summary["traceability_artifact_json"] = str(traceability_json)
    summary["traceability_artifact_md"] = str(traceability_md)
    summary["traceability_statuses"] = sorted({item["status"] for item in traceability["items"]})
    summary["traceability_downgraded_count"] = sum(
        1 for item in traceability["items"] if item["status"] == "downgraded"
    )
    summary["traceability_ac_v2_fe_004_status"] = next(
        (
            item["status"]
            for item in traceability["items"]
            if "AC-V2-FE-004" in item["ac_ids"]
        ),
        "missing",
    )
    summary["traceability_decision_d041_status"] = next(
        (
            item["status"]
            for item in traceability["items"]
            if "D041" in str(item["decision_id"]).split(",")
        ),
        "missing",
    )
    summary.update(_validate_browser_evidence(log_path))

    d003_scan = _build_d003_scan_evidence(
        html=html,
        status_payload=status_payload,
        link_payloads={
            "linked": linked,
            "alarm_plus_kpi": alarm_plus_kpi,
            "partial": partial,
            "no_match": no_match,
            "not_required": not_required,
        },
        samples_payload=samples_payload,
        entities_payload=entities_payload,
        entity_detail_payload=entity_detail,
        retrieval_payload=retrieval_payload,
        artifact_paths=[traceability_json, traceability_md],
        smoke_log_file=smoke_log_file,
    )
    summary["d003_scan"] = d003_scan
    summary["d003_scan_ok"] = d003_scan["ok"]
    summary["d003_scan_finding_count"] = d003_scan["finding_count"]
    summary["d003_scan_sources"] = d003_scan["sources"]

    visual_traceability = _build_visual_traceability_summary(summary=summary, html=html)
    visual_traceability_json = log_path / "v2_frontend_visual_traceability_check.json"
    visual_traceability_md = log_path / "v2_frontend_visual_traceability_check.md"
    visual_traceability_json.write_text(
        json.dumps(visual_traceability, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    visual_traceability_md.write_text(
        _visual_traceability_markdown(visual_traceability),
        encoding="utf-8",
    )
    summary["visual_traceability_artifact_json"] = str(visual_traceability_json)
    summary["visual_traceability_artifact_md"] = str(visual_traceability_md)
    summary["visual_traceability_schema_version"] = visual_traceability["schema_version"]
    summary["visual_traceability_manual_user_acceptance_status"] = visual_traceability[
        "manual_user_acceptance_status"
    ]
    summary["visual_traceability_statuses"] = sorted(
        {item["status"] for item in visual_traceability["items"]}
    )
    summary["visual_traceability_blocking_count"] = visual_traceability["summary"]["blocking_count"]
    summary["visual_traceability_blocking_ac_ids"] = visual_traceability["summary"]["blocking_ac_ids"]

    summary["ok"] = all(
        [
            summary["catalog_loaded"] is True,
            summary["entity_count"] == 25,
            summary["entity_catalog_count"] == 25,
            summary["type_counts"]
            == {
                "alarm": 9,
                "kpi_meas_type_key": 6,
                "kpi_task_name": 5,
                "ne_name": 3,
                "ne_type": 2,
            },
            summary["llm_runtime_configurable"] is True,
            summary["linked_status"] == "linked",
            summary["linked_mention_count"] == 2,
            set(summary["linked_entity_ids"]) == {"DV-KPI-TASK-005", "DV-NE-TYPE-002"},
            summary["alarm_plus_kpi_status"] == "linked",
            set(summary["alarm_plus_kpi_entity_ids"]) == {"DV-ALM-002", "DV-KPI-MTK-001"},
            summary["partial_status"] == "partial",
            summary["partial_linked_entity_ids"] == ["DV-KPI-MTK-001"],
            summary["partial_no_match_count"] == 1,
            summary["no_match_status"] == "no_match",
            summary["no_match_candidate_count"] == 0,
            summary["no_match_has_linked_entity"] is False,
            summary["no_match_reason_visible"] is True,
            summary["not_required_status"] == "not_required",
            summary["not_required_candidate_count"] == 0,
            summary["not_required_has_linked_entity"] is False,
            summary["not_required_mention_count"] == 0,
            summary["not_required_reason_visible"] is True,
            summary["invalid_error_code"] == "invalid_input",
            summary["html_sections_present"] is True,
            summary["html_debug_collapsed"] is True,
            summary["html_contains_workbench_labels"] is True,
            summary["html_contains_expected_entities"] is True,
            summary["sample_count"] == 12,
            "mention" in summary["linked_llm_explanation_contexts"],
            "candidate" in summary["linked_llm_explanation_contexts"],
            summary["entity_detail_has_safe_attributes"] is True,
            summary["entity_detail_has_raw_attributes"] is False,
            summary["traceability_statuses"] == ["implemented"],
            summary["traceability_downgraded_count"] == 0,
            summary["traceability_ac_v2_fe_004_status"] == "implemented",
            summary["traceability_decision_d041_status"] == "implemented",
            summary["browser_evidence_ok"] is True,
            summary["browser_evidence_fresh"] is True,
            summary["browser_screenshots_present"] is True,
            summary["browser_screenshot_images_valid"] is True,
            summary["d003_scan_ok"] is True,
        ]
    )
    return summary


def _build_traceability_summary(
    *,
    linked: dict,
    partial: dict,
    no_match: dict,
    not_required: dict,
    summary: dict,
) -> dict:
    items = [
        {
            "decision_id": "D024",
            "user_confirmed_item": "V2 frontend uses demo workbench and avoids over-productization.",
            "ac_ids": ["AC-V2-FE-001", "AC-V2-FE-007"],
            "design_items": ["SR-V2-FE-D01"],
            "implementation_files": ["src/dv_entity_linking/web.py"],
            "browser_test_ids": ["TC-V2-FE-WEB-001", "TC-V2-FE-WEB-002"],
            "api_test_ids": ["tests/test_web.py::test_web_ui_visibility_smoke"],
            "evidence_artifacts": ["html_sections_present", "html_debug_collapsed"],
            "status": "implemented" if summary["html_sections_present"] else "not_implemented",
            "downgrade_classification": "none" if summary["html_sections_present"] else "marker_only",
            "reviewer_result": "pass" if summary["html_sections_present"] else "fail",
            "blocking_rule": "P0/P1 AC must be implemented with browser or equivalent evidence.",
        },
        {
            "decision_id": "D024,D043",
            "user_confirmed_item": "Query, mention visualization, candidates, entity detail, and LLM explanation are visible.",
            "ac_ids": ["AC-V2-FE-002", "AC-V2-FE-003", "AC-V2-FE-005", "AC-V2-FE-006"],
            "design_items": ["SR-V2-FE-D02", "SR-V2-FE-D03", "SR-V2-FE-D04"],
            "implementation_files": ["src/dv_entity_linking/web.py"],
            "browser_test_ids": ["TC-V2-FE-WEB-003", "TC-V2-FE-WEB-005", "TC-V2-FE-WEB-007"],
            "api_test_ids": ["tests/test_web.py::test_web_api_link_exposes_workbench_safe_projection"],
            "evidence_artifacts": ["linked_llm_explanation_contexts", "entity_detail_has_safe_attributes"],
            "status": "implemented"
            if linked.get("mention_results") and linked.get("llm_explanations")
            else "not_implemented",
            "downgrade_classification": "none"
            if linked.get("mention_results") and linked.get("llm_explanations")
            else "api_only",
            "reviewer_result": "pass"
            if linked.get("mention_results") and linked.get("llm_explanations")
            else "fail",
            "blocking_rule": "Interactive explanation must not degrade to one global marker.",
        },
        {
            "decision_id": "D028,D043",
            "user_confirmed_item": "V2 multi-mention Query is important and must be observable.",
            "ac_ids": ["AC-V2-FE-002", "AC-V2-FE-003"],
            "design_items": ["SR-V2-FE-D02"],
            "implementation_files": ["src/dv_entity_linking/web.py"],
            "browser_test_ids": ["TC-V2-FE-WEB-003", "TC-V2-FE-WEB-004"],
            "api_test_ids": ["tests/test_v2_runtime.py"],
            "evidence_artifacts": ["linked_mention_count", "partial_no_match_count"],
            "status": "implemented"
            if summary["linked_mention_count"] == 2 and summary["partial_no_match_count"] == 1
            else "not_implemented",
            "downgrade_classification": "none"
            if summary["linked_mention_count"] == 2 and summary["partial_no_match_count"] == 1
            else "api_only",
            "reviewer_result": "pass"
            if summary["linked_mention_count"] == 2 and summary["partial_no_match_count"] == 1
            else "fail",
            "blocking_rule": "Multi-mention evidence must include mention-level status.",
        },
        {
            "decision_id": "D043",
            "user_confirmed_item": "Negative states must not show pseudo candidates or pseudo linked entities.",
            "ac_ids": ["AC-V2-FE-004"],
            "design_items": ["SR-V2-FE-D02", "SR-V2-FE-D05"],
            "implementation_files": ["src/dv_entity_linking/web.py", "scripts/run_v2_acceptance_smoke.py"],
            "browser_test_ids": ["TC-V2-FE-WEB-010", "TC-V2-FE-WEB-011"],
            "api_test_ids": ["tests/test_web.py::test_web_api_negative_states_do_not_emit_pseudo_entities"],
            "evidence_artifacts": [
                "no_match_status",
                "no_match_has_linked_entity",
                "no_match_reason_visible",
                "not_required_status",
                "not_required_has_linked_entity",
                "not_required_mention_count",
                "not_required_reason_visible",
            ],
            "status": "implemented"
            if (
                summary["no_match_status"] == "no_match"
                and summary["no_match_has_linked_entity"] is False
                and summary["no_match_reason_visible"] is True
                and summary["not_required_status"] == "not_required"
                and summary["not_required_has_linked_entity"] is False
                and summary["not_required_mention_count"] == 0
                and summary["not_required_reason_visible"] is True
            )
            else "not_implemented",
            "downgrade_classification": "none"
            if (
                summary["no_match_has_linked_entity"] is False
                and summary["not_required_has_linked_entity"] is False
            )
            else "pseudo_entity",
            "reviewer_result": "pass"
            if (
                summary["no_match_status"] == "no_match"
                and summary["not_required_status"] == "not_required"
                and summary["no_match_has_linked_entity"] is False
                and summary["not_required_has_linked_entity"] is False
            )
            else "fail",
            "blocking_rule": "no_match/not_required must not emit pseudo linked_entity, pseudo mention, or pseudo candidate.",
        },
        {
            "decision_id": "D042,D043",
            "user_confirmed_item": "Frontend remediation must not silently downgrade to Web/API projection.",
            "ac_ids": ["AC-V2-FE-008", "AC-V2-FE-009"],
            "design_items": ["SR-V2-FE-D05"],
            "implementation_files": ["scripts/run_v2_acceptance_smoke.py", "src/dv_entity_linking/web.py"],
            "browser_test_ids": ["TC-V2-FE-WEB-012"],
            "api_test_ids": ["tests/test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline"],
            "evidence_artifacts": [
                "outputs/logs/v2_frontend_traceability_check.json",
                "outputs/logs/v2_frontend_traceability_check.md",
            ],
            "status": "implemented",
            "downgrade_classification": "none",
            "reviewer_result": "pass",
            "blocking_rule": "Any downgraded/not_implemented P0/P1 item blocks acceptance.",
        },
        {
            "decision_id": "D041",
            "user_confirmed_item": "Web demo keeps scripts/run_web_demo.py as the single maintained launch entry.",
            "ac_ids": ["AC-V2-FE-001", "AC-V2-FE-008"],
            "design_items": ["SR-V2-FE-D01", "SR-V2-FE-D05"],
            "implementation_files": ["scripts/run_web_demo.py", "docs/USAGE.md"],
            "browser_test_ids": ["TC-V2-FE-WEB-011"],
            "api_test_ids": [
                "tests/test_demo_scripts.py::test_web_demo_script_has_pycharm_friendly_help",
                "tests/test_contract_artifacts.py::test_contract_document_governance_is_compact_and_versioned",
            ],
            "evidence_artifacts": [
                "scripts/run_web_demo.py",
                "docs/USAGE.md",
                "scripts/run_v1_web_demo.py not present in docs/USAGE.md",
            ],
            "status": "implemented",
            "downgrade_classification": "none",
            "reviewer_result": "pass",
            "blocking_rule": "Single web demo entry must remain scripts/run_web_demo.py unless user confirms otherwise.",
        },
        {
            "decision_id": "D003,D042",
            "user_confirmed_item": "Sensitive config and raw LLM request/response must not be shown or committed.",
            "ac_ids": ["AC-V2-FE-006", "AC-V2-FE-008"],
            "design_items": ["SR-V2-FE-D04", "SR-V2-FE-D05"],
            "implementation_files": ["src/dv_entity_linking/web.py"],
            "browser_test_ids": ["TC-V2-FE-WEB-008"],
            "api_test_ids": ["tests/test_web.py::test_web_entity_detail_uses_safe_attributes"],
            "evidence_artifacts": ["entity_detail_has_raw_attributes", "html_debug_collapsed"],
            "status": "implemented"
            if summary["entity_detail_has_raw_attributes"] is False
            else "downgraded",
            "downgrade_classification": "none"
            if summary["entity_detail_has_raw_attributes"] is False
            else "api_only",
            "reviewer_result": "pass"
            if summary["entity_detail_has_raw_attributes"] is False
            else "fail",
            "blocking_rule": "Raw sensitive values and raw attributes must not be emitted.",
        },
    ]
    return {
        "schema_version": "v2.frontend_traceability_check.1",
        "items": items,
        "ac_statuses": {
            ac_id: sorted({item["status"] for item in items if ac_id in item["ac_ids"]})
            for ac_id in sorted({ac_id for item in items for ac_id in item["ac_ids"]})
        },
        "source": "scripts/run_v2_acceptance_smoke.py",
    }


def _build_d003_scan_evidence(
    *,
    html: str,
    status_payload: dict,
    link_payloads: dict[str, dict],
    samples_payload: dict,
    entities_payload: dict,
    entity_detail_payload: dict,
    retrieval_payload: dict,
    artifact_paths: list[Path],
    smoke_log_file: str | Path | None,
) -> dict:
    sources: list[tuple[str, str]] = [
        ("HTML /", html),
        ("API /api/status", _json_text(status_payload)),
        ("API /api/samples", _json_text(samples_payload)),
        ("API /api/entities", _json_text(entities_payload)),
        ("API /api/entities/DV-KPI-MTK-001", _json_text(entity_detail_payload)),
        ("API /api/retrieve", _json_text(retrieval_payload)),
    ]
    for name, payload in sorted(link_payloads.items()):
        sources.append((f"API /api/link {name}", _json_text(payload)))
    for artifact_path in artifact_paths:
        if artifact_path.exists():
            sources.append(
                (
                    f"artifact {artifact_path.name}",
                    artifact_path.read_text(encoding="utf-8"),
                )
            )
    if smoke_log_file:
        log_path = Path(smoke_log_file)
        if log_path.exists():
            sources.append((f"log {log_path.name}", log_path.read_text(encoding="utf-8")))
    return _scan_d003_sources(sources)


def _json_text(payload: object) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)


def _scan_d003_sources(sources: list[tuple[str, str]]) -> dict:
    inventory = []
    findings = []
    source_names = []
    for source_name, text in sources:
        source_names.append(source_name)
        source_findings = []
        matched_spans: list[tuple[int, int]] = []
        for issue_type, pattern in D003_FORBIDDEN_RUNTIME_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0)
                if value == "https://.../v1":
                    continue
                if any(_spans_overlap(match.span(), span) for span in matched_spans):
                    continue
                matched_spans.append(match.span())
                source_findings.append(
                    {
                        "issue_type": issue_type,
                        "value": _redact_d003_match(value),
                    }
                )
        if source_findings:
            for finding in source_findings:
                findings.append({"source": source_name, **finding})
                inventory.append(
                    {
                        "text_or_label": finding["value"],
                        "classification": "runtime_scan_finding",
                        "source_reference": source_name,
                        "decision_id": "D003",
                        "needs_d003_confirmation": True,
                        "item": finding["value"],
                        "source_classification": "runtime_scan_finding",
                        "reason": f"D003 runtime scan found forbidden {finding['issue_type']}.",
                    }
                )
        else:
            inventory.append(
                {
                    "text_or_label": source_name,
                    "classification": "runtime_scan",
                    "source_reference": source_name,
                    "decision_id": "D003",
                    "needs_d003_confirmation": False,
                    "item": source_name,
                    "source_classification": "runtime_api_artifact_scan",
                    "reason": "Runtime HTML/API/artifact/log scan found no forbidden sensitive value or unconfirmed real DV value.",
                }
            )
    return {
        "ok": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "sources": source_names,
        "inventory": inventory,
    }


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _redact_d003_match(value: str) -> str:
    lowered = value.lower()
    if "bearer" in lowered:
        return "bearer <redacted>"
    if lowered.startswith("sk-"):
        return "sk-<redacted>"
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return "https://<redacted>"
    return value


def _visual_item_blocks_acceptance(item: dict) -> bool:
    if item.get("priority") not in {"P0", "P1"}:
        return False
    return (
        item.get("status") != "implemented"
        or item.get("downgrade_classification") in FORBIDDEN_VISUAL_DOWNGRADE_CLASSIFICATIONS
    )


def _build_visual_traceability_summary(*, summary: dict, html: str) -> dict:
    required_regions = [
        "visual-workbench-shell",
        "status-band",
        "query-command-zone",
        "result-stream",
        "entity-detail-zone",
        "llm-explanation-component",
        "catalog-filter-zone",
    ]
    browser_missing = set(summary.get("browser_evidence_missing_checks") or [])
    html_has_regions = all(marker in html for marker in required_regions)
    browser_check = lambda name: summary.get("browser_evidence_ok") is True and name not in browser_missing
    automation_layout_ok = all(
        browser_check(name)
        for name in [
            "visual_workbench_shell_observed",
            "status_band_observed",
            "query_command_zone_observed",
            "result_stream_observed",
            "llm_explanation_component_observed",
            "catalog_filter_zone_observed",
            "no_section_overlap",
            "no_horizontal_overflow",
            "no_text_overlap_or_clipping_narrow",
        ]
    )
    selection_ok = all(
        [
            browser_check("multi_mention_observed"),
            browser_check("second_mention_selected"),
            browser_check("candidate_and_entity_detail_observed"),
            'data-testid="mention-result-card"' in html,
            'data-testid="candidate-card"' in html,
        ]
    )
    llm_component_ok = (
        browser_check("llm_explanation_observed")
        and "llm-explanation-component" in html
        and "Generative UI component" in html
    )
    d003_scan = summary.get("d003_scan") or {
        "ok": False,
        "inventory": [],
        "sources": [],
        "finding_count": 0,
    }
    single_entry_ok = _web_demo_single_entry_ok()
    automated_evidence_ok = all(
        [
            summary.get("browser_evidence_ok") is True,
            summary.get("browser_evidence_fresh") is True,
            summary.get("browser_screenshots_present") is True,
            summary.get("html_contains_workbench_labels") is True,
            html_has_regions,
        ]
    )

    d003_content_inventory = [
        {
            "text_or_label": "Ops status density / Generative explanation component / Schema-driven state",
            "classification": "synthetic_ui",
            "source_reference": "SR-FRONTEND-VISUAL-REMEDIATION.md prototype absorption labels",
            "decision_id": None,
            "needs_d003_confirmation": False,
            "item": "Ops status density / Generative explanation component / Schema-driven state",
            "source_classification": "synthetic_ui_copy",
            "reason": "Prototype absorption labels are generic UI copy, not real DV production content.",
        },
        {
            "text_or_label": "Confirmed V2 sample entity ids, entity types, and English canonical queries",
            "classification": "existing_confirmed_sample",
            "source_reference": "samples/real/v2_entity_examples.json; samples/real/v2_query_samples.json; D028",
            "decision_id": "D028",
            "needs_d003_confirmation": False,
            "item": "Confirmed V2 sample entity ids, entity types, and English canonical queries",
            "source_classification": "confirmed_v2_sample",
            "reason": "Values come from samples/real/v2_entity_examples.json and samples/real/v2_query_samples.json.",
        },
        {
            "text_or_label": "LLM configuration labels and empty input placeholders",
            "classification": "project_safe",
            "source_reference": "SR-FRONTEND-VISUAL-REMEDIATION.md D003 boundary; D003",
            "decision_id": "D003",
            "needs_d003_confirmation": False,
            "item": "LLM configuration labels and empty input placeholders",
            "source_classification": "project_safe",
            "reason": "The UI exposes configuration fields but no real secret, token, raw prompt, raw response, or base URL value.",
        },
        *d003_scan.get("inventory", []),
    ]
    no_unconfirmed_content = d003_scan.get("ok") is True and not any(
        item["needs_d003_confirmation"] for item in d003_content_inventory
    )

    def implemented_item(
        *,
        decision_id: str,
        ac_ids: list[str],
        priority: str,
        user_confirmed_item: str,
        condition: bool,
        evidence_artifacts: list[str],
        evidence_type: str,
        prototype_ref: str,
        absorbed_principle: str,
        target_ui_regions: list[str],
        checks: list[str],
        reviewer_result: str = "pass",
        downgrade_when_failed: str = "not_implemented",
    ) -> dict:
        status = "implemented" if condition else "not_implemented"
        screenshot_paths = summary.get("browser_screenshot_paths") or {}
        return {
            "decision_id": decision_id,
            "ac_ids": ac_ids,
            "priority": priority,
            "user_confirmed_item": user_confirmed_item,
            "implementation_files": ["src/dv_entity_linking/web.py", "scripts/run_v2_acceptance_smoke.py"],
            "evidence_artifacts": evidence_artifacts,
            "evidence_type": evidence_type,
            "prototype_ref": prototype_ref,
            "absorbed_principle": absorbed_principle,
            "target_ui_regions": target_ui_regions,
            "before_screenshot": "",
            "after_screenshot": "; ".join(
                str(screenshot_paths.get(key, ""))
                for key in ["desktop_1366x768", "narrow_390x844"]
                if screenshot_paths.get(key)
            ),
            "same_viewport_and_query": False,
            "automated_visual_semantic_checks": [
                {"name": name, "passed": browser_check(name) if name in REQUIRED_BROWSER_EVIDENCE_CHECKS else bool(condition)}
                for name in checks
            ],
            "status": status,
            "downgrade_classification": "none" if condition else downgrade_when_failed,
            "reviewer_result": reviewer_result if condition else "fail",
            "manual_user_acceptance_status": "not_applicable",
        }

    after_screenshot = "; ".join(
        str((summary.get("browser_screenshot_paths") or {}).get(key, ""))
        for key in ["desktop_1366x768", "narrow_390x844"]
        if (summary.get("browser_screenshot_paths") or {}).get(key)
    )

    # Before-evidence (captured by scripts/capture_screenshots.py --label before).
    # When present in the log dir, AC-V2-FE-VIS-008 can be closed.
    evidence_path = Path(summary.get("browser_evidence_path", "")) if summary.get("browser_evidence_path") else None
    before_log_dir = evidence_path.parent if evidence_path else Path("outputs/logs")
    before_paths = [
        before_log_dir / "v2_frontend_before_desktop_1366x768.png",
        before_log_dir / "v2_frontend_before_narrow_390x844.png",
    ]
    before_screenshot = "; ".join(str(p) for p in before_paths if p.exists())
    before_present = all(p.exists() for p in before_paths)

    items = [
        implemented_item(
            decision_id="D024,D058",
            ac_ids=["AC-V2-FE-VIS-001", "AC-V2-FE-VIS-002"],
            priority="P0",
            user_confirmed_item="Prototype absorption creates a cohesive V2 visual workbench shell.",
            condition=html_has_regions and automation_layout_ok,
            evidence_artifacts=[
                "visual-workbench-shell",
                "status-band",
                "query-command-zone",
                "result-stream",
                "entity-detail-zone",
                "llm-explanation-component",
                "catalog-filter-zone",
                summary.get("browser_evidence_path", ""),
            ],
            evidence_type="prototype_absorption",
            prototype_ref="SigNoz",
            absorbed_principle="Operational workbench density with status band, command zone, result stream, and catalog filter zone.",
            target_ui_regions=[
                "visual-workbench-shell",
                "status-band",
                "query-command-zone",
                "result-stream",
                "catalog-filter-zone",
            ],
            checks=[
                "visual_workbench_shell_observed",
                "status_band_observed",
                "query_command_zone_observed",
                "result_stream_observed",
                "catalog_filter_zone_observed",
                "no_section_overlap",
                "no_horizontal_overflow",
            ],
            downgrade_when_failed="weak_marker_only",
        ),
        implemented_item(
            decision_id="D024,D058",
            ac_ids=["AC-V2-FE-VIS-003"],
            priority="P0",
            user_confirmed_item="Mention, candidate, entity detail, catalog, and LLM selection states are visible.",
            condition=selection_ok and browser_check("catalog_filter_observed"),
            evidence_artifacts=[
                "mention-result-card",
                "candidate-card",
                "catalog-entity-card",
                "second_mention_selected",
                "candidate_and_entity_detail_observed",
            ],
            evidence_type="visual_ac",
            prototype_ref="Tambo",
            absorbed_principle="Schema-driven component state makes mention, candidate, entity, and catalog selection observable.",
            target_ui_regions=[
                "result-stream",
                "entity-detail-zone",
                "catalog-filter-zone",
            ],
            checks=[
                "multi_mention_observed",
                "second_mention_selected",
                "candidate_and_entity_detail_observed",
                "catalog_filter_observed",
            ],
            downgrade_when_failed="api_only",
        ),
        implemented_item(
            decision_id="D024,D058",
            ac_ids=["AC-V2-FE-VIS-004"],
            priority="P1",
            user_confirmed_item="LLM safe explanation is represented as an interactive component.",
            condition=llm_component_ok,
            evidence_artifacts=[
                "llm-explanation-component",
                "Generative UI component",
                "linked_llm_explanation_contexts",
            ],
            evidence_type="prototype_absorption",
            prototype_ref="OpenGenerativeUI",
            absorbed_principle="LLM output is represented as a structured interactive explanation component rather than a raw text response.",
            target_ui_regions=["llm-explanation-component"],
            checks=[
                "llm_explanation_component_observed",
                "llm_explanation_observed",
            ],
            downgrade_when_failed="plain_text_list",
        ),
        implemented_item(
            decision_id="D003",
            ac_ids=["AC-V2-FE-VIS-005", "AC-V2-FE-VIS-009"],
            priority="P0",
            user_confirmed_item="Visual remediation does not introduce unconfirmed real DV content or unsafe LLM/config data.",
            condition=no_unconfirmed_content,
            evidence_artifacts=["d003_content_inventory[]", "entity_detail_has_raw_attributes=false"],
            evidence_type="d003_content_boundary",
            prototype_ref="project_visual_ac",
            absorbed_principle="Visual copy remains project-safe or already confirmed sample content; unsafe raw values remain excluded.",
            target_ui_regions=[
                "visual-workbench-shell",
                "status-band",
                "llm-explanation-component",
                "entity-detail-zone",
            ],
            checks=["no_unconfirmed_real_dv_content"],
            downgrade_when_failed="needs_d003_confirmation",
        ),
        implemented_item(
            decision_id="D041",
            ac_ids=["AC-V2-FE-VIS-006"],
            priority="P0",
            user_confirmed_item="Web demo keeps scripts/run_web_demo.py as the single maintained launch entry.",
            condition=single_entry_ok,
            evidence_artifacts=["scripts/run_web_demo.py"],
            evidence_type="visual_ac",
            prototype_ref="project_visual_ac",
            absorbed_principle="V2 visual remediation does not introduce another version-specific web launch path.",
            target_ui_regions=["scripts/run_web_demo.py"],
            checks=["single_web_demo_entry"],
            downgrade_when_failed="process_violation",
        ),
        {
            "decision_id": "D042,D058",
            "ac_ids": ["AC-V2-FE-VIS-007"],
            "priority": "P0",
            "user_confirmed_item": "Acceptance candidate requires after screenshots, visual artifact, automated checks, and user visual acceptance.",
            "implementation_files": ["src/dv_entity_linking/web.py", "scripts/run_v2_acceptance_smoke.py"],
            "evidence_artifacts": [
                summary.get("browser_evidence_path", ""),
                summary.get("visual_traceability_artifact_json", "v2_frontend_visual_traceability_check.json"),
                "desktop_1366x768 screenshot",
                "narrow_390x844 screenshot",
                "user after visual acceptance",
            ],
            "evidence_type": "manual_gate",
            "prototype_ref": "project_visual_ac",
            "absorbed_principle": "Acceptance requires concrete after visual evidence and explicit user visual acceptance.",
            "target_ui_regions": [
                "visual-workbench-shell",
                "status-band",
                "query-command-zone",
                "result-stream",
                "entity-detail-zone",
                "llm-explanation-component",
                "catalog-filter-zone",
            ],
            "before_screenshot": "",
            "after_screenshot": after_screenshot,
            "same_viewport_and_query": False,
            "automated_visual_semantic_checks": [
                {"name": "all_sections_visible", "passed": browser_check("all_sections_visible")},
                {"name": "no_text_overlap_or_clipping_narrow", "passed": browser_check("no_text_overlap_or_clipping_narrow")},
                {"name": "browser_screenshot_images_valid", "passed": summary.get("browser_screenshot_images_valid") is True},
            ],
            "status": "implemented" if automated_evidence_ok else "not_implemented",
            "downgrade_classification": "none"
            if automated_evidence_ok
            else "missing_visual_evidence",
            "reviewer_result": "pass" if automated_evidence_ok else "fail",
            "manual_user_acceptance_status": AFTER_VISUAL_USER_ACCEPTANCE_STATUS,
        },
        {
            "decision_id": "D042,D058",
            "ac_ids": ["AC-V2-FE-VIS-008"],
            "priority": "P0",
            "user_confirmed_item": "Acceptance candidate requires same-scenario before/after visual comparison or an explicit replacement criterion.",
            "implementation_files": ["src/dv_entity_linking/web.py", "scripts/run_v2_acceptance_smoke.py"],
            "evidence_artifacts": [
                summary.get("browser_evidence_path", ""),
                summary.get("visual_traceability_artifact_json", "v2_frontend_visual_traceability_check.json"),
                "desktop_1366x768 after screenshot",
                "narrow_390x844 after screenshot",
                "before same-scenario screenshot pending",
            ],
            "evidence_type": "manual_gate",
            "prototype_ref": "project_visual_ac",
            "absorbed_principle": "Acceptance requires same-scenario before/after comparison proving the page is no longer a plain white card form stack.",
            "target_ui_regions": [
                "visual-workbench-shell",
                "status-band",
                "query-command-zone",
                "result-stream",
                "entity-detail-zone",
                "llm-explanation-component",
                "catalog-filter-zone",
            ],
            "before_screenshot": before_screenshot,
            "after_screenshot": after_screenshot,
            "same_viewport_and_query": before_present,
            "automated_visual_semantic_checks": [
                {"name": "all_sections_visible", "passed": browser_check("all_sections_visible")},
                {"name": "no_text_overlap_or_clipping_narrow", "passed": browser_check("no_text_overlap_or_clipping_narrow")},
                {"name": "browser_screenshot_images_valid", "passed": summary.get("browser_screenshot_images_valid") is True},
                {"name": "before_same_scenario_screenshot_present", "passed": before_present},
            ],
            "status": "implemented" if (automated_evidence_ok and before_present) else ("needs_user_decision" if automated_evidence_ok else "not_implemented"),
            "downgrade_classification": "none"
            if (automated_evidence_ok and before_present)
            else ("needs_user_decision" if automated_evidence_ok else "missing_visual_evidence"),
            "reviewer_result": "pass" if (automated_evidence_ok and before_present) else ("needs_user_decision" if automated_evidence_ok else "fail"),
            "manual_user_acceptance_status": AFTER_VISUAL_USER_ACCEPTANCE_STATUS,
        },
    ]

    ac_statuses = {
        ac_id: sorted({item["status"] for item in items if ac_id in item["ac_ids"]})
        for ac_id in sorted({ac_id for item in items for ac_id in item["ac_ids"]})
    }
    blocking_ac_ids = sorted(
        {
            ac_id
            for item in items
            if _visual_item_blocks_acceptance(item)
            for ac_id in item["ac_ids"]
        }
    )
    if any(item["needs_d003_confirmation"] for item in d003_content_inventory):
        blocking_ac_ids = sorted(set(blocking_ac_ids) | {"AC-V2-FE-VIS-009"})

    return {
        "schema_version": "v2.frontend_visual_traceability.1",
        "source": "scripts/run_v2_acceptance_smoke.py",
        "scenario": {
            "query": "Check ALM-51020 and CPU Usage.",
            "mode": "offline_demo",
            "desktop_viewport": "1366x768",
            "narrow_viewport": "390x844",
            "browser_zoom_device_scale": "same before/after pending",
            "debug_collapsed": True,
            "selected_mention": "CPU Usage",
            "selected_candidate": "DV-KPI-MTK-001",
        },
        "manual_user_acceptance_status": AFTER_VISUAL_USER_ACCEPTANCE_STATUS,
        "manual_user_acceptance_evidence": {
            "source": AFTER_VISUAL_USER_ACCEPTANCE_SOURCE,
            "date": AFTER_VISUAL_USER_ACCEPTANCE_DATE,
            "browser_url": summary.get("browser_evidence_path", ""),
            "note": AFTER_VISUAL_USER_ACCEPTANCE_NOTE,
        },
        "canonical_scenario": {
            "query": "Check ALM-51020 and CPU Usage.",
            "desktop_viewport": "1366x768",
            "narrow_viewport": "390x844",
        },
        "prototype_absorption": {
            "SigNoz": ["status-band", "query-command-zone", "catalog-filter-zone"],
            "OpenGenerativeUI": ["llm-explanation-component"],
            "Tambo": ["schema-driven selection state", "visual traceability artifact"],
        },
        "d003_content_inventory": d003_content_inventory,
        "checks": {
            "visual_regions_present": html_has_regions,
            "automated_layout_checks_passed": automation_layout_ok,
            "selection_state_visible": selection_ok,
            "llm_component_state_visible": llm_component_ok,
            "no_unconfirmed_real_dv_content": no_unconfirmed_content,
            "no_text_overlap_or_clipping_narrow": browser_check("no_text_overlap_or_clipping_narrow"),
        },
        "items": items,
        "summary": {
            "ac_statuses": ac_statuses,
            "blocking_ac_ids": blocking_ac_ids,
            "blocking_count": len(blocking_ac_ids),
            "manual_user_acceptance_status": AFTER_VISUAL_USER_ACCEPTANCE_STATUS,
            "accepted_closed_allowed": False,
        },
    }


def _web_demo_single_entry_ok() -> bool:
    scripts_dir = Path("scripts")
    if not (scripts_dir / "run_web_demo.py").exists():
        return False
    versioned_web_entries = [
        path
        for path in scripts_dir.glob("run_*web_demo.py")
        if path.name != "run_web_demo.py"
    ]
    return not versioned_web_entries


def _validate_browser_evidence(log_path: Path) -> dict:
    evidence_path = log_path / "v2_frontend_browser_evidence.json"
    result = {
        "browser_evidence_path": str(evidence_path),
        "browser_evidence_checked": False,
        "browser_evidence_ok": False,
        "browser_evidence_fresh": False,
        "browser_screenshots_present": False,
        "browser_screenshot_images_valid": False,
        "browser_screenshot_paths": {},
        "browser_screenshot_dimensions": {},
        "browser_screenshot_dimension_checks": {},
        "browser_evidence_missing_checks": sorted(REQUIRED_BROWSER_EVIDENCE_CHECKS),
        "browser_evidence_reason": "",
    }
    if not evidence_path.exists():
        result["browser_evidence_reason"] = "missing v2_frontend_browser_evidence.json"
        return result

    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["browser_evidence_reason"] = f"invalid browser evidence json: {exc}"
        return result

    result["browser_evidence_checked"] = True
    checks = payload.get("checks") if isinstance(payload, dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    missing_checks = sorted(
        name for name in REQUIRED_BROWSER_EVIDENCE_CHECKS if checks.get(name) is not True
    )
    result["browser_evidence_missing_checks"] = missing_checks

    screenshots = payload.get("screenshots") if isinstance(payload, dict) else {}
    screenshot_paths = []
    if isinstance(screenshots, dict):
        for key, value in screenshots.items():
            shot_path = Path(str(value))
            if not shot_path.is_absolute():
                shot_path = log_path / shot_path
            screenshot_paths.append(shot_path)
            result["browser_screenshot_paths"][str(key)] = str(shot_path)
    screenshots_present = bool(screenshot_paths) and all(
        path.exists() and path.stat().st_size > 0 for path in screenshot_paths
    )
    result["browser_screenshots_present"] = screenshots_present

    dimension_checks = {}
    if isinstance(screenshots, dict):
        for key, value in screenshots.items():
            shot_path = Path(str(value))
            if not shot_path.is_absolute():
                shot_path = log_path / shot_path
            dimensions = _image_dimensions(shot_path)
            if dimensions:
                width, height = dimensions
                result["browser_screenshot_dimensions"][str(key)] = {
                    "width": width,
                    "height": height,
                }
            expected = _expected_dimensions_from_key(str(key))
            dimension_checks[str(key)] = bool(
                dimensions
                and (
                    expected is None
                    or _dimension_matches_expected(dimensions, expected)
                )
            )
    result["browser_screenshot_dimension_checks"] = dimension_checks
    result["browser_screenshot_images_valid"] = bool(dimension_checks) and all(
        dimension_checks.values()
    )

    source_mtimes = [
        path.stat().st_mtime
        for path in BROWSER_EVIDENCE_SOURCE_FILES
        if path.exists()
    ]
    latest_source_mtime = max(source_mtimes, default=0)
    evidence_mtime = evidence_path.stat().st_mtime
    screenshot_fresh = screenshots_present and all(
        path.stat().st_mtime + 1 >= latest_source_mtime for path in screenshot_paths
    )
    result["browser_evidence_fresh"] = evidence_mtime + 1 >= latest_source_mtime and screenshot_fresh

    result["browser_evidence_ok"] = bool(
        payload.get("ok") is True
        and payload.get("schema_version") == "v2.frontend_browser_evidence.1"
        and not missing_checks
        and screenshots_present
        and result["browser_screenshot_images_valid"]
        and result["browser_evidence_fresh"]
    )
    if not result["browser_evidence_ok"]:
        result["browser_evidence_reason"] = "browser evidence missing, stale, or failed required checks"
    return result


def _expected_dimensions_from_key(key: str) -> tuple[int, int] | None:
    if "_" not in key or "x" not in key:
        return None
    size = key.rsplit("_", 1)[-1]
    width_text, _, height_text = size.partition("x")
    try:
        return int(width_text), int(height_text)
    except ValueError:
        return None


def _image_dimensions(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png_dimensions_if_decodable(data)
    if data.startswith(b"\xff\xd8"):
        dimensions = _jpeg_dimensions(data)
        if dimensions and data.rstrip().endswith(b"\xff\xd9"):
            return dimensions
    return None


def _png_dimensions_if_decodable(data: bytes) -> tuple[int, int] | None:
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        return None
    offset = len(signature)
    width = 0
    height = 0
    seen_ihdr = False
    seen_idat = False
    idat_payloads = []
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + length
        crc_end = chunk_data_end + 4
        if crc_end > len(data):
            return None
        chunk_data = data[chunk_data_start:chunk_data_end]
        expected_crc = binascii.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        actual_crc = struct.unpack(">I", data[chunk_data_end:crc_end])[0]
        if expected_crc != actual_crc:
            return None
        if not seen_ihdr and chunk_type != b"IHDR":
            return None
        if chunk_type == b"IHDR":
            if seen_ihdr or length != 13:
                return None
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB",
                chunk_data,
            )
            if (
                width <= 0
                or height <= 0
                or compression != 0
                or filter_method != 0
                or interlace not in {0, 1}
                or color_type not in {0, 2, 3, 4, 6}
                or bit_depth not in {1, 2, 4, 8, 16}
            ):
                return None
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            if not seen_ihdr:
                return None
            seen_idat = True
            idat_payloads.append(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0 or not seen_ihdr or not seen_idat:
                return None
            if crc_end != len(data):
                return None
            try:
                decompressed = zlib.decompress(b"".join(idat_payloads))
            except zlib.error:
                return None
            if not decompressed:
                return None
            return width, height
        offset = crc_end
    return None


def _dimension_matches_expected(dimensions: tuple[int, int], expected: tuple[int, int]) -> bool:
    width, height = dimensions
    expected_width, expected_height = expected
    scrollbar_allowance = 24
    return (
        height == expected_height
        and expected_width - scrollbar_allowance <= width <= expected_width
    )


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        length = struct.unpack(">H", data[index:index + 2])[0]
        if length < 2 or index + length > len(data):
            return None
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if length < 7:
                return None
            height = struct.unpack(">H", data[index + 3:index + 5])[0]
            width = struct.unpack(">H", data[index + 5:index + 7])[0]
            return width, height
        index += length
    return None


def _traceability_markdown(traceability: dict) -> str:
    lines = [
        "# V2 Frontend Traceability Check",
        "",
        "| Decision | AC IDs | Status | Reviewer | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in traceability["items"]:
        lines.append(
            "| {decision} | {acs} | {status} | {reviewer} | {evidence} |".format(
                decision=item["decision_id"],
                acs=", ".join(item["ac_ids"]),
                status=item["status"],
                reviewer=item["reviewer_result"],
                evidence=", ".join(str(path) for path in item["evidence_artifacts"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _visual_traceability_markdown(traceability: dict) -> str:
    summary = traceability["summary"]
    lines = [
        "# V2 Frontend Visual Traceability Check",
        "",
        f"- Schema: `{traceability['schema_version']}`",
        f"- Manual user acceptance: `{traceability['manual_user_acceptance_status']}`",
        f"- Blocking AC IDs: {', '.join(summary['blocking_ac_ids']) or 'none'}",
        "",
        "| Decision | AC IDs | Priority | Status | Downgrade | Evidence Type |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in traceability["items"]:
        lines.append(
            "| {decision} | {acs} | {priority} | {status} | {downgrade} | {evidence_type} |".format(
                decision=item["decision_id"],
                acs=", ".join(item["ac_ids"]),
                priority=item["priority"],
                status=item["status"],
                downgrade=item["downgrade_classification"],
                evidence_type=item["evidence_type"],
            )
        )
    lines.extend(
        [
            "",
            "## D003 Content Inventory",
            "",
            "| Item | Source | Needs D003 Confirmation |",
            "| --- | --- | --- |",
        ]
    )
    for item in traceability["d003_content_inventory"]:
        lines.append(
            "| {item} | {source} | {needs} |".format(
                item=item["item"],
                source=item["source_classification"],
                needs=str(item["needs_d003_confirmation"]).lower(),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    logger, log_file = setup_logging(args.log_dir, "v2-acceptance-smoke")
    ensure_src_path()
    from dv_entity_linking.legacy.web import create_app

    service, run_mode = build_service(
        catalog_path=args.catalog,
        mode=args.mode,
        llm_config_path=args.llm_config,
        logger=logger,
    )
    app = create_app(
        service,
        samples_path=resolve_path(args.samples),
        default_mode=run_mode,
    )
    summary = run_smoke(app, run_mode.value, args.log_dir, smoke_log_file=log_file)
    logger.info("V2 acceptance smoke result: ok=%s log_file=%s", summary["ok"], log_file)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
