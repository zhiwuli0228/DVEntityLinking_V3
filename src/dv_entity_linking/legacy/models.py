"""Shared schemas for the DV entity linking demo."""

from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from enum import StrEnum
from typing import Any


class DataLayer(StrEnum):
    L0_SYNTHETIC = "L0_SYNTHETIC"
    L1_SANITIZED = "L1_SANITIZED"
    L2_SIMULATED_INTERFACE = "L2_SIMULATED_INTERFACE"
    L3_REAL_READONLY = "L3_REAL_READONLY"
    LOCAL_REAL_ARTIFACT = "LOCAL_REAL_ARTIFACT"


class EntityType(StrEnum):
    ALARM = "alarm"
    NETWORK_RESOURCE = "network_resource"
    ALARM_EVENT = "alarm_event"
    KPI_METRIC = "kpi_metric"
    TOPOLOGY_RELATION = "topology_relation"
    KNOWLEDGE_CASE = "knowledge_case"
    NE_TYPE = "ne_type"
    NE_NAME = "ne_name"
    KPI_TASK_NAME = "kpi_task_name"
    KPI_MEAS_OBJECTS = "kpi_meas_objects"
    KPI_MEAS_TYPE_KEY = "kpi_meas_type_key"


class Status(StrEnum):
    LINKED = "linked"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"
    NOT_REQUIRED = "not_required"
    DEPENDENCY_FAILED = "dependency_failed"
    INVALID_INPUT = "invalid_input"


class RunMode(StrEnum):
    OFFLINE_DEMO = "offline_demo"
    LLM_ENABLED_DEMO = "llm_enabled_demo"
    MOCK_FALLBACK = "mock_fallback"


class MentionSource(StrEnum):
    LLM = "llm"
    DETERMINISTIC = "deterministic"
    MOCK = "mock"


class ResultSource(StrEnum):
    OFFLINE_DETERMINISTIC = "offline_deterministic"
    LLM = "llm"
    FALLBACK_OFFLINE = "fallback_offline"
    RUNTIME_MOCK = "runtime_mock"
    CONFIRMED_SAMPLE = "confirmed_sample"
    NONE = "none"


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_MODE = "invalid_mode"
    INVALID_ALLOW_FALLBACK = "invalid_allow_fallback"
    CATALOG_LOAD_FAILED = "catalog_load_failed"
    RUNTIME_SOURCE_FAILED = "runtime_source_failed"
    QUERY_DATASET_LOAD_FAILED = "query_dataset_load_failed"
    VALIDATION_FAILED = "validation_failed"
    DATA_LAYER_NOT_CONFIRMED = "data_layer_not_confirmed"
    LLM_TIMEOUT = "llm_timeout"
    LLM_HTTP_ERROR = "llm_http_error"
    LLM_AUTH_ERROR = "llm_auth_error"
    LLM_SCHEMA_ERROR = "llm_schema_error"
    DEPENDENCY_FAILED = "dependency_failed"
    OUTPUT_WRITE_FAILED = "output_write_failed"
    DUPLICATE_KEY = "duplicate_key"
    DUPLICATE_ENTITY_ID = "duplicate_entity_id"
    DANGLING_ENTITY_ID = "dangling_entity_id"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    INVALID_KEY = "invalid_key"


class StorageLookupStatus(StrEnum):
    HIT = "hit"
    MISS = "miss"
    INVALID_KEY = "invalid_key"
    ENTITY_MISS = "entity_miss"
    SCHEMA_ERROR = "schema_error"
    DEPENDENCY_FAILED = "dependency_failed"


class StorageStartupStatus(StrEnum):
    READY = "ready"
    FAILED = "failed"


class StorageErrorCode(StrEnum):
    DUPLICATE_KEY = "duplicate_key"
    DUPLICATE_ENTITY_ID = "duplicate_entity_id"
    DANGLING_ENTITY_ID = "dangling_entity_id"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    UNCONFIRMED_DATA_LAYER = "unconfirmed_data_layer"
    INVALID_KEY = "invalid_key"
    SCHEMA_ERROR = "schema_error"


@dataclass(frozen=True)
class RelationshipRecord:
    target_entity_id: str
    relation_type: str
    source: str
    data_layer: DataLayer


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    entity_type: EntityType
    entity_name: str
    alias: list[str] = field(default_factory=list)
    desc: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    relationships: list[RelationshipRecord] = field(default_factory=list)
    data_layer: DataLayer = DataLayer.L0_SYNTHETIC
    source: str = "mock_catalog"


@dataclass(frozen=True)
class EntityMention:
    text: str
    span: tuple[int, int] | None
    predicted_type: EntityType | None
    source: MentionSource


@dataclass(frozen=True)
class LinkCandidate:
    entity_id: str
    entity_name: str
    entity_type: EntityType
    confidence: float
    match_reason: str
    rank: int | None = None
    dedup_key: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class StructuredEntityRecord:
    entity_id: str
    entity_type: EntityType
    entity_name: str
    alias: list[str] = field(default_factory=list)
    desc: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    relationships: list[RelationshipRecord] = field(default_factory=list)
    source: str = "v3_gauss_mock"

    def to_entity_record(self) -> EntityRecord:
        return EntityRecord(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            entity_name=self.entity_name,
            alias=list(self.alias),
            desc=self.desc,
            attributes=dict(self.attributes),
            relationships=list(self.relationships),
            data_layer=DataLayer.L1_SANITIZED,
            source=self.source,
        )


@dataclass(frozen=True)
class EntityWordRecord:
    entity_word: str
    normalized_key: str
    entity_id: str
    source: str = "confirmed_alias"
    normalization_version: str = "v3.entity_word_norm.1"


@dataclass(frozen=True)
class StartupCheckReport:
    status: StorageStartupStatus
    entity_count: int = 0
    word_count: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class EntityWordLookupResult:
    status: StorageLookupStatus
    entity_word_key: str
    normalized_key: str
    entity_id: str | None = None
    error_code: StorageErrorCode | None = None
    safe_trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuredEntityLookupResult:
    status: StorageLookupStatus
    entity_id: str
    entity_record: StructuredEntityRecord | None = None
    error_code: StorageErrorCode | None = None
    safe_trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MentionLinkResult:
    mention: EntityMention
    status: Status
    linked_entity: EntityRecord | None = None
    candidates: list[LinkCandidate] = field(default_factory=list)
    confidence: float | None = None
    disambiguation_reason: str = ""
    no_match_reason: str = ""
    bypass_reason: str = ""
    degraded: bool = False
    error_code: ErrorCode | None = None
    source: str = "deterministic+catalog"
    data_layer: DataLayer = DataLayer.L0_SYNTHETIC
    storage_lookup: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityLinkResult:
    query: str
    status: Status
    mentions: list[EntityMention] = field(default_factory=list)
    mention_results: list[MentionLinkResult] = field(default_factory=list)
    linked_entity: EntityRecord | None = None
    candidates: list[LinkCandidate] = field(default_factory=list)
    confidence: float | None = None
    disambiguation_reason: str = ""
    no_match_reason: str = ""
    bypass_reason: str = ""
    degraded: bool = False
    error_code: ErrorCode | None = None
    data_layer: DataLayer = DataLayer.L0_SYNTHETIC
    source: str = "deterministic+catalog"
    stage_trace: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalItem:
    entity_id: str
    entity_name: str
    entity_type: EntityType
    score: float
    similarity_reason: str
    source: str
    data_layer: DataLayer


@dataclass(frozen=True)
class RetrievalResult:
    status: Status
    query_entity_id: str
    k: int = 5
    items: list[RetrievalItem] = field(default_factory=list)
    no_match_reason: str = ""


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    mode: RunMode
    query: str
    result: dict[str, Any]
    llm_used: bool
    degraded: bool
    created_at: str


@dataclass(frozen=True)
class CatalogLoadResult:
    status: Status
    entity_count: int
    type_counts: dict[str, int]
    errors: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractionResult:
    mentions: list[EntityMention]
    degraded: bool = False
    error_code: ErrorCode | None = None
    llm_used: bool = False
    fallback_available: bool = True
    not_required: bool = False
    bypass_reason: str = ""


@dataclass(frozen=True)
class ModeRequest:
    query: str
    mode: RunMode
    allow_fallback: bool = True


@dataclass(frozen=True)
class ModeStatus:
    requested_mode: RunMode
    effective_mode: RunMode | None
    allow_fallback: bool
    llm_enabled: bool
    llm_used: bool = False
    fallback_used: bool = False
    degraded: bool = False
    result_source: str = ResultSource.OFFLINE_DETERMINISTIC.value
    stage_statuses: list[dict[str, Any]] = field(default_factory=list)
    error_code: ErrorCode | None = None


@dataclass(frozen=True)
class ApiError:
    error_code: ErrorCode
    message: str
    field: str = ""


@dataclass(frozen=True)
class CandidateSet:
    mention: EntityMention
    candidates: list[LinkCandidate]
    retrieval_strategy: str = "alarm_exact_index"
    errors: list[ApiError] = field(default_factory=list)


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def to_plain(value: Any) -> Any:
    """Convert dataclasses and enums to JSON-serializable plain objects."""
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value):
        return {
            key: to_plain(item)
            for key, item in value.__dict__.items()
            if item is not None and item != ""
        }
    if isinstance(value, tuple):
        return [to_plain(item) for item in value]
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    return value
