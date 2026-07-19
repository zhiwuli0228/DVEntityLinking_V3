"""Aho-Corasick matcher used only by the opt-in performance mock."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Iterable


AutomatonFactory = Callable[[], Any]


def _default_automaton_factory() -> Any:
    try:
        import ahocorasick
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "pyahocorasick is required for the AC mock strategy; "
            "install dv-entity-linking[performance-mock]"
        ) from exc
    return ahocorasick.Automaton()


@dataclass(frozen=True)
class AhoCorasickStats:
    data_version: str
    pattern_count: int
    build_seconds: float
    size_bytes: int | None


class AhoCorasickSnapshot:
    """Immutable, versioned AC index containing only word identifiers."""

    def __init__(
        self,
        automaton: Any,
        stats: AhoCorasickStats,
    ) -> None:
        self._automaton = automaton
        self.stats = stats

    @classmethod
    def build(
        cls,
        data_version: str,
        patterns: Iterable[tuple[int, str]],
        *,
        automaton_factory: AutomatonFactory | None = None,
    ) -> AhoCorasickSnapshot:
        started = perf_counter()
        automaton = (automaton_factory or _default_automaton_factory)()
        pattern_count = 0
        for entity_word_id, normalized_key in patterns:
            if not normalized_key:
                continue
            automaton.add_word(normalized_key, int(entity_word_id))
            pattern_count += 1
        automaton.make_automaton()
        raw_stats = automaton.get_stats() if hasattr(automaton, "get_stats") else {}
        size_bytes = raw_stats.get("total_size")
        return cls(
            automaton,
            AhoCorasickStats(
                data_version=data_version,
                pattern_count=pattern_count,
                build_seconds=perf_counter() - started,
                size_bytes=int(size_bytes) if size_bytes is not None else None,
            ),
        )

    def match_ids(self, normalized_query: str) -> tuple[int, ...]:
        matched_ids = {int(entity_word_id) for _, entity_word_id in self._automaton.iter(normalized_query)}
        return tuple(sorted(matched_ids))
