from __future__ import annotations

import asyncio
import json
from threading import Event

from dv_entity_linking import LinkRequestV1, ModuleConfig, create_entity_linking_module
from dv_entity_linking.domain.ports import (
    EntityBatchGetResponse,
    EntityDataDependencyError,
    EntityDataRecord,
    EntityWordMatch,
    EntityWordMatchResponse,
    ExtractedMention,
)
from dv_entity_linking.module import EntityLinkingModule
from dv_entity_linking.domain.components import LinkingIntentPolicy, SafeTraceBuilder
from dv_entity_linking.infrastructure.entity_data_rest import RestEntityDataClient
from dv_entity_linking.legacy.v3_mock import V3MockEntityDataClient


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


def test_v3_mock_is_only_usable_through_explicit_test_injection() -> None:
    module = EntityLinkingModule(
        data_client=V3MockEntityDataClient.from_paths(
            gauss_mock_path="samples/real/v3_gauss_entities.json",
            redis_mock_path="samples/real/v3_redis_entity_words.json",
        )
    )

    result = module.link(LinkRequestV1(query="Check ALM-51020 and CPU Usage."))

    assert result.contract_version == "v4.link-response.1"
    assert result.status == "linked"
    assert [(item.text, item.entity.entity_id) for item in result.mentions] == [
        ("ALM-51020", "DV-ALM-002"),
        ("CPU Usage", "DV-KPI-MTK-001"),
    ]
    assert [item.span for item in result.mentions] == [(6, 15), (20, 29)]


def test_v4_factory_requires_ir_url_and_platform_client() -> None:
    try:
        create_entity_linking_module()
    except ValueError as exc:
        assert "entity_data_ir_url" in str(exc)
    else:
        raise AssertionError("V4 factory must not enable a legacy mock fallback")

    try:
        create_entity_linking_module(ModuleConfig(entity_data_ir_url="ir://entity-data/service"))
    except ValueError as exc:
        assert "platform_client" in str(exc)
    else:
        raise AssertionError("V4 factory must require the platform client")


def test_v4_factory_applies_health_policy_without_legacy_fallback() -> None:
    class _UnavailablePlatformClient:
        def invoke(self, *, url, payload, timeout_ms):
            raise TimeoutError("service unavailable")

    config = ModuleConfig(entity_data_ir_url="ir://entity-data/service", startup_failure_policy="FAIL_FAST")
    try:
        create_entity_linking_module(config, platform_client=_UnavailablePlatformClient())
    except EntityDataDependencyError as exc:
        assert exc.code == "startup_health_failed"
    else:
        raise AssertionError("FAIL_FAST must reject an unavailable Entity Data IR")

    module = create_entity_linking_module(
        ModuleConfig(entity_data_ir_url="ir://entity-data/service", startup_failure_policy="DEGRADED"),
        platform_client=_UnavailablePlatformClient(),
    )
    result = module.link(LinkRequestV1(query="Check CPU Usage"))
    assert result.status == "dependency_failed"
    assert result.error_code == "startup_health_failed"


def test_v4_component_substitution_preserves_public_response_contract() -> None:
    class _NeverLink(LinkingIntentPolicy):
        def should_link(self, query: str) -> bool:
            return False

    result = EntityLinkingModule(data_client=_FailingClient(), intent_policy=_NeverLink()).link(
        LinkRequestV1(query="Check CPU Usage")
    )
    assert result.contract_version == "v4.link-response.1"
    assert result.status == "not_required"


def test_safe_trace_builder_rejects_raw_objects() -> None:
    builder = SafeTraceBuilder()
    assert builder.stage("word_match", match_count=2) == {"stage": "word_match", "match_count": 2}
    try:
        builder.stage("word_match", raw_response={"secret": "value"})
    except ValueError:
        pass
    else:
        raise AssertionError("safe trace builder must reject raw response objects")


def test_v4_factory_invokes_ir_url_through_the_platform_client() -> None:
    calls: list[tuple[str, dict[str, object], int]] = []

    class _PlatformClient:
        def invoke(self, *, url, payload, timeout_ms):
            calls.append((url, payload, timeout_ms))
            if payload["operation"] == "HEALTH":
                return {
                    "contract_version": "v4.entity-data.1",
                    "operation": "HEALTH",
                    "status": "success",
                    "data_version": "data-1",
                    "data": {"status": "healthy"},
                }
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
    assert [call[0] for call in calls] == ["ir://entity-data/entity-data:execute"] * 3
    assert [call[1]["operation"] for call in calls] == ["HEALTH", "MATCH_WORDS", "BATCH_GET_ENTITIES"]
    assert [call[2] for call in calls] == [321, 321, 321]


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


def test_v4_async_entry_does_not_block_the_event_loop() -> None:
    started = Event()
    release = Event()

    class _BlockingClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            started.set()
            assert release.wait(1)
            return EntityWordMatchResponse(matches=(), data_version="test-v1")

        def batch_get(self, entity_ids, *, expected_data_version=None):
            raise AssertionError("no details expected")

    async def run() -> str:
        task = asyncio.create_task(
            EntityLinkingModule(data_client=_BlockingClient()).link_async(LinkRequestV1(query="Check text"))
        )
        while not started.is_set():
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        release.set()
        return (await task).status

    assert asyncio.run(run()) == "no_match"


def test_v4_unknown_entity_shape_is_retained_and_aggregated_as_partial() -> None:
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

    result = module.link(LinkRequestV1(query="Show CPU Usage for UnknownApp-999."))

    assert result.status == "partial"
    assert [(item.text, item.status) for item in result.mentions] == [
        ("CPU Usage", "linked"),
        ("UnknownApp-999", "no_match"),
    ]
    assert result.mentions[1].no_match_reason


def test_v4_database_miss_does_not_stop_local_recognition_or_fetch_details() -> None:
    calls: list[str] = []

    class _EmptyRecallClient:
        def match_words(self, normalized_query: str, *, entity_types=(), expected_data_version=None):
            calls.append("MATCH_WORDS")
            return EntityWordMatchResponse(matches=(), data_version="test-v1")

        def batch_get(self, entity_ids, *, expected_data_version=None):
            calls.append("BATCH_GET_ENTITIES")
            raise AssertionError("no confirmed candidate must not fetch entity details")

    result = EntityLinkingModule(data_client=_EmptyRecallClient()).link(
        LinkRequestV1(query="Check UnknownApp-999.")
    )

    assert result.status == "no_match"
    assert [(item.text, item.status) for item in result.mentions] == [("UnknownApp-999", "no_match")]
    assert calls == ["MATCH_WORDS"]
    stages = [item["stage"] for item in result.service_trace]
    assert stages.index("local_recognition") < stages.index("word_match") < stages.index("mention_merge")
    assert stages.index("mention_merge") < stages.index("candidate_resolution") < stages.index("entity_batch_get")
    assert result.service_trace[-2]["status"] == "skipped_no_confirmed_candidate"


def test_v4_resolves_candidates_before_fetching_entity_details() -> None:
    first = EntityWordMatch(
        entity_word_id="word-1",
        entity_id="KPI-1",
        entity_type="kpi_meas_type_key",
        entity_word="CPU Usage",
        normalized_key="cpuusage",
        source="entity_name",
    )
    second = EntityWordMatch(
        entity_word_id="word-2",
        entity_id="KPI-2",
        entity_type="kpi_meas_type_key",
        entity_word="CPU Usage",
        normalized_key="cpuusage",
        source="confirmed_alias",
    )

    class _AmbiguousClient:
        def match_words(self, normalized_query: str, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(matches=(first, second), data_version="test-v1")

        def batch_get(self, entity_ids, *, expected_data_version=None):
            assert entity_ids == ("KPI-1", "KPI-2")
            return EntityBatchGetResponse(
                entities=(
                    EntityDataRecord(entity_id="KPI-1", entity_type="kpi_meas_type_key", entity_name="CPU Usage A"),
                    EntityDataRecord(entity_id="KPI-2", entity_type="kpi_meas_type_key", entity_name="CPU Usage B"),
                ),
                missing_ids=(),
                data_version="test-v1",
            )

    result = EntityLinkingModule(data_client=_AmbiguousClient()).link(LinkRequestV1(query="Check CPU Usage"))

    assert result.status == "ambiguous"
    assert [item.entity_id for item in result.mentions[0].candidates] == ["KPI-1", "KPI-2"]
    stages = [item["stage"] for item in result.service_trace]
    assert stages.index("candidate_resolution") < stages.index("entity_batch_get")


def test_v4_dashboard_request_bypasses_data_service() -> None:
    class _NoCallClient:
        def match_words(self, *args, **kwargs):
            raise AssertionError("dashboard request must not recall entity words")

        def batch_get(self, *args, **kwargs):
            raise AssertionError("dashboard request must not get entities")

    result = EntityLinkingModule(data_client=_NoCallClient()).link(
        LinkRequestV1(query="Open the operations dashboard")
    )

    assert result.status == "not_required"
    assert result.bypass_reason


def test_v4_optional_enhancer_failure_falls_back_to_deterministic_result() -> None:
    class _FailingEnhancer:
        def extract(self, query, *, agent_context, entity_types):
            raise TimeoutError("simulated")

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
        ),
        enhancer=_FailingEnhancer(),
    )

    result = module.link(LinkRequestV1(query="Check CPU Usage", extraction_mode="llm"))

    assert result.status == "partial"
    assert result.degraded is True
    assert result.mode_status["fallback_used"] is True


def test_v4_optional_enhancer_output_must_map_to_original_query_span() -> None:
    class _InvalidEnhancer:
        def extract(self, query, *, agent_context, entity_types):
            return (ExtractedMention(text="not in query", span=(0, 2), confidence=0.8),)

    result = EntityLinkingModule(
        data_client=_StaticClient(
            EntityWordMatch(
                entity_word_id="word-1",
                entity_id="KPI-1",
                entity_type="kpi_meas_type_key",
                entity_word="CPU Usage",
                normalized_key="cpuusage",
                source="entity_name",
            )
        ),
        enhancer=_InvalidEnhancer(),
    ).link(LinkRequestV1(query="Check CPU Usage", extraction_mode="llm", allow_fallback=False))

    assert result.status == "dependency_failed"
    assert result.error_code == "extractor_failed"


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
