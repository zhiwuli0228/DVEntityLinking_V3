from __future__ import annotations

import argparse
import json

from demo_runtime import ensure_src_path, resolve_path, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the V3 two-layer storage and NER smoke checks.")
    parser.add_argument("--mode", choices=["offline_demo", "llm_enabled_demo"], default="offline_demo")
    parser.add_argument("--gauss-mock", default="samples/real/v3_gauss_entities.json")
    parser.add_argument("--redis-mock", default="samples/real/v3_redis_entity_words.json")
    parser.add_argument("--log-dir", default="outputs/logs")
    return parser.parse_args()


def _linked_entity_ids(payload: dict) -> list[str]:
    return [
        item.get("linked_entity", {}).get("entity_id", "")
        for item in payload.get("mention_results", [])
        if item.get("linked_entity")
    ]


def run_smoke(app, mode: str) -> dict:
    client = app.test_client()
    status = client.get("/api/status")
    status_payload = status.get_json()
    linked = client.post(
        "/api/link",
        json={"query": "Check ALM-51020 and CPU Usage.", "mode": mode, "allow_fallback": True},
    ).get_json()
    partial = client.post(
        "/api/link",
        json={"query": "Show CPU Usage for CloudHost-VM-1-1-000000.", "mode": mode, "allow_fallback": True},
    ).get_json()
    no_match = client.post(
        "/api/link",
        json={"query": "Show metrics for UnknownApp-999.", "mode": mode, "allow_fallback": True},
    ).get_json()
    not_required = client.post(
        "/api/link",
        json={"query": "Open the operations dashboard.", "mode": mode, "allow_fallback": True},
    ).get_json()
    linked_storage_statuses = [
        item.get("storage_lookup", {}).get("redis_status", "")
        for item in linked.get("mention_results", [])
    ]
    summary = {
        "mode": mode,
        "status_code": status.status_code,
        "catalog_loaded": status_payload.get("catalog_loaded"),
        "entity_count": status_payload.get("entity_count"),
        "type_counts": status_payload.get("type_counts"),
        "linked_status": linked.get("status"),
        "linked_entity_ids": _linked_entity_ids(linked),
        "linked_stage_names": [item.get("stage") for item in linked.get("stage_trace", [])],
        "linked_storage_redis_statuses": linked_storage_statuses,
        "partial_status": partial.get("status"),
        "partial_entity_ids": _linked_entity_ids(partial),
        "partial_no_match_count": sum(
            1 for item in partial.get("mention_results", []) if item.get("status") == "no_match"
        ),
        "no_match_status": no_match.get("status"),
        "no_match_candidates": no_match.get("candidates", []),
        "not_required_status": not_required.get("status"),
        "not_required_mention_count": len(not_required.get("mention_results", [])),
    }
    summary["ok"] = all(
        [
            summary["catalog_loaded"] is True,
            summary["entity_count"] == 7,
            summary["linked_status"] == "linked",
            set(summary["linked_entity_ids"]) == {"DV-ALM-002", "DV-KPI-MTK-001"},
            summary["linked_storage_redis_statuses"] == ["hit", "hit"],
            {"query_validation", "mention_detection", "storage_lookup", "status_aggregation"}
            <= set(summary["linked_stage_names"]),
            summary["partial_status"] == "partial",
            summary["partial_entity_ids"] == ["DV-KPI-MTK-001"],
            summary["partial_no_match_count"] == 1,
            summary["no_match_status"] == "no_match",
            summary["no_match_candidates"] == [],
            summary["not_required_status"] == "not_required",
            summary["not_required_mention_count"] == 0,
        ]
    )
    return summary


def main() -> int:
    args = parse_args()
    logger, log_file = setup_logging(args.log_dir, "v3-acceptance-smoke")
    ensure_src_path()
    from dv_entity_linking.models import RunMode
    from dv_entity_linking.service import EntityLinkingService
    from dv_entity_linking.web import create_app

    run_mode = RunMode(args.mode)
    service = EntityLinkingService.from_v3_mock(
        gauss_mock_path=resolve_path(args.gauss_mock),
        redis_mock_path=resolve_path(args.redis_mock),
    )
    app = create_app(
        service,
        samples_path=resolve_path("samples/real/v3_ner_golden_cases.json"),
        default_mode=run_mode,
    )
    summary = run_smoke(app, run_mode.value)
    logger.info("V3 acceptance smoke result: ok=%s log_file=%s", summary["ok"], log_file)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
