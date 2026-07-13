from __future__ import annotations

from pathlib import Path

import pytest

from dv_entity_linking.catalog import CatalogRepository
from dv_entity_linking.service import EntityLinkingService


@pytest.fixture()
def catalog_path() -> Path:
    return Path("samples/mock/entity_catalog.json")


@pytest.fixture()
def catalog(catalog_path: Path) -> CatalogRepository:
    repository = CatalogRepository(catalog_path)
    repository.load()
    return repository


@pytest.fixture()
def service(catalog: CatalogRepository) -> EntityLinkingService:
    return EntityLinkingService(catalog)

