"""Entity lookup and Top-K related entity retrieval."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .catalog import CatalogRepository, normalize_text
from .models import EntityRecord, RetrievalItem, RetrievalResult, Status, clamp_score


class EntityRetriever:
    def __init__(self, catalog: CatalogRepository) -> None:
        self.catalog = catalog

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        return self.catalog.get(entity_id)

    def search_entities(
        self,
        query: str,
        *,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> list[EntityRecord]:
        return self.catalog.search(query, entity_type=entity_type, limit=limit)

    def similar_entities(self, entity_id: str, k: int = 5) -> RetrievalResult:
        k = min(max(int(k), 1), 20)
        source = self.catalog.get(entity_id)
        if not source:
            return RetrievalResult(
                status=Status.NO_MATCH,
                query_entity_id=entity_id,
                k=k,
                items=[],
                no_match_reason=f"entity not found: {entity_id}",
            )

        neighbors = {item.entity_id for item in self.catalog.neighbors(entity_id)}
        items: list[RetrievalItem] = []
        for candidate in self.catalog.entities:
            if candidate.entity_id == entity_id:
                continue
            score, reasons = self._score(source, candidate, neighbors)
            if score <= 0:
                continue
            items.append(
                RetrievalItem(
                    entity_id=candidate.entity_id,
                    canonical_name=candidate.canonical_name,
                    entity_type=candidate.entity_type,
                    score=clamp_score(score),
                    similarity_reason=", ".join(reasons),
                    source=candidate.source,
                    data_layer=candidate.data_layer,
                )
            )
        items.sort(key=lambda item: (-item.score, item.entity_id))
        return RetrievalResult(
            status=Status.LINKED if items else Status.NO_MATCH,
            query_entity_id=entity_id,
            k=k,
            items=items[:k],
            no_match_reason="" if items else "no related entities found",
        )

    def _score(
        self,
        source: EntityRecord,
        candidate: EntityRecord,
        neighbor_ids: set[str],
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        name_score = self._name_score(source, candidate)
        if name_score > 0.45:
            score += 0.30 * name_score
            reasons.append("name/alias similarity")
        desc_score = self._token_overlap(source.description, candidate.description)
        if desc_score > 0:
            score += 0.20 * desc_score
            reasons.append("description semantic overlap")
        if source.entity_type == candidate.entity_type:
            score += 0.15
            reasons.append("same entity type")
        if candidate.entity_id in neighbor_ids:
            score += 0.20
            reasons.append("topology neighbor")
        if (
            source.entity_type.value == "knowledge_case"
            or candidate.entity_type.value == "knowledge_case"
        ):
            linked = any(
                relation.target_entity_id == candidate.entity_id
                for relation in source.relations
            ) or any(
                relation.target_entity_id == source.entity_id
                for relation in candidate.relations
            )
            if linked:
                score += 0.15
                reasons.append("knowledge/case relation")
        return clamp_score(score), reasons

    @staticmethod
    def _name_score(source: EntityRecord, candidate: EntityRecord) -> float:
        left_names = [source.canonical_name, *source.aliases]
        right_names = [candidate.canonical_name, *candidate.aliases]
        return max(
            SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()
            for left in left_names
            for right in right_names
        )

    @staticmethod
    def _token_overlap(left: str, right: str) -> float:
        left_tokens = {token.lower() for token in re.findall(r"[\w]+", left)}
        right_tokens = {token.lower() for token in re.findall(r"[\w]+", right)}
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
