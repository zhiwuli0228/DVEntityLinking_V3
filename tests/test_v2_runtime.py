from __future__ import annotations

import json
from pathlib import Path

import pytest

from dv_entity_linking.legacy.catalog import CatalogRepository
from dv_entity_linking.legacy.datasets import (
    QueryDataset,
    QueryDatasetError,
    QueryDatasetLoader,
    QueryMentionExpectation,
    QuerySample,
)
from dv_entity_linking.legacy.evaluation import evaluate_query_dataset
from dv_entity_linking.legacy.llm import MockLLMClient
from dv_entity_linking.legacy.models import EntityType, Status
from dv_entity_linking.legacy.service import EntityLinkingService
from dv_entity_linking.legacy.web import create_app


V2_ENTITY_PATH = Path("samples/real/v2_entity_examples.json")
V2_QUERY_PATH = Path("samples/real/v2_query_samples.json")


def _v2_service() -> EntityLinkingService:
    repository = CatalogRepository(V2_ENTITY_PATH)
    repository.load()
    return EntityLinkingService(repository)


def test_v2_catalog_and_query_dataset_load():
    repository = CatalogRepository(V2_ENTITY_PATH)
    load_result = repository.load()
    dataset = QueryDatasetLoader().load(V2_QUERY_PATH, repository)

    assert load_result.entity_count == 25
    assert load_result.type_counts == {
        EntityType.ALARM.value: 9,
        EntityType.KPI_MEAS_TYPE_KEY.value: 6,
        EntityType.KPI_TASK_NAME.value: 5,
        EntityType.NE_NAME.value: 3,
        EntityType.NE_TYPE.value: 2,
    }
    assert all(
        not entity.alias
        for entity in repository.entities
        if entity.entity_type != EntityType.ALARM
    )
    assert len(dataset.queries) == 12
    assert any(sample.expected_status == Status.PARTIAL for sample in dataset.queries)
    assert max(len(sample.mentions) for sample in dataset.queries) == 2


def test_v2_multi_mention_partial_linking():
    service = _v2_service()

    result = service.link_query("Show CPU Usage for CloudHost-VM-1-1-000000.")

    assert result.status == Status.PARTIAL
    assert [item.status for item in result.mention_results] == [
        Status.LINKED,
        Status.NO_MATCH,
    ]
    assert result.mention_results[0].linked_entity.entity_id == "DV-KPI-MTK-001"
    assert result.mention_results[1].candidates == []


def test_v2_unified_catalog_links_alarm_and_new_type_in_one_query():
    service = _v2_service()

    result = service.link_query("Check ALM-51020 and CPU Usage.")

    assert result.status == Status.LINKED
    assert [item.linked_entity.entity_id for item in result.mention_results] == [
        "DV-ALM-002",
        "DV-KPI-MTK-001",
    ]


def test_v2_degraded_all_linked_result_becomes_partial():
    repository = CatalogRepository(V2_ENTITY_PATH)
    repository.load()
    service = EntityLinkingService(
        repository,
        llm_client=MockLLMClient(error_code="llm_timeout"),
    )

    result = service.link_query(
        "Check ALM-51020 and CPU Usage.",
        mode="llm_enabled_demo",
        allow_fallback=True,
    )

    assert result.status == Status.PARTIAL
    assert result.degraded is True


def test_v2_query_dataset_reaches_startup_threshold():
    service = _v2_service()
    dataset = QueryDatasetLoader().load(V2_QUERY_PATH, service.catalog)

    report = evaluate_query_dataset(service, dataset)

    assert report["schema_version"] == "v2.entity_linking_evaluation_report.1"
    assert report["summary"]["passed"] is True
    assert report["summary"]["fail"] == 0
    assert report["summary"]["negative_false_positive"] == 0
    assert report["summary"]["precision"] == 1.0
    assert report["summary"]["recall"] == 1.0
    assert report["summary"]["status_counts"]["partial"] == 1
    assert report["failures"] == []
    assert report["summary"]["type_metrics"] == {
        "alarm": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0},
        "kpi_meas_type_key": {
            "tp": 8,
            "fp": 0,
            "fn": 0,
            "precision": 1.0,
            "recall": 1.0,
        },
        "kpi_task_name": {
            "tp": 3,
            "fp": 0,
            "fn": 0,
            "precision": 1.0,
            "recall": 1.0,
        },
        "ne_name": {"tp": 3, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0},
        "ne_type": {"tp": 2, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0},
    }


def test_v2_evaluator_counts_unexpected_extra_mentions_as_false_positive():
    service = _v2_service()
    dataset = QueryDataset(
        metadata={"schema_version": "v2.query_samples.1"},
        queries=[
            QuerySample(
                id="V2-Q-FP",
                query="Show CPU Usage for CBS_1_cbpmdb_b2fc41cbb389(FI01).",
                expected_status=Status.LINKED,
                mentions=[
                    QueryMentionExpectation(
                        text="CPU Usage",
                        span=(5, 14),
                        expected_entity_ids=["DV-KPI-MTK-001"],
                        expected_status=Status.LINKED,
                    )
                ],
                expected_entities=[{"entity_id": "DV-KPI-MTK-001"}],
            )
        ],
    )

    report = evaluate_query_dataset(service, dataset)

    assert report["summary"]["passed"] is False
    assert report["summary"]["fp"] == 1
    assert report["failures"][0]["reason"].startswith("unexpected mention output")


def test_v2_query_dataset_loader_fails_closed_on_metadata_contract(tmp_path):
    repository = CatalogRepository(V2_ENTITY_PATH)
    repository.load()
    payload = json.loads(V2_QUERY_PATH.read_text(encoding="utf-8"))
    payload["metadata"]["query_language"] = "zh"
    payload["metadata"]["multi_mention_supported"] = False
    payload["metadata"]["query_count"] = 999
    bad_dataset = tmp_path / "bad_v2_query_samples.json"
    bad_dataset.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryDatasetError) as exc_info:
        QueryDatasetLoader().load(bad_dataset, repository)

    fields = {error["field"] for error in exc_info.value.errors}
    assert {
        "metadata.query_language",
        "metadata.multi_mention_supported",
        "metadata.query_count",
    } <= fields


def test_v2_web_api_returns_multi_mention_projection():
    service = _v2_service()
    client = create_app(
        service,
        samples_path=V2_QUERY_PATH,
    ).test_client()

    response = client.post(
        "/api/link",
        json={"query": "Run Network quality monitoring for onlinecharging_docker."},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == Status.LINKED.value
    assert [item["linked_entity"]["entity_id"] for item in payload["mention_results"]] == [
        "DV-KPI-TASK-005",
        "DV-NE-TYPE-002",
    ]
    assert payload["result_source"] == "offline_deterministic"


def test_v2_web_mode_status_includes_degraded_stage_summary():
    repository = CatalogRepository(V2_ENTITY_PATH)
    repository.load()
    service = EntityLinkingService(
        repository,
        llm_client=MockLLMClient(error_code="llm_timeout"),
    )
    client = create_app(
        service,
        samples_path=V2_QUERY_PATH,
        default_mode="llm_enabled_demo",
    ).test_client()

    response = client.post(
        "/api/link",
        json={
            "query": "Check ALM-51020 and CPU Usage.",
            "mode": "llm_enabled_demo",
            "allow_fallback": True,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == Status.PARTIAL.value
    assert payload["mode_status"]["degraded"] is True
    assert payload["mode_status"]["stage_statuses"][0]["error_code"] == "llm_timeout"
