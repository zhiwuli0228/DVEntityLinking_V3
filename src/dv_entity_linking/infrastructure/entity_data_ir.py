"""Entity Data Service adapter using the host platform's internal-route client."""

from __future__ import annotations

from typing import Any

from ..domain.ports import (
    EntityDataDependencyError,
    EntityDataOperation,
    InternalRouteClient,
)
from .entity_data_base import EntityDataClientBase


class IrEntityDataClient(EntityDataClientBase):
    """Primary production adapter: invoke an IR URL through a platform-owned client."""

    def __init__(
        self,
        ir_url: str,
        *,
        platform_client: InternalRouteClient,
        timeout_ms: int = 2_000,
    ) -> None:
        if not ir_url.strip():
            raise ValueError("entity data IR URL must not be empty")
        self._ir_url = ir_url
        self._platform_client = platform_client
        self._timeout_ms = timeout_ms

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
        try:
            decoded = self._platform_client.invoke(
                url=self._ir_url,
                payload=envelope,
                timeout_ms=self._timeout_ms,
            )
        except PermissionError as exc:
            raise EntityDataDependencyError("auth_error") from exc
        except TimeoutError as exc:
            raise EntityDataDependencyError("timeout") from exc
        except ConnectionError as exc:
            raise EntityDataDependencyError("transport_error") from exc
        if not isinstance(decoded, dict):
            raise EntityDataDependencyError("schema_error", "response root must be object")
        if decoded.get("operation") != operation.value or decoded.get("status") != "success":
            raise EntityDataDependencyError("schema_error", "invalid operation response")
        data = decoded.get("data")
        data_version = decoded.get("data_version")
        if not isinstance(data, dict) or not isinstance(data_version, str):
            raise EntityDataDependencyError("schema_error", "invalid response envelope")
        return {**data, "data_version": data_version, "contract_version": decoded.get("contract_version")}
