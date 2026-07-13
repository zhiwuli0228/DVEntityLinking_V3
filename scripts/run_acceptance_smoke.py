from __future__ import annotations

import argparse
import json

from demo_runtime import build_service, ensure_src_path, resolve_path, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the V0 demo acceptance smoke checks.")
    parser.add_argument("--mode", choices=["offline_demo", "llm_enabled_demo"], default="offline_demo")
    parser.add_argument("--catalog", default="samples/mock/entity_catalog.json")
    parser.add_argument("--samples", default="samples/mock/query_samples.json")
    parser.add_argument("--llm-config", default="config/llm.local.json")
    parser.add_argument("--log-dir", default="outputs/logs")
    return parser.parse_args()


def run_smoke(app, mode: str) -> dict:
    client = app.test_client()
    summary = {"mode": mode}

    status = client.get("/api/status")
    status_payload = status.get_json()
    summary["status_code"] = status.status_code
    summary["catalog_loaded"] = status_payload.get("catalog_loaded")
    summary["entity_count"] = status_payload.get("entity_count")
    summary["llm_enabled"] = status_payload.get("llm_enabled")

    link = client.post(
        "/api/link",
        json={"query": "RAN-A1 的 ASR 最近如何", "mode": mode},
    )
    link_payload = link.get_json()
    summary["link_status_code"] = link.status_code
    summary["link_status"] = link_payload.get("status")
    summary["link_degraded"] = link_payload.get("degraded")
    summary["link_entity_ids"] = [
        item.get("linked_entity", {}).get("entity_id")
        for item in link_payload.get("mention_results", [])
        if item.get("linked_entity")
    ]

    ambiguous = client.post("/api/link", json={"query": "CP01 是什么告警", "mode": mode})
    summary["ambiguous_status"] = ambiguous.get_json().get("status")

    no_match = client.post(
        "/api/link",
        json={"query": "查询不存在的 Gamma 虚拟设备", "mode": mode},
    )
    summary["no_match_status"] = no_match.get_json().get("status")

    invalid = client.post("/api/link", json={"query": "", "mode": mode})
    invalid_payload = invalid.get_json()
    summary["invalid_status"] = invalid_payload.get("status")
    summary["invalid_error_code"] = invalid_payload.get("error_code")

    retrieve = client.post("/api/retrieve", json={"entity_id": "NE-DV-RAN-001", "k": 5})
    retrieve_payload = retrieve.get_json()
    summary["retrieve_status_code"] = retrieve.status_code
    summary["retrieve_count"] = len(retrieve_payload.get("items", []))
    summary["retrieve_top_similarity_reason_present"] = bool(
        retrieve_payload.get("items", [{}])[0].get("similarity_reason")
    )

    page = client.get("/classic", query_string={"query": "RAN-A1 的 ASR 最近如何"})
    html = page.get_data(as_text=True)
    summary["html_status_code"] = page.status_code
    summary["html_sections_present"] = all(
        marker in html
        for marker in [
            "runtime-status",
            "llm-config-panel",
            "result-summary",
            "mention-summary",
            "entity-catalog",
            "candidate-list",
            "entity-detail",
            "retrieval-result",
            "debug-details",
        ]
    )
    summary["html_contains_expected_entity"] = (
        "NE-DV-RAN-001" in html and "KPI-ACCESS-SUCCESS" in html
    )

    expected = {
        "NE-DV-RAN-001",
        "KPI-ACCESS-SUCCESS",
    }
    summary["ok"] = all(
        [
            summary["catalog_loaded"] is True,
            summary["entity_count"] >= 20,
            summary["link_status"] == "linked",
            expected.issubset(set(summary["link_entity_ids"])),
            summary["ambiguous_status"] in {"ambiguous", "linked"},
            summary["no_match_status"] == "no_match",
            summary["invalid_error_code"] == "invalid_input",
            summary["retrieve_count"] == 5,
            summary["retrieve_top_similarity_reason_present"] is True,
            summary["html_sections_present"] is True,
            summary["html_contains_expected_entity"] is True,
        ]
    )
    return summary


def main() -> int:
    args = parse_args()
    logger, log_file = setup_logging(args.log_dir, "acceptance-smoke")
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
    logger.info("Acceptance smoke result: ok=%s log_file=%s", summary["ok"], log_file)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
