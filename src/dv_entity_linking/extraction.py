"""Query-level entity mention extraction."""

from __future__ import annotations

import re

from .catalog import CatalogRepository, normalize_text
from .llm import LLMClient, LLMError
from .models import (
    EntityMention,
    EntityType,
    ErrorCode,
    ExtractionResult,
    MentionSource,
    RunMode,
)


ALARM_ID_IN_TEXT = re.compile(r"(?<![A-Za-z0-9])ALM-\d+(?![A-Za-z0-9])", re.IGNORECASE)
ALARM_NUMBER_AFTER_KEYWORD = re.compile(
    r"(?i)(?:\balarm\b|告警)\s*(?:id|number|编号|号)?\s*[:：#-]?\s*(\d+)"
)
ALARM_INTENT_PATTERN = re.compile(r"(?i)\balarm\b|告警|ALM-\d+")
UNKNOWN_ENTITY_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?=[A-Za-z0-9_.()/-]*\d)"
    r"[A-Za-z][A-Za-z0-9_.]*(?:[-_/().][A-Za-z0-9_.()]+)+"
    r"(?![A-Za-z0-9_])"
)
MULTI_TYPE_INTENT_PATTERN = re.compile(
    r"(?i)\b(show|check|query|open|compare|run|metrics?|kpi|usage|speed|iops|monitor|monitoring|abnormal)\b"
    r"|查询|查看|指标|网元|告警"
)
MULTI_TYPE_NOT_REQUIRED_PATTERN = re.compile(
    r"(?i)\b(dashboard|system health|health summary|operations dashboard)\b"
)


class EntityExtractor:
    def __init__(self, catalog: CatalogRepository, llm_client: LLMClient | None = None) -> None:
        self.catalog = catalog
        self.llm_client = llm_client

    def extract(
        self,
        query: str,
        *,
        mode: RunMode = RunMode.OFFLINE_DEMO,
        entity_type_hints: list[EntityType] | None = None,
        allow_fallback: bool = True,
    ) -> ExtractionResult:
        if not query or not query.strip():
            return ExtractionResult(
                mentions=[],
                degraded=False,
                error_code=ErrorCode.INVALID_INPUT,
                llm_used=False,
            )

        if mode == RunMode.LLM_ENABLED_DEMO and self.llm_client:
            try:
                extraction = self._extract_with_llm(query)
                if self._is_alarm_only_hint(entity_type_hints):
                    return self._constrain_alarm_llm_result(query, extraction)
                return extraction
            except LLMError as exc:
                if not allow_fallback:
                    return ExtractionResult(
                        mentions=[],
                        degraded=True,
                        error_code=ErrorCode.DEPENDENCY_FAILED,
                        llm_used=True,
                        fallback_available=False,
                    )
                fallback = self._extract_deterministic(query, entity_type_hints=entity_type_hints)
                return ExtractionResult(
                    mentions=fallback.mentions,
                    degraded=True,
                    error_code=exc.error_code,
                    llm_used=True,
                    fallback_available=True,
                    not_required=fallback.not_required,
                    bypass_reason=fallback.bypass_reason,
                )

        return self._extract_deterministic(query, entity_type_hints=entity_type_hints)

    def _extract_with_llm(self, query: str) -> ExtractionResult:
        result = self.llm_client.complete_json(
            "extract_entities",
            [
                {
                    "role": "system",
                    "content": (
                        "Return only one valid JSON object for EntityMentionList. "
                        "Use schema {\"mentions\":[{\"text\":string,"
                        "\"predicted_type\":string,\"span\":[start,end]}]}. "
                        "The predicted_type value must be one of: "
                        "alarm, network_resource, alarm_event, kpi_metric, "
                        "topology_relation, knowledge_case, ne_type, ne_name, "
                        "kpi_task_name, kpi_meas_objects, kpi_meas_type_key. "
                        "Omit span when unsure."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "EntityMentionList",
        )
        raw_mentions = result.data.get("mentions")
        if not isinstance(raw_mentions, list):
            raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "mentions must be a list")
        mentions: list[EntityMention] = []
        for raw in raw_mentions:
            if not isinstance(raw, dict) or not raw.get("text"):
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "mention.text is required")
            predicted_type = raw.get("predicted_type")
            try:
                normalized_type = EntityType(predicted_type) if predicted_type else None
            except ValueError as exc:
                raise LLMError(ErrorCode.LLM_SCHEMA_ERROR, "invalid predicted_type") from exc
            mentions.append(
                EntityMention(
                    text=str(raw["text"]),
                    span=tuple(raw["span"]) if raw.get("span") else None,
                    predicted_type=normalized_type,
                    source=MentionSource.LLM,
                )
            )
        return ExtractionResult(mentions=mentions, degraded=False, llm_used=True)

    def _constrain_alarm_llm_result(
        self,
        query: str,
        extraction: ExtractionResult,
    ) -> ExtractionResult:
        mentions: list[EntityMention] = []
        for mention in extraction.mentions:
            if mention.predicted_type == EntityType.ALARM:
                mentions.append(mention)
            elif mention.predicted_type is None and self._looks_like_alarm_identifier(mention.text):
                mentions.append(
                    EntityMention(
                        text=mention.text,
                        span=mention.span,
                        predicted_type=EntityType.ALARM,
                        source=mention.source,
                    )
                )
        if mentions:
            return ExtractionResult(
                mentions=mentions[:1],
                degraded=extraction.degraded,
                error_code=extraction.error_code,
                llm_used=extraction.llm_used,
                fallback_available=extraction.fallback_available,
            )

        fallback = self._extract_alarm_deterministic(query)
        return ExtractionResult(
            mentions=fallback.mentions,
            degraded=extraction.degraded,
            error_code=extraction.error_code,
            llm_used=extraction.llm_used,
            fallback_available=extraction.fallback_available,
            not_required=fallback.not_required,
            bypass_reason=fallback.bypass_reason,
        )

    def _extract_deterministic(
        self,
        query: str,
        *,
        entity_type_hints: list[EntityType] | None = None,
    ) -> ExtractionResult:
        if self._is_alarm_only_hint(entity_type_hints):
            return self._extract_alarm_deterministic(query)

        matches: list[tuple[int, int, str, EntityType | None]] = []
        for entity in self.catalog.entities:
            if entity_type_hints and entity.entity_type not in entity_type_hints:
                continue
            for name in [entity.canonical_name, *entity.aliases]:
                for start, end in self._literal_spans(query, name):
                    matches.append((start, end, query[start:end], entity.entity_type))

        matches.extend(self._unknown_multi_type_spans(query))

        # Prefer longest non-overlapping mentions for stable offline behavior.
        matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
        accepted: list[tuple[int, int, str, EntityType | None]] = []
        occupied: set[int] = set()
        for start, end, text, entity_type in matches:
            positions = set(range(start, end))
            if occupied & positions:
                continue
            occupied.update(positions)
            accepted.append((start, end, text, entity_type))

        mentions = [
            EntityMention(
                text=text,
                span=(start, end),
                predicted_type=entity_type,
                source=MentionSource.DETERMINISTIC,
            )
            for start, end, text, entity_type in sorted(accepted)
        ]
        if not mentions and (
            self._looks_not_required_multi_type(query)
            or not self._has_multi_type_linking_intent(query)
        ):
            return ExtractionResult(
                mentions=[],
                not_required=True,
                bypass_reason="no entity-linking intent or entity-shaped mention detected",
            )
        return ExtractionResult(mentions=mentions)

    def _extract_alarm_deterministic(self, query: str) -> ExtractionResult:
        matches: list[tuple[int, int, str, EntityType | None]] = []
        for entity in self.catalog.entities:
            if entity.entity_type != EntityType.ALARM:
                continue
            for name in [entity.canonical_name, *entity.aliases]:
                for start, end in self._literal_spans(query, name):
                    matches.append((start, end, query[start:end], EntityType.ALARM))

        matches.extend(self._unknown_alarm_spans(query))
        matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2].lower()))

        accepted: list[tuple[int, int, str, EntityType | None]] = []
        occupied: set[int] = set()
        for start, end, text, entity_type in matches:
            positions = set(range(start, end))
            if occupied & positions:
                continue
            accepted.append((start, end, text, entity_type))
            occupied.update(positions)
            break

        if not accepted:
            if ALARM_INTENT_PATTERN.search(query):
                return ExtractionResult(mentions=[])
            return ExtractionResult(
                mentions=[],
                not_required=True,
                bypass_reason="no alarm intent or alarm-shaped mention detected",
            )

        return ExtractionResult(
            mentions=[
                EntityMention(
                    text=text,
                    span=(start, end),
                    predicted_type=entity_type,
                    source=MentionSource.DETERMINISTIC,
                )
                for start, end, text, entity_type in accepted
            ]
        )

    @staticmethod
    def _is_alarm_only_hint(entity_type_hints: list[EntityType] | None) -> bool:
        return entity_type_hints == [EntityType.ALARM]

    @staticmethod
    def _looks_like_alarm_identifier(text: str) -> bool:
        return re.fullmatch(r"(?i)(?:ALM-\d+|\d+)", text.strip()) is not None

    @staticmethod
    def _literal_spans(query: str, literal: str) -> list[tuple[int, int]]:
        if not literal:
            return []
        spans: list[tuple[int, int]] = []
        for match in re.finditer(re.escape(literal), query, re.IGNORECASE):
            start, end = match.span()
            if EntityExtractor._has_token_boundary(query, start, end):
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
    def _unknown_alarm_spans(query: str) -> list[tuple[int, int, str, EntityType | None]]:
        spans: list[tuple[int, int, str, EntityType | None]] = []
        for match in ALARM_ID_IN_TEXT.finditer(query):
            start, end = match.span()
            spans.append((start, end, query[start:end], EntityType.ALARM))
        for match in ALARM_NUMBER_AFTER_KEYWORD.finditer(query):
            start, end = match.span(1)
            spans.append((start, end, query[start:end], EntityType.ALARM))
        return spans

    @staticmethod
    def _unknown_multi_type_spans(query: str) -> list[tuple[int, int, str, EntityType | None]]:
        spans: list[tuple[int, int, str, EntityType | None]] = []
        for match in UNKNOWN_ENTITY_TOKEN.finditer(query):
            start, end = match.span()
            spans.append((start, end, query[start:end], None))
        return spans

    @staticmethod
    def _has_multi_type_linking_intent(query: str) -> bool:
        return MULTI_TYPE_INTENT_PATTERN.search(query) is not None

    @staticmethod
    def _looks_not_required_multi_type(query: str) -> bool:
        return MULTI_TYPE_NOT_REQUIRED_PATTERN.search(query) is not None
