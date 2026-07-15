from __future__ import annotations

import json

from dv_entity_linking.legacy.catalog import CatalogRepository
from dv_entity_linking.legacy.linking import EntityLinker
from dv_entity_linking.legacy.llm import MockLLMClient
from dv_entity_linking.legacy.models import (
    DataLayer,
    EntityMention,
    EntityType,
    ErrorCode,
    MentionSource,
    RunMode,
    Status,
)
from dv_entity_linking.legacy.service import EntityLinkingService


class RecordingLLMClient(MockLLMClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = []

    def complete_json(self, task, messages, schema_name):
        self.calls.append(
            {
                "task": task,
                "messages": messages,
                "schema_name": schema_name,
            }
        )
        return super().complete_json(task, messages, schema_name)


def test_exact_query_links_to_entity(service):
    result = service.link_query("查看 DV RAN Site Alpha 的状态")

    assert result.status == Status.LINKED
    assert result.mention_results[0].linked_entity.entity_id == "NE-DV-RAN-001"
    assert result.mention_results[0].candidates[0].confidence >= 0.95


def test_alias_query_links_to_entity(service):
    result = service.link_query("RAN-A1 的 ASR 最近如何")

    entity_ids = {
        item.linked_entity.entity_id
        for item in result.mention_results
        if item.linked_entity
    }
    assert {"NE-DV-RAN-001", "KPI-ACCESS-SUCCESS"} <= entity_ids


def test_multi_entity_query_returns_mention_level_results(service):
    result = service.link_query("DV RAN Site Alpha 的链路断告警和接入成功率一起看")

    assert result.status == Status.LINKED
    assert len(result.mention_results) >= 3
    assert all(item.mention.text for item in result.mention_results)
    assert any(item.linked_entity and item.linked_entity.entity_id == "ALM-LINK-DOWN" for item in result.mention_results)


def test_fuzzy_mention_returns_ordered_candidates(catalog):
    mention = EntityMention(
        text="DV RAN Site Alfa",
        span=None,
        predicted_type=EntityType.NETWORK_RESOURCE,
        source=MentionSource.DETERMINISTIC,
    )

    result = EntityLinker(catalog).link("DV RAN Site Alfa", [mention])
    candidates = result.mention_results[0].candidates
    confidences = [candidate.confidence for candidate in candidates]

    assert candidates
    assert candidates[0].entity_id == "NE-DV-RAN-001"
    assert candidates[0].match_reason == "fuzzy text similarity"
    assert all(0.0 <= confidence <= 1.0 for confidence in confidences)
    assert confidences == sorted(confidences, reverse=True)


def test_ambiguous_query_returns_ambiguous(service):
    result = service.link_query("CP01 是什么告警")

    assert result.status == Status.AMBIGUOUS
    assert result.mention_results[0].status == Status.AMBIGUOUS
    assert len(result.mention_results[0].candidates) >= 2


def test_no_match_query_returns_reason(service):
    result = service.link_query("查询不存在的 Gamma 虚拟设备")

    assert result.status == Status.NO_MATCH
    assert result.no_match_reason


def test_empty_query_returns_invalid_input(service):
    result = service.link_query("   ")

    assert result.status == Status.INVALID_INPUT
    assert result.error_code == ErrorCode.INVALID_INPUT
    assert result.no_match_reason == "query is empty"


def test_llm_failure_falls_back_with_error_code(catalog):
    service = EntityLinkingService(
        catalog,
        llm_client=MockLLMClient(error_code=ErrorCode.LLM_AUTH_ERROR),
    )

    result = service.link_query("RAN-A1 的 ASR 最近如何", mode=RunMode.LLM_ENABLED_DEMO)

    assert result.degraded is True
    assert result.error_code == ErrorCode.LLM_AUTH_ERROR
    assert result.status == Status.PARTIAL


def test_llm_fallback_error_codes_are_preserved(catalog):
    for error_code in [
        ErrorCode.LLM_TIMEOUT,
        ErrorCode.LLM_HTTP_ERROR,
        ErrorCode.LLM_AUTH_ERROR,
        ErrorCode.LLM_SCHEMA_ERROR,
    ]:
        service = EntityLinkingService(catalog, llm_client=MockLLMClient(error_code=error_code))

        result = service.link_query("RAN-A1 的 ASR 最近如何", mode=RunMode.LLM_ENABLED_DEMO)

        assert result.degraded is True
        assert result.error_code == error_code
        assert result.status == Status.PARTIAL


def test_llm_schema_error_from_bad_mention_response_falls_back(catalog):
    service = EntityLinkingService(catalog, llm_client=MockLLMClient(response={"bad": []}))

    result = service.link_query("RAN-A1 的 ASR 最近如何", mode=RunMode.LLM_ENABLED_DEMO)

    assert result.degraded is True
    assert result.error_code == ErrorCode.LLM_SCHEMA_ERROR
    assert result.status == Status.PARTIAL


def test_llm_extraction_prompt_declares_json_schema(catalog):
    llm_client = RecordingLLMClient(
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

    result = service.link_query("RAN-A1 状态", mode=RunMode.LLM_ENABLED_DEMO)

    extract_call = next(call for call in llm_client.calls if call["task"] == "extract_entities")
    assert result.status == Status.LINKED
    assert extract_call["schema_name"] == "EntityMentionList"
    assert "valid JSON object" in extract_call["messages"][0]["content"]
    assert "EntityMentionList" in extract_call["messages"][0]["content"]


def test_llm_dependency_failed_when_fallback_disabled(catalog):
    service = EntityLinkingService(
        catalog,
        llm_client=MockLLMClient(error_code=ErrorCode.LLM_HTTP_ERROR),
    )

    result = service.link_query(
        "RAN-A1 的 ASR 最近如何",
        mode=RunMode.LLM_ENABLED_DEMO,
        allow_fallback=False,
    )

    assert result.status == Status.DEPENDENCY_FAILED
    assert result.error_code == ErrorCode.DEPENDENCY_FAILED
    assert result.degraded is True


def test_llm_disambiguates_ambiguous_candidate(catalog):
    service = EntityLinkingService(
        catalog,
        llm_client=MockLLMClient(
            responses_by_task={
                "extract_entities": {
                    "mentions": [
                        {
                            "text": "CP01",
                            "predicted_type": "alarm_event",
                        }
                    ]
                },
                "disambiguate_entity": {
                    "selected_entity_id": "ALM-CP01-POWER",
                    "confidence": 0.88,
                    "disambiguation_reason": "power context selected",
                },
            }
        ),
    )

    result = service.link_query("CP01 是什么告警", mode=RunMode.LLM_ENABLED_DEMO)

    assert result.status == Status.LINKED
    assert result.mention_results[0].linked_entity.entity_id == "ALM-CP01-POWER"
    assert result.mention_results[0].source == "llm+catalog"


def test_llm_disambiguation_prompt_declares_json_schema_and_candidates(catalog):
    llm_client = RecordingLLMClient(
        responses_by_task={
            "extract_entities": {
                "mentions": [
                    {
                        "text": "CP01",
                        "predicted_type": "alarm_event",
                    }
                ]
            },
            "disambiguate_entity": {
                "selected_entity_id": "ALM-CP01-POWER",
                "confidence": 0.88,
                "disambiguation_reason": "power context selected",
            },
        }
    )
    service = EntityLinkingService(catalog, llm_client=llm_client)

    result = service.link_query("CP01 是什么告警", mode=RunMode.LLM_ENABLED_DEMO)

    disambiguate_call = next(
        call for call in llm_client.calls if call["task"] == "disambiguate_entity"
    )
    assert result.status == Status.LINKED
    assert disambiguate_call["schema_name"] == "EntityDisambiguation"
    assert "valid JSON object" in disambiguate_call["messages"][0]["content"]
    assert "selected_entity_id" in disambiguate_call["messages"][0]["content"]
    assert "ALM-CP01-CONTROL" in disambiguate_call["messages"][1]["content"]
    assert "ALM-CP01-POWER" in disambiguate_call["messages"][1]["content"]


def test_llm_disambiguation_failure_marks_top_level_degraded(catalog):
    service = EntityLinkingService(
        catalog,
        llm_client=MockLLMClient(
            responses_by_task={
                "extract_entities": {
                    "mentions": [
                        {
                            "text": "CP01",
                            "predicted_type": "alarm_event",
                        }
                    ]
                }
            },
            error_codes_by_task={"disambiguate_entity": ErrorCode.LLM_TIMEOUT},
        ),
    )

    result = service.link_query("CP01 是什么告警", mode=RunMode.LLM_ENABLED_DEMO)

    assert result.status == Status.AMBIGUOUS
    assert result.degraded is True
    assert result.error_code == ErrorCode.LLM_TIMEOUT
    assert result.mention_results[0].degraded is True


def test_llm_disambiguation_rejects_non_candidate_selection(catalog):
    service = EntityLinkingService(
        catalog,
        llm_client=MockLLMClient(
            responses_by_task={
                "extract_entities": {
                    "mentions": [
                        {
                            "text": "CP01",
                            "predicted_type": "alarm_event",
                        }
                    ]
                },
                "disambiguate_entity": {
                    "selected_entity_id": "NE-DV-RAN-001",
                    "confidence": 0.95,
                    "disambiguation_reason": "invalid non-candidate selection",
                },
            }
        ),
    )

    result = service.link_query("CP01 是什么告警", mode=RunMode.LLM_ENABLED_DEMO)

    assert result.status == Status.AMBIGUOUS
    assert result.degraded is True
    assert result.error_code == ErrorCode.LLM_SCHEMA_ERROR
    assert result.mention_results[0].linked_entity is None


def test_non_l0_ambiguous_result_reports_candidate_data_layer(tmp_path):
    confirmation = tmp_path / "confirm.md"
    confirmation.write_text("confirmed", encoding="utf-8")
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "entity_id": "L1-A",
                        "entity_type": "alarm_event",
                        "entity_name": "CP01 Control",
                        "alias": ["CP01"],
                        "relationships": [],
                        "data_layer": "L1_SANITIZED",
                        "source": "user_sanitized_sample",
                    },
                    {
                        "entity_id": "L1-B",
                        "entity_type": "alarm_event",
                        "entity_name": "CP01 Power",
                        "alias": ["CP01"],
                        "relationships": [],
                        "data_layer": "L1_SANITIZED",
                        "source": "user_sanitized_sample",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    repository = CatalogRepository(
        catalog_file,
        allowed_data_layers=[DataLayer.L1_SANITIZED],
        data_layer_confirmation_path=confirmation,
    )
    repository.load()
    service = EntityLinkingService(repository)

    result = service.link_query("CP01")

    assert result.status == Status.AMBIGUOUS
    assert result.data_layer == DataLayer.L1_SANITIZED
    assert result.mention_results[0].data_layer == DataLayer.L1_SANITIZED
