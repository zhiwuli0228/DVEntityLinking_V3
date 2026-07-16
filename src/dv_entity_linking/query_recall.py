"""Versionless external query-recall facade over the compatible linker."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from threading import RLock
from typing import Any, Protocol

from .application.dto import LinkRequestV1, LinkResponseV1


@dataclass(frozen=True)
class QueryRecallRequest:
    query: str
    use_llm: bool | None = None
    top_k: int | None = None


@dataclass(frozen=True)
class QueryCandidate:
    entity_id: str
    entity_name: str
    entity_type: str
    confidence: float
    rank: int
    match_reason: str


@dataclass(frozen=True)
class QueryMention:
    text: str
    span: tuple[int, int]
    status: str
    candidates: tuple[QueryCandidate, ...] = ()
    entity_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class QueryRecallResult:
    query: str
    status: str
    mentions: tuple[QueryMention, ...] = ()
    candidates: tuple[QueryCandidate, ...] = ()
    top_entity_id: str | None = None
    error_code: str | None = None
    degraded: bool = False


@dataclass(frozen=True)
class RecallPolicy:
    use_llm: bool = False
    top_k: int = 3
    allow_fallback: bool = True
    entity_types: tuple[str, ...] = ()


class RecallConfigProvider:
    """Atomically retains the last valid JSON configuration."""

    def __init__(self, path: str | Path, *, default: RecallPolicy = RecallPolicy()) -> None:
        self._path = Path(path)
        self._policy = default
        self._mtime_ns: int | None = None
        self._lock = RLock()
        self.last_error: str | None = None
        self.reload(force=True)

    @property
    def policy(self) -> RecallPolicy:
        with self._lock:
            return self._policy

    def reload(self, *, force: bool = False) -> bool:
        try:
            mtime_ns = self._path.stat().st_mtime_ns
            if not force and mtime_ns == self._mtime_ns:
                return False
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            recall = raw["recall"]
            policy = RecallPolicy(
                use_llm=bool(recall.get("use_llm", False)),
                top_k=int(recall.get("top_k", 3)),
                allow_fallback=bool(recall.get("allow_fallback", True)),
                entity_types=tuple(str(value) for value in recall.get("entity_types", ())),
            )
            if policy.top_k < 1 or policy.top_k > 100:
                raise ValueError("top_k out of range")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.last_error = "recall_config_reload_failed"
            return False
        with self._lock:
            self._policy, self._mtime_ns, self.last_error = policy, mtime_ns, None
        return True


class CompatibleLinker(Protocol):
    def link(self, request: LinkRequestV1) -> LinkResponseV1: ...


class QueryRecallFacade:
    def __init__(self, linker: CompatibleLinker, config: RecallConfigProvider) -> None:
        self._linker = linker
        self._config = config

    def recall(self, query: str, *, use_llm: bool | None = None, top_k: int | None = None) -> QueryRecallResult:
        # Always validate the small policy file before a new request.  This
        # avoids timestamp-resolution gaps on filesystems used by local hosts.
        self._config.reload(force=True)
        policy = self._config.policy
        if top_k is not None and not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        request = LinkRequestV1(
            query=query,
            entity_types=policy.entity_types,
            extraction_mode="llm" if (policy.use_llm if use_llm is None else use_llm) else "disabled",
            allow_fallback=policy.allow_fallback,
        )
        return self._project(self._linker.link(request), top_k or policy.top_k)

    @staticmethod
    def _project(response: LinkResponseV1, top_k: int) -> QueryRecallResult:
        def candidate(value: Any) -> QueryCandidate:
            return QueryCandidate(value.entity_id, value.entity_name, value.entity_type, value.confidence, value.rank, value.match_reason)
        mentions = tuple(
            QueryMention(
                text=item.text, span=item.span, status=item.status,
                candidates=tuple(candidate(value) for value in item.candidates[:top_k]),
                entity_id=item.entity.entity_id if item.entity else None, reason=item.reason,
            ) for item in response.mentions
        )
        candidates = tuple(candidate(value) for value in response.candidates[:top_k])
        return QueryRecallResult(response.query, response.status, mentions, candidates,
                                 response.mentions[0].entity.entity_id if len(response.mentions) == 1 and response.mentions[0].entity else None,
                                 response.error_code, response.degraded)
