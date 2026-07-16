"""Stable V4 facade for embedding entity linking in another Python project."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import asyncio
from dataclasses import dataclass

from .application.dto import (
    CandidateResponseV1,
    EntitySummaryV1,
    LinkRequestV1,
    LinkResponseV1,
    MentionResponseV1,
)
from .domain.normalization import normalize_query
from .domain.components import (
    CandidateResolver,
    EntityTypeResolver,
    KnownMentionRecognizer,
    LinkingIntentPolicy,
    MentionSelector,
    ResultAggregator,
    SafeTraceBuilder,
    UnknownMentionRecognizer,
)
from .domain.ports import (
    CandidateRerankDecision,
    CandidateReranker,
    EntityDataClient,
    EntityDataDependencyError,
    EntityExtractionEnhancer,
    InternalRouteClient,
    RerankCandidate,
)
from .domain.recognition import validate_extracted_mentions
from .infrastructure.entity_data_ir import IrEntityDataClient


PUBLIC_CONTRACT_VERSION = "v4.link-response.1"


@dataclass(frozen=True)
class ModuleConfig:
    entity_data_ir_url: str = ""
    timeout_ms: int = 2_000
    startup_failure_policy: str = "DEGRADED"
    llm_mention_min_confidence: float = 0.70
    llm_rerank_min_confidence: float = 0.70


class EntityLinkingModule:
    """Public facade; only V1 DTOs are exposed to embedding applications."""

    def __init__(
        self,
        *,
        data_client: EntityDataClient,
        config: ModuleConfig | None = None,
        enhancer: EntityExtractionEnhancer | None = None,
        reranker: CandidateReranker | None = None,
        intent_policy: LinkingIntentPolicy | None = None,
        known_recognizer: KnownMentionRecognizer | None = None,
        unknown_recognizer: UnknownMentionRecognizer | None = None,
        type_resolver: EntityTypeResolver | None = None,
        candidate_resolver: CandidateResolver | None = None,
        mention_selector: MentionSelector | None = None,
        result_aggregator: ResultAggregator | None = None,
        trace_builder: SafeTraceBuilder | None = None,
    ) -> None:
        self._data_client = data_client
        self._config = config or ModuleConfig()
        self._enhancer = enhancer
        self._reranker = reranker
        self._intent_policy = intent_policy or LinkingIntentPolicy()
        self._known_recognizer = known_recognizer or KnownMentionRecognizer()
        self._unknown_recognizer = unknown_recognizer or UnknownMentionRecognizer()
        self._type_resolver = type_resolver or EntityTypeResolver()
        self._candidate_resolver = candidate_resolver or CandidateResolver()
        self._mention_selector = mention_selector or MentionSelector()
        self._result_aggregator = result_aggregator or ResultAggregator()
        self._trace_builder = trace_builder or SafeTraceBuilder()

    def link(self, request: LinkRequestV1) -> LinkResponseV1:
        if not isinstance(request.query, str) or not request.query.strip():
            return self._response(request.query, "invalid_input", error_code="invalid_input")
        try:
            if not self._intent_policy.should_link(request.query):
                return self._response(
                    request.query,
                    "not_required",
                    bypass_reason="explicit non-linking request",
                    trace=({"stage": "need_linking", "status": "bypassed"},),
                )
            normalized = normalize_query(request.query)
            if not normalized.normalized_text:
                return self._response(request.query, "invalid_input", error_code="invalid_input")

            # P4 and P5 are genuinely independent: local deterministic rules and
            # the optional enhancer run while the data client performs recall.
            # They only meet at the explicit P7 merge stage below.
            with ThreadPoolExecutor(max_workers=2) as executor:
                local_future = executor.submit(self._unknown_recognizer.recognize, request.query)
                enhancer_future = None
                if request.extraction_mode != "disabled" and self._enhancer is not None:
                    enhancer_future = executor.submit(
                        self._enhancer.extract,
                        request.query,
                        agent_context=dict(request.agent_context),
                        entity_types=tuple(request.entity_types),
                    )
                match_response = self._data_client.match_words(
                    normalized.normalized_text,
                    entity_types=tuple(request.entity_types),
                )
                local_mentions = local_future.result()

                enhancer_degraded = False
                extracted_mentions = []
                if request.extraction_mode != "disabled":
                    if self._enhancer is None:
                        # Legacy LLM-enabled mode without a configured client
                        # remained deterministic; an unconfigured optional hook
                        # is therefore closed, not a dependency failure.
                        pass
                    else:
                        try:
                            extracted = enhancer_future.result() if enhancer_future is not None else ()
                            validated = validate_extracted_mentions(request.query, extracted)
                            if len(validated) != len(extracted) or any(
                                item.confidence is None
                                or item.confidence < self._config.llm_mention_min_confidence
                                for item in validated
                            ):
                                raise ValueError("invalid or low-confidence extracted mention")
                            extracted_mentions = validated
                        except Exception:
                            if not request.allow_fallback:
                                return self._response(
                                    request.query,
                                    "dependency_failed",
                                    error_code="extractor_failed",
                                    data_version=match_response.data_version,
                                )
                            enhancer_degraded = True

            trace: list[dict[str, object]] = [
                self._trace_builder.stage("need_linking", status="used"),
                self._trace_builder.stage("local_recognition", status="used", mention_count=len(local_mentions)),
                self._trace_builder.stage("word_match", match_count=len(match_response.matches)),
            ]
            if request.extraction_mode != "disabled":
                if enhancer_degraded:
                    trace.append(
                        {
                            "stage": "optional_enhancer",
                            "status": "fallback",
                            "error_code": "extractor_unavailable" if self._enhancer is None else "extractor_failed",
                        }
                    )
                else:
                    trace.append(
                        {
                            "stage": "optional_enhancer",
                            "status": "not_configured" if self._enhancer is None else "used",
                            "mention_count": len(extracted_mentions),
                        }
                    )
            known_mentions = self._known_recognizer.recognize(normalized, match_response.matches)

            matches_by_span: dict[tuple[int, int], list] = {}
            for known in known_mentions:
                if known.match is not None:
                    matches_by_span.setdefault(known.span, []).append(known.match)
            all_mentions = [*known_mentions, *local_mentions, *extracted_mentions]
            selected = self._mention_selector.select(all_mentions)
            trace.append(
                {
                    "stage": "mention_merge",
                    "known_count": len(known_mentions),
                    "local_count": len(local_mentions),
                    "extracted_count": len(extracted_mentions),
                    "mention_count": len(selected),
                }
            )
            if not selected:
                return self._response(
                    request.query,
                    "no_match",
                    data_version=match_response.data_version,
                    no_match_reason="no known or entity-shaped mention detected",
                    trace=tuple(trace),
                )

            # Candidate generation and disambiguation intentionally happen before
            # any entity detail read.  EntityWordMatch contains the confirmed ID,
            # type, priority and matching policy needed for this decision.
            candidate_matches_by_span: dict[tuple[int, int], tuple] = {}
            extracted_type_hints_by_span: dict[tuple[int, int], set[str]] = {}
            for item in extracted_mentions:
                if item.predicted_type is not None:
                    extracted_type_hints_by_span.setdefault(item.span, set()).add(item.predicted_type)
            for item in selected:
                span_matches = matches_by_span.get(item.span, ())
                if item.match is not None and not span_matches:
                    span_matches = (item.match,)
                # A database mention's type is candidate evidence, not a reason
                # to discard other IDs on the same confirmed span.  A single type
                # hint from the merged enhancer evidence can narrow that set even
                # when the known-word mention won overlap selection.
                type_hints = extracted_type_hints_by_span.get(item.span, set())
                filtered = self._type_resolver.filter(span_matches, item, type_hints)
                candidate_matches_by_span[item.span] = self._candidate_resolver.resolve(filtered)

            # This is the second, and only other, legacy LLM position: after
            # deterministic candidates exist and only for unresolved ambiguity.
            # The reranker receives no entity record and can select only an ID
            # that is already in the confirmed candidate set.
            rerank_decisions_by_span: dict[tuple[int, int], CandidateRerankDecision] = {}
            rerank_degraded = False
            for item in selected:
                candidate_matches = candidate_matches_by_span[item.span]
                if request.extraction_mode == "disabled" or len(candidate_matches) < 2:
                    continue
                if self._reranker is None:
                    # An absent optional reranker is equivalent to the legacy
                    # offline mode: keep the deterministic ambiguous result.
                    continue
                try:
                    decision = self._reranker.rerank(
                        request.query,
                        mention_text=item.text,
                        candidates=tuple(
                            RerankCandidate(
                                entity_id=match.entity_id,
                                entity_type=match.entity_type,
                                entity_word=match.entity_word,
                                match_reason=f"confirmed database entity-word match:{match.source}",
                                confidence=1.0,
                            )
                            for match in candidate_matches
                        ),
                        agent_context=dict(request.agent_context),
                    )
                    allowed_ids = {match.entity_id for match in candidate_matches}
                    if (
                        decision.selected_entity_id not in allowed_ids
                        or not 0.0 <= decision.confidence <= 1.0
                        or decision.confidence < self._config.llm_rerank_min_confidence
                        or not decision.reason.strip()
                    ):
                        raise ValueError("invalid or low-confidence rerank decision")
                    candidate_matches_by_span[item.span] = tuple(
                        match for match in candidate_matches if match.entity_id == decision.selected_entity_id
                    )
                    rerank_decisions_by_span[item.span] = decision
                except Exception:
                    # Legacy disambiguation always retained the deterministic
                    # candidate set on LLM failure, including strict callers.
                    rerank_degraded = True

            entity_ids = tuple(
                dict.fromkeys(
                    match.entity_id
                    for matches in candidate_matches_by_span.values()
                    for match in matches
                )
            )
            trace.append(
                {
                    "stage": "candidate_resolution",
                    "mention_count": len(selected),
                    "resolved_entity_count": len(entity_ids),
                    "ambiguous_mention_count": sum(
                        1 for matches in candidate_matches_by_span.values() if len(matches) > 1
                    ),
                }
            )
            if request.extraction_mode != "disabled":
                trace.append(
                    {
                        "stage": "optional_reranker",
                        "status": "fallback" if rerank_degraded else "used" if rerank_decisions_by_span else "not_needed",
                        "decision_count": len(rerank_decisions_by_span),
                    }
                )

            entities = {}
            if entity_ids:
                entity_response = self._data_client.batch_get(
                    entity_ids,
                    expected_data_version=match_response.data_version,
                )
                if entity_response.data_version != match_response.data_version or entity_response.missing_ids:
                    return self._response(
                        request.query,
                        "dependency_failed",
                        error_code="entity_miss",
                        data_version=match_response.data_version,
                        trace=tuple(trace),
                    )
                entities = {item.entity_id: item for item in entity_response.entities}
                trace.append({"stage": "entity_batch_get", "entity_count": len(entities)})
            else:
                trace.append({"stage": "entity_batch_get", "status": "skipped_no_confirmed_candidate"})

            mentions: list[MentionResponseV1] = []
            for item in selected:
                candidate_matches = candidate_matches_by_span[item.span]
                if not candidate_matches:
                    mentions.append(
                        MentionResponseV1(
                            text=item.text,
                            span=item.span,
                            status="no_match",
                            source=item.source,
                            predicted_type=item.predicted_type,
                            normalized_text=normalize_query(item.text).normalized_text,
                            confidence=item.confidence,
                            no_match_reason="mention has no confirmed candidate after candidate resolution",
                            storage_lookup={"word_match_status": "miss", "candidate_resolution_status": "no_candidate"},
                        )
                    )
                    continue
                candidate_records = [entities.get(match.entity_id) for match in candidate_matches]
                if any(record is None for record in candidate_records):
                    return self._response(
                        request.query,
                        "dependency_failed",
                        error_code="entity_miss",
                        data_version=match_response.data_version,
                        trace=tuple(trace),
                    )
                candidates = tuple(
                    CandidateResponseV1(
                        entity_id=entity_data.entity_id,
                        entity_name=entity_data.entity_name,
                        entity_type=entity_data.entity_type,
                        confidence=rerank_decisions_by_span.get(item.span).confidence
                        if len(candidate_matches) == 1 and item.span in rerank_decisions_by_span
                        else 1.0,
                        rank=index,
                        match_reason="confirmed database entity-word match",
                    )
                    for index, entity_data in enumerate(candidate_records, start=1)
                )
                if len(candidates) > 1:
                    mentions.append(
                        MentionResponseV1(
                            text=item.text,
                            span=item.span,
                            status="ambiguous",
                            match_mode=item.match.match_mode,
                        reason="multiple confirmed candidates after disambiguation",
                        source=item.source,
                        predicted_type=item.predicted_type,
                        normalized_text=normalize_query(item.text).normalized_text,
                        candidates=candidates,
                        disambiguation_reason="multiple confirmed candidate IDs remain after rule-based disambiguation",
                        storage_lookup={"word_match_status": "hit", "candidate_resolution_status": "ambiguous", "entity_lookup_status": "hit"},
                        )
                    )
                    continue
                entity_data = candidate_records[0]
                candidate = candidates[0]
                rerank_decision = rerank_decisions_by_span.get(item.span)
                mentions.append(
                    MentionResponseV1(
                        text=item.text,
                        span=item.span,
                        status="linked",
                        entity=EntitySummaryV1(
                            entity_id=entity_data.entity_id,
                            entity_type=entity_data.entity_type,
                            entity_name=entity_data.entity_name,
                            desc=entity_data.desc,
                            attributes=dict(entity_data.attributes),
                            relationships=entity_data.relationships,
                        ),
                        match_mode=candidate_matches[0].match_mode,
                        reason="llm_candidate_rerank" if rerank_decision else f"candidate_resolved:{candidate_matches[0].source}",
                        source=item.source,
                        predicted_type=candidate_matches[0].entity_type,
                        normalized_text=normalize_query(item.text).normalized_text,
                        confidence=candidate.confidence,
                        candidates=(candidate,),
                        disambiguation_reason=rerank_decision.reason
                        if rerank_decision
                        else "single confirmed candidate after rule-based disambiguation",
                        storage_lookup={
                            "word_match_status": "hit",
                            "entity_lookup_status": "hit",
                            "candidate_resolution_status": "resolved",
                            "entity_word_id": candidate_matches[0].entity_word_id,
                            "entity_id": candidate_matches[0].entity_id,
                        },
                    )
                )
            status = self._result_aggregator.status(
                [item.status for item in mentions], degraded=enhancer_degraded or rerank_degraded
            )
            linked = [item for item in mentions if item.status == "linked"]
            candidates = tuple(candidate for item in mentions for candidate in item.candidates)
            trace.append({"stage": "status_aggregation", "status": status})
            return self._response(
                request.query,
                status,
                mentions=tuple(mentions),
                data_version=match_response.data_version,
                candidates=candidates,
                no_match_reason="all recognized mentions have no confirmed candidate" if not linked else "",
                degraded=enhancer_degraded or rerank_degraded,
                mode_status={
                    "requested_extraction_mode": request.extraction_mode,
                    "effective_mode": "offline_deterministic"
                    if enhancer_degraded or rerank_degraded
                    else request.extraction_mode,
                    "fallback_used": enhancer_degraded or rerank_degraded,
                },
                trace=tuple(trace),
            )
        except EntityDataDependencyError as exc:
            return self._response(request.query, "dependency_failed", error_code=exc.code, degraded=True)

    async def link_async(self, request: LinkRequestV1) -> LinkResponseV1:
        """Run the synchronous IR pipeline without blocking the caller event loop."""
        return await asyncio.to_thread(self.link, request)

    @staticmethod
    def _response(
        query: str,
        status: str,
        *,
        mentions: tuple[MentionResponseV1, ...] = (),
        error_code: str | None = None,
        degraded: bool = False,
        data_version: str = "",
        trace: tuple[dict[str, object], ...] = (),
        candidates: tuple[CandidateResponseV1, ...] = (),
        no_match_reason: str = "",
        bypass_reason: str = "",
        mode_status: dict[str, object] | None = None,
    ) -> LinkResponseV1:
        return LinkResponseV1(
            contract_version=PUBLIC_CONTRACT_VERSION,
            query=query,
            status=status,
            mentions=mentions,
            error_code=error_code,
            degraded=degraded,
            data_version=data_version,
            service_trace=trace,
            candidates=candidates,
            no_match_reason=no_match_reason,
            bypass_reason=bypass_reason,
            mode_status=mode_status or {
                "requested_extraction_mode": "disabled",
                "effective_mode": "offline_deterministic",
                "fallback_used": False,
            },
        )


class _UnavailableEntityDataClient:
    """Fail closed after a DEGRADED startup health check."""

    def __init__(self, error: EntityDataDependencyError) -> None:
        self._error = error

    def health(self):
        raise self._error

    def match_words(self, normalized_query: str, *, entity_types=(), expected_data_version=None):
        raise self._error

    def batch_get(self, entity_ids, *, expected_data_version=None):
        raise self._error


def create_entity_linking_module(
    config: ModuleConfig | None = None,
    *,
    platform_client: InternalRouteClient | None = None,
    enhancer: EntityExtractionEnhancer | None = None,
    reranker: CandidateReranker | None = None,
) -> EntityLinkingModule:
    if config is None or not config.entity_data_ir_url.strip():
        raise ValueError("ModuleConfig.entity_data_ir_url is required for V4 module assembly")
    if platform_client is None:
        raise ValueError("platform_client is required for V4 module assembly")
    resolved = config
    policy = resolved.startup_failure_policy.upper()
    if policy not in {"FAIL_FAST", "DEGRADED"}:
        raise ValueError("startup_failure_policy must be FAIL_FAST or DEGRADED")
    client: EntityDataClient = IrEntityDataClient(
        resolved.entity_data_ir_url,
        platform_client=platform_client,
        timeout_ms=resolved.timeout_ms,
    )
    try:
        client.health()
    except EntityDataDependencyError as exc:
        if policy == "FAIL_FAST":
            raise EntityDataDependencyError("startup_health_failed", str(exc)) from exc
        client = _UnavailableEntityDataClient(EntityDataDependencyError("startup_health_failed", str(exc)))
    return EntityLinkingModule(data_client=client, config=resolved, enhancer=enhancer, reranker=reranker)
