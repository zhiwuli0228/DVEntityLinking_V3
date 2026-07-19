"""Production-contract-compatible HTTP facade for the performance mock."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from .mysql_source import (
    EntityBatch,
    MockDataStats,
    SourceUnavailable,
    WordMatchBatch,
)


class EntityDataMockSource(Protocol):
    def health(self) -> str: ...

    def match_words(
        self,
        normalized_query: str,
        *,
        entity_types: Sequence[str] = (),
    ) -> WordMatchBatch: ...

    def batch_get(self, entity_ids: Sequence[str]) -> EntityBatch: ...

    def stats(self) -> MockDataStats: ...


class MockRequestError(ValueError):
    def __init__(self, code: str, *, operation: str = "UNKNOWN") -> None:
        super().__init__(code)
        self.code = code
        self.operation = operation


class DVAIAgentServiceMock:
    """Transport-neutral operation handler for the remote-interface mock."""

    contract_version = "v1"

    def __init__(self, source: EntityDataMockSource) -> None:
        self._source = source

    @staticmethod
    def _payload(envelope: dict[str, Any], operation: str) -> dict[str, Any]:
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise MockRequestError("invalid_payload", operation=operation)
        return payload

    @staticmethod
    def _assert_expected_version(
        expected: Any,
        actual: str,
        *,
        operation: str,
    ) -> None:
        if expected is not None and (not isinstance(expected, str) or expected != actual):
            raise MockRequestError("data_version_mismatch", operation=operation)

    def execute(self, envelope: Any) -> dict[str, Any]:
        if not isinstance(envelope, dict):
            raise MockRequestError("invalid_envelope")
        operation = envelope.get("operation")
        if not isinstance(operation, str):
            raise MockRequestError("invalid_operation")
        if envelope.get("contract_version") != self.contract_version:
            raise MockRequestError("unsupported_contract", operation=operation)
        payload = self._payload(envelope, operation)

        if operation == "HEALTH":
            data_version = self._source.health()
            return self._success(
                operation,
                data_version,
                {
                    "status": "healthy",
                    "contract_version": "v4.entity-data.1",
                },
            )

        if operation == "MATCH_WORDS":
            normalized_query = payload.get("normalized_query")
            entity_types = payload.get("entity_types", [])
            if not isinstance(normalized_query, str) or not isinstance(entity_types, list):
                raise MockRequestError("invalid_match_words_request", operation=operation)
            if any(not isinstance(value, str) for value in entity_types):
                raise MockRequestError("invalid_match_words_request", operation=operation)
            try:
                result = self._source.match_words(
                    normalized_query,
                    entity_types=entity_types,
                )
            except ValueError as exc:
                raise MockRequestError("invalid_match_words_request", operation=operation) from exc
            self._assert_expected_version(
                payload.get("expected_data_version"),
                result.data_version,
                operation=operation,
            )
            return self._success(
                operation,
                result.data_version,
                {"matches": list(result.matches)},
            )

        if operation == "BATCH_GET_ENTITIES":
            entity_ids = payload.get("entity_ids")
            if not isinstance(entity_ids, list) or any(
                not isinstance(value, str) for value in entity_ids
            ):
                raise MockRequestError("invalid_batch_get_request", operation=operation)
            try:
                result = self._source.batch_get(entity_ids)
            except ValueError as exc:
                raise MockRequestError("invalid_batch_get_request", operation=operation) from exc
            self._assert_expected_version(
                payload.get("expected_data_version"),
                result.data_version,
                operation=operation,
            )
            return self._success(
                operation,
                result.data_version,
                {
                    "entities": list(result.entities),
                    "missing_ids": list(result.missing_ids),
                },
            )

        raise MockRequestError("unsupported_operation", operation=operation)

    def stats(self) -> dict[str, Any]:
        stats = self._source.stats()
        return {
            "status": "healthy",
            "data_version": stats.data_version,
            "entity_count": stats.entity_count,
            "entity_word_count": stats.entity_word_count,
            "match_strategy": stats.match_strategy,
            "matcher_data_version": stats.matcher_data_version,
            "matcher_pattern_count": stats.matcher_pattern_count,
            "matcher_build_seconds": stats.matcher_build_seconds,
            "matcher_size_bytes": stats.matcher_size_bytes,
        }

    def _success(
        self,
        operation: str,
        data_version: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "operation": operation,
            "status": "success",
            "data_version": data_version,
            "data": data,
        }


def _error_envelope(code: str, operation: str) -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "operation": operation,
        "status": "error",
        "error": {"code": code},
    }


def create_mock_app(source: EntityDataMockSource):
    """Create the optional Flask adapter without importing Flask in core paths."""

    try:
        from flask import Flask, jsonify, request
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Flask is required; install dv-entity-linking[performance-mock]"
        ) from exc

    app = Flask("dv_entity_data_performance_mock")
    service = DVAIAgentServiceMock(source)

    @app.post("/v1/entity-data:execute")
    def execute_entity_data():
        envelope = request.get_json(silent=True)
        try:
            return jsonify(service.execute(envelope)), 200
        except MockRequestError as exc:
            status = 409 if exc.code == "data_version_mismatch" else 400
            return jsonify(_error_envelope(exc.code, exc.operation)), status
        except SourceUnavailable as exc:
            return jsonify(_error_envelope(str(exc), "UNKNOWN")), 503
        except Exception:
            return jsonify(_error_envelope("mock_internal_error", "UNKNOWN")), 500

    @app.get("/healthz")
    def health():
        try:
            return jsonify(service.stats()), 200
        except SourceUnavailable as exc:
            return jsonify({"status": "unavailable", "error_code": str(exc)}), 503

    @app.get("/timings")
    def timings():
        drain = getattr(source, "drain_timings", None)
        captured = drain() if callable(drain) else []
        return jsonify({"timings": captured}), 200

    return app
