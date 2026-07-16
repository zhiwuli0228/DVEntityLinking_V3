from __future__ import annotations

import pytest

from dv_entity_linking.infrastructure.rest_tool import RestRequest, RestRequestError, RestRequestTool, RestResponse


class _Transport:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_shared_rest_tool_retries_idempotent_request() -> None:
    transport = _Transport([TimeoutError(), RestResponse(200, {"ok": True})])
    response = RestRequestTool(transport).execute(RestRequest("GET", "https://example.invalid", retry_count=1))
    assert response.body == {"ok": True}
    assert transport.calls == 2


def test_shared_rest_tool_rejects_retried_write_without_idempotency_key() -> None:
    with pytest.raises(ValueError, match="idempotency"):
        RestRequestTool(_Transport([])).execute(RestRequest("POST", "https://example.invalid", retry_count=1))


def test_shared_rest_tool_returns_safe_error_code() -> None:
    with pytest.raises(RestRequestError) as exc:
        RestRequestTool(_Transport([PermissionError("secret-token")])).execute(RestRequest("GET", "https://example.invalid"))
    assert exc.value.code == "auth_error"
    assert "secret" not in str(exc.value)
