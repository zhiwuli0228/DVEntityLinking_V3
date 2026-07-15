"""Entity catalog loading and in-memory lookup."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .models import (
    CatalogLoadResult,
    DataLayer,
    EntityRecord,
    EntityType,
    ErrorCode,
    RelationshipRecord,
    Status,
)


class CatalogError(ValueError):
    def __init__(self, error_code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def normalize_text(text: str) -> str:
    return "".join(ch.lower() for ch in text.strip() if not ch.isspace())


class CatalogRepository:
    V1_SCHEMA_VERSIONS = {"v1.alarm_entity.1", "v1.alarm_entity.2"}
    V2_SCHEMA_VERSIONS = {"v2.entity_examples.1"}
    V2_ENTITY_TYPES = {
        EntityType.NE_TYPE,
        EntityType.NE_NAME,
        EntityType.KPI_TASK_NAME,
        EntityType.KPI_MEAS_TYPE_KEY,
    }

    def __init__(
        self,
        catalog_path: str | Path,
        *,
        allowed_data_layers: Iterable[DataLayer | str] | None = None,
        data_layer_confirmation_path: str | Path | None = None,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.allowed_data_layers = {
            DataLayer(layer) for layer in (allowed_data_layers or [DataLayer.L0_SYNTHETIC])
        }
        self.data_layer_confirmation_path = (
            Path(data_layer_confirmation_path) if data_layer_confirmation_path else None
        )
        self._entities: dict[str, EntityRecord] = {}
        self._name_index: dict[str, set[str]] = defaultdict(set)
        self._type_index: dict[EntityType, list[str]] = defaultdict(list)
        self._metadata: dict = {}

    def load(self) -> CatalogLoadResult:
        try:
            records = self._read_records()
            self._validate_metadata(records)
            self._validate_layers(records)
            self._validate_relationships(records)
        except CatalogError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise CatalogError(ErrorCode.CATALOG_LOAD_FAILED, str(exc)) from exc

        self._entities = {record.entity_id: record for record in records}
        self._name_index.clear()
        self._type_index.clear()
        for record in records:
            self._type_index[record.entity_type].append(record.entity_id)
            for name in [record.entity_name, *record.alias]:
                self._name_index[normalize_text(name)].add(record.entity_id)

        counts = Counter(record.entity_type.value for record in records)
        return CatalogLoadResult(
            status=Status.LINKED,
            entity_count=len(records),
            type_counts=dict(sorted(counts.items())),
        )

    @property
    def entities(self) -> list[EntityRecord]:
        return list(self._entities.values())

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

    def get(self, entity_id: str) -> EntityRecord | None:
        return self._entities.get(entity_id)

    def by_type(self, entity_type: EntityType | str) -> list[EntityRecord]:
        normalized = EntityType(entity_type)
        return [self._entities[item] for item in self._type_index.get(normalized, [])]

    def search(
        self,
        text: str,
        *,
        entity_type: EntityType | str | None = None,
        limit: int = 20,
    ) -> list[EntityRecord]:
        needle = normalize_text(text)
        if not needle:
            return []
        type_filter = EntityType(entity_type) if entity_type else None
        exact_ids = set(self._name_index.get(needle, set()))
        matches: list[EntityRecord] = []
        seen: set[str] = set()
        for entity_id in exact_ids:
            record = self._entities[entity_id]
            if type_filter and record.entity_type != type_filter:
                continue
            matches.append(record)
            seen.add(entity_id)
        for record in self.entities:
            if record.entity_id in seen:
                continue
            if type_filter and record.entity_type != type_filter:
                continue
            names = [record.entity_name, *record.alias]
            if any(needle in normalize_text(name) or normalize_text(name) in needle for name in names):
                matches.append(record)
                seen.add(record.entity_id)
            if len(matches) >= limit:
                break
        return matches[:limit]

    def neighbors(self, entity_id: str) -> list[EntityRecord]:
        record = self.get(entity_id)
        if not record:
            return []
        return [
            self._entities[relation.target_entity_id]
            for relation in record.relationships
            if relation.target_entity_id in self._entities
        ]

    def _read_records(self) -> list[EntityRecord]:
        metadata, items = self._read_payload(self.catalog_path)
        self._metadata = metadata
        records = [self._record_from_dict(item) for item in items]
        if metadata.get("schema_version") in self.V2_SCHEMA_VERSIONS:
            records = self._read_v2_base_records(metadata) + records
        ids = [record.entity_id for record in records]
        duplicates = {entity_id for entity_id in ids if ids.count(entity_id) > 1}
        if duplicates:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"duplicate entity_id values: {sorted(duplicates)}",
            )
        return records

    def _read_payload(self, path: Path) -> tuple[dict, list]:
        if not path.exists():
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"catalog file not found: {path}",
            )
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        items = raw.get("entities") if isinstance(raw, dict) else None
        metadata = raw.get("metadata", {}) if isinstance(raw, dict) else {}
        if metadata and not isinstance(metadata, dict):
            raise CatalogError(ErrorCode.CATALOG_LOAD_FAILED, "catalog metadata must be an object")
        if not isinstance(items, list):
            raise CatalogError(ErrorCode.CATALOG_LOAD_FAILED, "catalog root must contain entities[]")
        return metadata, items

    def _read_v2_base_records(self, metadata: dict) -> list[EntityRecord]:
        base_records: list[EntityRecord] = []
        base_files = metadata.get("base_entity_files", [])
        if not isinstance(base_files, list):
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                "v2 catalog metadata base_entity_files must be a list",
            )
        primary_metadata = self._metadata
        for raw_path in base_files:
            if not isinstance(raw_path, str):
                raise CatalogError(
                    ErrorCode.CATALOG_LOAD_FAILED,
                    "v2 catalog metadata base_entity_files values must be strings",
                )
            base_path = self._resolve_related_path(raw_path)
            base_metadata, base_items = self._read_payload(base_path)
            self._metadata = base_metadata
            records = [self._record_from_dict(item) for item in base_items]
            self._validate_metadata(records)
            base_records.extend(records)
        self._metadata = primary_metadata
        return base_records

    def _resolve_related_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        if candidate.exists():
            return candidate
        local_candidate = self.catalog_path.parent / candidate
        if local_candidate.exists():
            return local_candidate
        resolved_catalog = self.catalog_path.resolve()
        for parent in resolved_catalog.parents:
            parent_candidate = parent / candidate
            if parent_candidate.exists():
                return parent_candidate
        return candidate

    def _validate_metadata(self, records: list[EntityRecord]) -> None:
        if not self._metadata:
            return
        schema_version = self._metadata.get("schema_version")
        if schema_version in self.V2_SCHEMA_VERSIONS:
            self._validate_v2_metadata(records)
            return
        if schema_version not in self.V1_SCHEMA_VERSIONS:
            return
        entity_type_scope = self._metadata.get("entity_type_scope")
        if entity_type_scope != ["alarm"]:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                "v1 alarm catalog metadata must declare entity_type_scope=['alarm']",
            )
        if self._metadata.get("entity_count") != len(records):
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                "v1 alarm catalog metadata entity_count does not match entities[]",
            )
        invalid_types = [
            record.entity_id for record in records if record.entity_type != EntityType.ALARM
        ]
        if invalid_types:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"v1 alarm catalog contains non-alarm entities: {invalid_types}",
            )
        missing_descs = [
            record.entity_id for record in records if not record.desc.strip()
        ]
        if missing_descs:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"v1 alarm catalog entities require desc: {missing_descs}",
            )
        duplicate_alias = [
            record.entity_id
            for record in records
            if len({normalize_text(alias) for alias in record.alias}) != len(record.alias)
        ]
        if duplicate_alias:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"duplicate alias within alarm entities: {duplicate_alias}",
            )

    def _record_from_dict(self, item: dict) -> EntityRecord:
        required = ["entity_id", "entity_type", "entity_name", "alias"]
        missing = [field for field in required if field not in item]
        if missing:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"missing required entity fields: {missing}",
            )
        relationships = [self._relationship_from_dict(relationship) for relationship in item.get("relationships", [])]
        return EntityRecord(
            entity_id=str(item["entity_id"]),
            entity_type=EntityType(item["entity_type"]),
            entity_name=str(item["entity_name"]),
            alias=[str(alias) for alias in item.get("alias", [])],
            desc=str(item.get("desc", "")),
            attributes=dict(item.get("attributes", {})),
            relationships=relationships,
            data_layer=self._record_data_layer(item),
            source=str(item.get("source") or self._metadata.get("source") or "catalog"),
        )

    def _record_data_layer(self, item: dict) -> DataLayer:
        raw_layer = item.get("data_layer") or self._metadata.get("data_layer")
        if raw_layer:
            return DataLayer(raw_layer)
        if self._metadata.get("schema_version") in self.V1_SCHEMA_VERSIONS:
            return DataLayer.L1_SANITIZED
        return DataLayer.L0_SYNTHETIC

    def _validate_v2_metadata(self, records: list[EntityRecord]) -> None:
        declared_scope = set(self._metadata.get("entity_type_scope") or [])
        expected_scope = {entity_type.value for entity_type in self.V2_ENTITY_TYPES}
        v2_records = [record for record in records if record.entity_type in self.V2_ENTITY_TYPES]
        if declared_scope != expected_scope:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                "v2 catalog metadata entity_type_scope does not match V2 entity types",
            )
        if self._metadata.get("entity_count") != len(v2_records):
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                "v2 catalog metadata entity_count does not match entities[]",
            )
        if self._metadata.get("kpi_meas_objects_included") is not False:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                "v2 startup catalog must declare kpi_meas_objects_included=false",
            )
        invalid_types = [
            record.entity_id
            for record in records
            if record.entity_type not in self.V2_ENTITY_TYPES | {EntityType.ALARM}
        ]
        if invalid_types:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"v2 catalog contains unsupported entity types: {invalid_types}",
            )
        if self._metadata.get("alias_default_empty") is True:
            alias_entities = [record.entity_id for record in v2_records if record.alias]
            if alias_entities:
                raise CatalogError(
                    ErrorCode.CATALOG_LOAD_FAILED,
                    f"v2 alias require explicit confirmation: {alias_entities}",
                )
        missing_descs = [
            record.entity_id for record in records if not record.desc.strip()
        ]
        if missing_descs:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"v2 catalog entities require desc: {missing_descs}",
            )

    def _relationship_from_dict(self, relationship: dict) -> RelationshipRecord:
        required = ["target_entity_id", "relation_type"]
        missing = [field for field in required if field not in relationship]
        if missing:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"missing required relationship fields: {missing}",
            )
        return RelationshipRecord(
            target_entity_id=str(relationship["target_entity_id"]),
            relation_type=str(relationship["relation_type"]),
            source=str(relationship.get("source") or "catalog"),
            data_layer=DataLayer(relationship.get("data_layer") or DataLayer.L0_SYNTHETIC),
        )

    def _validate_layers(self, records: list[EntityRecord]) -> None:
        layers = {record.data_layer for record in records}
        disallowed = layers - self.allowed_data_layers
        metadata_confirms_layers = self._metadata_confirms_data_layers(records)
        if disallowed and not metadata_confirms_layers:
            raise CatalogError(
                ErrorCode.DATA_LAYER_NOT_CONFIRMED,
                f"data layers not allowed by configuration: {sorted(layer.value for layer in disallowed)}",
            )
        if layers - {DataLayer.L0_SYNTHETIC}:
            confirmation_file_exists = (
                self.data_layer_confirmation_path is not None
                and self.data_layer_confirmation_path.exists()
            )
            if not confirmation_file_exists and not metadata_confirms_layers:
                raise CatalogError(
                    ErrorCode.DATA_LAYER_NOT_CONFIRMED,
                    "non-L0 data layers require a confirmation record path",
                )

    def _metadata_confirms_data_layers(self, records: list[EntityRecord]) -> bool:
        schema_version = self._metadata.get("schema_version")
        layers = {record.data_layer for record in records}
        if schema_version in self.V1_SCHEMA_VERSIONS:
            return layers <= {DataLayer.L1_SANITIZED}
        if schema_version in self.V2_SCHEMA_VERSIONS:
            return all(
                record.data_layer == DataLayer.L0_SYNTHETIC
                or (
                    record.entity_type == EntityType.ALARM
                    and record.data_layer == DataLayer.L1_SANITIZED
                )
                for record in records
            )
        return False

    def _validate_relationships(self, records: list[EntityRecord]) -> None:
        ids = {record.entity_id for record in records}
        invalid = [
            (record.entity_id, relation.target_entity_id)
            for record in records
            for relation in record.relationships
            if relation.target_entity_id not in ids
        ]
        if invalid:
            raise CatalogError(
                ErrorCode.CATALOG_LOAD_FAILED,
                f"relationships reference unknown entities: {invalid}",
            )
