"""End-to-end V4 acceptance through an IR URL and a mocked remote entity-data service."""

from __future__ import annotations

from typing import Any

from dv_entity_linking import LinkRequestV1, ModuleConfig, create_entity_linking_module
from dv_entity_linking.domain.ports import CandidateRerankDecision


class MockEntityDataService:
    """A contract-faithful remote-service double; no module internals are called directly."""

    data_version = "mock-data-v1"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.words = (
            {
                "entity_word_id": "word-alarm-1",
                "entity_id": "DV-ALM-002",
                "entity_type": "alarm",
                "entity_word": "ALM-51020",
                "normalized_key": "alm-51020",
                "source": "entity_name",
                "match_mode": "STRUCTURED_TOKEN",
            },
            {
                "entity_word_id": "word-kpi-1",
                "entity_id": "DV-KPI-MTK-001",
                "entity_type": "kpi_meas_type_key",
                "entity_word": "CPU Usage",
                "normalized_key": "cpuusage",
                "source": "entity_name",
                "match_mode": "EXACT_WORD",
            },
        )
        self.entities = {
            "DV-ALM-002": {
                "entity_id": "DV-ALM-002",
                "entity_type": "alarm",
                "entity_name": "ALM-51020 CPU High",
                "alias": ["51020"],
                "desc": "CPU alarm",
                "attributes": {},
                "relationships": [],
            },
            "DV-KPI-MTK-001": {
                "entity_id": "DV-KPI-MTK-001",
                "entity_type": "kpi_meas_type_key",
                "entity_name": "CPU Usage",
                "alias": [],
                "desc": "CPU metric",
                "attributes": {},
                "relationships": [],
            },
        }

    def invoke(self, *, url: str, payload: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
        assert url == "ir://entity-data/entity-data:execute"
        assert payload["contract_version"] == "v1"
        self.calls.append({"operation": payload["operation"], "payload": payload["payload"], "timeout_ms": timeout_ms})
        if payload["operation"] == "HEALTH":
            return self._success("HEALTH", {"status": "healthy"})
        if payload["operation"] == "MATCH_WORDS":
            query = payload["payload"]["normalized_query"]
            allowed_types = set(payload["payload"]["entity_types"])
            matches = [
                word
                for word in self.words
                if word["normalized_key"] in query
                and (not allowed_types or word["entity_type"] in allowed_types)
            ]
            return self._success("MATCH_WORDS", {"matches": matches})
        if payload["operation"] == "BATCH_GET_ENTITIES":
            ids = payload["payload"]["entity_ids"]
            assert payload["payload"]["expected_data_version"] == self.data_version
            return self._success(
                "BATCH_GET_ENTITIES",
                {
                    "entities": [self.entities[entity_id] for entity_id in ids if entity_id in self.entities],
                    "missing_ids": [entity_id for entity_id in ids if entity_id not in self.entities],
                },
            )
        raise AssertionError(f"unexpected operation: {payload['operation']}")

    def _success(self, operation: str, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "contract_version": "v1",
            "operation": operation,
            "status": "success",
            "data_version": self.data_version,
            "data": data,
        }


def _module(service: MockEntityDataService, **kwargs):
    return create_entity_linking_module(
        ModuleConfig(entity_data_ir_url="ir://entity-data/entity-data:execute", timeout_ms=456),
        platform_client=service,
        **kwargs,
    )


def test_v4_ir_end_to_end_links_multiple_remote_entities() -> None:
    service = MockEntityDataService()

    result = _module(service).link(LinkRequestV1(query="Check ALM-51020 and CPU Usage."))

    assert result.status == "linked"
    assert [(item.text, item.entity.entity_id) for item in result.mentions] == [
        ("ALM-51020", "DV-ALM-002"),
        ("CPU Usage", "DV-KPI-MTK-001"),
    ]
    assert [call["operation"] for call in service.calls] == ["HEALTH", "MATCH_WORDS", "BATCH_GET_ENTITIES"]
    assert service.calls[1]["payload"]["normalized_query"] == "checkalm-51020andcpuusage."
    assert all(call["timeout_ms"] == 456 for call in service.calls)


def test_v4_ir_end_to_end_keeps_unknown_mention_and_returns_partial() -> None:
    service = MockEntityDataService()

    result = _module(service).link(LinkRequestV1(query="Show CPU Usage for UnknownApp-999."))

    assert result.status == "partial"
    assert [(item.text, item.status) for item in result.mentions] == [
        ("CPU Usage", "linked"),
        ("UnknownApp-999", "no_match"),
    ]
    assert [call["operation"] for call in service.calls] == ["HEALTH", "MATCH_WORDS", "BATCH_GET_ENTITIES"]


def test_v4_ir_end_to_end_not_required_does_not_call_remote_service() -> None:
    service = MockEntityDataService()

    result = _module(service).link(LinkRequestV1(query="Open the operations dashboard."))

    assert result.status == "not_required"
    assert [call["operation"] for call in service.calls] == ["HEALTH"]


def test_v4_ir_end_to_end_maps_service_error_to_dependency_failure() -> None:
    class _TimeoutService(MockEntityDataService):
        def invoke(self, *, url, payload, timeout_ms):
            if payload["operation"] == "MATCH_WORDS":
                raise TimeoutError("remote unavailable")
            return super().invoke(url=url, payload=payload, timeout_ms=timeout_ms)

    result = _module(_TimeoutService()).link(LinkRequestV1(query="Check CPU Usage"))
    assert result.status == "dependency_failed"
    assert result.error_code == "timeout"


def test_v4_ir_end_to_end_rejects_cross_version_detail_response() -> None:
    class _VersionMismatchService(MockEntityDataService):
        def invoke(self, *, url, payload, timeout_ms):
            response = super().invoke(url=url, payload=payload, timeout_ms=timeout_ms)
            if payload["operation"] == "BATCH_GET_ENTITIES":
                response["data_version"] = "unexpected-version"
            return response

    result = _module(_VersionMismatchService()).link(LinkRequestV1(query="Check CPU Usage"))
    assert result.status == "dependency_failed"
    assert result.error_code == "entity_miss"


def test_v4_ir_end_to_end_preserves_cross_type_top_k_after_bad_rerank() -> None:
    class _BadReranker:
        def rerank(self, query, *, mention_text, candidates, agent_context):
            return CandidateRerankDecision("invented", 0.99, "invalid")

    service = MockEntityDataService()
    service.words = (*service.words, {**service.words[1], "entity_word_id": "word-alarm-cpu", "entity_id": "DV-ALM-002", "entity_type": "alarm"})
    result = _module(service, reranker=_BadReranker()).link(
        LinkRequestV1(query="Check CPU Usage", extraction_mode="llm", allow_fallback=False)
    )
    assert result.status == "ambiguous"
    assert [candidate.entity_id for candidate in result.mentions[0].candidates] == ["DV-ALM-002", "DV-KPI-MTK-001"]
