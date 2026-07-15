"""Direct HTTP adapter retained only for local standalone development and contract tests."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..domain.ports import (
    EntityBatchGetResponse,
    EntityDataDependencyError,
    EntityDataRecord,
    EntityDataOperation,
    EntityDataWriteResponse,
    EntityWordMatch,
    EntityWordMatchResponse,
)


class RestEntityDataClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_ms: int = 2_000,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        if not base_url.strip():
            raise ValueError("data service base_url must not be empty")
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_ms / 1000
        self._opener = opener

    def match_words(
        self,
        normalized_query: str,
        *,
        entity_types: tuple[str, ...] = (),
        expected_data_version: str | None = None,
    ) -> EntityWordMatchResponse:
        payload = self._execute(
            EntityDataOperation.MATCH_WORDS,
            {
                "normalized_query": normalized_query,
                "entity_types": list(entity_types),
                "expected_data_version": expected_data_version,
            },
        )
        matches = payload.get("matches")
        data_version = payload.get("data_version")
        if not isinstance(matches, list) or not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid word-match response")
        try:
            records = tuple(
                EntityWordMatch(
                    entity_word_id=str(item["entity_word_id"]),
                    entity_id=str(item["entity_id"]),
                    entity_type=str(item["entity_type"]),
                    entity_word=str(item["entity_word"]),
                    normalized_key=str(item["normalized_key"]),
                    source=str(item["source"]),
                    match_mode=str(item.get("match_mode", "EXACT_WORD")),
                    min_context_required=bool(item.get("min_context_required", False)),
                    context_keywords=tuple(str(value) for value in item.get("context_keywords", [])),
                    priority=int(item.get("priority", 0)),
                )
                for item in matches
                if isinstance(item, dict)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EntityDataDependencyError("schema_error", "invalid word-match record") from exc
        if len(records) != len(matches):
            raise EntityDataDependencyError("schema_error", "word-match record must be object")
        return EntityWordMatchResponse(
            matches=records,
            data_version=data_version,
            contract_version=str(payload.get("contract_version", "v4.entity-data.1")),
        )

    def batch_get(
        self,
        entity_ids: tuple[str, ...],
        *,
        expected_data_version: str | None = None,
    ) -> EntityBatchGetResponse:
        payload = self._execute(
            EntityDataOperation.BATCH_GET_ENTITIES,
            {"entity_ids": list(entity_ids), "expected_data_version": expected_data_version},
        )
        entities = payload.get("entities")
        missing_ids = payload.get("missing_ids", [])
        data_version = payload.get("data_version")
        if not isinstance(entities, list) or not isinstance(missing_ids, list) or not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid batch-get response")
        try:
            records = tuple(
                EntityDataRecord(
                    entity_id=str(item["entity_id"]),
                    entity_type=str(item["entity_type"]),
                    entity_name=str(item["entity_name"]),
                    alias=tuple(str(value) for value in item.get("alias", [])),
                    desc=str(item["desc"]),
                    attributes=dict(item.get("attributes", {})),
                    relationships=tuple(dict(value) for value in item.get("relationships", [])),
                )
                for item in entities
                if isinstance(item, dict)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EntityDataDependencyError("schema_error", "invalid entity record") from exc
        if len(records) != len(entities):
            raise EntityDataDependencyError("schema_error", "entity record must be object")
        return EntityBatchGetResponse(
            entities=records,
            missing_ids=tuple(str(value) for value in missing_ids),
            data_version=data_version,
            contract_version=str(payload.get("contract_version", "v4.entity-data.1")),
        )

    def upsert_entity(self, entity: dict[str, Any], *, request_id: str) -> EntityDataWriteResponse:
        """Create or update an entity; the remote service rebuilds its word projection atomically."""
        if not request_id.strip():
            raise ValueError("request_id must not be empty for a write operation")
        payload = self._execute(
            EntityDataOperation.UPSERT_ENTITY,
            {"entity": entity},
            request_id=request_id,
        )
        return self._write_response(EntityDataOperation.UPSERT_ENTITY, payload, request_id)

    def delete_entity(self, entity_id: str, *, request_id: str) -> EntityDataWriteResponse:
        if not entity_id.strip() or not request_id.strip():
            raise ValueError("entity_id and request_id must not be empty")
        payload = self._execute(
            EntityDataOperation.DELETE_ENTITY,
            {"entity_id": entity_id},
            request_id=request_id,
        )
        return self._write_response(EntityDataOperation.DELETE_ENTITY, payload, request_id)

    def rebuild_entity_words(
        self, *, entity_ids: tuple[str, ...] = (), request_id: str
    ) -> EntityDataWriteResponse:
        if not request_id.strip():
            raise ValueError("request_id must not be empty for a write operation")
        payload = self._execute(
            EntityDataOperation.REBUILD_ENTITY_WORDS,
            {"entity_ids": list(entity_ids)},
            request_id=request_id,
        )
        return self._write_response(EntityDataOperation.REBUILD_ENTITY_WORDS, payload, request_id)

    @staticmethod
    def _write_response(
        operation: EntityDataOperation, payload: dict[str, Any], request_id: str
    ) -> EntityDataWriteResponse:
        data_version = payload.get("data_version")
        if not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid write response")
        return EntityDataWriteResponse(operation=operation, data_version=data_version, request_id=request_id)

    def _execute(
        self,
        operation: EntityDataOperation,
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        envelope: dict[str, Any] = {
            "contract_version": "v1",
            "operation": operation.value,
            "payload": payload,
        }
        if request_id is not None:
            envelope["request_id"] = request_id
        request = Request(
            f"{self._base_url}/v1/entity-data:execute",
            data=json.dumps(envelope).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            code = "auth_error" if exc.code in {401, 403} else "http_error"
            raise EntityDataDependencyError(code) from exc
        except URLError as exc:
            raise EntityDataDependencyError("transport_error") from exc
        except TimeoutError as exc:
            raise EntityDataDependencyError("timeout") from exc
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise EntityDataDependencyError("schema_error", "response is not JSON") from exc
        if not isinstance(decoded, dict):
            raise EntityDataDependencyError("schema_error", "response root must be object")
        if decoded.get("operation") != operation.value or decoded.get("status") != "success":
            raise EntityDataDependencyError("schema_error", "invalid operation response")
        data = decoded.get("data")
        data_version = decoded.get("data_version")
        if not isinstance(data, dict) or not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid response envelope")
        return {**data, "data_version": data_version, "contract_version": decoded.get("contract_version")}
