from __future__ import annotations

import json
from pathlib import Path

import pytest

from dv_entity_linking.legacy.catalog import CatalogRepository
from dv_entity_linking.legacy.datasets import (
    QueryDataset,
    QueryDatasetError,
    QueryDatasetLoader,
    QuerySample,
)
from dv_entity_linking.legacy.evaluation import evaluate_query_dataset
from dv_entity_linking.legacy.llm import MockLLMClient
from dv_entity_linking.legacy.models import DataLayer, ErrorCode, RunMode, Status
from dv_entity_linking.legacy.service import EntityLinkingService
from dv_entity_linking.legacy.web import create_app


REAL_ENTITY_PATH = Path("samples/real/entity_examples.json")
REAL_QUERY_PATH = Path("samples/real/query_samples.json")


@pytest.fixture()
def alarm_catalog() -> CatalogRepository:
    repository = CatalogRepository(
        REAL_ENTITY_PATH,
        allowed_data_layers=[DataLayer.L1_SANITIZED],
    )
    repository.load()
    return repository


@pytest.fixture()
def alarm_service(alarm_catalog: CatalogRepository) -> EntityLinkingService:
    return EntityLinkingService(alarm_catalog)


def test_v1_alarm_catalog_and_query_dataset_load(alarm_catalog):
    dataset = QueryDatasetLoader().load(REAL_QUERY_PATH, alarm_catalog)

    assert alarm_catalog.metadata["schema_version"] == "v1.alarm_entity.2"
    assert len(alarm_catalog.entities) == 9
    assert len(dataset.queries) == 16
    assert {sample.expected_status for sample in dataset.queries} >= {
        Status.LINKED,
        Status.AMBIGUOUS,
        Status.NO_MATCH,
        Status.NOT_REQUIRED,
    }


def test_v1_alarm_startup_dataset_reaches_acceptance_threshold(alarm_catalog, alarm_service):
    dataset = QueryDatasetLoader().load(REAL_QUERY_PATH, alarm_catalog)

    report = evaluate_query_dataset(alarm_service, dataset)

    assert report["schema_version"] == "v1.alarm_evaluation_report.1"
    assert report["summary"]["passed"] is True
    assert report["summary"]["fail"] == 0
    assert report["summary"]["negative_false_positive"] == 0
    assert report["summary"]["precision"] == 1.0
    assert report["summary"]["recall"] == 1.0
    assert report["failures"] == []


def test_v1_evaluator_reports_failure_counts(alarm_service):
    dataset = QueryDataset(
        metadata={"schema_version": "v1.alarm_query.1"},
        queries=[
            QuerySample(
                id="Q-FAIL",
                query="Check ALM-51020 impact.",
                expected_status=Status.LINKED,
                mentions=[],
                expected_entities=[
                    {
                        "entity_id": "DV-ALM-003",
                        "entity_type": "alarm",
                        "mention_text": "ALM-51020",
                    }
                ],
            )
        ],
    )

    report = evaluate_query_dataset(alarm_service, dataset)

    assert report["summary"]["passed"] is False
    assert report["summary"]["fail"] == 1
    assert report["summary"]["fp"] == 1
    assert report["summary"]["fn"] == 1
    assert report["summary"]["precision"] == 0.0
    assert report["summary"]["recall"] == 0.0
    assert report["failures"][0]["id"] == "Q-FAIL"


def test_v1_evaluator_zero_denominator_notes(alarm_service):
    dataset = QueryDataset(metadata={"schema_version": "v1.alarm_query.1"}, queries=[])

    report = evaluate_query_dataset(alarm_service, dataset)

    assert report["summary"]["passed"] is True
    assert report["summary"]["precision"] == 1.0
    assert report["summary"]["recall"] == 1.0
    assert "no_positive_predictions" in report["summary"]["metric_notes"]
    assert "no_expected_positive_cases" in report["summary"]["metric_notes"]


def test_v1_alarm_short_id_substring_guards(alarm_service):
    short_number = alarm_service.link_query("What is alarm 51?")
    partial_id = alarm_service.link_query("Explain ALM-5102.")
    no_alarm_intent = alarm_service.link_query("Open the operations dashboard.")

    assert short_number.status == Status.NO_MATCH
    assert short_number.candidates == []
    assert partial_id.status == Status.NO_MATCH
    assert partial_id.candidates == []
    assert no_alarm_intent.status == Status.NOT_REQUIRED
    assert no_alarm_intent.candidates == []


def test_v1_alarm_ambiguous_phrase_returns_all_expected_candidates(alarm_service):
    result = alarm_service.link_query("What should I do if certificate is about to expire?")

    assert result.status == Status.AMBIGUOUS
    assert {candidate.entity_id for candidate in result.candidates[:5]} >= {
        "DV-ALM-002",
        "DV-ALM-003",
    }
    assert result.linked_entity is None


def test_v1_query_dataset_loader_fails_closed_on_bad_span(tmp_path, alarm_catalog):
    payload = json.loads(REAL_QUERY_PATH.read_text(encoding="utf-8"))
    payload["queries"][0]["mentions"][0]["span"] = [0, 3]
    bad_dataset = tmp_path / "bad_query_samples.json"
    bad_dataset.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryDatasetError) as exc_info:
        QueryDatasetLoader().load(bad_dataset, alarm_catalog)

    assert exc_info.value.error_code == ErrorCode.QUERY_DATASET_LOAD_FAILED
    assert any("span" in error["field"] for error in exc_info.value.errors)


def test_v1_query_dataset_loader_fails_closed_on_inconsistent_expected_ids(tmp_path, alarm_catalog):
    payload = json.loads(REAL_QUERY_PATH.read_text(encoding="utf-8"))
    payload["queries"][0]["mentions"][0]["expected_entity_ids"] = ["DV-ALM-002"]
    bad_dataset = tmp_path / "bad_query_samples.json"
    bad_dataset.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryDatasetError) as exc_info:
        QueryDatasetLoader().load(bad_dataset, alarm_catalog)

    assert any("must equal expected_entities" in error["message"] for error in exc_info.value.errors)


def test_v1_query_dataset_loader_fails_closed_on_bad_query_count(tmp_path, alarm_catalog):
    payload = json.loads(REAL_QUERY_PATH.read_text(encoding="utf-8"))
    payload["metadata"]["query_count"] = 1
    bad_dataset = tmp_path / "bad_query_samples.json"
    bad_dataset.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QueryDatasetError) as exc_info:
        QueryDatasetLoader().load(bad_dataset, alarm_catalog)

    assert any(error["field"] == "metadata.query_count" for error in exc_info.value.errors)


def test_v1_l1_catalog_requires_v1_sanitized_metadata_confirmation(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "metadata": {
                    "schema_version": "not-v1",
                },
                "entities": [
                    {
                        "entity_id": "DV-ALM-X",
                        "entity_type": "alarm",
                        "entity_name": "ALM-123 Example",
                        "alias": ["123", "ALM-123"],
                        "relationships": [],
                        "data_layer": "L1_SANITIZED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    repository = CatalogRepository(catalog_file, allowed_data_layers=[DataLayer.L1_SANITIZED])

    with pytest.raises(Exception) as exc_info:
        repository.load()

    assert getattr(exc_info.value, "error_code", None) == ErrorCode.DATA_LAYER_NOT_CONFIRMED


def test_v1_web_api_validates_mode_and_allow_fallback(alarm_service):
    client = create_app(
        alarm_service,
        samples_path=REAL_QUERY_PATH,
        default_mode=RunMode.OFFLINE_DEMO,
    ).test_client()

    bad_mode = client.post("/api/link", json={"query": "Check ALM-51020 impact.", "mode": "bad"})
    bad_fallback = client.post(
        "/api/link",
        json={"query": "Check ALM-51020 impact.", "allow_fallback": "false"},
    )
    good = client.post(
        "/api/link",
        json={"query": "Check ALM-51020 impact.", "mode": "offline_demo", "allow_fallback": True},
    )

    assert bad_mode.status_code == 400
    assert bad_mode.get_json()["error_code"] == ErrorCode.INVALID_MODE.value
    assert bad_mode.get_json()["result_source"] == "none"
    assert bad_fallback.status_code == 400
    assert bad_fallback.get_json()["error_code"] == ErrorCode.INVALID_ALLOW_FALLBACK.value
    assert good.status_code == 200
    assert good.get_json()["status"] == Status.LINKED.value
    assert good.get_json()["mode_status"]["requested_mode"] == RunMode.OFFLINE_DEMO.value


def test_v1_llm_failure_without_fallback_projects_no_result_source(alarm_catalog):
    service = EntityLinkingService(
        alarm_catalog,
        llm_client=MockLLMClient(error_code=ErrorCode.LLM_HTTP_ERROR),
    )
    client = create_app(service, default_mode=RunMode.LLM_ENABLED_DEMO).test_client()

    response = client.post(
        "/api/link",
        json={
            "query": "Check ALM-51020 impact.",
            "mode": "llm_enabled_demo",
            "allow_fallback": False,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == Status.DEPENDENCY_FAILED.value
    assert payload["mode_status"]["result_source"] == "none"
    assert payload["mode_status"]["allow_fallback"] is False


def test_v1_web_api_catalog_load_failure_does_not_become_no_match(tmp_path):
    catalog_file = tmp_path / "bad_catalog.json"
    catalog_file.write_text(json.dumps({"not_entities": []}), encoding="utf-8")
    service = EntityLinkingService(CatalogRepository(catalog_file))
    client = create_app(service).test_client()

    response = client.post("/api/link", json={"query": "Check ALM-51020 impact."})
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["error_code"] == ErrorCode.CATALOG_LOAD_FAILED.value
    assert payload["status"] == Status.INVALID_INPUT.value
    assert payload["result_source"] == "none"
    assert payload["candidates"] == []


def test_v1_alarm_llm_missing_type_still_uses_short_id_guard(alarm_catalog):
    service = EntityLinkingService(
        alarm_catalog,
        llm_client=MockLLMClient(
            responses_by_task={
                "extract_entities": {
                    "mentions": [
                        {
                            "text": "51",
                            "span": [14, 16],
                        }
                    ]
                }
            }
        ),
    )

    result = service.link_query("What is alarm 51?", mode=RunMode.LLM_ENABLED_DEMO)

    assert result.status == Status.NO_MATCH
    assert result.candidates == []


def test_v1_alarm_llm_fallback_preserves_not_required(alarm_catalog):
    service = EntityLinkingService(
        alarm_catalog,
        llm_client=MockLLMClient(error_code=ErrorCode.LLM_TIMEOUT),
    )

    result = service.link_query(
        "Open the operations dashboard.",
        mode=RunMode.LLM_ENABLED_DEMO,
        allow_fallback=True,
    )

    assert result.status == Status.NOT_REQUIRED
    assert result.candidates == []
    assert result.degraded is True
    assert result.error_code == ErrorCode.LLM_TIMEOUT
