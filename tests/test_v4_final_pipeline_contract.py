"""Black-box contract tests for the V4 final pipeline.

These tests deliberately avoid asserting module-generated trace text.  Their
fakes observe real calls at the EntityDataClient boundary and reject incorrect
call order or an incorrect batch ID set.  Each case is a regression guard for a
previously plausible but invalid ``match_words -> batch_get`` implementation.
"""

from __future__ import annotations

from threading import Event

from dv_entity_linking import LinkRequestV1
from dv_entity_linking.domain.ports import (
    CandidateRerankDecision,
    EntityBatchGetResponse,
    EntityDataRecord,
    EntityWordMatch,
    EntityWordMatchResponse,
    ExtractedMention,
)
from dv_entity_linking.module import EntityLinkingModule


def _match(*, word_id: str, entity_id: str, entity_type: str) -> EntityWordMatch:
    return EntityWordMatch(
        entity_word_id=word_id,
        entity_id=entity_id,
        entity_type=entity_type,
        entity_word="CPU Usage",
        normalized_key="cpuusage",
        source="entity_name",
    )


def _record(entity_id: str, entity_type: str) -> EntityDataRecord:
    return EntityDataRecord(
        entity_id=entity_id,
        entity_type=entity_type,
        entity_name=f"{entity_type} CPU Usage",
        desc="contract test entity",
    )


def test_final_pipeline_starts_optional_extraction_before_remote_recall() -> None:
    """A match-first implementation fails because the remote fake waits for P5."""

    extractor_started = Event()
    calls: list[str] = []

    class _GateEnhancer:
        def extract(self, query, *, agent_context, entity_types):
            extractor_started.set()
            return (ExtractedMention(text="CPU Usage", span=(6, 15), predicted_type="metric", confidence=0.9),)

    class _ObservingClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            calls.append("MATCH_WORDS")
            assert extractor_started.wait(1), "optional extraction was not started before remote recall"
            return EntityWordMatchResponse(matches=(_match(word_id="word-1", entity_id="metric-1", entity_type="metric"),), data_version="v1")

        def batch_get(self, entity_ids, *, expected_data_version=None):
            calls.append("BATCH_GET_ENTITIES")
            assert entity_ids == ("metric-1",)
            return EntityBatchGetResponse(entities=(_record("metric-1", "metric"),), missing_ids=(), data_version="v1")

    result = EntityLinkingModule(data_client=_ObservingClient(), enhancer=_GateEnhancer()).link(
        LinkRequestV1(query="Check CPU Usage", extraction_mode="llm")
    )

    assert result.status == "linked"
    assert calls == ["MATCH_WORDS", "BATCH_GET_ENTITIES"]


def test_final_pipeline_uses_merged_type_evidence_before_detail_lookup() -> None:
    """A detail-first implementation would request both IDs and is rejected."""

    calls: list[tuple[str, tuple[str, ...]]] = []

    class _MetricEnhancer:
        def extract(self, query, *, agent_context, entity_types):
            return (ExtractedMention(text="CPU Usage", span=(6, 15), predicted_type="metric", confidence=0.95),)

    class _CandidateGuardClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            calls.append(("MATCH_WORDS", ()))
            return EntityWordMatchResponse(
                matches=(
                    _match(word_id="word-metric", entity_id="metric-1", entity_type="metric"),
                    _match(word_id="word-alarm", entity_id="alarm-1", entity_type="alarm"),
                ),
                data_version="v1",
            )

        def batch_get(self, entity_ids, *, expected_data_version=None):
            calls.append(("BATCH_GET_ENTITIES", tuple(entity_ids)))
            assert entity_ids == ("metric-1",), "batch lookup must receive post-disambiguation IDs only"
            return EntityBatchGetResponse(entities=(_record("metric-1", "metric"),), missing_ids=(), data_version="v1")

    result = EntityLinkingModule(data_client=_CandidateGuardClient(), enhancer=_MetricEnhancer()).link(
        LinkRequestV1(query="Check CPU Usage", extraction_mode="llm")
    )

    assert result.status == "linked"
    assert result.mentions[0].entity.entity_id == "metric-1"
    assert calls == [("MATCH_WORDS", ()), ("BATCH_GET_ENTITIES", ("metric-1",))]


def test_final_pipeline_never_reads_details_for_local_only_no_match() -> None:
    """A database miss remains observable as a local no-match mention, not a lookup."""

    class _NoCandidateClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(matches=(), data_version="v1")

        def batch_get(self, entity_ids, *, expected_data_version=None):
            raise AssertionError("local-only no-match must not invoke BATCH_GET_ENTITIES")

    result = EntityLinkingModule(data_client=_NoCandidateClient()).link(
        LinkRequestV1(query="Check UnknownApp-999")
    )

    assert result.status == "no_match"
    assert [(mention.text, mention.status) for mention in result.mentions] == [("UnknownApp-999", "no_match")]


def test_llm_reranker_runs_only_after_candidates_and_before_detail_lookup() -> None:
    """This is the legacy V1/V2 disambiguation position, preserved in V4."""

    observed_candidates: list[tuple[str, ...]] = []

    class _NoopExtractor:
        def extract(self, query, *, agent_context, entity_types):
            return ()

    class _Reranker:
        def rerank(self, query, *, mention_text, candidates, agent_context):
            observed_candidates.append(tuple(candidate.entity_id for candidate in candidates))
            assert mention_text == "CPU Usage"
            return CandidateRerankDecision(
                selected_entity_id="metric-1", confidence=0.91, reason="query requests a metric"
            )

    class _DetailGuardClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(
                matches=(
                    _match(word_id="word-metric", entity_id="metric-1", entity_type="metric"),
                    _match(word_id="word-alarm", entity_id="alarm-1", entity_type="alarm"),
                ),
                data_version="v1",
            )

        def batch_get(self, entity_ids, *, expected_data_version=None):
            assert observed_candidates == [("alarm-1", "metric-1")]
            assert entity_ids == ("metric-1",)
            return EntityBatchGetResponse(entities=(_record("metric-1", "metric"),), missing_ids=(), data_version="v1")

    result = EntityLinkingModule(
        data_client=_DetailGuardClient(), enhancer=_NoopExtractor(), reranker=_Reranker()
    ).link(LinkRequestV1(query="Check CPU Usage", extraction_mode="llm"))

    assert result.status == "linked"
    assert result.mentions[0].reason == "llm_candidate_rerank"
    assert result.mentions[0].disambiguation_reason == "query requests a metric"


def test_llm_reranker_invalid_choice_falls_back_to_deterministic_ambiguity() -> None:
    """The reranker cannot create an ID or force a Top-1 result when it is invalid."""

    class _NoopExtractor:
        def extract(self, query, *, agent_context, entity_types):
            return ()

    class _InvalidReranker:
        def rerank(self, query, *, mention_text, candidates, agent_context):
            return CandidateRerankDecision(selected_entity_id="invented-id", confidence=0.99, reason="unsafe")

    class _AmbiguousClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(
                matches=(
                    _match(word_id="word-metric", entity_id="metric-1", entity_type="metric"),
                    _match(word_id="word-alarm", entity_id="alarm-1", entity_type="alarm"),
                ),
                data_version="v1",
            )

        def batch_get(self, entity_ids, *, expected_data_version=None):
            assert entity_ids == ("alarm-1", "metric-1")
            return EntityBatchGetResponse(
                entities=(_record("alarm-1", "alarm"), _record("metric-1", "metric")),
                missing_ids=(),
                data_version="v1",
            )

    result = EntityLinkingModule(
        data_client=_AmbiguousClient(), enhancer=_NoopExtractor(), reranker=_InvalidReranker()
    ).link(LinkRequestV1(query="Check CPU Usage", extraction_mode="llm", allow_fallback=True))

    assert result.status == "ambiguous"
    assert result.degraded is True
    assert [candidate.entity_id for candidate in result.mentions[0].candidates] == ["alarm-1", "metric-1"]


def test_llm_reranker_invalid_choice_preserves_legacy_ambiguity_even_without_fallback() -> None:
    class _NoopExtractor:
        def extract(self, query, *, agent_context, entity_types):
            return ()

    class _InvalidReranker:
        def rerank(self, query, *, mention_text, candidates, agent_context):
            return CandidateRerankDecision(selected_entity_id="invented-id", confidence=0.99, reason="unsafe")

    class _AmbiguousClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(
                matches=(
                    _match(word_id="word-metric", entity_id="metric-1", entity_type="metric"),
                    _match(word_id="word-alarm", entity_id="alarm-1", entity_type="alarm"),
                ),
                data_version="v1",
            )

        def batch_get(self, entity_ids, *, expected_data_version=None):
            assert entity_ids == ("alarm-1", "metric-1")
            return EntityBatchGetResponse(
                entities=(_record("alarm-1", "alarm"), _record("metric-1", "metric")),
                missing_ids=(),
                data_version="v1",
            )

    result = EntityLinkingModule(
        data_client=_AmbiguousClient(), enhancer=_NoopExtractor(), reranker=_InvalidReranker()
    ).link(LinkRequestV1(query="Check CPU Usage", extraction_mode="llm", allow_fallback=False))

    assert result.status == "ambiguous"
    assert result.degraded is True


def test_low_confidence_llm_mention_is_discarded_in_favor_of_deterministic_candidates() -> None:
    class _LowConfidenceExtractor:
        def extract(self, query, *, agent_context, entity_types):
            return (ExtractedMention(text="CPU Usage", span=(6, 15), predicted_type="metric", confidence=0.20),)

    class _CandidateGuardClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(
                matches=(
                    _match(word_id="word-metric", entity_id="metric-1", entity_type="metric"),
                    _match(word_id="word-alarm", entity_id="alarm-1", entity_type="alarm"),
                ),
                data_version="v1",
            )

        def batch_get(self, entity_ids, *, expected_data_version=None):
            assert entity_ids == ("alarm-1", "metric-1"), "low-confidence type hint must not filter candidates"
            return EntityBatchGetResponse(
                entities=(_record("alarm-1", "alarm"), _record("metric-1", "metric")),
                missing_ids=(),
                data_version="v1",
            )

    result = EntityLinkingModule(data_client=_CandidateGuardClient(), enhancer=_LowConfidenceExtractor()).link(
        LinkRequestV1(query="Check CPU Usage", extraction_mode="llm", allow_fallback=True)
    )

    assert result.status == "ambiguous"
    assert result.degraded is True


def test_strict_rerank_timeout_schema_and_low_confidence_keep_top_k() -> None:
    class _NoopExtractor:
        def extract(self, query, *, agent_context, entity_types):
            return ()

    class _AmbiguousClient:
        def match_words(self, normalized_query, *, entity_types=(), expected_data_version=None):
            return EntityWordMatchResponse(
                matches=(
                    _match(word_id="word-metric", entity_id="metric-1", entity_type="metric"),
                    _match(word_id="word-alarm", entity_id="alarm-1", entity_type="alarm"),
                ),
                data_version="v1",
            )

        def batch_get(self, entity_ids, *, expected_data_version=None):
            return EntityBatchGetResponse(
                entities=(_record("alarm-1", "alarm"), _record("metric-1", "metric")),
                missing_ids=(),
                data_version="v1",
            )

    for outcome in (TimeoutError("timeout"), CandidateRerankDecision("metric-1", 0.1, "low"), object()):
        class _BadReranker:
            def rerank(self, query, *, mention_text, candidates, agent_context):
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome

        result = EntityLinkingModule(
            data_client=_AmbiguousClient(), enhancer=_NoopExtractor(), reranker=_BadReranker()
        ).link(LinkRequestV1(query="Check CPU Usage", extraction_mode="llm", allow_fallback=False))
        assert result.status == "ambiguous"
        assert [candidate.entity_id for candidate in result.mentions[0].candidates] == ["alarm-1", "metric-1"]
