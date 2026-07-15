from __future__ import annotations

import json
import os

from dv_entity_linking.legacy.catalog import CatalogRepository
from dv_entity_linking.legacy.llm import MockLLMClient
from dv_entity_linking.legacy.models import DataLayer
from dv_entity_linking.legacy.models import EntityRecord
from dv_entity_linking.legacy.models import EntityType
from dv_entity_linking.legacy.models import ErrorCode
from dv_entity_linking.legacy.models import RunMode
from dv_entity_linking.legacy.service import EntityLinkingService
from dv_entity_linking.legacy.web import create_app


def test_web_api_smoke(service):
    client = create_app(service).test_client()

    status = client.get("/api/status")
    assert status.status_code == 200
    assert status.get_json()["catalog_loaded"] is True
    assert status.get_json()["llm_config"]["runtime_configurable"] is True

    samples = client.get("/api/samples")
    assert samples.status_code == 200
    assert samples.get_json()["queries"]

    all_entities = client.get("/api/entities?limit=200")
    assert all_entities.status_code == 200
    assert len(all_entities.get_json()["items"]) >= 20

    entities = client.get("/api/entities?q=RAN-A1")
    assert entities.status_code == 200
    assert entities.get_json()["items"][0]["entity_id"] == "NE-DV-RAN-001"

    link = client.post("/api/link", json={"query": "RAN-A1 的 ASR 最近如何"})
    assert link.status_code == 200
    assert link.get_json()["mention_results"]

    retrieve = client.post("/api/retrieve", json={"entity_id": "NE-DV-RAN-001", "k": 5})
    assert retrieve.status_code == 200
    assert retrieve.get_json()["items"]


def test_web_app_can_default_to_llm_enabled_demo(catalog):
    llm_client = MockLLMClient(
        responses_by_task={
            "extract_entities": {
                "mentions": [
                    {
                        "text": "RAN-A1",
                        "predicted_type": "network_resource",
                    }
                ]
            }
        }
    )
    service = EntityLinkingService(catalog, llm_client=llm_client)
    client = create_app(service, default_mode=RunMode.LLM_ENABLED_DEMO).test_client()

    status = client.get("/api/status").get_json()
    link = client.post("/api/link", json={"query": "RAN-A1 的 ASR 最近如何"}).get_json()

    assert status["mode"] == RunMode.LLM_ENABLED_DEMO.value
    assert status["llm_enabled"] is True
    assert link["status"] == "linked"
    assert link["mention_results"][0]["mention"]["source"] == "llm"


def test_web_spa_shell_served_from_dist(service, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<!doctype html><div id="root"></div>', encoding="utf-8")
    client = create_app(service, frontend_dist=dist).test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<div id="root">' in html


def test_web_spa_returns_503_when_dist_missing(service, tmp_path):
    dist = tmp_path / "does-not-exist"
    client = create_app(service, frontend_dist=dist).test_client()

    response = client.get("/")

    assert response.status_code == 503
    assert b"npm run build" in response.data


def test_web_api_link_exposes_workbench_safe_projection(service):
    client = create_app(service).test_client()

    payload = client.post(
        "/api/link",
        json={"query": "RAN-A1 的 ASR 最近如何", "mode": "offline_demo"},
    ).get_json()

    mention_result = payload["mention_results"][0]
    mention = mention_result["mention"]

    assert mention["text"] == "RAN-A1"
    assert mention["span"]
    assert mention["predicted_type"]
    assert mention_result["status"] == "linked"
    assert mention_result["linked_entity"]["entity_id"] == "NE-DV-RAN-001"
    assert mention_result["candidates"]
    assert "llm_explanations" in payload
    assert any(item["context_type"] == "mention" for item in payload["llm_explanations"])
    assert any(item["context_type"] == "candidate" for item in payload["llm_explanations"])
    assert "attributes" not in json.dumps(payload)


def test_web_entity_detail_uses_safe_attributes(service):
    client = create_app(service).test_client()

    payload = client.get("/api/entities/ALM-LINK-DOWN").get_json()

    assert payload["entity_id"] == "ALM-LINK-DOWN"
    assert payload["attributes_safe"] == [
        {"key": "severity", "value": "major", "source": "catalog"}
    ]
    assert payload["omitted_attribute_count"] == 1
    assert "mock_field" not in json.dumps(payload)


def test_web_entity_detail_omits_forbidden_attributes_and_values(catalog):
    catalog._entities["UNSAFE-ATTRIBUTES"] = EntityRecord(
        entity_id="UNSAFE-ATTRIBUTES",
        entity_type=EntityType.KPI_TASK_NAME,
        entity_name="Unsafe Attributes Regression",
        desc="Regression record for fail-closed attribute projection.",
        attributes={
            "severity": "critical",
            "api_key": "sk-secret-leak",
            "category": "token-like category value",
            "raw_response": '{"authorization":"Bearer test"}',
        },
        data_layer=DataLayer.L0_SYNTHETIC,
        source="test_catalog",
    )
    client = create_app(EntityLinkingService(catalog)).test_client()

    payload = client.get("/api/entities/UNSAFE-ATTRIBUTES").get_json()
    serialized = json.dumps(payload)

    assert payload["attributes_safe"] == [
        {"key": "severity", "value": "critical", "source": "catalog"}
    ]
    assert payload["omitted_attribute_count"] == 3
    assert "attributes" not in payload
    assert "api_key" not in serialized
    assert "sk-secret-leak" not in serialized
    assert "token-like category value" not in serialized
    assert "raw_response" not in serialized


def test_web_api_negative_states_do_not_emit_pseudo_entities(service):
    client = create_app(service).test_client()

    no_match = client.post(
        "/api/link",
        json={"query": "Show metrics for UnknownApp-999.", "mode": "offline_demo"},
    ).get_json()
    not_required = client.post(
        "/api/link",
        json={"query": "Open the operations dashboard.", "mode": "offline_demo"},
    ).get_json()

    assert no_match["status"] == "no_match"
    assert no_match["linked_entity"] is None
    assert no_match["candidates"] == []
    assert no_match["mention_results"][0]["no_candidate_reason"]

    assert not_required["status"] == "not_required"
    assert not_required["linked_entity"] is None
    assert not_required["candidates"] == []
    assert not_required["mention_results"] == []
    assert not_required["bypass_reason"]


def test_web_llm_config_can_be_updated_from_frontend(monkeypatch, service):
    monkeypatch.delenv("DVEL_WEB_LLM_API_KEY", raising=False)
    client = create_app(service).test_client()

    initial = client.get("/api/llm/config").get_json()
    assert initial["enabled"] is False
    assert initial["base_url_configured"] is False

    missing_key = client.post(
        "/api/llm/config",
        json={
            "enabled": True,
            "model": "qwen3.6-27b",
            "base_url": "http://127.0.0.1:8000/v1",
            "timeout_seconds": 3,
        },
    )
    assert missing_key.status_code == 400
    assert missing_key.get_json()["error_code"] == ErrorCode.INVALID_INPUT.value

    response = client.post(
        "/api/llm/config",
        json={
            "enabled": True,
            "model": "qwen3.6-27b",
            "base_url": "http://127.0.0.1:8000/v1",
            "api_key": "local-test-key",
            "timeout_seconds": 3,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["enabled"] is True
    assert payload["model"] == "qwen3.6-27b"
    assert payload["base_url_configured"] is True
    assert payload["api_key_configured"] is True
    assert "local-test-key" not in json.dumps(payload)
    assert os.environ["DVEL_WEB_LLM_API_KEY"] == "local-test-key"
    assert service.llm_client is not None
    assert client.get("/api/status").get_json()["llm_enabled"] is True

    disabled = client.post("/api/llm/config", json={"enabled": False}).get_json()
    assert disabled["enabled"] is False
    assert service.llm_client is None


def test_web_link_empty_query_returns_invalid_input(service):
    client = create_app(service).test_client()

    response = client.post("/api/link", json={"query": ""})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "invalid_input"
    assert payload["error_code"] == ErrorCode.INVALID_INPUT.value


def test_web_status_returns_structured_catalog_error(tmp_path):
    catalog_file = tmp_path / "bad_catalog.json"
    catalog_file.write_text(json.dumps({"not_entities": []}), encoding="utf-8")
    repository = CatalogRepository(catalog_file)
    client = create_app(EntityLinkingService(repository)).test_client()

    response = client.get("/api/status")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["error_code"] == ErrorCode.CATALOG_LOAD_FAILED.value
    assert payload["errors"]
