"""Run recording and output sanitization helpers."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .catalog import normalize_text
from .models import RunMode, RunRecord, to_plain
from .models import Status


FORBIDDEN_KEY_PARTS = (
    "api_key",
    "api_base",
    "base_url",
    "token",
    "cookie",
    "authorization",
    "password",
    "secret",
    "endpoint_url",
    "host",
    "url",
    "traceback",
    "exception",
    "payload",
    "raw_request",
    "raw_response",
    "llm_full_log",
)


def new_run_id() -> str:
    return uuid4().hex


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_for_record(value: Any) -> Any:
    plain = to_plain(value)
    if isinstance(plain, dict):
        sanitized: dict[str, Any] = {}
        for key, item in plain.items():
            lowered = key.lower()
            if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_for_record(item)
        return sanitized
    if isinstance(plain, list):
        return [sanitize_for_record(item) for item in plain]
    return plain


class RunRepository:
    def __init__(self, output_path: str | Path = "outputs/runs.jsonl") -> None:
        self.output_path = Path(output_path)

    def append(self, record: RunRecord) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        safe_record = replace(record, result=sanitize_for_record(record.result))
        with self.output_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(to_plain(safe_record), ensure_ascii=False, sort_keys=True))
            stream.write("\n")


def build_run_record(
    *,
    mode: RunMode,
    query: str,
    result: Any,
    llm_used: bool,
    degraded: bool,
) -> RunRecord:
    summary = sanitize_for_record(result)
    return RunRecord(
        run_id=new_run_id(),
        mode=mode,
        query=query,
        result=summary,
        llm_used=llm_used,
        degraded=degraded,
        created_at=utc_now_iso(),
    )


def evaluate_query_dataset(service, dataset) -> dict[str, Any]:
    """Run startup dataset evaluation with query-level and mention-level metrics."""

    cases: list[dict[str, Any]] = []
    counts = {
        "total": len(dataset.queries),
        "pass": 0,
        "fail": 0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 0,
        "negative_false_positive": 0,
    }
    status_counts: dict[str, int] = {}
    type_counts: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []

    for sample in dataset.queries:
        result = service.link_query(sample.query, mode=RunMode.OFFLINE_DEMO)
        case = _score_case(sample, result)
        cases.append(case)
        status_counts[sample.expected_status.value] = status_counts.get(sample.expected_status.value, 0) + 1
        for key in ["tp", "fp", "fn", "tn", "negative_false_positive"]:
            counts[key] += int(case["counts"].get(key, 0))
        _accumulate_type_counts(type_counts, case["mention_cases"])
        if case["passed"]:
            counts["pass"] += 1
        else:
            counts["fail"] += 1
            failures.append(
                {
                    "id": sample.id,
                    "query": sample.query,
                    "expected_status": sample.expected_status.value,
                    "actual_status": result.status.value,
                    "reason": case["reason"],
                }
            )

    precision_denominator = counts["tp"] + counts["fp"]
    recall_denominator = counts["tp"] + counts["fn"]
    precision = 1.0 if precision_denominator == 0 else counts["tp"] / precision_denominator
    recall = 1.0 if recall_denominator == 0 else counts["tp"] / recall_denominator
    notes: list[str] = []
    if precision_denominator == 0:
        notes.append("no_positive_predictions")
    if recall_denominator == 0:
        notes.append("no_expected_positive_cases")

    schema_version = str(dataset.metadata.get("schema_version", ""))
    report_schema = (
        "v2.entity_linking_evaluation_report.1"
        if schema_version.startswith("v2.")
        else "v1.alarm_evaluation_report.1"
    )
    summary = {
        **counts,
        "status_counts": dict(sorted(status_counts.items())),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "passed": (
            counts["fail"] == 0
            and counts["negative_false_positive"] == 0
            and round(precision, 4) == 1.0
            and round(recall, 4) == 1.0
        ),
        "metric_notes": notes,
        "type_metrics": _build_type_metrics(type_counts),
    }
    return sanitize_for_record(
        {
            "schema_version": report_schema,
            "summary": summary,
            "cases": cases,
            "failures": failures,
            "safe_config": {
                "mode": RunMode.OFFLINE_DEMO.value,
                "llm_enabled": False,
                "catalog_metadata": service.catalog.metadata,
            },
            "redaction_applied": True,
        }
    )


def _score_case(sample, result) -> dict[str, Any]:
    expected_ids = [item["entity_id"] for item in sample.expected_entities]
    candidate_ids = [item.entity_id for item in result.candidates]
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "negative_false_positive": 0}
    mention_cases: list[dict[str, Any]] = []
    matched_actual_indexes: set[int] = set()
    for expected in sample.mentions:
        actual_index, actual = _find_actual_mention(expected.text, result.mention_results)
        if actual_index is not None:
            matched_actual_indexes.add(actual_index)
        mention_case = _score_mention(expected, actual)
        mention_cases.append(mention_case)
        for key in counts:
            counts[key] += int(mention_case["counts"].get(key, 0))
    for index, actual in enumerate(result.mention_results):
        if index in matched_actual_indexes:
            continue
        mention_case = _score_unexpected_mention(actual)
        mention_cases.append(mention_case)
        for key in counts:
            counts[key] += int(mention_case["counts"].get(key, 0))

    linked_ids = [
        item.linked_entity.entity_id
        for item in result.mention_results
        if item.linked_entity
    ]
    if not sample.mentions and expected_ids:
        linked_id_set = set(linked_ids)
        passed_without_mentions = result.status == sample.expected_status and set(expected_ids) <= linked_id_set
        if passed_without_mentions:
            counts["tp"] = len(expected_ids)
        else:
            counts["fn"] = max(1, len(expected_ids))
            if candidate_ids or linked_ids:
                counts["fp"] = 1
            mention_cases.append(
                {
                    "text": "",
                    "expected_status": sample.expected_status.value,
                    "actual_status": result.status.value,
                    "expected_entity_ids": expected_ids,
                    "actual_entity_id": linked_ids[0] if linked_ids else "",
                    "candidate_ids": candidate_ids,
                    "passed": False,
                    "reason": "sample has expected entities but no expected mentions",
                    "counts": {
                        "tp": 0,
                        "fp": counts["fp"],
                        "fn": counts["fn"],
                        "tn": 0,
                        "negative_false_positive": 0,
                    },
                }
            )

    if sample.expected_status == Status.NOT_REQUIRED:
        no_entity_output = not candidate_ids and not linked_ids and not result.mention_results
        query_passed = result.status == Status.NOT_REQUIRED and no_entity_output
        if query_passed:
            counts["tn"] += 1
        else:
            counts["fp"] += 1
            counts["negative_false_positive"] += 1
    elif sample.expected_status == Status.NO_MATCH and not sample.mentions:
        no_entity_output = not candidate_ids and not linked_ids
        query_passed = result.status == Status.NO_MATCH and no_entity_output
        if query_passed:
            counts["tn"] += 1
        else:
            counts["fp"] += 1
            counts["negative_false_positive"] += 1
    else:
        query_passed = _query_status_passed(sample.expected_status, result.status, mention_cases)

    passed = query_passed and all(item["passed"] for item in mention_cases)
    reason = "" if passed else _case_failure_reason(sample, result, mention_cases)

    return {
        "id": sample.id,
        "query": sample.query,
        "expected_status": sample.expected_status.value,
        "actual_status": result.status.value,
        "expected_entity_ids": expected_ids,
        "candidate_ids": candidate_ids,
        "linked_entity_id": linked_ids[0] if len(linked_ids) == 1 else "",
        "linked_entity_ids": linked_ids,
        "mention_cases": mention_cases,
        "passed": passed,
        "reason": reason,
        "counts": counts,
    }


def _score_mention(expected, actual) -> dict[str, Any]:
    actual_status = actual.status if actual else None
    actual_entity_id = actual.linked_entity.entity_id if actual and actual.linked_entity else ""
    actual_entity_type = actual.linked_entity.entity_type.value if actual and actual.linked_entity else ""
    actual_candidate_ids = [candidate.entity_id for candidate in actual.candidates] if actual else []
    actual_candidate_types = [candidate.entity_type.value for candidate in actual.candidates] if actual else []
    if not actual_entity_type and actual_candidate_types:
        actual_entity_type = actual_candidate_types[0]
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "negative_false_positive": 0}
    passed = False
    reason = ""

    if expected.expected_status == Status.LINKED:
        passed = actual_status == Status.LINKED and actual_entity_id in set(expected.expected_entity_ids)
        if passed:
            counts["tp"] = 1
        else:
            counts["fn"] = 1
            if actual_candidate_ids or actual_entity_id:
                counts["fp"] = 1
            reason = (
                f"expected linked {expected.expected_entity_ids}, "
                f"got status={actual_status.value if actual_status else 'missing'}, "
                f"linked={actual_entity_id}"
            )
    elif expected.expected_status == Status.AMBIGUOUS:
        covered = set(expected.expected_entity_ids) <= set(actual_candidate_ids[:5])
        passed = actual_status == Status.AMBIGUOUS and covered
        if passed:
            counts["tp"] = 1
        else:
            counts["fn"] = 1
            if actual_candidate_ids:
                counts["fp"] = 1
            reason = (
                f"expected ambiguous candidates {expected.expected_entity_ids}, "
                f"got status={actual_status.value if actual_status else 'missing'}, "
                f"candidates={actual_candidate_ids[:5]}"
            )
    elif expected.expected_status in {Status.NO_MATCH, Status.NOT_REQUIRED, Status.DEPENDENCY_FAILED}:
        passed = actual_status == expected.expected_status and not actual_candidate_ids and not actual_entity_id
        if passed:
            counts["tn"] = 1
        else:
            counts["fp"] = 1
            counts["negative_false_positive"] = 1
            reason = (
                f"expected {expected.expected_status.value} with empty candidates, "
                f"got status={actual_status.value if actual_status else 'missing'}, "
                f"candidates={actual_candidate_ids}, linked={actual_entity_id}"
            )

    return {
        "text": expected.text,
        "expected_status": expected.expected_status.value,
        "actual_status": actual_status.value if actual_status else "missing",
        "expected_entity_ids": expected.expected_entity_ids,
        "expected_entity_type": expected.expected_entity_type,
        "actual_entity_id": actual_entity_id,
        "actual_entity_type": actual_entity_type,
        "candidate_ids": actual_candidate_ids,
        "candidate_entity_types": actual_candidate_types,
        "passed": passed,
        "reason": reason,
        "counts": counts,
    }


def _score_unexpected_mention(actual) -> dict[str, Any]:
    actual_entity_id = actual.linked_entity.entity_id if actual.linked_entity else ""
    actual_entity_type = actual.linked_entity.entity_type.value if actual.linked_entity else ""
    actual_candidate_ids = [candidate.entity_id for candidate in actual.candidates]
    actual_candidate_types = [candidate.entity_type.value for candidate in actual.candidates]
    if not actual_entity_type and actual_candidate_types:
        actual_entity_type = actual_candidate_types[0]
    negative_false_positive = 1 if actual_candidate_ids or actual_entity_id else 0
    return {
        "text": actual.mention.text,
        "expected_status": "unexpected",
        "actual_status": actual.status.value,
        "expected_entity_ids": [],
        "expected_entity_type": "",
        "actual_entity_id": actual_entity_id,
        "actual_entity_type": actual_entity_type,
        "candidate_ids": actual_candidate_ids,
        "candidate_entity_types": actual_candidate_types,
        "passed": False,
        "reason": f"unexpected mention output: {actual.mention.text}",
        "counts": {
            "tp": 0,
            "fp": 1,
            "fn": 0,
            "tn": 0,
            "negative_false_positive": negative_false_positive,
        },
    }


def _accumulate_type_counts(
    type_counts: dict[str, dict[str, int]],
    mention_cases: list[dict[str, Any]],
) -> None:
    for mention_case in mention_cases:
        counts = mention_case.get("counts", {})
        expected_type = str(mention_case.get("expected_entity_type", "") or "")
        actual_type = str(mention_case.get("actual_entity_type", "") or "")
        if expected_type:
            bucket = type_counts.setdefault(expected_type, {"tp": 0, "fp": 0, "fn": 0})
            bucket["tp"] += int(counts.get("tp", 0))
            bucket["fn"] += int(counts.get("fn", 0))
        if actual_type:
            bucket = type_counts.setdefault(actual_type, {"tp": 0, "fp": 0, "fn": 0})
            bucket["fp"] += int(counts.get("fp", 0))


def _build_type_metrics(type_counts: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for entity_type, counts in sorted(type_counts.items()):
        precision_denominator = counts["tp"] + counts["fp"]
        recall_denominator = counts["tp"] + counts["fn"]
        precision = 1.0 if precision_denominator == 0 else counts["tp"] / precision_denominator
        recall = 1.0 if recall_denominator == 0 else counts["tp"] / recall_denominator
        metrics[entity_type] = {
            **counts,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
        }
    return metrics


def _find_actual_mention(expected_text: str, mention_results: list) -> tuple[int | None, Any]:
    expected_key = normalize_text(expected_text)
    for index, item in enumerate(mention_results):
        actual_key = normalize_text(item.mention.text)
        if actual_key == expected_key:
            return index, item
    for index, item in enumerate(mention_results):
        actual_key = normalize_text(item.mention.text)
        if expected_key and (expected_key in actual_key or actual_key in expected_key):
            return index, item
    return None, None


def _query_status_passed(expected_status: Status, actual_status: Status, mention_cases: list[dict[str, Any]]) -> bool:
    if expected_status == Status.LINKED:
        return actual_status == Status.LINKED
    if expected_status == Status.PARTIAL:
        return (
            actual_status == Status.PARTIAL
            and any(item["expected_status"] == Status.LINKED.value and item["passed"] for item in mention_cases)
            and any(item["expected_status"] != Status.LINKED.value and item["passed"] for item in mention_cases)
        )
    if expected_status == Status.AMBIGUOUS:
        return actual_status == Status.AMBIGUOUS
    if expected_status == Status.NO_MATCH:
        return actual_status == Status.NO_MATCH
    if expected_status == Status.DEPENDENCY_FAILED:
        return actual_status == Status.DEPENDENCY_FAILED
    return actual_status == expected_status


def _case_failure_reason(sample, result, mention_cases: list[dict[str, Any]]) -> str:
    failed_mentions = [item for item in mention_cases if not item["passed"]]
    if failed_mentions:
        return failed_mentions[0]["reason"]
    return f"expected status={sample.expected_status.value}, got status={result.status.value}"
