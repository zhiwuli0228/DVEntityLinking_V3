"""Transport-neutral read-side implementation of the Entity Data client contract."""

from __future__ import annotations

from typing import Any

from ..domain.ports import (
    EntityBatchGetResponse,
    EntityDataDependencyError,
    EntityDataHealth,
    EntityDataOperation,
    EntityDataRecord,
    EntityWordMatch,
    EntityWordMatchResponse,
)


class EntityDataClientBase:
    """Shared response validation for platform-IR and test-only HTTP adapters."""

    def _execute(self, operation: EntityDataOperation, payload: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def health(self) -> EntityDataHealth:
        payload = self._execute(EntityDataOperation.HEALTH, {"client_contract_version": "v4.entity-data.1"})
        if payload.get("status") != "healthy" or not isinstance(payload.get("data_version"), str) or not isinstance(payload.get("contract_version"), str):
            raise EntityDataDependencyError("health_unavailable", "invalid health response")
        return EntityDataHealth("healthy", payload["data_version"], payload["contract_version"])

    def match_words(self, normalized_query: str, *, entity_types: tuple[str, ...] = (), expected_data_version: str | None = None) -> EntityWordMatchResponse:
        payload = self._execute(EntityDataOperation.MATCH_WORDS, {"normalized_query": normalized_query, "entity_types": list(entity_types), "expected_data_version": expected_data_version})
        matches, data_version = payload.get("matches"), payload.get("data_version")
        if not isinstance(matches, list) or not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid word-match response")
        try:
            records = tuple(EntityWordMatch(
                entity_word_id=str(item["entity_word_id"]), entity_id=str(item["entity_id"]), entity_type=str(item["entity_type"]),
                entity_word=str(item["entity_word"]), normalized_key=str(item["normalized_key"]), source=str(item["source"]),
                match_mode=str(item.get("match_mode", "EXACT_WORD")), min_context_required=bool(item.get("min_context_required", False)),
                context_keywords=tuple(str(value) for value in item.get("context_keywords", [])), priority=int(item.get("priority", 0)),
            ) for item in matches if isinstance(item, dict))
        except (KeyError, TypeError, ValueError) as exc:
            raise EntityDataDependencyError("schema_error", "invalid word-match record") from exc
        if len(records) != len(matches):
            raise EntityDataDependencyError("schema_error", "word-match record must be object")
        return EntityWordMatchResponse(records, data_version, str(payload.get("contract_version", "v4.entity-data.1")))

    def batch_get(self, entity_ids: tuple[str, ...], *, expected_data_version: str | None = None) -> EntityBatchGetResponse:
        payload = self._execute(EntityDataOperation.BATCH_GET_ENTITIES, {"entity_ids": list(entity_ids), "expected_data_version": expected_data_version})
        entities, missing_ids, data_version = payload.get("entities"), payload.get("missing_ids", []), payload.get("data_version")
        if not isinstance(entities, list) or not isinstance(missing_ids, list) or not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid batch-get response")
        try:
            records = tuple(EntityDataRecord(
                entity_id=str(item["entity_id"]), entity_type=str(item["entity_type"]), entity_name=str(item["entity_name"]),
                alias=tuple(str(value) for value in item.get("alias", [])), desc=str(item["desc"]), attributes=dict(item.get("attributes", {})),
                relationships=tuple(dict(value) for value in item.get("relationships", [])),
            ) for item in entities if isinstance(item, dict))
        except (KeyError, TypeError, ValueError) as exc:
            raise EntityDataDependencyError("schema_error", "invalid entity record") from exc
        if len(records) != len(entities):
            raise EntityDataDependencyError("schema_error", "entity record must be object")
        return EntityBatchGetResponse(records, tuple(str(value) for value in missing_ids), data_version, str(payload.get("contract_version", "v4.entity-data.1")))
