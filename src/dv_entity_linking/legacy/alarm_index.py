"""Alarm-only in-memory index and candidate retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .catalog import CatalogRepository, normalize_text
from .models import CandidateSet, EntityMention, EntityType, LinkCandidate, clamp_score


ALARM_ID_PATTERN = re.compile(r"^alm-\d+$", re.IGNORECASE)
NUMERIC_ALIAS_PATTERN = re.compile(r"^\d+$")


def is_alarm_identifier(text: str) -> bool:
    normalized = text.strip()
    return bool(ALARM_ID_PATTERN.fullmatch(normalized) or NUMERIC_ALIAS_PATTERN.fullmatch(normalized))


def alarm_dedup_key(text: str) -> str:
    normalized = normalize_text(text)
    if normalized.startswith("alm-"):
        return normalized.removeprefix("alm-")
    return normalized


@dataclass(frozen=True)
class AlarmIndexEntry:
    entity_id: str
    display_name: str
    score: float
    reason: str


class AlarmIndexBundle:
    """Small Python index for V1 alarm entities.

    It intentionally avoids substring matches for alarm IDs so that short IDs like
    ``51`` never match longer IDs such as ``51020`` or ``151``.
    """

    def __init__(self, catalog: CatalogRepository) -> None:
        self.catalog = catalog
        self._exact_index: dict[str, list[AlarmIndexEntry]] = {}
        self._phrase_entries: list[AlarmIndexEntry] = []
        self._build()

    def retrieve(self, mention: EntityMention, *, limit: int = 5) -> CandidateSet:
        exact_key = normalize_text(mention.text)
        exact_entries = self._exact_index.get(exact_key, [])
        entries = exact_entries or self._phrase_fallback(mention.text)
        candidates = self._entries_to_candidates(entries, mention.text, limit=limit)
        return CandidateSet(
            mention=mention,
            candidates=candidates,
            retrieval_strategy="alarm_exact_index" if exact_entries else "alarm_phrase_index",
        )

    def _build(self) -> None:
        for entity in self.catalog.entities:
            if entity.entity_type != EntityType.ALARM:
                continue
            names = [entity.entity_name, *entity.alias]
            for index, name in enumerate(names):
                key = normalize_text(name)
                if not key:
                    continue
                reason = "canonical alarm name match" if index == 0 else "alarm alias match"
                score = 1.0 if index == 0 else 0.96
                entry = AlarmIndexEntry(
                    entity_id=entity.entity_id,
                    display_name=name,
                    score=score,
                    reason=reason,
                )
                self._exact_index.setdefault(key, []).append(entry)
                if not is_alarm_identifier(name):
                    self._phrase_entries.append(entry)

    def _phrase_fallback(self, text: str) -> list[AlarmIndexEntry]:
        if is_alarm_identifier(text):
            return []
        mention_key = normalize_text(text)
        scored: list[AlarmIndexEntry] = []
        for entry in self._phrase_entries:
            entry_key = normalize_text(entry.display_name)
            ratio = SequenceMatcher(None, mention_key, entry_key).ratio()
            if ratio >= 0.9:
                scored.append(
                    AlarmIndexEntry(
                        entity_id=entry.entity_id,
                        display_name=entry.display_name,
                        score=0.78 + ratio * 0.1,
                        reason="alarm phrase similarity",
                    )
                )
        return scored

    def _entries_to_candidates(
        self,
        entries: list[AlarmIndexEntry],
        mention_text: str,
        *,
        limit: int,
    ) -> list[LinkCandidate]:
        best_by_entity: dict[str, AlarmIndexEntry] = {}
        for entry in entries:
            current = best_by_entity.get(entry.entity_id)
            if current is None or entry.score > current.score:
                best_by_entity[entry.entity_id] = entry

        candidates: list[LinkCandidate] = []
        for entity_id, entry in best_by_entity.items():
            entity = self.catalog.get(entity_id)
            if not entity:
                continue
            candidates.append(
                LinkCandidate(
                    entity_id=entity.entity_id,
                    entity_name=entity.entity_name,
                    entity_type=entity.entity_type,
                    confidence=clamp_score(entry.score),
                    match_reason=entry.reason,
                    dedup_key=alarm_dedup_key(entry.display_name),
                    evidence=[
                        {
                            "source": entity.source,
                            "data_layer": entity.data_layer.value,
                            "mention": mention_text,
                            "matched_name": entry.display_name,
                        }
                    ],
                )
            )
        candidates.sort(key=lambda item: (-item.confidence, item.entity_id))
        return [
            LinkCandidate(
                entity_id=item.entity_id,
                entity_name=item.entity_name,
                entity_type=item.entity_type,
                confidence=item.confidence,
                match_reason=item.match_reason,
                rank=index + 1,
                dedup_key=item.dedup_key,
                evidence=item.evidence,
            )
            for index, item in enumerate(candidates[:limit])
        ]
