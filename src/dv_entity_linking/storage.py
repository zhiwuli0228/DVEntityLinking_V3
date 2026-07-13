"""V3 two-layer storage mocks and validation."""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .models import (
    CatalogLoadResult,
    EntityRecord,
    EntityType,
    EntityWordLookupResult,
    EntityWordRecord,
    StartupCheckReport,
    Status,
    StorageErrorCode,
    StorageLookupStatus,
    StorageStartupStatus,
    StructuredEntityLookupResult,
    StructuredEntityRecord,
)


GAUSS_SCHEMA_VERSION = "v3.gauss_entities.1"
REDIS_SCHEMA_VERSION = "v3.redis_entity_words.1"
NORMALIZATION_VERSION = "v3.entity_word_norm.1"
CONFIRMED_WORD_SOURCES = {"canonical_name", "confirmed_alias"}
EXPECTED_KEY_SCOPE = ["canonical_name", "confirmed_aliases"]


class StorageError(ValueError):
    def __init__(self, report: StartupCheckReport) -> None:
        message = "; ".join(error["message"] for error in report.errors) or "storage validation failed"
        super().__init__(message)
        self.report = report


def normalize_entity_word(text: str) -> str:
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(char for char in normalized if not char.isspace())


def _read_json(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("artifact root must be object")
    return payload


def _error(field: str, code: StorageErrorCode, message: str) -> dict[str, str]:
    return {"field": field, "error_code": code.value, "message": message}


class GaussEntityStoreMock:
    def __init__(self) -> None:
        self._entities: dict[str, StructuredEntityRecord] = {}
        self._metadata: dict[str, Any] = {}
        self.startup_report = StartupCheckReport(status=StorageStartupStatus.FAILED)

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    @property
    def entities(self) -> list[StructuredEntityRecord]:
        return list(self._entities.values())

    def load_path(self, path: str | Path) -> StartupCheckReport:
        try:
            payload = _read_json(path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
            report = StartupCheckReport(
                status=StorageStartupStatus.FAILED,
                errors=[_error("path", StorageErrorCode.SCHEMA_ERROR, str(exc))],
            )
            self.startup_report = report
            return report
        return self.load(payload)

    def load(self, payload: dict[str, Any]) -> StartupCheckReport:
        errors: list[dict[str, str]] = []
        metadata = payload.get("metadata")
        raw_entities = payload.get("entities")
        if not isinstance(metadata, dict):
            errors.append(_error("metadata", StorageErrorCode.MISSING_REQUIRED_FIELD, "metadata must be object"))
            metadata = {}
        if metadata.get("schema_version") != GAUSS_SCHEMA_VERSION:
            errors.append(
                _error(
                    "metadata.schema_version",
                    StorageErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                    f"schema_version must be {GAUSS_SCHEMA_VERSION}",
                )
            )
        if not isinstance(raw_entities, list):
            errors.append(_error("entities", StorageErrorCode.MISSING_REQUIRED_FIELD, "entities must be list"))
            raw_entities = []

        records: list[StructuredEntityRecord] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(raw_entities):
            field_prefix = f"entities[{index}]"
            if not isinstance(item, dict):
                errors.append(_error(field_prefix, StorageErrorCode.SCHEMA_ERROR, "entity item must be object"))
                continue
            record = self._parse_record(item, field_prefix, errors)
            if record is None:
                continue
            if record.entity_id in seen_ids:
                errors.append(
                    _error(
                        f"{field_prefix}.entity_id",
                        StorageErrorCode.DUPLICATE_ENTITY_ID,
                        f"duplicate entity_id: {record.entity_id}",
                    )
                )
            seen_ids.add(record.entity_id)
            records.append(record)

        if metadata.get("entity_count") is not None and metadata.get("entity_count") != len(raw_entities):
            errors.append(
                _error(
                    "metadata.entity_count",
                    StorageErrorCode.SCHEMA_ERROR,
                    "entity_count does not match entities[] length",
                )
            )

        if errors:
            report = StartupCheckReport(
                status=StorageStartupStatus.FAILED,
                entity_count=0,
                errors=errors,
            )
            self.startup_report = report
            return report

        self._metadata = metadata
        self._entities = {record.entity_id: record for record in records}
        report = StartupCheckReport(
            status=StorageStartupStatus.READY,
            entity_count=len(records),
            word_count=0,
        )
        self.startup_report = report
        return report

    def get(self, entity_id: str) -> StructuredEntityLookupResult:
        if self.startup_report.status != StorageStartupStatus.READY:
            return StructuredEntityLookupResult(
                status=StorageLookupStatus.DEPENDENCY_FAILED,
                entity_id=entity_id,
                error_code=StorageErrorCode.SCHEMA_ERROR,
                safe_trace={"adapter": "gauss_mock", "status": StorageLookupStatus.DEPENDENCY_FAILED.value},
            )
        record = self._entities.get(entity_id)
        if record is None:
            return StructuredEntityLookupResult(
                status=StorageLookupStatus.ENTITY_MISS,
                entity_id=entity_id,
                error_code=StorageErrorCode.DANGLING_ENTITY_ID,
                safe_trace={"adapter": "gauss_mock", "status": StorageLookupStatus.ENTITY_MISS.value},
            )
        return StructuredEntityLookupResult(
            status=StorageLookupStatus.HIT,
            entity_id=entity_id,
            entity_record=record,
            safe_trace={
                "adapter": "gauss_mock",
                "status": StorageLookupStatus.HIT.value,
                "schema_version": GAUSS_SCHEMA_VERSION,
            },
        )

    def _parse_record(
        self,
        item: dict[str, Any],
        field_prefix: str,
        errors: list[dict[str, str]],
    ) -> StructuredEntityRecord | None:
        required = ["entity_id", "entity_type", "canonical_name", "aliases", "description"]
        missing = [field for field in required if field not in item]
        if missing:
            errors.append(
                _error(
                    field_prefix,
                    StorageErrorCode.MISSING_REQUIRED_FIELD,
                    f"missing required fields: {missing}",
                )
            )
            return None
        aliases = item.get("aliases")
        if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
            errors.append(
                _error(
                    f"{field_prefix}.aliases",
                    StorageErrorCode.SCHEMA_ERROR,
                    "aliases must be list[string]",
                )
            )
            return None
        try:
            entity_type = EntityType(item["entity_type"])
        except ValueError:
            errors.append(
                _error(
                    f"{field_prefix}.entity_type",
                    StorageErrorCode.SCHEMA_ERROR,
                    f"unsupported entity_type: {item.get('entity_type')}",
                )
            )
            return None
        values = {key: item.get(key) for key in ["entity_id", "canonical_name", "description"]}
        non_strings = [key for key, value in values.items() if not isinstance(value, str)]
        if non_strings:
            errors.append(
                _error(
                    field_prefix,
                    StorageErrorCode.SCHEMA_ERROR,
                    f"fields must be strings: {non_strings}",
                )
            )
            return None
        if not item["entity_id"].strip() or not item["canonical_name"].strip() or not item["description"].strip():
            errors.append(
                _error(
                    field_prefix,
                    StorageErrorCode.MISSING_REQUIRED_FIELD,
                    "entity_id, canonical_name, and description must be non-empty",
                )
            )
            return None
        return StructuredEntityRecord(
            entity_id=str(item["entity_id"]),
            entity_type=entity_type,
            canonical_name=str(item["canonical_name"]),
            aliases=list(aliases),
            description=str(item["description"]),
        )


class RedisEntityWordCacheMock:
    def __init__(self) -> None:
        self._records: dict[str, EntityWordRecord] = {}
        self._metadata: dict[str, Any] = {}
        self.startup_report = StartupCheckReport(status=StorageStartupStatus.FAILED)

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    @property
    def records(self) -> list[EntityWordRecord]:
        return list(self._records.values())

    def load_path(self, path: str | Path, entity_store: GaussEntityStoreMock) -> StartupCheckReport:
        try:
            payload = _read_json(path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
            report = StartupCheckReport(
                status=StorageStartupStatus.FAILED,
                errors=[_error("path", StorageErrorCode.SCHEMA_ERROR, str(exc))],
            )
            self.startup_report = report
            return report
        return self.load(payload, entity_store)

    def load(self, payload: dict[str, Any], entity_store: GaussEntityStoreMock) -> StartupCheckReport:
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        metadata = payload.get("metadata")
        raw_words = payload.get("entity_words")
        if not isinstance(metadata, dict):
            errors.append(_error("metadata", StorageErrorCode.MISSING_REQUIRED_FIELD, "metadata must be object"))
            metadata = {}
        if metadata.get("schema_version") != REDIS_SCHEMA_VERSION:
            errors.append(
                _error(
                    "metadata.schema_version",
                    StorageErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                    f"schema_version must be {REDIS_SCHEMA_VERSION}",
                )
            )
        if metadata.get("normalization_version") not in {None, NORMALIZATION_VERSION}:
            errors.append(
                _error(
                    "metadata.normalization_version",
                    StorageErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                    f"normalization_version must be {NORMALIZATION_VERSION}",
                )
            )
        if metadata.get("aliases_auto_generated") is not False:
            errors.append(
                _error(
                    "metadata.aliases_auto_generated",
                    StorageErrorCode.UNCONFIRMED_DATA_LAYER,
                    "aliases_auto_generated must be false",
                )
            )
        if metadata.get("key_scope") != EXPECTED_KEY_SCOPE:
            errors.append(
                _error(
                    "metadata.key_scope",
                    StorageErrorCode.UNCONFIRMED_DATA_LAYER,
                    "key_scope must be ['canonical_name', 'confirmed_aliases']",
                )
            )
        if not isinstance(raw_words, list):
            errors.append(_error("entity_words", StorageErrorCode.MISSING_REQUIRED_FIELD, "entity_words must be list"))
            raw_words = []

        records: dict[str, EntityWordRecord] = {}
        for index, item in enumerate(raw_words):
            field_prefix = f"entity_words[{index}]"
            if not isinstance(item, dict):
                errors.append(_error(field_prefix, StorageErrorCode.SCHEMA_ERROR, "entity word item must be object"))
                continue
            record = self._parse_record(item, field_prefix, entity_store, errors)
            if record is None:
                continue
            existing = records.get(record.normalized_key)
            if existing and existing.entity_id != record.entity_id:
                errors.append(
                    _error(
                        f"{field_prefix}.normalized_key",
                        StorageErrorCode.DUPLICATE_KEY,
                        f"duplicate key maps to multiple entity IDs: {record.normalized_key}",
                    )
                )
                continue
            if existing and existing.entity_id == record.entity_id:
                warnings.append(
                    _error(
                        f"{field_prefix}.normalized_key",
                        StorageErrorCode.DUPLICATE_KEY,
                        f"duplicate key maps to same entity ID and was deduplicated: {record.normalized_key}",
                    )
                )
                continue
            records[record.normalized_key] = record

        if metadata.get("word_count") is not None and metadata.get("word_count") != len(raw_words):
            errors.append(
                _error(
                    "metadata.word_count",
                    StorageErrorCode.SCHEMA_ERROR,
                    "word_count does not match entity_words[] length",
                )
            )

        if errors:
            report = StartupCheckReport(
                status=StorageStartupStatus.FAILED,
                entity_count=entity_store.startup_report.entity_count,
                word_count=0,
                errors=errors,
                warnings=warnings,
            )
            self.startup_report = report
            return report

        self._metadata = metadata
        self._records = records
        report = StartupCheckReport(
            status=StorageStartupStatus.READY,
            entity_count=entity_store.startup_report.entity_count,
            word_count=len(records),
            warnings=warnings,
        )
        self.startup_report = report
        return report

    def lookup(self, entity_word: str) -> EntityWordLookupResult:
        normalized_key = normalize_entity_word(entity_word)
        if self.startup_report.status != StorageStartupStatus.READY:
            return EntityWordLookupResult(
                status=StorageLookupStatus.DEPENDENCY_FAILED,
                entity_word_key=entity_word,
                normalized_key=normalized_key,
                error_code=StorageErrorCode.SCHEMA_ERROR,
                safe_trace={"adapter": "redis_mock", "status": StorageLookupStatus.DEPENDENCY_FAILED.value},
            )
        if not normalized_key:
            return EntityWordLookupResult(
                status=StorageLookupStatus.INVALID_KEY,
                entity_word_key=entity_word,
                normalized_key=normalized_key,
                error_code=StorageErrorCode.INVALID_KEY,
                safe_trace={"adapter": "redis_mock", "status": StorageLookupStatus.INVALID_KEY.value},
            )
        record = self._records.get(normalized_key)
        if record is None:
            return EntityWordLookupResult(
                status=StorageLookupStatus.MISS,
                entity_word_key=entity_word,
                normalized_key=normalized_key,
                safe_trace={"adapter": "redis_mock", "status": StorageLookupStatus.MISS.value},
            )
        return EntityWordLookupResult(
            status=StorageLookupStatus.HIT,
            entity_word_key=entity_word,
            normalized_key=normalized_key,
            entity_id=record.entity_id,
            safe_trace={
                "adapter": "redis_mock",
                "status": StorageLookupStatus.HIT.value,
                "schema_version": REDIS_SCHEMA_VERSION,
                "normalization_version": NORMALIZATION_VERSION,
            },
        )

    def _parse_record(
        self,
        item: dict[str, Any],
        field_prefix: str,
        entity_store: GaussEntityStoreMock,
        errors: list[dict[str, str]],
    ) -> EntityWordRecord | None:
        required = ["entity_word", "normalized_key", "entity_id", "source"]
        missing = [field for field in required if field not in item]
        if missing:
            errors.append(
                _error(
                    field_prefix,
                    StorageErrorCode.MISSING_REQUIRED_FIELD,
                    f"missing required fields: {missing}",
                )
            )
            return None
        values = {key: item.get(key) for key in required}
        non_strings = [key for key, value in values.items() if not isinstance(value, str)]
        if non_strings:
            errors.append(
                _error(field_prefix, StorageErrorCode.SCHEMA_ERROR, f"fields must be strings: {non_strings}")
            )
            return None
        entity_word = str(item["entity_word"])
        normalized_key = normalize_entity_word(entity_word)
        if not normalized_key:
            errors.append(_error(f"{field_prefix}.entity_word", StorageErrorCode.INVALID_KEY, "entity_word is empty"))
            return None
        if normalized_key != item["normalized_key"]:
            errors.append(
                _error(
                    f"{field_prefix}.normalized_key",
                    StorageErrorCode.SCHEMA_ERROR,
                    "normalized_key must be recomputed from entity_word",
                )
            )
            return None
        if item.get("normalization_version", NORMALIZATION_VERSION) != NORMALIZATION_VERSION:
            errors.append(
                _error(
                    f"{field_prefix}.normalization_version",
                    StorageErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                    f"normalization_version must be {NORMALIZATION_VERSION}",
                )
            )
            return None
        source = str(item["source"])
        if source not in CONFIRMED_WORD_SOURCES:
            errors.append(
                _error(
                    f"{field_prefix}.source",
                    StorageErrorCode.UNCONFIRMED_DATA_LAYER,
                    "source must be canonical_name or confirmed_alias",
                )
            )
            return None
        entity_lookup = entity_store.get(str(item["entity_id"]))
        if entity_lookup.status != StorageLookupStatus.HIT or entity_lookup.entity_record is None:
            errors.append(
                _error(
                    f"{field_prefix}.entity_id",
                    StorageErrorCode.DANGLING_ENTITY_ID,
                    f"entity_id not found in Gauss mock: {item['entity_id']}",
                )
            )
            return None
        if not self._word_is_confirmed_for_entity(entity_word, source, entity_lookup.entity_record):
            errors.append(
                _error(
                    f"{field_prefix}.entity_word",
                    StorageErrorCode.UNCONFIRMED_DATA_LAYER,
                    "entity_word must be canonical_name or a confirmed alias of the referenced entity",
                )
            )
            return None
        return EntityWordRecord(
            entity_word=entity_word,
            normalized_key=normalized_key,
            entity_id=str(item["entity_id"]),
            source=source,
            normalization_version=str(item.get("normalization_version", NORMALIZATION_VERSION)),
        )

    @staticmethod
    def _word_is_confirmed_for_entity(
        entity_word: str,
        source: str,
        entity: StructuredEntityRecord,
    ) -> bool:
        normalized_word = normalize_entity_word(entity_word)
        if source == "canonical_name":
            return normalized_word == normalize_entity_word(entity.canonical_name)
        return normalized_word in {normalize_entity_word(alias) for alias in entity.aliases}


class EntityStorageRepository:
    def __init__(
        self,
        entity_store: GaussEntityStoreMock,
        word_cache: RedisEntityWordCacheMock,
        startup_report: StartupCheckReport,
    ) -> None:
        self.entity_store = entity_store
        self.word_cache = word_cache
        self.startup_report = startup_report

    @property
    def ready(self) -> bool:
        return self.startup_report.status == StorageStartupStatus.READY

    @property
    def entity_records(self) -> list[EntityRecord]:
        return [record.to_entity_record() for record in self.entity_store.entities]

    @property
    def entity_words(self) -> list[str]:
        return [record.entity_word for record in self.word_cache.records]

    @classmethod
    def load_from_paths(
        cls,
        gauss_path: str | Path,
        redis_path: str | Path,
    ) -> "EntityStorageRepository":
        entity_store = GaussEntityStoreMock()
        gauss_report = entity_store.load_path(gauss_path)
        if gauss_report.status != StorageStartupStatus.READY:
            raise StorageError(gauss_report)

        word_cache = RedisEntityWordCacheMock()
        redis_report = word_cache.load_path(redis_path, entity_store)
        if redis_report.status != StorageStartupStatus.READY:
            raise StorageError(redis_report)

        report = StartupCheckReport(
            status=StorageStartupStatus.READY,
            entity_count=gauss_report.entity_count,
            word_count=redis_report.word_count,
            warnings=[*gauss_report.warnings, *redis_report.warnings],
        )
        return cls(entity_store=entity_store, word_cache=word_cache, startup_report=report)

    def lookup(self, entity_word: str) -> tuple[EntityWordLookupResult, StructuredEntityLookupResult | None]:
        word_result = self.word_cache.lookup(entity_word)
        if word_result.status != StorageLookupStatus.HIT or not word_result.entity_id:
            return word_result, None
        entity_result = self.entity_store.get(word_result.entity_id)
        return word_result, entity_result


class V3CatalogAdapter:
    def __init__(self, storage_repository: EntityStorageRepository) -> None:
        self.storage_repository = storage_repository
        self._metadata = {
            "schema_version": GAUSS_SCHEMA_VERSION,
            "source": "v3_gauss_mock",
        }

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    @property
    def entities(self) -> list[EntityRecord]:
        return self.storage_repository.entity_records

    def load(self) -> CatalogLoadResult:
        counts = Counter(record.entity_type.value for record in self.entities)
        return CatalogLoadResult(
            status=Status.LINKED,
            entity_count=len(self.entities),
            type_counts=dict(sorted(counts.items())),
        )

    def get(self, entity_id: str) -> EntityRecord | None:
        result = self.storage_repository.entity_store.get(entity_id)
        if result.status != StorageLookupStatus.HIT or result.entity_record is None:
            return None
        return result.entity_record.to_entity_record()

    def by_type(self, entity_type: EntityType | str) -> list[EntityRecord]:
        normalized = EntityType(entity_type)
        return [entity for entity in self.entities if entity.entity_type == normalized]

    def search(
        self,
        text: str,
        *,
        entity_type: EntityType | str | None = None,
        limit: int = 20,
    ) -> list[EntityRecord]:
        needle = normalize_entity_word(text)
        if not needle:
            return []
        type_filter = EntityType(entity_type) if entity_type else None
        matches: list[EntityRecord] = []
        for entity in self.entities:
            if type_filter and entity.entity_type != type_filter:
                continue
            names = [entity.canonical_name, *entity.aliases]
            if any(needle in normalize_entity_word(name) or normalize_entity_word(name) in needle for name in names):
                matches.append(entity)
            if len(matches) >= limit:
                break
        return matches

    def neighbors(self, entity_id: str) -> list[EntityRecord]:
        return []
