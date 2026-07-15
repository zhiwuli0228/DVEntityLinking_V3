"""Query normalization with a reversible span mapping."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata


NORMALIZATION_VERSION = "v4.entity_word_norm.1"


@dataclass(frozen=True)
class NormalizedQuery:
    original_text: str
    normalized_text: str
    normalized_to_original: tuple[int, ...]
    normalization_version: str = NORMALIZATION_VERSION

    def restore_span(self, start: int, end: int) -> tuple[int, int] | None:
        if start < 0 or end <= start or end > len(self.normalized_to_original):
            return None
        return self.normalized_to_original[start], self.normalized_to_original[end - 1] + 1


def normalize_query(text: str) -> NormalizedQuery:
    if not isinstance(text, str):
        raise TypeError("query must be a string")
    normalized_parts: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        for normalized_char in unicodedata.normalize("NFKC", char).casefold():
            if normalized_char.isspace():
                continue
            normalized_parts.append(normalized_char)
            positions.append(index)
    return NormalizedQuery(
        original_text=text,
        normalized_text="".join(normalized_parts),
        normalized_to_original=tuple(positions),
    )
