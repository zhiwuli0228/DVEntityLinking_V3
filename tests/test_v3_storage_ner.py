from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dv_entity_linking.legacy.models import ErrorCode, RunMode, Status, StorageLookupStatus
from dv_entity_linking.legacy.service import EntityLinkingService
from dv_entity_linking.legacy.storage import (
    EntityStorageRepository,
    StorageError,
    normalize_entity_word,
)
from dv_entity_linking.legacy.web import create_app


V3_GAUSS_PATH = Path("samples/real/v3_gauss_entities.json")
V3_REDIS_PATH = Path("samples/real/v3_redis_entity_words.json")


def _v3_service() -> EntityLinkingService:
    return EntityLinkingService.from_v3_mock(
        gauss_mock_path=V3_GAUSS_PATH,
        redis_mock_path=V3_REDIS_PATH,
    )


def test_v3_storage_repository_loads_two_layers():
    repository = EntityStorageRepository.load_from_paths(V3_GAUSS_PATH, V3_REDIS_PATH)

    assert repository.ready is True
    assert repository.startup_report.entity_count == 7
    assert repository.startup_report.word_count == 11
    word_result, entity_result = repository.lookup(" ALM-51020 ")

    assert normalize_entity_word("ＣＰＵ Usage") == "cpuusage"
    assert word_result.status == StorageLookupStatus.HIT
    assert word_result.entity_id == "DV-ALM-002"
    assert entity_result.status == StorageLookupStatus.HIT
    assert entity_result.entity_record.entity_name.startswith("ALM-51020")


def test_v3_gauss_duplicate_entity_id_fails_closed(tmp_path):
    gauss_payload = json.loads(V3_GAUSS_PATH.read_text(encoding="utf-8"))
    gauss_payload["entities"][1]["entity_id"] = gauss_payload["entities"][0]["entity_id"]
    gauss_path = tmp_path / "gauss.json"
    gauss_path.write_text(json.dumps(gauss_payload), encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        EntityStorageRepository.load_from_paths(gauss_path, V3_REDIS_PATH)

    assert exc_info.value.report.errors[0]["error_code"] == "duplicate_entity_id"


def test_v3_gauss_missing_required_field_fails_closed(tmp_path):
    gauss_payload = json.loads(V3_GAUSS_PATH.read_text(encoding="utf-8"))
    del gauss_payload["entities"][0]["desc"]
    gauss_path = tmp_path / "gauss.json"
    gauss_path.write_text(json.dumps(gauss_payload), encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        EntityStorageRepository.load_from_paths(gauss_path, V3_REDIS_PATH)

    assert exc_info.value.report.errors[0]["error_code"] == "missing_required_field"


def test_v3_gauss_legacy_fields_and_dangling_relationship_fail_closed(tmp_path):
    legacy_payload = json.loads(V3_GAUSS_PATH.read_text(encoding="utf-8"))
    legacy = legacy_payload["entities"][0]
    legacy["canonical_name"] = legacy.pop("entity_name")
    legacy["aliases"] = legacy.pop("alias")
    legacy["description"] = legacy.pop("desc")
    legacy_path = tmp_path / "gauss-legacy.json"
    legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    with pytest.raises(StorageError) as legacy_error:
        EntityStorageRepository.load_from_paths(legacy_path, V3_REDIS_PATH)

    assert legacy_error.value.report.errors[0]["error_code"] == "missing_required_field"

    dangling_payload = json.loads(V3_GAUSS_PATH.read_text(encoding="utf-8"))
    dangling_payload["entities"][0]["relationships"] = [
        {"relation_type": "monitors", "target_entity_id": "MISSING"}
    ]
    dangling_path = tmp_path / "gauss-dangling.json"
    dangling_path.write_text(json.dumps(dangling_payload), encoding="utf-8")

    with pytest.raises(StorageError) as dangling_error:
        EntityStorageRepository.load_from_paths(dangling_path, V3_REDIS_PATH)

    assert any(error["error_code"] == "dangling_entity_id" for error in dangling_error.value.report.errors)


def test_v3_redis_duplicate_key_conflict_fails_closed(tmp_path):
    gauss = {
        "metadata": {
            "schema_version": "v3.gauss_entities.1",
            "entity_count": 2,
            "source": "confirmed_sample",
        },
        "entities": [
            {
                "entity_id": "E-1",
                "entity_type": "alarm",
                "entity_name": "Entity One",
                "alias": ["Shared-Key"],
                "desc": "Entity one.",
                "attributes": {},
                "relationships": [],
            },
            {
                "entity_id": "E-2",
                "entity_type": "alarm",
                "entity_name": "Entity Two",
                "alias": ["Shared-Key"],
                "desc": "Entity two.",
                "attributes": {},
                "relationships": [],
            },
        ],
    }
    redis = {
        "metadata": {
            "schema_version": "v3.redis_entity_words.1",
            "normalization_version": "v3.entity_word_norm.1",
            "key_scope": ["entity_name", "confirmed_alias"],
            "alias_auto_generated": False,
            "word_count": 2,
        },
        "entity_words": [
            {
                "entity_word": "Shared-Key",
                "normalized_key": "shared-key",
                "entity_id": "E-1",
                "source": "confirmed_alias",
            },
            {
                "entity_word": "Shared-Key",
                "normalized_key": "shared-key",
                "entity_id": "E-2",
                "source": "confirmed_alias",
            },
        ],
    }
    gauss_path = tmp_path / "gauss.json"
    redis_path = tmp_path / "redis.json"
    gauss_path.write_text(json.dumps(gauss), encoding="utf-8")
    redis_path.write_text(json.dumps(redis), encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        EntityStorageRepository.load_from_paths(gauss_path, redis_path)

    assert exc_info.value.report.errors[0]["error_code"] == "duplicate_key"


def test_v3_redis_dangling_entity_id_fails_closed(tmp_path):
    gauss_payload = json.loads(V3_GAUSS_PATH.read_text(encoding="utf-8"))
    redis_payload = json.loads(V3_REDIS_PATH.read_text(encoding="utf-8"))
    redis_payload["entity_words"][0]["entity_id"] = "DV-MISSING"
    gauss_path = tmp_path / "gauss.json"
    redis_path = tmp_path / "redis.json"
    gauss_path.write_text(json.dumps(gauss_payload), encoding="utf-8")
    redis_path.write_text(json.dumps(redis_payload), encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        EntityStorageRepository.load_from_paths(gauss_path, redis_path)

    assert exc_info.value.report.errors[0]["error_code"] == "dangling_entity_id"


def test_v3_redis_key_scope_metadata_fails_closed(tmp_path):
    gauss_payload = json.loads(V3_GAUSS_PATH.read_text(encoding="utf-8"))
    redis_payload = json.loads(V3_REDIS_PATH.read_text(encoding="utf-8"))
    redis_payload["metadata"]["key_scope"] = ["auto_generated_alias"]
    gauss_path = tmp_path / "gauss.json"
    redis_path = tmp_path / "redis.json"
    gauss_path.write_text(json.dumps(gauss_payload), encoding="utf-8")
    redis_path.write_text(json.dumps(redis_payload), encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        EntityStorageRepository.load_from_paths(gauss_path, redis_path)

    assert exc_info.value.report.errors[0]["field"] == "metadata.key_scope"
    assert exc_info.value.report.errors[0]["error_code"] == "unconfirmed_data_layer"


def test_v3_ner_pipeline_links_and_exposes_storage_trace():
    service = _v3_service()

    result = service.link_query("Check ALM-51020 and CPU Usage.")

    assert result.status == Status.LINKED
    assert [item.linked_entity.entity_id for item in result.mention_results] == [
        "DV-ALM-002",
        "DV-KPI-MTK-001",
    ]
    assert [item.storage_lookup["redis_status"] for item in result.mention_results] == [
        "hit",
        "hit",
    ]
    assert {item["stage"] for item in result.stage_trace} >= {
        "query_validation",
        "mention_detection",
        "storage_lookup",
        "status_aggregation",
    }


def test_v3_ner_pipeline_partial_no_match_and_not_required():
    service = _v3_service()

    partial = service.link_query("Show CPU Usage for CloudHost-VM-1-1-000000.")
    not_required = service.link_query("Open the operations dashboard.")
    no_match = service.link_query("Show metrics for UnknownApp-999.")

    assert partial.status == Status.PARTIAL
    assert [item.status for item in partial.mention_results] == [
        Status.LINKED,
        Status.NO_MATCH,
    ]
    assert partial.mention_results[1].storage_lookup["redis_status"] == "miss"
    assert not_required.status == Status.NOT_REQUIRED
    assert not_required.mention_results == []
    assert no_match.status == Status.NO_MATCH
    assert no_match.mention_results[0].storage_lookup["normalized_key"] == "unknownapp-999"


def test_v3_ner_pipeline_blank_query_is_invalid_input():
    service = _v3_service()

    result = service.link_query("   ")

    assert result.status == Status.INVALID_INPUT
    assert result.error_code == ErrorCode.INVALID_INPUT
    assert result.stage_trace[0]["stage"] == "query_validation"
    assert result.stage_trace[0]["error_code"] == "invalid_input"


def test_v3_web_api_uses_storage_backed_projection():
    service = _v3_service()
    client = create_app(
        service,
        samples_path="samples/real/v3_ner_golden_cases.json",
    ).test_client()

    status = client.get("/api/status").get_json()
    linked = client.post(
        "/api/link",
        json={"query": "Run Network quality monitoring for onlinecharging_docker."},
    ).get_json()

    assert status["catalog_loaded"] is True
    assert status["entity_count"] == 7
    assert linked["status"] == "linked"
    assert [item["linked_entity"]["entity_id"] for item in linked["mention_results"]] == [
        "DV-KPI-TASK-005",
        "DV-NE-TYPE-002",
    ]
    assert linked["stage_trace"]
    assert linked["mention_results"][0]["storage_lookup"]["gauss_status"] == "hit"

    entity_detail = client.get("/api/entities/DV-ALM-002").get_json()
    assert entity_detail["entity_name"].startswith("ALM-51020")
    assert entity_detail["relationships"] == [
        {"relation_type": "monitors", "target_entity_id": "DV-KPI-MTK-001"}
    ]
    assert "canonical_name" not in entity_detail


def test_v3_web_api_does_not_claim_llm_used_without_llm_stage():
    service = _v3_service()
    service.configure_llm_client(object())  # V3 currently keeps LLM as a future optional stage.
    client = create_app(
        service,
        samples_path="samples/real/v3_ner_golden_cases.json",
        default_mode=RunMode.LLM_ENABLED_DEMO,
    ).test_client()

    linked = client.post(
        "/api/link",
        json={
            "query": "Check ALM-51020 and CPU Usage.",
            "mode": "llm_enabled_demo",
            "allow_fallback": True,
        },
    ).get_json()

    assert linked["status"] == "linked"
    assert linked["mode_status"]["llm_enabled"] is True
    assert linked["mode_status"]["llm_used"] is False
    assert "llm" not in {item["stage"] for item in linked["stage_trace"]}


def test_v3_evaluation_and_smoke_scripts_run_offline():
    evaluation = subprocess.run(
        [sys.executable, "scripts/run_v3_evaluation.py"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    smoke = subprocess.run(
        [sys.executable, "scripts/run_v3_acceptance_smoke.py"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    eval_payload = json.loads(evaluation.stdout)
    smoke_payload = json.loads(smoke.stdout)

    assert eval_payload["schema_version"] == "v3.ner_storage_evaluation_report.1"
    assert eval_payload["summary"]["passed"] is True
    assert eval_payload["summary"]["precision"] == 1.0
    assert eval_payload["summary"]["recall"] == 1.0
    assert smoke_payload["ok"] is True
    assert smoke_payload["linked_storage_redis_statuses"] == ["hit", "hit"]
