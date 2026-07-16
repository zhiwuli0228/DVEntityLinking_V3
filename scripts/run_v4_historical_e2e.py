"""Run every V1/V2/V3 business query through the V4 IR integration path."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dv_entity_linking import LinkRequestV1, ModuleConfig, create_entity_linking_module
from dv_entity_linking.domain.normalization import normalize_query


class HistoricalEntityDataService:
    def __init__(
        self,
        entities: list[dict[str, Any]],
        words: list[dict[str, Any]] | None = None,
    ) -> None:
        self.entities = {item["entity_id"]: item for item in entities}
        self.calls: list[str] = []
        self.data_version = "historical-e2e-v1"
        self.words = words or [
            {
                "entity_word_id": f"{entity['entity_id']}:{index}",
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "entity_word": word,
                "normalized_key": normalize_query(word).normalized_text,
                "source": "entity_name" if index == 0 else "confirmed_alias",
                "match_mode": "STRUCTURED_TOKEN" if any(char.isdigit() for char in word) else "EXACT_WORD",
            }
            for entity in entities
            for index, word in enumerate([entity["entity_name"], *entity.get("alias", [])])
            if normalize_query(word).normalized_text
        ]

    def invoke(self, *, url: str, payload: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
        assert url == "ir://historical/entity-data:execute"
        operation = payload["operation"]
        self.calls.append(operation)
        body = payload["payload"]
        if operation == "MATCH_WORDS":
            allowed = set(body["entity_types"])
            matches = [
                word for word in self.words
                if word["normalized_key"] in body["normalized_query"]
                and (not allowed or word["entity_type"] in allowed)
            ]
            return self._response(operation, {"matches": matches})
        if operation == "BATCH_GET_ENTITIES":
            ids = body["entity_ids"]
            return self._response(
                operation,
                {"entities": [self.entities[item] for item in ids if item in self.entities],
                 "missing_ids": [item for item in ids if item not in self.entities]},
            )
        raise AssertionError(operation)

    def _response(self, operation: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"contract_version": "v1", "operation": operation, "status": "success", "data_version": self.data_version, "data": data}


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def v3_words() -> list[dict[str, Any]]:
    payload = load_json("samples/real/v3_redis_entity_words.json")
    return [
        {"entity_word_id": f"v3:{index}", "entity_type": "", "match_mode": "STRUCTURED_TOKEN" if any(char.isdigit() for char in item["entity_word"]) else "EXACT_WORD", "priority": 0, **item}
        for index, item in enumerate(payload["entity_words"])
    ]


def scenarios() -> list[tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]] | None]]:
    v1_entities = load_json("samples/real/entity_examples.json")["entities"]
    v1_queries = load_json("samples/real/query_samples.json")["queries"]
    v2_entities = [*v1_entities, *load_json("samples/real/v2_entity_examples.json")["entities"]]
    v2_queries = load_json("samples/real/v2_query_samples.json")["queries"]
    v3_entities = load_json("samples/real/v3_gauss_entities.json")["entities"]
    v3_queries = load_json("samples/real/v3_ner_golden_cases.json")["queries"]
    words = v3_words()
    for word in words:
        word["entity_type"] = next(item["entity_type"] for item in v3_entities if item["entity_id"] == word["entity_id"])
    return [("V1", v1_entities, v1_queries, None), ("V2", v2_entities, v2_queries, None), ("V3", v3_entities, v3_queries, words)]


def assess(response, expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if response.status != expected["expected_status"]:
        failures.append(f"status expected={expected['expected_status']} actual={response.status}")
    actual = {(item.text, item.span): item for item in response.mentions}
    for mention in expected.get("mentions", []):
        key = (mention["text"], tuple(mention["span"]))
        result = actual.get(key)
        if result is None:
            failures.append(f"missing mention {mention['text']}@{mention['span']}")
            continue
        expected_status = mention.get(
            "expected_status",
            "ambiguous" if expected["expected_status"] == "ambiguous" and len(mention.get("expected_entity_ids", [])) > 1
            else "linked" if mention.get("expected_entity_ids") else "no_match",
        )
        if result.status != expected_status:
            failures.append(f"mention {mention['text']} status expected={expected_status} actual={result.status}")
        expected_ids = set(mention.get("expected_entity_ids", []))
        actual_ids = {candidate.entity_id for candidate in result.candidates}
        if expected_ids and not expected_ids.issubset(actual_ids):
            failures.append(f"mention {mention['text']} ids expected={sorted(expected_ids)} actual={sorted(actual_ids)}")
    return failures


def main() -> int:
    report: dict[str, Any] = {"report": "v4.historical_ir_e2e.1", "versions": {}, "failures": []}
    for version, entities, queries, words in scenarios():
        service = HistoricalEntityDataService(entities, words)
        if version == "V1":
            # This legacy sample explicitly annotated the long alarm ID's numeric alias.
            # The entity-data service expresses that compatibility policy as word priority.
            service.words = [
                {**word, "priority": 10 if word["entity_word"] == "505001314" else 0}
                for word in service.words
            ]
        module = create_entity_linking_module(
            ModuleConfig(entity_data_ir_url="ir://historical/entity-data:execute"), platform_client=service
        )
        rows = []
        for item in queries:
            response = module.link(LinkRequestV1(query=item["query"]))
            failures = assess(response, item)
            rows.append({"id": item["id"], "expected_status": item["expected_status"], "actual_status": response.status, "passed": not failures, "failures": failures})
            report["failures"].extend([f"{version}/{item['id']}: {failure}" for failure in failures])
        report["versions"][version] = {"query_count": len(rows), "passed": sum(row["passed"] for row in rows), "failed": sum(not row["passed"] for row in rows), "cases": rows, "remote_calls": service.calls}
    report["summary"] = {"passed": not report["failures"], "failure_count": len(report["failures"])}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
