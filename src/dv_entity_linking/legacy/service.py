"""Application service orchestration for entity linking."""

from __future__ import annotations

from pathlib import Path

from .catalog import CatalogRepository
from .evaluation import RunRepository, build_run_record
from .extraction import EntityExtractor
from .linking import EntityLinker
from .llm import LLMClient
from .models import DataLayer, EntityLinkResult, EntityType, RunMode
from .ner_pipeline import NerPipeline
from .retrieval import EntityRetriever
from .storage import EntityStorageRepository, V3CatalogAdapter


class EntityLinkingService:
    def __init__(
        self,
        catalog: CatalogRepository,
        *,
        llm_client: LLMClient | None = None,
        run_repository: RunRepository | None = None,
        v3_pipeline: NerPipeline | None = None,
    ) -> None:
        self.catalog = catalog
        self.llm_client = llm_client
        self.run_repository = run_repository
        self.v3_pipeline = v3_pipeline
        self._rebuild_runtime_components()

    def _rebuild_runtime_components(self) -> None:
        self.extractor = EntityExtractor(self.catalog, llm_client=self.llm_client)
        self.linker = EntityLinker(self.catalog, llm_client=self.llm_client)
        self.retriever = EntityRetriever(self.catalog)
        self.alarm_only = bool(self.catalog.entities) and all(
            entity.entity_type == EntityType.ALARM for entity in self.catalog.entities
        )

    def configure_llm_client(self, llm_client: LLMClient | None) -> None:
        self.llm_client = llm_client
        self._rebuild_runtime_components()

    def ensure_catalog_loaded(self) -> None:
        self.catalog.load()
        self._rebuild_runtime_components()

    @classmethod
    def from_catalog_path(
        cls,
        catalog_path: str | Path = "samples/mock/entity_catalog.json",
        *,
        allowed_data_layers: list[DataLayer | str] | None = None,
        data_layer_confirmation_path: str | Path | None = None,
        llm_client: LLMClient | None = None,
        run_repository: RunRepository | None = None,
    ) -> "EntityLinkingService":
        catalog = CatalogRepository(
            catalog_path,
            allowed_data_layers=allowed_data_layers,
            data_layer_confirmation_path=data_layer_confirmation_path,
        )
        catalog.load()
        return cls(catalog, llm_client=llm_client, run_repository=run_repository)

    @classmethod
    def from_v3_mock(
        cls,
        *,
        gauss_mock_path: str | Path = "samples/real/v3_gauss_entities.json",
        redis_mock_path: str | Path = "samples/real/v3_redis_entity_words.json",
        llm_client: LLMClient | None = None,
        run_repository: RunRepository | None = None,
    ) -> "EntityLinkingService":
        storage_repository = EntityStorageRepository.load_from_paths(
            gauss_path=gauss_mock_path,
            redis_path=redis_mock_path,
        )
        catalog = V3CatalogAdapter(storage_repository)
        return cls(
            catalog,
            llm_client=llm_client,
            run_repository=run_repository,
            v3_pipeline=NerPipeline(storage_repository),
        )

    def link_query(
        self,
        query: str,
        *,
        mode: RunMode = RunMode.OFFLINE_DEMO,
        persist_run: bool = False,
        allow_fallback: bool = True,
    ) -> EntityLinkResult:
        self.ensure_catalog_loaded()
        run_mode = RunMode(mode)
        if self.v3_pipeline is not None:
            result = self.v3_pipeline.run(
                query,
                mode=run_mode,
                allow_fallback=allow_fallback,
            )
            if persist_run and self.run_repository:
                self.run_repository.append(
                    build_run_record(
                        mode=run_mode,
                        query=query,
                        result={
                            "summary": {
                                "status": result.status.value,
                                "entity_ids": [
                                    item.linked_entity.entity_id
                                    for item in result.mention_results
                                    if item.linked_entity
                                ],
                                "error_code": result.error_code.value if result.error_code else "",
                            }
                        },
                        llm_used=False,
                        degraded=result.degraded,
                    )
                )
            return result
        entity_type_hints = [EntityType.ALARM] if self.alarm_only else None
        extraction = self.extractor.extract(
            query,
            mode=run_mode,
            entity_type_hints=entity_type_hints,
            allow_fallback=allow_fallback,
        )
        result = self.linker.link(
            query,
            extraction.mentions,
            degraded=extraction.degraded,
            error_code=extraction.error_code,
            fallback_available=extraction.fallback_available,
            not_required=extraction.not_required,
            bypass_reason=extraction.bypass_reason,
            use_llm=run_mode == RunMode.LLM_ENABLED_DEMO and self.llm_client is not None,
        )
        if persist_run and self.run_repository:
            self.run_repository.append(
                build_run_record(
                    mode=run_mode,
                    query=query,
                    result={
                        "summary": {
                            "status": result.status.value,
                            "entity_ids": [
                                item.linked_entity.entity_id
                                for item in result.mention_results
                                if item.linked_entity
                            ],
                            "error_code": result.error_code.value if result.error_code else "",
                        }
                    },
                    llm_used=extraction.llm_used,
                    degraded=result.degraded,
                )
            )
        return result
