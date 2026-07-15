from __future__ import annotations

import json

from dv_entity_linking import LinkRequestV1, ModuleConfig, create_entity_linking_module
from dv_entity_linking.domain.ports import (
    EntityBatchGetResponse,
    EntityDataDependencyError,
    EntityDataRecord,
    EntityWordMatch,
    EntityWordMatchResponse,
)
from dv_entity_linking.module import EntityLinkingModule
from dv_entity_linking.infrastructure.entity_data_rest import RestEntityDataClient


class _StaticClient:
    def __init__(self, match: EntityWordMatch) -> None:
        self.match = match

    def match_words(self, normalized_query: str, *, entity_types=(), expected_data_version=None):
        return EntityWordMatchResponse(matches=(self.match,), data_version="test-v1")

    def batch_get(self, entity_ids, *, expected_data_version=None):
        return EntityBatchGetResponse(
            entities=(
                EntityDataRecord(
                    entity_id=self.match.entity_id,
                    entity_type=self.match.entity_type,
                    entity_name=self.match.entity_word,
                    desc="test entity",
                ),
            ),
            missing_ids=(),
            data_version="test-v1",
        )


class _FailingClient:
    def match_words(self, normalized_query: str, *, entity_types=(), expected_data_version=None):
        raise EntityDataDependencyError("timeout")

    def batch_get(self, entity_ids, *, expected_data_version=None):
        raise AssertionError("batch_get must not run")


def test_v4_public_facade_uses_v3_mock_as_offline_acceptance_adapter() -> None:
    module = create_entity_linking_module()

    result = module.link(LinkRequestV1(query="Check ALM-51020 and CPU Usage."))

    assert result.contract_version == "v4.link-response.1"
    assert result.status == "linked"
    assert [(item.text, item.entity.entity_id) for item in result.mentions] == [
        ("ALM-51020", "DV-ALM-002"),
        ("CPU Usage", "DV-KPI-MTK-001"),
    ]
    assert [item.span for item in result.mentions] == [(6, 15), (20, 29)]


def test_v4_factory_invokes_ir_url_through_the_platform_client() -> None:
    calls: list[tuple[str, dict[str, object], int]] = []

    class _PlatformClient:
        def invoke(self, *, url, payload, timeout_ms):
            calls.append((url, payload, timeout_ms))
            if payload["operation"] == "MATCH_WORDS":
                return {
                    "operation": "MATCH_WORDS",
                    "status": "success",
                    "data_version": "data-1",
                    "data": {"matches": [{"entity_word_id": "word-1", "entity_id": "KPI-1", "entity_type": "metric", "entity_word": "CPU Usage", "normalized_key": "cpuusage", "source": "entity_name"}]},
                }
            return {
                "operation": "BATCH_GET_ENTITIES",
                "status": "success",
                "data_version": "data-1",
                "data": {"missing_ids": [], "entities": [{"entity_id": "KPI-1", "entity_type": "metric", "entity_name": "CPU Usage", "desc": "test", "alias": [], "attributes": {}, "relationships": []}]},
            }

    module = create_entity_linking_module(
        ModuleConfig(entity_data_ir_url="ir://entity-data/entity-data:execute", timeout_ms=321),
        platform_client=_PlatformClient(),
    )

    assert module.link(LinkRequestV1(query="Check CPU Usage")).status == "linked"
    assert [call[0] for call in calls] == ["ir://entity-data/entity-data:execute"] * 2
    assert [call[1]["operation"] for call in calls] == ["MATCH_WORDS", "BATCH_GET_ENTITIES"]
    assert [call[2] for call in calls] == [321, 321]


def test_v4_rest_match_results_restore_original_span_after_whitespace_normalization() -> None:
    module = EntityLinkingModule(
        data_client=_StaticClient(
            EntityWordMatch(
                entity_word_id="word-1",
                entity_id="KPI-1",
                entity_type="kpi_meas_type_key",
                entity_word="CPU Usage",
                normalized_key="cpuusage",
                source="entity_name",
            )
        )
    )

    result = module.link(LinkRequestV1(query="Check CPU  Usage now"))

    assert result.status == "linked"
    assert result.mentions[0].text == "CPU  Usage"
    assert result.mentions[0].span == (6, 16)


def test_v4_context_required_word_does_not_link_without_context_keyword() -> None:
    module = EntityLinkingModule(
        data_client=_StaticClient(
            EntityWordMatch(
                entity_word_id="word-1",
                entity_id="DB-1",
                entity_type="database_tablespace",
                entity_word="SYSTEM",
                normalized_key="system",
                source="entity_name",
                match_mode="CONTEXT_REQUIRED",
                min_context_required=True,
                context_keywords=("tablespace",),
            )
        )
    )

    assert module.link(LinkRequestV1(query="Show system health")).status == "no_match"
    assert module.link(LinkRequestV1(query="Show SYSTEM tablespace usage")).status == "linked"


def test_v4_dependency_failure_is_not_projected_as_no_match() -> None:
    result = EntityLinkingModule(data_client=_FailingClient()).link(LinkRequestV1(query="Check CPU Usage"))

    assert result.status == "dependency_failed"
    assert result.error_code == "timeout"
    assert result.degraded is True


def test_v4_rest_client_uses_one_word_match_and_one_batch_get_call() -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    class _Response:
        def __init__(self, payload) -> None:
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request, *, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        requests.append((request.full_url, payload))
        if payload["operation"] == "MATCH_WORDS":
            return _Response(
                {
                    "contract_version": "v1",
                    "operation": "MATCH_WORDS",
                    "status": "success",
                    "data_version": "data-1",
                    "data": {"matches": [{"entity_word_id": "word-1", "entity_id": "KPI-1", "entity_type": "kpi_meas_type_key", "entity_word": "CPU Usage", "normalized_key": "cpuusage", "source": "entity_name"}]},
                }
            )
        return _Response(
            {
                "contract_version": "v1",
                "operation": "BATCH_GET_ENTITIES",
                "status": "success",
                "data_version": "data-1",
                "data": {"missing_ids": [], "entities": [{"entity_id": "KPI-1", "entity_type": "kpi_meas_type_key", "entity_name": "CPU Usage", "desc": "test entity", "alias": [], "attributes": {}, "relationships": []}]},
            }
        )

    module = EntityLinkingModule(
        data_client=RestEntityDataClient("https://entity-data.example", opener=opener)
    )

    result = module.link(LinkRequestV1(query="Check CPU Usage"))

    assert result.status == "linked"
    assert [url.rsplit("/", 1)[-1] for url, _ in requests] == ["entity-data:execute", "entity-data:execute"]
    assert [payload["operation"] for _, payload in requests] == ["MATCH_WORDS", "BATCH_GET_ENTITIES"]
    assert requests[0][1]["payload"]["normalized_query"] == "checkcpuusage"
    assert requests[1][1]["payload"]["entity_ids"] == ["KPI-1"]


def test_v4_rest_client_write_uses_the_same_endpoint_with_an_idempotency_key() -> None:
    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "contract_version": "v1",
                    "operation": "UPSERT_ENTITY",
                    "status": "success",
                    "data_version": "data-2",
                    "data": {"entity_id": "KPI-1"},
                }
            ).encode("utf-8")

    def opener(request, *, timeout):
        captured.update(json.loads(request.data.decode("utf-8")))
        return _Response()

    client = RestEntityDataClient("https://entity-data.example", opener=opener)
    result = client.upsert_entity(
        {"entity_id": "KPI-1", "entity_name": "CPU Usage"}, request_id="request-1"
    )

    assert result.data_version == "data-2"
    assert captured["operation"] == "UPSERT_ENTITY"
    assert captured["request_id"] == "request-1"
