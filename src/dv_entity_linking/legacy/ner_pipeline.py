"""V3 storage-backed NER pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import (
    DataLayer,
    EntityLinkResult,
    EntityMention,
    ErrorCode,
    LinkCandidate,
    MentionLinkResult,
    MentionSource,
    ResultSource,
    RunMode,
    Status,
    StorageLookupStatus,
    clamp_score,
)
from .storage import EntityStorageRepository, normalize_entity_word


ENTITY_SHAPED_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?=[A-Za-z0-9_.()/-]*\d)"
    r"[A-Za-z][A-Za-z0-9_.]*(?:[-_/().][A-Za-z0-9_.()]+)+"
    r"(?![A-Za-z0-9_])"
)
LINKING_INTENT_PATTERN = re.compile(
    r"(?i)\b(show|check|query|open|compare|run|metrics?|kpi|usage|speed|iops|monitor|monitoring|abnormal|alarm)\b"
    r"|查询|查看|指标|网元|告警"
)
NOT_REQUIRED_PATTERN = re.compile(
    r"(?i)\b(dashboard|system health|health summary|operations dashboard)\b"
)


@dataclass(frozen=True)
class _DetectedMention:
    text: str
    span: tuple[int, int]
    source: MentionSource


class NerPipeline:
    def __init__(self, storage_repository: EntityStorageRepository) -> None:
        self.storage_repository = storage_repository

    def run(
        self,
        query: str,
        *,
        mode: RunMode = RunMode.OFFLINE_DEMO,
        allow_fallback: bool = True,
    ) -> EntityLinkResult:
        stage_trace: list[dict[str, Any]] = []
        if not isinstance(query, str) or not query.strip():
            stage_trace.append(
                self._stage(
                    "query_validation",
                    "invalid_input",
                    error_code=ErrorCode.INVALID_INPUT.value,
                    degraded=False,
                    summary="query is empty",
                )
            )
            return EntityLinkResult(
                query=query,
                status=Status.INVALID_INPUT,
                error_code=ErrorCode.INVALID_INPUT,
                no_match_reason="query is empty",
                source="v3_storage_mock",
                stage_trace=stage_trace,
            )

        stage_trace.append(self._stage("query_validation", "used", summary="query accepted"))
        known_mentions = self._detect_known_mentions(query)
        unknown_mentions = self._detect_unknown_mentions(query, known_mentions)
        detected = sorted([*known_mentions, *unknown_mentions], key=lambda item: item.span)
        has_intent = self._has_linking_intent(query)
        if not detected and self._looks_not_required(query):
            has_intent = False
        stage_trace.append(
            self._stage(
                "need_linking",
                "used",
                summary="entity-linking intent detected" if has_intent or detected else "no entity-linking intent",
            )
        )
        stage_trace.append(
            self._stage(
                "mention_detection",
                "used" if detected else "not_used",
                output_summary={"mention_count": len(detected)},
            )
        )

        if not detected:
            if not has_intent:
                return EntityLinkResult(
                    query=query,
                    status=Status.NOT_REQUIRED,
                    bypass_reason="no entity-linking intent or entity-shaped mention detected",
                    source="v3_storage_mock",
                    stage_trace=stage_trace,
                )
            return EntityLinkResult(
                query=query,
                status=Status.NO_MATCH,
                no_match_reason="no entity mention detected",
                source="v3_storage_mock",
                stage_trace=stage_trace,
            )

        mention_results = [self._link_detected_mention(item) for item in detected]
        stage_trace.append(
            self._stage(
                "storage_lookup",
                "used",
                output_summary={
                    "linked_count": sum(item.status == Status.LINKED for item in mention_results),
                    "miss_count": sum(item.status == Status.NO_MATCH for item in mention_results),
                    "dependency_failed_count": sum(item.status == Status.DEPENDENCY_FAILED for item in mention_results),
                },
            )
        )
        result_status = self._aggregate_status(mention_results)
        stage_trace.append(
            self._stage(
                "status_aggregation",
                "used",
                output_summary={"query_status": result_status.value},
            )
        )
        candidates = self._top_candidates(mention_results)
        linked_entities = [
            item.linked_entity for item in mention_results if item.linked_entity is not None
        ]
        result_error_code = next(
            (item.error_code for item in mention_results if item.error_code),
            None,
        )
        return EntityLinkResult(
            query=query,
            status=result_status,
            mentions=[item.mention for item in mention_results],
            mention_results=mention_results,
            linked_entity=linked_entities[0] if len(linked_entities) == 1 else None,
            candidates=candidates,
            confidence=candidates[0].confidence if candidates else None,
            disambiguation_reason="storage-backed exact entity-word lookup"
            if result_status in {Status.LINKED, Status.PARTIAL}
            else "",
            no_match_reason="all mentions missed storage lookup"
            if result_status == Status.NO_MATCH
            else "",
            degraded=any(item.degraded for item in mention_results),
            error_code=result_error_code,
            data_layer=DataLayer.L1_SANITIZED
            if any(item.status == Status.LINKED for item in mention_results)
            else DataLayer.L0_SYNTHETIC,
            source="v3_storage_mock",
            stage_trace=stage_trace,
        )

    def _link_detected_mention(self, detected: _DetectedMention) -> MentionLinkResult:
        word_result, entity_result = self.storage_repository.lookup(detected.text)
        storage_lookup = {
            "entity_word_key": word_result.entity_word_key,
            "normalized_key": word_result.normalized_key,
            "redis_status": word_result.status.value,
            "redis_error_code": word_result.error_code.value if word_result.error_code else "",
            "gauss_status": "",
            "gauss_error_code": "",
            "entity_id": word_result.entity_id or "",
        }
        if word_result.status != StorageLookupStatus.HIT or entity_result is None:
            mention = EntityMention(
                text=detected.text,
                span=detected.span,
                predicted_type=None,
                source=detected.source,
            )
            return MentionLinkResult(
                mention=mention,
                status=Status.NO_MATCH
                if word_result.status in {StorageLookupStatus.MISS, StorageLookupStatus.INVALID_KEY}
                else Status.DEPENDENCY_FAILED,
                no_match_reason=f"no Redis entity-word hit for '{detected.text}'"
                if word_result.status == StorageLookupStatus.MISS
                else "",
                degraded=word_result.status == StorageLookupStatus.DEPENDENCY_FAILED,
                error_code=ErrorCode.DEPENDENCY_FAILED
                if word_result.status == StorageLookupStatus.DEPENDENCY_FAILED
                else None,
                source="v3_storage_mock",
                data_layer=DataLayer.L0_SYNTHETIC,
                storage_lookup=storage_lookup,
            )

        storage_lookup["gauss_status"] = entity_result.status.value
        storage_lookup["gauss_error_code"] = entity_result.error_code.value if entity_result.error_code else ""
        if entity_result.status != StorageLookupStatus.HIT or entity_result.entity_record is None:
            mention = EntityMention(
                text=detected.text,
                span=detected.span,
                predicted_type=None,
                source=detected.source,
            )
            return MentionLinkResult(
                mention=mention,
                status=Status.DEPENDENCY_FAILED,
                no_match_reason="Redis entity ID was not found in Gauss mock",
                degraded=True,
                error_code=ErrorCode.DEPENDENCY_FAILED,
                source="v3_storage_mock",
                data_layer=DataLayer.L0_SYNTHETIC,
                storage_lookup=storage_lookup,
            )

        entity = entity_result.entity_record.to_entity_record()
        mention = EntityMention(
            text=detected.text,
            span=detected.span,
            predicted_type=entity.entity_type,
            source=detected.source,
        )
        candidate = LinkCandidate(
            entity_id=entity.entity_id,
            entity_name=entity.entity_name,
            entity_type=entity.entity_type,
            confidence=clamp_score(1.0),
            match_reason="storage exact entity-word match",
            rank=1,
            evidence=[
                {
                    "source": ResultSource.CONFIRMED_SAMPLE.value,
                    "redis_status": word_result.status.value,
                    "gauss_status": entity_result.status.value,
                    "normalization_version": "v3.entity_word_norm.1",
                }
            ],
        )
        return MentionLinkResult(
            mention=mention,
            status=Status.LINKED,
            linked_entity=entity,
            candidates=[candidate],
            confidence=candidate.confidence,
            disambiguation_reason="Redis entity-word hit and Gauss entity lookup hit",
            source="v3_storage_mock",
            data_layer=DataLayer.L1_SANITIZED,
            storage_lookup=storage_lookup,
        )

    def _detect_known_mentions(self, query: str) -> list[_DetectedMention]:
        matches: list[_DetectedMention] = []
        for word in sorted(self.storage_repository.entity_words, key=lambda item: (-len(item), item)):
            for span in self._literal_spans(query, word):
                matches.append(
                    _DetectedMention(
                        text=query[span[0] : span[1]],
                        span=span,
                        source=MentionSource.DETERMINISTIC,
                    )
                )
        return self._longest_non_overlapping(matches)

    def _detect_unknown_mentions(
        self,
        query: str,
        known_mentions: list[_DetectedMention],
    ) -> list[_DetectedMention]:
        occupied = {position for mention in known_mentions for position in range(*mention.span)}
        matches: list[_DetectedMention] = []
        for match in ENTITY_SHAPED_TOKEN.finditer(query):
            span = match.span()
            span = self._trim_terminal_punctuation(query, span)
            if occupied & set(range(*span)):
                continue
            matches.append(
                _DetectedMention(
                    text=query[span[0] : span[1]],
                    span=span,
                    source=MentionSource.DETERMINISTIC,
                )
            )
        return self._longest_non_overlapping(matches)

    @staticmethod
    def _trim_terminal_punctuation(query: str, span: tuple[int, int]) -> tuple[int, int]:
        start, end = span
        while end > start and query[end - 1] in ".,;:!?":
            end -= 1
        return start, end

    @staticmethod
    def _literal_spans(query: str, literal: str) -> list[tuple[int, int]]:
        if not literal:
            return []
        spans: list[tuple[int, int]] = []
        for match in re.finditer(re.escape(literal), query, re.IGNORECASE):
            start, end = match.span()
            if NerPipeline._has_token_boundary(query, start, end):
                spans.append((start, end))
        return spans

    @staticmethod
    def _has_token_boundary(query: str, start: int, end: int) -> bool:
        before = query[start - 1] if start > 0 else ""
        after = query[end] if end < len(query) else ""
        if before and before.isascii() and before.isalnum():
            return False
        if after and after.isascii() and after.isalnum():
            return False
        return True

    @staticmethod
    def _longest_non_overlapping(matches: list[_DetectedMention]) -> list[_DetectedMention]:
        accepted: list[_DetectedMention] = []
        occupied: set[int] = set()
        for item in sorted(matches, key=lambda match: (match.span[0], -(match.span[1] - match.span[0]), match.text)):
            positions = set(range(*item.span))
            if occupied & positions:
                continue
            occupied.update(positions)
            accepted.append(item)
        return sorted(accepted, key=lambda item: item.span)

    @staticmethod
    def _aggregate_status(mention_results: list[MentionLinkResult]) -> Status:
        if any(item.status == Status.DEPENDENCY_FAILED for item in mention_results):
            return Status.PARTIAL if any(item.status == Status.LINKED for item in mention_results) else Status.DEPENDENCY_FAILED
        linked_count = sum(item.status == Status.LINKED for item in mention_results)
        if linked_count == len(mention_results):
            return Status.LINKED
        if linked_count > 0:
            return Status.PARTIAL
        if any(item.status == Status.AMBIGUOUS for item in mention_results):
            return Status.AMBIGUOUS
        return Status.NO_MATCH

    @staticmethod
    def _top_candidates(mention_results: list[MentionLinkResult]) -> list[LinkCandidate]:
        candidates: list[LinkCandidate] = []
        seen: set[str] = set()
        for result in mention_results:
            for candidate in result.candidates:
                if candidate.entity_id in seen:
                    continue
                seen.add(candidate.entity_id)
                candidates.append(candidate)
        return sorted(candidates, key=lambda item: (-item.confidence, item.entity_id))

    @staticmethod
    def _has_linking_intent(query: str) -> bool:
        return LINKING_INTENT_PATTERN.search(query) is not None

    @staticmethod
    def _looks_not_required(query: str) -> bool:
        return NOT_REQUIRED_PATTERN.search(query) is not None

    @staticmethod
    def _stage(
        stage: str,
        status: str,
        *,
        input_summary: Any = "",
        output_summary: Any = "",
        error_code: str = "",
        degraded: bool = False,
        summary: Any = "",
    ) -> dict[str, Any]:
        safe_summary = summary or output_summary or status
        return {
            "stage": stage,
            "status": status,
            "stage_status": status,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "error_code": error_code,
            "degraded": degraded,
            "safe_summary": safe_summary,
        }
