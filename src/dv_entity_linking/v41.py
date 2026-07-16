"""V4.1 migration and configuration validation utilities.

These functions are deliberately pure: they never contact an Entity Data
Service, read credentials, or write data.  An authorized host can publish the
returned bundle after a successful dry run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .domain.normalization import normalize_query


_DEPRECATED_RUNTIME_KEYS = frozenset(
    {
        "v3_mock_path",
        "redis_mock_path",
        "gauss_mock_path",
        "redis_url",
        "gauss_url",
        "catalog_path",
        "flask_runtime",
    }
)


class V41ValidationError(ValueError):
    """Raised when a V4.1 migration or runtime configuration is invalid."""


@dataclass(frozen=True)
class EntityWordProjection:
    entity_id: str
    entity_type: str
    entity_word: str
    normalized_key: str
    source: str


@dataclass(frozen=True)
class EntityMigrationBundle:
    entities: tuple[dict[str, Any], ...]
    entity_words: tuple[EntityWordProjection, ...]
    report: dict[str, Any]


def validate_v41_config(config: Mapping[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    """Validate a V4.1 configuration without interpreting legacy settings."""
    deprecated = sorted(key for key in config if key in _DEPRECATED_RUNTIME_KEYS)
    if deprecated:
        raise V41ValidationError(f"deprecated V4.1 runtime settings: {', '.join(deprecated)}")
    ir_url = config.get("entity_data_ir_url", "")
    if not isinstance(ir_url, str) or not ir_url.strip():
        raise V41ValidationError("entity_data_ir_url is required")
    policy = str(config.get("startup_failure_policy", "DEGRADED")).upper()
    if policy not in {"FAIL_FAST", "DEGRADED"}:
        raise V41ValidationError("startup_failure_policy must be FAIL_FAST or DEGRADED")
    return {
        "config_version": "v4.1",
        "dry_run": dry_run,
        "accepted_keys": sorted(config),
        "startup_failure_policy": policy,
    }


def build_entity_migration_bundle(
    entities: Sequence[Mapping[str, Any]], *, source_version: str, dry_run: bool = True
) -> EntityMigrationBundle:
    """Validate canonical entities and derive the publishable entity-word projection."""
    normalized_entities: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(entities):
        item = _validate_entity(raw, index=index)
        entity_id = item["entity_id"]
        if entity_id in seen_ids:
            raise V41ValidationError(f"duplicate entity_id: {entity_id}")
        seen_ids.add(entity_id)
        normalized_entities.append(item)

    _validate_relationship_targets(normalized_entities, seen_ids)
    words = _build_word_projection(normalized_entities)
    report = {
        "report_version": "v4.1",
        "source_version": source_version,
        "dry_run": dry_run,
        "entity_count": len(normalized_entities),
        "active_entity_count": sum(item["status"] == "active" for item in normalized_entities),
        "entity_word_count": len(words),
        "conflict_count": 0,
        "relationship_count": sum(len(item["relationships"]) for item in normalized_entities),
        "validation": "passed",
    }
    return EntityMigrationBundle(entities=tuple(normalized_entities), entity_words=tuple(words), report=report)


def _validate_entity(raw: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    required = ("entity_id", "entity_type", "entity_name", "alias", "desc", "attributes", "relationships")
    missing = [field for field in required if field not in raw]
    if missing:
        raise V41ValidationError(f"entities[{index}] missing required fields: {', '.join(missing)}")
    for field in ("entity_id", "entity_type", "entity_name", "desc"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise V41ValidationError(f"entities[{index}].{field} must be a non-empty string")
    alias = raw["alias"]
    if not isinstance(alias, list) or not all(isinstance(value, str) and value.strip() for value in alias):
        raise V41ValidationError(f"entities[{index}].alias must be list[string]")
    if not isinstance(raw["attributes"], dict):
        raise V41ValidationError(f"entities[{index}].attributes must be an object")
    relationships = raw["relationships"]
    if not isinstance(relationships, list):
        raise V41ValidationError(f"entities[{index}].relationships must be a list")
    seen_relations: set[tuple[str, str]] = set()
    safe_relations: list[dict[str, str]] = []
    for relation_index, relation in enumerate(relationships):
        if not isinstance(relation, Mapping):
            raise V41ValidationError(f"entities[{index}].relationships[{relation_index}] must be an object")
        target = relation.get("target_entity_id")
        relation_type = relation.get("relation_type")
        if not isinstance(target, str) or not target.strip() or not isinstance(relation_type, str) or not relation_type.strip():
            raise V41ValidationError(f"entities[{index}].relationships[{relation_index}] requires relation_type and target_entity_id")
        key = (relation_type, target)
        if key in seen_relations:
            raise V41ValidationError(f"entities[{index}] contains duplicate relationship: {relation_type}:{target}")
        seen_relations.add(key)
        safe_relations.append({"relation_type": relation_type, "target_entity_id": target})
    status = raw.get("status", "active")
    if status not in {"active", "inactive"}:
        raise V41ValidationError(f"entities[{index}].status must be active or inactive")
    return {
        "entity_id": raw["entity_id"],
        "entity_type": raw["entity_type"],
        "entity_name": raw["entity_name"],
        "alias": list(alias),
        "desc": raw["desc"],
        "attributes": dict(raw["attributes"]),
        "relationships": safe_relations,
        "status": status,
    }


def _validate_relationship_targets(entities: Sequence[Mapping[str, Any]], entity_ids: set[str]) -> None:
    for entity in entities:
        for relation in entity["relationships"]:
            if relation["target_entity_id"] not in entity_ids:
                raise V41ValidationError(
                    f"entity {entity['entity_id']} references unknown target: {relation['target_entity_id']}"
                )


def _build_word_projection(entities: Sequence[Mapping[str, Any]]) -> list[EntityWordProjection]:
    projections: list[EntityWordProjection] = []
    active_keys: dict[str, str] = {}
    for entity in entities:
        if entity["status"] != "active":
            continue
        seen_for_entity: set[str] = set()
        for source, word in [("entity_name", entity["entity_name"]), *( ("confirmed_alias", alias) for alias in entity["alias"] )]:
            normalized_key = normalize_query(word).normalized_text
            if not normalized_key:
                raise V41ValidationError(f"entity {entity['entity_id']} has an empty normalized entity word")
            if normalized_key in seen_for_entity:
                continue
            seen_for_entity.add(normalized_key)
            conflicting_id = active_keys.get(normalized_key)
            if conflicting_id is not None and conflicting_id != entity["entity_id"]:
                raise V41ValidationError(
                    f"active normalized entity word conflict: {normalized_key} ({conflicting_id}, {entity['entity_id']})"
                )
            active_keys[normalized_key] = entity["entity_id"]
            projections.append(
                EntityWordProjection(
                    entity_id=entity["entity_id"],
                    entity_type=entity["entity_type"],
                    entity_word=word,
                    normalized_key=normalized_key,
                    source=source,
                )
            )
    return projections
