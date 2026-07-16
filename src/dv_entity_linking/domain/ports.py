"""Ports used by the V4 application layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class EntityDataOperation(str, Enum):
    """Operations accepted by the single Entity Data Service endpoint."""

    MATCH_WORDS = "MATCH_WORDS"
    BATCH_GET_ENTITIES = "BATCH_GET_ENTITIES"
    UPSERT_ENTITY = "UPSERT_ENTITY"
    DELETE_ENTITY = "DELETE_ENTITY"
    REBUILD_ENTITY_WORDS = "REBUILD_ENTITY_WORDS"
    HEALTH = "HEALTH"


class InternalRouteClient(Protocol):
    """Platform-owned client used to invoke a published internal-route URL."""

    def invoke(
        self,
        *,
        url: str,
        payload: dict[str, Any],
        timeout_ms: int,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ExtractedMention:
    text: str
    span: tuple[int, int]
    predicted_type: str | None = None
    confidence: float = 0.0
    source: str = "enhancer"


class EntityExtractionEnhancer(Protocol):
    """Optional LLM/rule enhancement; it never creates a confirmed entity ID."""

    def extract(
        self,
        query: str,
        *,
        agent_context: dict[str, Any],
        entity_types: tuple[str, ...],
    ) -> tuple[ExtractedMention, ...]: ...


@dataclass(frozen=True)
class RerankCandidate:
    """Safe, pre-detail candidate evidence supplied to an optional reranker."""

    entity_id: str
    entity_type: str
    entity_word: str
    match_reason: str
    confidence: float


@dataclass(frozen=True)
class CandidateRerankDecision:
    """A reranker may select only one ID that was supplied in its candidate set."""

    selected_entity_id: str
    confidence: float
    reason: str


class CandidateReranker(Protocol):
    """Optional LLM reranker for an already ambiguous, confirmed candidate set."""

    def rerank(
        self,
        query: str,
        *,
        mention_text: str,
        candidates: tuple[RerankCandidate, ...],
        agent_context: dict[str, Any],
    ) -> CandidateRerankDecision: ...


class EntityDataDependencyError(RuntimeError):
    """A safe, structured dependency failure from the entity data service."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class EntityDataHealth:
    """Safe lifecycle information exposed by the Entity Data service."""

    status: str
    data_version: str
    contract_version: str


@dataclass(frozen=True)
class EntityWordMatch:
    entity_word_id: str
    entity_id: str
    entity_type: str
    entity_word: str
    normalized_key: str
    source: str
    match_mode: str = "EXACT_WORD"
    min_context_required: bool = False
    context_keywords: tuple[str, ...] = ()
    priority: int = 0


@dataclass(frozen=True)
class EntityWordMatchResponse:
    matches: tuple[EntityWordMatch, ...]
    data_version: str
    contract_version: str = "v4.entity-data.1"


@dataclass(frozen=True)
class EntityDataRecord:
    entity_id: str
    entity_type: str
    entity_name: str
    alias: tuple[str, ...] = ()
    desc: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    relationships: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class EntityBatchGetResponse:
    entities: tuple[EntityDataRecord, ...]
    missing_ids: tuple[str, ...]
    data_version: str
    contract_version: str = "v4.entity-data.1"


@dataclass(frozen=True)
class EntityDataWriteResponse:
    """Acknowledgement returned by a write operation of the data service."""

    operation: EntityDataOperation
    data_version: str
    request_id: str = ""


class EntityDataClient(Protocol):
    def health(self) -> EntityDataHealth: ...

    def match_words(
        self,
        normalized_query: str,
        *,
        entity_types: tuple[str, ...] = (),
        expected_data_version: str | None = None,
    ) -> EntityWordMatchResponse: ...

    def batch_get(
        self,
        entity_ids: tuple[str, ...],
        *,
        expected_data_version: str | None = None,
    ) -> EntityBatchGetResponse: ...
