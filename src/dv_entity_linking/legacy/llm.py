"""LLM adapter abstractions used by extraction and linking."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ErrorCode


class LLMError(RuntimeError):
    def __init__(self, error_code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class LLMResult:
    data: dict[str, Any]
    usage: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openai_compatible"
    enabled: bool = False
    model: str = "qwen3.6-27b"
    base_url: str = ""
    api_key_env: str = "DVEL_LLM_API_KEY"
    timeout_seconds: float = 20.0

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "")

    @classmethod
    def from_file(cls, path: str | Path) -> "LLMConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            provider=str(payload.get("provider", "openai_compatible")),
            enabled=bool(payload.get("enabled", False)),
            model=str(payload.get("model", "qwen3.6-27b")),
            base_url=str(payload.get("base_url", "")),
            api_key_env=str(payload.get("api_key_env", "DVEL_LLM_API_KEY")),
            timeout_seconds=float(payload.get("timeout_seconds", 20.0)),
        )


class LLMClient:
    def complete_json(
        self,
        task: str,
        messages: list[dict[str, str]],
        schema_name: str,
    ) -> LLMResult:
        raise NotImplementedError


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_json(
        self,
        task: str,
        messages: list[dict[str, str]],
        schema_name: str,
    ) -> LLMResult:
        if not self.config.enabled:
            raise LLMError(ErrorCode.DEPENDENCY_FAILED, "llm is disabled")
        if not self.config.base_url:
            raise LLMError(ErrorCode.DEPENDENCY_FAILED, "llm base_url is empty")
        api_key = self.config.api_key
        if not api_key:
            raise LLMError(ErrorCode.LLM_AUTH_ERROR, f"missing env var {self.config.api_key_env}")

        body = {
            "model": self.config.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "metadata": {"task": task, "schema_name": schema_name},
        }
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except (TimeoutError, socket.timeout) as exc:
            raise LLMError(ErrorCode.LLM_TIMEOUT, "llm request timed out") from exc
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise LLMError(ErrorCode.LLM_AUTH_ERROR, f"llm auth failed: {exc.code}") from exc
            raise LLMError(ErrorCode.LLM_HTTP_ERROR, f"llm http error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(ErrorCode.LLM_HTTP_ERROR, str(exc.reason)) from exc

        try:
            payload = json.loads(raw)
            content = payload["choices"][0]["message"]["content"]
            data = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "llm response is not valid JSON") from exc
        if not isinstance(data, dict):
            raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "llm JSON content must be an object")
        return LLMResult(data=data, usage=payload.get("usage"))


class MockLLMClient(LLMClient):
    """Deterministic LLM test double."""

    def __init__(
        self,
        *,
        response: dict[str, Any] | None = None,
        responses_by_task: dict[str, dict[str, Any]] | None = None,
        error_code: ErrorCode | str | None = None,
        error_codes_by_task: dict[str, ErrorCode | str] | None = None,
    ) -> None:
        self.response = response or {"mentions": []}
        self.responses_by_task = responses_by_task or {}
        self.error_code = ErrorCode(error_code) if error_code else None
        self.error_codes_by_task = {
            task: ErrorCode(code) for task, code in (error_codes_by_task or {}).items()
        }

    def complete_json(
        self,
        task: str,
        messages: list[dict[str, str]],
        schema_name: str,
    ) -> LLMResult:
        error_code = self.error_codes_by_task.get(task) or self.error_code
        if error_code:
            raise LLMError(error_code, f"mock llm failure: {error_code.value}")
        return LLMResult(data=self.responses_by_task.get(task, self.response), usage={"mock": True})
