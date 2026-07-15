from __future__ import annotations

import argparse
import json
from typing import Any

from demo_runtime import ensure_src_path, resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V3 storage-backed NER golden-case evaluation.")
    parser.add_argument("--gauss-mock", default="samples/real/v3_gauss_entities.json")
    parser.add_argument("--redis-mock", default="samples/real/v3_redis_entity_words.json")
    parser.add_argument("--queries", default="samples/real/v3_ner_golden_cases.json")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def _load_queries(path: str) -> dict[str, Any]:
    payload = json.loads(resolve_path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("V3 golden cases root must be object")
    metadata = payload.get("metadata")
    queries = payload.get("queries")
    if not isinstance(metadata, dict) or metadata.get("schema_version") != "v3.ner_golden_cases.1":
        raise ValueError("metadata.schema_version must be v3.ner_golden_cases.1")
    if not isinstance(queries, list):
        raise ValueError("queries must be list")
    if metadata.get("query_count") != len(queries):
        raise ValueError("metadata.query_count does not match queries[] length")
    return payload


def _score_case(service, sample: dict[str, Any]) -> dict[str, Any]:
    from dv_entity_linking.legacy.models import RunMode
    from dv_entity_linking.legacy.storage import normalize_entity_word

    result = service.link_query(str(sample.get("query", "")), mode=RunMode.OFFLINE_DEMO)
    expected_mentions = sample.get("mentions") or []
    actual_by_text = {
        normalize_entity_word(item.mention.text): item
        for item in result.mention_results
    }
    mention_cases: list[dict[str, Any]] = []
    linked_tp = linked_fp = linked_fn = negative_fp = 0
    for expected in expected_mentions:
        key = normalize_entity_word(str(expected.get("text", "")))
        actual = actual_by_text.get(key)
        expected_status = str(expected.get("expected_status", "linked"))
        expected_ids = set(expected.get("expected_entity_ids") or [])
        actual_id = actual.linked_entity.entity_id if actual and actual.linked_entity else ""
        actual_candidates = [candidate.entity_id for candidate in actual.candidates] if actual else []
        actual_status = actual.status.value if actual else "missing"
        span_ok = bool(actual and list(actual.mention.span or []) == expected.get("span"))
        norm_ok = bool(actual and normalize_entity_word(actual.mention.text) == expected.get("normalized_text"))
        if expected_status == "linked":
            passed = actual_status == "linked" and actual_id in expected_ids and span_ok and norm_ok
            if passed:
                linked_tp += 1
            else:
                linked_fn += 1
                if actual_id or actual_candidates:
                    linked_fp += 1
        else:
            passed = actual_status == expected_status and not actual_id and not actual_candidates and span_ok and norm_ok
            if not passed:
                negative_fp += 1
                linked_fp += 1
        mention_cases.append(
            {
                "text": expected.get("text", ""),
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_entity_ids": sorted(expected_ids),
                "actual_entity_id": actual_id,
                "candidate_ids": actual_candidates,
                "span_ok": span_ok,
                "normalization_ok": norm_ok,
                "passed": passed,
            }
        )
    if not expected_mentions and result.mention_results:
        negative_fp += 1
        linked_fp += 1
    case_passed = result.status.value == sample.get("expected_status") and all(
        item["passed"] for item in mention_cases
    )
    if sample.get("expected_status") == "not_required":
        case_passed = result.status.value == "not_required" and not result.mention_results
    return {
        "id": sample.get("id", ""),
        "query": sample.get("query", ""),
        "expected_status": sample.get("expected_status", ""),
        "actual_status": result.status.value,
        "mention_cases": mention_cases,
        "passed": case_passed,
        "counts": {
            "tp": linked_tp,
            "fp": linked_fp,
            "fn": linked_fn,
            "negative_false_positive": negative_fp,
        },
    }


def main() -> int:
    args = parse_args()
    ensure_src_path()
    from dv_entity_linking.legacy.service import EntityLinkingService

    payload = _load_queries(args.queries)
    service = EntityLinkingService.from_v3_mock(
        gauss_mock_path=resolve_path(args.gauss_mock),
        redis_mock_path=resolve_path(args.redis_mock),
    )
    cases = [_score_case(service, sample) for sample in payload["queries"]]
    total = len(cases)
    passed = sum(case["passed"] for case in cases)
    counts = {
        "tp": sum(case["counts"]["tp"] for case in cases),
        "fp": sum(case["counts"]["fp"] for case in cases),
        "fn": sum(case["counts"]["fn"] for case in cases),
        "negative_false_positive": sum(case["counts"]["negative_false_positive"] for case in cases),
    }
    precision_denominator = counts["tp"] + counts["fp"]
    recall_denominator = counts["tp"] + counts["fn"]
    report = {
        "schema_version": "v3.ner_storage_evaluation_report.1",
        "summary": {
            "total": total,
            "pass": passed,
            "fail": total - passed,
            **counts,
            "precision": 1.0 if precision_denominator == 0 else round(counts["tp"] / precision_denominator, 4),
            "recall": 1.0 if recall_denominator == 0 else round(counts["tp"] / recall_denominator, 4),
            "passed": passed == total and counts["negative_false_positive"] == 0,
        },
        "startup_report": {
            "entity_count": service.v3_pipeline.storage_repository.startup_report.entity_count
            if service.v3_pipeline
            else 0,
            "word_count": service.v3_pipeline.storage_repository.startup_report.word_count
            if service.v3_pipeline
            else 0,
        },
        "cases": cases,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = resolve_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
