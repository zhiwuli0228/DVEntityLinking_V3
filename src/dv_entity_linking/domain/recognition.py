"""Deterministic V4 NER policies independent from storage and transport."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalization import NormalizedQuery
from .ports import EntityWordMatch, ExtractedMention


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
NOT_REQUIRED_PATTERN = re.compile(r"(?i)\b(dashboard|system health|health summary|operations dashboard)\b")
NUMERIC_ALARM_TOKEN = re.compile(r"(?i)(?<=\balarm\s)\d+(?![A-Za-z0-9])")


@dataclass(frozen=True)
class DetectedMention:
    text: str
    span: tuple[int, int]
    source: str
    match: EntityWordMatch | None = None
    confidence: float | None = None
    predicted_type_hint: str | None = None

    @property
    def predicted_type(self) -> str | None:
        return self.match.entity_type if self.match else self.predicted_type_hint


def needs_linking(query: str) -> bool:
    """Return False only for an unambiguous dashboard request before remote recall.

    Other phrases such as ``system health`` can contain a known entity word (for
    example ``SYSTEM``), so preserving V3 semantics requires normal recognition.
    """
    lowered = query.casefold()
    return "dashboard" not in lowered and "system health summary" not in lowered


def restore_known_mentions(normalized: NormalizedQuery, matches: tuple[EntityWordMatch, ...]) -> list[DetectedMention]:
    mentions: list[DetectedMention] = []
    for match in matches:
        start = normalized.normalized_text.find(match.normalized_key)
        while start >= 0:
            end = start + len(match.normalized_key)
            span = normalized.restore_span(start, end)
            if span is not None and is_confirmed(normalized.original_text, span, match):
                mentions.append(
                    DetectedMention(
                        text=normalized.original_text[span[0] : span[1]],
                        span=span,
                        source="database_word_match",
                        match=match,
                    )
                )
            start = normalized.normalized_text.find(match.normalized_key, start + 1)
    return mentions


def detect_unknown_mentions(query: str) -> list[DetectedMention]:
    """Recognize entity-shaped text without relying on database recall.

    This is intentionally independent from known-word matches: V4 treats local
    rules as a parallel mention source, then resolves overlap in one merge step.
    """
    results: list[DetectedMention] = []
    for match in ENTITY_SHAPED_TOKEN.finditer(query):
        start, end = match.span()
        while end > start and query[end - 1] in ".,;:!?":
            end -= 1
        span = (start, end)
        if start == end:
            continue
        results.append(DetectedMention(text=query[start:end], span=span, source="deterministic_unknown"))
    for match in NUMERIC_ALARM_TOKEN.finditer(query):
        span = match.span()
        results.append(DetectedMention(text=match.group(), span=span, source="deterministic_unknown"))
    return select_non_overlapping(results)


def validate_extracted_mentions(
    query: str, extracted: tuple[ExtractedMention, ...]
) -> list[DetectedMention]:
    """Accept only schema-valid mentions that map exactly back to the source query."""
    validated: list[DetectedMention] = []
    for item in extracted:
        start, end = item.span
        if start < 0 or end <= start or end > len(query) or query[start:end] != item.text:
            continue
        if not 0.0 <= item.confidence <= 1.0:
            continue
        validated.append(
            DetectedMention(
                text=item.text,
                span=item.span,
                source=item.source,
                confidence=item.confidence,
                predicted_type_hint=item.predicted_type,
            )
        )
    return validated


def select_non_overlapping(mentions: list[DetectedMention]) -> list[DetectedMention]:
    """Retain earliest, longest, then highest-priority mentions with an explainable order."""
    selected: list[DetectedMention] = []
    occupied: set[int] = set()
    for item in sorted(
        mentions,
        key=lambda value: (
            -(value.match.priority if value.match else 0),
            value.span[0],
            -(value.span[1] - value.span[0]),
            value.text,
        ),
    ):
        positions = set(range(*item.span))
        if positions.intersection(occupied):
            continue
        selected.append(item)
        occupied.update(positions)
    return sorted(selected, key=lambda value: value.span)


def is_confirmed(query: str, span: tuple[int, int], match: EntityWordMatch) -> bool:
    start, end = span
    if match.match_mode in {"EXACT_WORD", "STRUCTURED_TOKEN"}:
        if start > 0 and _is_ascii_alnum(query[start - 1]):
            return False
        if end < len(query) and _is_ascii_alnum(query[end]):
            return False
    if match.match_mode == "CONTEXT_REQUIRED" or match.min_context_required:
        lowered = query.casefold()
        if not match.context_keywords or not any(keyword.casefold() in lowered for keyword in match.context_keywords):
            return False
    return True


def _is_ascii_alnum(value: str) -> bool:
    return value.isascii() and value.isalnum()
