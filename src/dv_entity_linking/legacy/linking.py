"""Entity candidate generation and disambiguation."""

from __future__ import annotations

from difflib import SequenceMatcher

from .alarm_index import AlarmIndexBundle
from .catalog import CatalogRepository, normalize_text
from .llm import LLMClient, LLMError
from .models import (
    DataLayer,
    EntityLinkResult,
    EntityMention,
    EntityType,
    ErrorCode,
    LinkCandidate,
    MentionLinkResult,
    ResultSource,
    Status,
    clamp_score,
)


class EntityLinker:
    def __init__(
        self,
        catalog: CatalogRepository,
        *,
        llm_client: LLMClient | None = None,
        link_min_confidence: float = 0.70,
        ambiguity_margin: float = 0.08,
        llm_rerank_min_confidence: float = 0.70,
        max_candidates: int = 5,
    ) -> None:
        self.catalog = catalog
        self.llm_client = llm_client
        self.link_min_confidence = link_min_confidence
        self.ambiguity_margin = ambiguity_margin
        self.llm_rerank_min_confidence = llm_rerank_min_confidence
        self.max_candidates = max_candidates
        self.alarm_only = bool(catalog.entities) and all(
            entity.entity_type == EntityType.ALARM for entity in catalog.entities
        )
        self.alarm_index = AlarmIndexBundle(catalog)

    def link(
        self,
        query: str,
        mentions: list[EntityMention],
        *,
        degraded: bool = False,
        error_code: ErrorCode | None = None,
        fallback_available: bool = True,
        not_required: bool = False,
        bypass_reason: str = "",
        use_llm: bool = False,
    ) -> EntityLinkResult:
        if not query or not query.strip():
            return EntityLinkResult(
                query=query,
                status=Status.INVALID_INPUT,
                degraded=degraded,
                error_code=error_code or ErrorCode.INVALID_INPUT,
                no_match_reason="query is empty",
            )
        if not mentions:
            if not_required:
                return EntityLinkResult(
                    query=query,
                    status=Status.NOT_REQUIRED,
                    mentions=[],
                    mention_results=[],
                    candidates=[],
                    bypass_reason=bypass_reason or "entity linking is not required for this query",
                    degraded=degraded,
                    error_code=error_code,
                    source=ResultSource.NONE.value,
                )
            if error_code == ErrorCode.DEPENDENCY_FAILED or not fallback_available:
                return EntityLinkResult(
                    query=query,
                    status=Status.DEPENDENCY_FAILED,
                    mentions=[],
                    mention_results=[],
                    degraded=True,
                    error_code=ErrorCode.DEPENDENCY_FAILED,
                    no_match_reason="dependency failed and fallback is unavailable",
                    source=ResultSource.NONE.value,
                )
            return EntityLinkResult(
                query=query,
                status=Status.NO_MATCH,
                mentions=[],
                mention_results=[],
                degraded=degraded,
                error_code=error_code,
                no_match_reason="no entity mention detected",
            )

        mention_results = [
            self._link_mention(mention, degraded=degraded, error_code=error_code)
            for mention in mentions
        ]
        if use_llm and self.llm_client:
            mention_results = [
                self._llm_disambiguate(result) if result.status == Status.AMBIGUOUS else result
                for result in mention_results
            ]
        result_degraded = degraded or any(result.degraded for result in mention_results)
        result_error_code = error_code or next(
            (result.error_code for result in mention_results if result.error_code),
            None,
        )
        status = self._aggregate_status(
            mention_results,
            degraded=result_degraded,
            error_code=result_error_code,
            fallback_available=fallback_available,
            partial_on_degraded=not self.alarm_only,
        )
        top_candidates: list[LinkCandidate] = []
        seen_candidate_ids: set[str] = set()
        for result in mention_results:
            for candidate in result.candidates:
                if candidate.entity_id in seen_candidate_ids:
                    continue
                seen_candidate_ids.add(candidate.entity_id)
                top_candidates.append(candidate)
        top_candidates.sort(key=lambda item: (-item.confidence, item.entity_id))
        linked_entities = [
            result.linked_entity
            for result in mention_results
            if result.linked_entity is not None
        ]
        return EntityLinkResult(
            query=query,
            status=status,
            mentions=mentions,
            mention_results=mention_results,
            linked_entity=linked_entities[0] if len(linked_entities) == 1 else None,
            candidates=top_candidates[: self.max_candidates],
            confidence=top_candidates[0].confidence if top_candidates else None,
            disambiguation_reason=self._summary_reason(mention_results),
            no_match_reason="all mentions have no candidates"
            if all(result.status == Status.NO_MATCH for result in mention_results)
            else "",
            degraded=result_degraded,
            error_code=result_error_code,
            data_layer=self._highest_data_layer(mention_results),
            source=ResultSource.FALLBACK_OFFLINE.value
            if result_degraded
            else ResultSource.OFFLINE_DETERMINISTIC.value,
        )

    def _link_mention(
        self,
        mention: EntityMention,
        *,
        degraded: bool,
        error_code: ErrorCode | None,
    ) -> MentionLinkResult:
        candidates = self._candidates_for(mention)
        if not candidates:
            return MentionLinkResult(
                mention=mention,
                status=Status.NO_MATCH,
                no_match_reason=f"no catalog candidate for mention '{mention.text}'",
                degraded=degraded,
                error_code=error_code,
            )

        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        if top.confidence < self.link_min_confidence:
            status = Status.NO_MATCH
            linked_entity = None
            if mention.predicted_type is None:
                candidates = []
            reason = ""
            no_match_reason = f"top candidate below threshold: {top.confidence:.2f}"
        elif second and top.confidence - second.confidence < self.ambiguity_margin:
            status = Status.AMBIGUOUS
            linked_entity = None
            reason = "top candidates are within ambiguity margin"
            no_match_reason = ""
        else:
            status = Status.LINKED
            linked_entity = self.catalog.get(top.entity_id)
            reason = top.match_reason
            no_match_reason = ""

        return MentionLinkResult(
            mention=mention,
            status=status,
            linked_entity=linked_entity,
            candidates=candidates,
            confidence=top.confidence,
            disambiguation_reason=reason,
            no_match_reason=no_match_reason,
            degraded=degraded,
            error_code=error_code,
            data_layer=self._highest_candidate_layer(candidates, linked_entity),
            source=ResultSource.FALLBACK_OFFLINE.value
            if degraded
            else ResultSource.OFFLINE_DETERMINISTIC.value,
        )

    def _candidates_for(self, mention: EntityMention) -> list[LinkCandidate]:
        if self.alarm_only or mention.predicted_type == EntityType.ALARM:
            return self.alarm_index.retrieve(mention, limit=self.max_candidates).candidates

        normalized_mention = normalize_text(mention.text)
        candidates: list[LinkCandidate] = []
        for entity in self.catalog.entities:
            if mention.predicted_type and entity.entity_type != mention.predicted_type:
                continue
            names = [entity.entity_name, *entity.alias]
            best_score = 0.0
            best_reason = ""
            for name in names:
                normalized_name = normalize_text(name)
                if normalized_mention == normalized_name:
                    score = 0.99 if name == entity.entity_name else 0.92
                    reason = "canonical name match" if name == entity.entity_name else "alias match"
                elif normalized_mention in normalized_name or normalized_name in normalized_mention:
                    score = 0.78
                    reason = "partial name match"
                else:
                    score = SequenceMatcher(None, normalized_mention, normalized_name).ratio() * 0.7
                    reason = "fuzzy text similarity"
                if mention.predicted_type and mention.predicted_type == entity.entity_type:
                    score += 0.05
                if score > best_score:
                    best_score = score
                    best_reason = reason
            if best_score >= 0.45:
                candidates.append(
                    LinkCandidate(
                        entity_id=entity.entity_id,
                        entity_name=entity.entity_name,
                        entity_type=entity.entity_type,
                        confidence=clamp_score(best_score),
                        match_reason=best_reason,
                        evidence=[
                            {
                                "source": entity.source,
                                "data_layer": entity.data_layer.value,
                                "mention": mention.text,
                            }
                        ],
                    )
                )
        candidates.sort(key=lambda item: (-item.confidence, item.entity_id))
        return candidates[: self.max_candidates]

    def _llm_disambiguate(self, result: MentionLinkResult) -> MentionLinkResult:
        candidate_summary = [
            {
                "entity_id": candidate.entity_id,
                "entity_name": candidate.entity_name,
                "entity_type": candidate.entity_type.value,
                "confidence": candidate.confidence,
                "match_reason": candidate.match_reason,
            }
            for candidate in result.candidates
        ]
        try:
            response = self.llm_client.complete_json(
                "disambiguate_entity",
                [
                    {
                        "role": "system",
                        "content": (
                            "Return only one valid JSON object for EntityDisambiguation. "
                            "Use schema {\"selected_entity_id\":string,"
                            "\"confidence\":number,\"disambiguation_reason\":string}. "
                            "selected_entity_id must be one of the provided candidate ids."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Mention: {result.mention.text}\n"
                            f"Candidates: {candidate_summary}"
                        ),
                    }
                ],
                "EntityDisambiguation",
            )
            selected_entity_id = response.data.get("selected_entity_id")
            reason = response.data.get("disambiguation_reason") or "llm disambiguation"
            confidence = response.data.get("confidence", result.confidence or 0.0)
            if not isinstance(selected_entity_id, str):
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "selected_entity_id is required")
            candidate_ids = {candidate.entity_id for candidate in result.candidates}
            if selected_entity_id not in candidate_ids:
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "selected entity is not in candidates")
            if not isinstance(confidence, int | float):
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "confidence must be numeric")
            if float(confidence) < self.llm_rerank_min_confidence:
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "llm rerank confidence below threshold")
            entity = self.catalog.get(selected_entity_id)
            if not entity:
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "selected entity not found in catalog")
            return MentionLinkResult(
                mention=result.mention,
                status=Status.LINKED,
                linked_entity=entity,
                candidates=result.candidates,
                confidence=clamp_score(float(confidence)),
                disambiguation_reason=str(reason),
                degraded=result.degraded,
                error_code=result.error_code,
                source="llm+catalog",
                data_layer=self._highest_candidate_layer(result.candidates, entity),
            )
        except (LLMError, TypeError, ValueError) as exc:
            error_code = exc.error_code if isinstance(exc, LLMError) else ErrorCode.LLM_SCHEMA_ERROR
            return MentionLinkResult(
                mention=result.mention,
                status=result.status,
                linked_entity=result.linked_entity,
                candidates=result.candidates,
                confidence=result.confidence,
                disambiguation_reason=result.disambiguation_reason,
                no_match_reason=result.no_match_reason,
                degraded=True,
                error_code=error_code,
                source=ResultSource.FALLBACK_OFFLINE.value,
                data_layer=result.data_layer,
            )

    @staticmethod
    def _aggregate_status(
        mention_results: list[MentionLinkResult],
        *,
        degraded: bool,
        error_code: ErrorCode | None,
        fallback_available: bool = True,
        partial_on_degraded: bool = False,
    ) -> Status:
        if error_code == ErrorCode.DEPENDENCY_FAILED or not fallback_available:
            return Status.DEPENDENCY_FAILED
        if any(result.status == Status.DEPENDENCY_FAILED for result in mention_results):
            return Status.DEPENDENCY_FAILED
        linked_count = sum(result.status == Status.LINKED for result in mention_results)
        if linked_count > 0 and degraded and partial_on_degraded:
            return Status.PARTIAL
        if linked_count == len(mention_results):
            return Status.LINKED
        if linked_count > 0:
            return Status.PARTIAL
        if any(result.status == Status.AMBIGUOUS for result in mention_results):
            return Status.AMBIGUOUS
        if all(result.status == Status.NO_MATCH for result in mention_results):
            return Status.NO_MATCH
        return Status.NO_MATCH

    @staticmethod
    def _summary_reason(mention_results: list[MentionLinkResult]) -> str:
        reasons = [result.disambiguation_reason for result in mention_results if result.disambiguation_reason]
        return "; ".join(reasons)

    @staticmethod
    def _highest_data_layer(mention_results: list[MentionLinkResult]) -> DataLayer:
        for layer in [
            DataLayer.LOCAL_REAL_ARTIFACT,
            DataLayer.L3_REAL_READONLY,
            DataLayer.L2_SIMULATED_INTERFACE,
            DataLayer.L1_SANITIZED,
            DataLayer.L0_SYNTHETIC,
        ]:
            if any(result.data_layer == layer for result in mention_results):
                return layer
        return DataLayer.L0_SYNTHETIC

    def _highest_candidate_layer(
        self,
        candidates: list[LinkCandidate],
        linked_entity,
    ) -> DataLayer:
        candidate_layers: list[DataLayer] = []
        if linked_entity:
            candidate_layers.append(linked_entity.data_layer)
        for candidate in candidates:
            entity = self.catalog.get(candidate.entity_id)
            if entity:
                candidate_layers.append(entity.data_layer)
        for layer in [
            DataLayer.LOCAL_REAL_ARTIFACT,
            DataLayer.L3_REAL_READONLY,
            DataLayer.L2_SIMULATED_INTERFACE,
            DataLayer.L1_SANITIZED,
            DataLayer.L0_SYNTHETIC,
        ]:
            if layer in candidate_layers:
                return layer
        return DataLayer.L0_SYNTHETIC
