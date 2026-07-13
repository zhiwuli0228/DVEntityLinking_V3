from __future__ import annotations

import json

import pytest

from dv_entity_linking.catalog import CatalogError, CatalogRepository
from dv_entity_linking.models import DataLayer, EntityType, ErrorCode


def test_l0_catalog_loads_with_required_coverage(catalog):
    result = catalog.load()

    assert result.entity_count >= 20
    v0_entity_types = {
        EntityType.NETWORK_RESOURCE.value,
        EntityType.ALARM_EVENT.value,
        EntityType.KPI_METRIC.value,
        EntityType.TOPOLOGY_RELATION.value,
        EntityType.KNOWLEDGE_CASE.value,
    }
    assert set(result.type_counts) == v0_entity_types
    assert all(count >= 2 for count in result.type_counts.values())
    assert {entity.data_layer for entity in catalog.entities} == {DataLayer.L0_SYNTHETIC}
    assert all(entity.source for entity in catalog.entities)


def test_non_l0_catalog_requires_confirmation(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "entity_id": "REAL-1",
                        "entity_type": "network_resource",
                        "canonical_name": "Local Real Entity",
                        "aliases": [],
                        "relations": [],
                        "data_layer": "LOCAL_REAL_ARTIFACT",
                        "source": "local_real_dv_ignored",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    repository = CatalogRepository(
        catalog_file,
        allowed_data_layers=[DataLayer.LOCAL_REAL_ARTIFACT],
    )

    with pytest.raises(CatalogError) as exc_info:
        repository.load()

    assert exc_info.value.error_code == ErrorCode.DATA_LAYER_NOT_CONFIRMED


def test_relation_source_and_data_layer_are_required(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "entity_id": "NE-1",
                        "entity_type": "network_resource",
                        "canonical_name": "Node One",
                        "aliases": [],
                        "relations": [
                            {
                                "target_entity_id": "NE-2",
                                "relation_type": "connects",
                            }
                        ],
                        "data_layer": "L0_SYNTHETIC",
                        "source": "mock_catalog",
                    },
                    {
                        "entity_id": "NE-2",
                        "entity_type": "network_resource",
                        "canonical_name": "Node Two",
                        "aliases": [],
                        "relations": [],
                        "data_layer": "L0_SYNTHETIC",
                        "source": "mock_catalog",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    repository = CatalogRepository(catalog_file)

    with pytest.raises(CatalogError) as exc_info:
        repository.load()

    assert exc_info.value.error_code == ErrorCode.CATALOG_LOAD_FAILED
    assert "missing required relation fields" in str(exc_info.value)


def test_search_uses_alias_index(catalog):
    matches = catalog.search("RAN-A1")

    assert matches
    assert matches[0].entity_id == "NE-DV-RAN-001"
