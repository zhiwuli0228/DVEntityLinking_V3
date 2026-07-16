"""Test-only V3 JSON storage adapter retained for migration comparisons."""

from __future__ import annotations

from pathlib import Path

from ..domain.ports import (
    EntityBatchGetResponse,
    EntityDataDependencyError,
    EntityDataRecord,
    EntityWordMatch,
    EntityWordMatchResponse,
)
from .storage import EntityStorageRepository


class V3MockEntityDataClient:
    """Explicit test double; never assembled by the V4 production factory."""

    def __init__(self, repository: EntityStorageRepository) -> None:
        self._repository = repository
        self._data_version = "v3-mock"

    @classmethod
    def from_paths(
        cls,
        *,
        gauss_mock_path: str | Path,
        redis_mock_path: str | Path,
    ) -> "V3MockEntityDataClient":
        return cls(
            EntityStorageRepository.load_from_paths(
                gauss_path=gauss_mock_path,
                redis_path=redis_mock_path,
            )
        )

    def match_words(
        self,
        normalized_query: str,
        *,
        entity_types: tuple[str, ...] = (),
        expected_data_version: str | None = None,
    ) -> EntityWordMatchResponse:
        self._assert_version(expected_data_version)
        if not self._repository.ready:
            raise EntityDataDependencyError("dependency_failed", "V3 mock storage is not ready")
        requested_types = set(entity_types)
        records: list[EntityWordMatch] = []
        for word in self._repository.word_cache.records:
            entity = self._repository.entity_store.get(word.entity_id).entity_record
            if entity is None:
                raise EntityDataDependencyError("entity_miss", "word references an unavailable entity")
            if requested_types and entity.entity_type.value not in requested_types:
                continue
            if word.normalized_key in normalized_query:
                records.append(
                    EntityWordMatch(
                        entity_word_id=f"v3:{word.normalized_key}:{word.entity_id}",
                        entity_id=word.entity_id,
                        entity_type=entity.entity_type.value,
                        entity_word=word.entity_word,
                        normalized_key=word.normalized_key,
                        source=word.source,
                    )
                )
        return EntityWordMatchResponse(matches=tuple(records), data_version=self._data_version)

    def batch_get(
        self,
        entity_ids: tuple[str, ...],
        *,
        expected_data_version: str | None = None,
    ) -> EntityBatchGetResponse:
        self._assert_version(expected_data_version)
        records: list[EntityDataRecord] = []
        missing: list[str] = []
        for entity_id in entity_ids:
            lookup = self._repository.entity_store.get(entity_id)
            entity = lookup.entity_record
            if entity is None:
                missing.append(entity_id)
                continue
            records.append(
                EntityDataRecord(
                    entity_id=entity.entity_id,
                    entity_type=entity.entity_type.value,
                    entity_name=entity.entity_name,
                    alias=tuple(entity.alias),
                    desc=entity.desc,
                    attributes=dict(entity.attributes),
                    relationships=tuple(
                        {
                            "target_entity_id": relation.target_entity_id,
                            "relation_type": relation.relation_type,
                        }
                        for relation in entity.relationships
                    ),
                )
            )
        return EntityBatchGetResponse(
            entities=tuple(records),
            missing_ids=tuple(missing),
            data_version=self._data_version,
        )

    def _assert_version(self, expected_data_version: str | None) -> None:
        if expected_data_version and expected_data_version != self._data_version:
            raise EntityDataDependencyError("data_version_mismatch")
