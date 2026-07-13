from __future__ import annotations

import argparse
import json

from demo_runtime import build_service, ensure_src_path, resolve_path, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the V1 alarm demo acceptance smoke checks.")
    parser.add_argument("--mode", choices=["offline_demo", "llm_enabled_demo"], default="offline_demo")
    parser.add_argument("--catalog", default="samples/real/entity_examples.json")
    parser.add_argument("--samples", default="samples/real/query_samples.json")
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


def _candidate_ids(payload: dict) -> list[str]:
    return [item.get("entity_id", "") for item in payload.get("candidates", [])]


def run_smoke(app, mode: str) -> dict:
    client = app.test_client()
    summary = {"mode": mode}

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

    exact = _link(client, "Check ALM-51020 impact.", mode)
    summary["exact_status_code"] = exact["_http_status"]
    summary["exact_status"] = exact.get("status")
    summary["exact_linked_entity_id"] = (exact.get("linked_entity") or {}).get("entity_id")

    id_and_name = _link(client, "Explain ALM-51020 The certificate is about to expire.", mode)
    summary["id_and_name_status"] = id_and_name.get("status")
    summary["id_and_name_linked_entity_id"] = (id_and_name.get("linked_entity") or {}).get("entity_id")

    ambiguous = _link(client, "What should I do if certificate is about to expire?", mode)
    summary["ambiguous_status"] = ambiguous.get("status")
    summary["ambiguous_candidate_ids"] = _candidate_ids(ambiguous)

    no_match = _link(client, "What is alarm 51?", mode)
    summary["short_id_no_match_status"] = no_match.get("status")
    summary["short_id_candidate_count"] = len(no_match.get("candidates", []))

    not_required = _link(client, "Open the operations dashboard.", mode)
    summary["not_required_status"] = not_required.get("status")
    summary["not_required_candidate_count"] = len(not_required.get("candidates", []))

    invalid = client.post("/api/link", json={"query": "", "mode": mode})
    invalid_payload = invalid.get_json()
    summary["invalid_status"] = invalid_payload.get("status")
    summary["invalid_error_code"] = invalid_payload.get("error_code")

    invalid_mode = client.post("/api/link", json={"query": "Check ALM-51020 impact.", "mode": "bad"})
    invalid_mode_payload = invalid_mode.get_json()
    summary["invalid_mode_status_code"] = invalid_mode.status_code
    summary["invalid_mode_error_code"] = invalid_mode_payload.get("error_code")

    retrieve = client.post("/api/retrieve", json={"entity_id": "DV-ALM-002", "k": 5})
    retrieve_payload = retrieve.get_json()
    summary["retrieve_status_code"] = retrieve.status_code
    summary["retrieve_count"] = len(retrieve_payload.get("items", []))
    summary["retrieve_top_similarity_reason_present"] = bool(
        retrieve_payload.get("items", [{}])[0].get("similarity_reason")
    )

    page = client.get("/classic", query_string={"query": "Check ALM-51020 impact."})
    html = page.get_data(as_text=True)
    summary["html_status_code"] = page.status_code
    summary["html_sections_present"] = all(
        marker in html
        for marker in [
            "runtime-status",
            "llm-config-panel",
            "llm-config-form",
            "result-summary",
            "mention-summary",
            "entity-catalog",
            "show-entities",
            "candidate-list",
            "entity-detail",
            "retrieval-result",
            "debug-details",
        ]
    )
    summary["html_mode_controls_present"] = all(
        marker in html
        for marker in [
            'name="mode"',
            'value="offline_demo"',
            'value="llm_enabled_demo"',
            'name="allow_fallback"',
        ]
    )
    summary["html_contains_expected_entity"] = "DV-ALM-002" in html

    samples = client.get("/api/samples")
    samples_payload = samples.get_json()
    summary["sample_count"] = len(samples_payload.get("queries", []))

    entities = client.get("/api/entities?limit=200")
    entities_payload = entities.get_json()
    summary["entity_catalog_count"] = len(entities_payload.get("items", []))

    summary["ok"] = all(
        [
            summary["catalog_loaded"] is True,
            summary["entity_count"] == 9,
            summary["entity_catalog_count"] == 9,
            summary["type_counts"] == {"alarm": 9},
            summary["llm_runtime_configurable"] is True,
            summary["exact_status"] == "linked",
            summary["exact_linked_entity_id"] == "DV-ALM-002",
            summary["id_and_name_status"] == "linked",
            summary["id_and_name_linked_entity_id"] == "DV-ALM-002",
            summary["ambiguous_status"] == "ambiguous",
            {"DV-ALM-002", "DV-ALM-003"} <= set(summary["ambiguous_candidate_ids"]),
            summary["short_id_no_match_status"] == "no_match",
            summary["short_id_candidate_count"] == 0,
            summary["not_required_status"] == "not_required",
            summary["not_required_candidate_count"] == 0,
            summary["invalid_error_code"] == "invalid_input",
            summary["invalid_mode_status_code"] == 400,
            summary["invalid_mode_error_code"] == "invalid_mode",
            summary["retrieve_count"] == 5,
            summary["retrieve_top_similarity_reason_present"] is True,
            summary["html_sections_present"] is True,
            summary["html_mode_controls_present"] is True,
            summary["html_contains_expected_entity"] is True,
            summary["sample_count"] == 16,
        ]
    )
    return summary


def main() -> int:
    args = parse_args()
    logger, log_file = setup_logging(args.log_dir, "v1-acceptance-smoke")
    ensure_src_path()
    from dv_entity_linking.web import create_app

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
    summary = run_smoke(app, run_mode.value)
    logger.info("V1 acceptance smoke result: ok=%s log_file=%s", summary["ok"], log_file)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
