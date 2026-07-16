"""Shared, transport-neutral REST request boundary for V4 and V5."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode


@dataclass(frozen=True)
class RestRequest:
    method: str
    url: str
    params: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    timeout_ms: int = 2_000
    retry_count: int = 0
    idempotency_key: str | None = None


@dataclass(frozen=True)
class RestResponse:
    status_code: int
    body: Any


class RestRequestError(RuntimeError):
    """Safe transport error; details deliberately exclude request secrets."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RestTransport(Protocol):
    def execute(self, request: RestRequest) -> RestResponse: ...


class RestRequestTool:
    """The only shared layer that executes a remote request.

    Adapters provide a declarative request and receive decoded data or a safe
    ``RestRequestError``.  Credentials remain in a transport implementation,
    never in a trace or result object.
    """

    def __init__(self, transport: RestTransport) -> None:
        self._transport = transport

    def execute(self, request: RestRequest) -> RestResponse:
        if request.method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("unsupported REST method")
        if not request.url.strip() or request.timeout_ms <= 0 or request.retry_count < 0:
            raise ValueError("invalid REST request")
        if request.retry_count and request.method.upper() not in {"GET", "HEAD"} and not request.idempotency_key:
            raise ValueError("retryable write requests require an idempotency key")

        for attempt in range(request.retry_count + 1):
            try:
                response = self._transport.execute(request)
            except TimeoutError as exc:
                error = RestRequestError("timeout")
            except PermissionError as exc:
                raise RestRequestError("auth_error") from exc
            except ConnectionError as exc:
                error = RestRequestError("transport_error")
            else:
                if response.status_code in {408, 429} or 500 <= response.status_code <= 599:
                    error = RestRequestError("http_error")
                elif not 200 <= response.status_code < 300:
                    raise RestRequestError("http_error")
                else:
                    return response
            if attempt == request.retry_count:
                raise error
        raise AssertionError("unreachable")


class JsonTextTransport:
    """Adapter helper for transports that return a JSON text payload."""

    @staticmethod
    def decode(body: str) -> dict[str, Any]:
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RestRequestError("schema_error") from exc
        if not isinstance(decoded, dict):
            raise RestRequestError("schema_error")
        return decoded


class UrlopenTransport:
    """Small HTTP transport kept below the shared tool boundary."""

    def __init__(self, opener=urlopen) -> None:
        self._opener = opener

    def execute(self, request: RestRequest) -> RestResponse:
        headers = {"Accept": "application/json", **request.headers}
        data = json.dumps(request.json_body).encode("utf-8") if request.json_body is not None else None
        url = request.url
        if request.params:
            url += ("&" if "?" in url else "?") + urlencode(request.params)
        try:
            with self._opener(Request(url, data=data, headers=headers, method=request.method), timeout=request.timeout_ms / 1000) as response:
                text = response.read().decode("utf-8")
                return RestResponse(getattr(response, "status", 200), JsonTextTransport.decode(text))
        except HTTPError as exc:
            return RestResponse(exc.code, {})
        except URLError as exc:
            raise ConnectionError from exc


class PlatformIrTransport:
    """Adapts the existing platform-owned IR client to the shared tool."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def execute(self, request: RestRequest) -> RestResponse:
        return RestResponse(200, self._client.invoke(url=request.url, payload=request.json_body or {}, timeout_ms=request.timeout_ms))
