"""Small, replaceable V4 domain components used by the public facade."""

from __future__ import annotations

from .normalization import NormalizedQuery
from .ports import EntityWordMatch, ExtractedMention
from .recognition import (
    DetectedMention,
    detect_unknown_mentions,
    needs_linking,
    restore_known_mentions,
    select_non_overlapping,
)


class LinkingIntentPolicy:
    def should_link(self, query: str) -> bool:
        return needs_linking(query)


class KnownMentionRecognizer:
    def recognize(self, normalized: NormalizedQuery, matches: tuple[EntityWordMatch, ...]) -> list[DetectedMention]:
        return restore_known_mentions(normalized, matches)


class UnknownMentionRecognizer:
    def recognize(self, query: str) -> list[DetectedMention]:
        return detect_unknown_mentions(query)


class EntityTypeResolver:
    def filter(
        self,
        matches: tuple[EntityWordMatch, ...] | list[EntityWordMatch],
        mention: DetectedMention,
        extraction_hints: set[str],
    ) -> list[EntityWordMatch]:
        if len(extraction_hints) == 1:
            return [match for match in matches if match.entity_type in extraction_hints]
        if mention.match is None and mention.predicted_type is not None:
            return [match for match in matches if match.entity_type == mention.predicted_type]
        return list(matches)


class CandidateResolver:
    def resolve(self, matches: list[EntityWordMatch]) -> tuple[EntityWordMatch, ...]:
        # Priority establishes deterministic ordering; IDs are never invented.
        unique = {match.entity_id: match for match in sorted(matches, key=lambda item: (-item.priority, item.entity_id))}
        return tuple(unique.values())


class MentionSelector:
    def select(self, mentions: list[DetectedMention]) -> list[DetectedMention]:
        return select_non_overlapping(mentions)


class ResultAggregator:
    def status(self, mention_statuses: list[str], *, degraded: bool) -> str:
        linked = sum(status == "linked" for status in mention_statuses)
        ambiguous = sum(status == "ambiguous" for status in mention_statuses)
        result = "linked" if linked == len(mention_statuses) else "partial" if linked else "ambiguous" if ambiguous else "no_match"
        return "partial" if degraded and linked else result


class SafeTraceBuilder:
    """Keeps trace construction internal and restricted to safe scalar metadata."""

    def stage(self, name: str, **values: object) -> dict[str, object]:
        if not isinstance(name, str) or not name or any(not isinstance(value, (str, int, float, bool, type(None))) for value in values.values()):
            raise ValueError("trace stages accept only safe scalar metadata")
        return {"stage": name, **values}
