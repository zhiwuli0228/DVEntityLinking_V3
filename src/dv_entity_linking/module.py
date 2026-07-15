"""Stable V4 facade for embedding entity linking in another Python project."""

from __future__ import annotations

from dataclasses import dataclass

from .application.dto import (
    EntitySummaryV1,
    LinkRequestV1,
    LinkResponseV1,
    MentionResponseV1,
)
from .domain.normalization import normalize_query
from .domain.ports import (
    EntityDataClient,
    EntityDataDependencyError,
    EntityWordMatch,
    InternalRouteClient,
)
from .infrastructure.entity_data_ir import IrEntityDataClient
from .infrastructure.v3_mock import V3MockEntityDataClient


PUBLIC_CONTRACT_VERSION = "v4.link-response.1"


@dataclass(frozen=True)
class ModuleConfig:
    entity_data_ir_url: str = ""
    timeout_ms: int = 2_000
    startup_failure_policy: str = "DEGRADED"
    gauss_mock_path: str = "samples/real/v3_gauss_entities.json"
    redis_mock_path: str = "samples/real/v3_redis_entity_words.json"


@dataclass(frozen=True)
class _ConfirmedMention:
    text: str
    span: tuple[int, int]
    match: EntityWordMatch


class EntityLinkingModule:
    """Public facade; only V1 DTOs are exposed to embedding applications."""

    def __init__(self, *, data_client: EntityDataClient, config: ModuleConfig | None = None) -> None:
        self._data_client = data_client
        self._config = config or ModuleConfig()

    def link(self, request: LinkRequestV1) -> LinkResponseV1:
        if not isinstance(request.query, str) or not request.query.strip():
            return self._response(request.query, "invalid_input", error_code="invalid_input")
        try:
            normalized = normalize_query(request.query)
            if not normalized.normalized_text:
                return self._response(request.query, "invalid_input", error_code="invalid_input")
            match_response = self._data_client.match_words(
                normalized.normalized_text,
                entity_types=tuple(request.entity_types),
            )
            confirmed = self._confirm_matches(normalized, match_response.matches)
            selected = self._longest_non_overlapping(confirmed)
            if not selected:
                return self._response(
                    request.query,
                    "no_match",
                    data_version=match_response.data_version,
                    trace=({"stage": "word_match", "match_count": len(match_response.matches)},),
                )
            entity_ids = tuple(dict.fromkeys(item.match.entity_id for item in selected))
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
                )
            entities = {item.entity_id: item for item in entity_response.entities}
            mentions = tuple(
                MentionResponseV1(
                    text=item.text,
                    span=item.span,
                    status="linked",
                    entity=EntitySummaryV1(
                        entity_id=entities[item.match.entity_id].entity_id,
                        entity_type=entities[item.match.entity_id].entity_type,
                        entity_name=entities[item.match.entity_id].entity_name,
                        desc=entities[item.match.entity_id].desc,
                        attributes=dict(entities[item.match.entity_id].attributes),
                        relationships=entities[item.match.entity_id].relationships,
                    ),
                    match_mode=item.match.match_mode,
                    reason=f"database_word_match:{item.match.source}",
                )
                for item in selected
            )
            return self._response(
                request.query,
                "linked",
                mentions=mentions,
                data_version=match_response.data_version,
                trace=(
                    {"stage": "word_match", "match_count": len(match_response.matches)},
                    {"stage": "entity_batch_get", "entity_count": len(entities)},
                ),
            )
        except EntityDataDependencyError as exc:
            return self._response(request.query, "dependency_failed", error_code=exc.code, degraded=True)

    async def link_async(self, request: LinkRequestV1) -> LinkResponseV1:
        return self.link(request)

    def _confirm_matches(self, normalized, matches: tuple[EntityWordMatch, ...]) -> list[_ConfirmedMention]:
        confirmed: list[_ConfirmedMention] = []
        for match in matches:
            start = normalized.normalized_text.find(match.normalized_key)
            while start >= 0:
                end = start + len(match.normalized_key)
                span = normalized.restore_span(start, end)
                if span is not None and self._is_confirmed(normalized.original_text, span, match):
                    confirmed.append(
                        _ConfirmedMention(
                            text=normalized.original_text[span[0] : span[1]],
                            span=span,
                            match=match,
                        )
                    )
                start = normalized.normalized_text.find(match.normalized_key, start + 1)
        return confirmed

    @staticmethod
    def _is_confirmed(query: str, span: tuple[int, int], match: EntityWordMatch) -> bool:
        start, end = span
        if match.match_mode in {"EXACT_WORD", "STRUCTURED_TOKEN"}:
            if start > 0 and EntityLinkingModule._is_ascii_alnum(query[start - 1]):
                return False
            if end < len(query) and EntityLinkingModule._is_ascii_alnum(query[end]):
                return False
        if match.match_mode == "CONTEXT_REQUIRED" or match.min_context_required:
            lowered = query.casefold()
            if not match.context_keywords or not any(keyword.casefold() in lowered for keyword in match.context_keywords):
                return False
        return True

    @staticmethod
    def _is_ascii_alnum(value: str) -> bool:
        return value.isascii() and value.isalnum()

    @staticmethod
    def _longest_non_overlapping(matches: list[_ConfirmedMention]) -> list[_ConfirmedMention]:
        selected: list[_ConfirmedMention] = []
        occupied: set[int] = set()
        for item in sorted(
            matches,
            key=lambda value: (value.span[0], -(value.span[1] - value.span[0]), -value.match.priority, value.match.entity_id),
        ):
            positions = set(range(*item.span))
            if positions & occupied:
                continue
            selected.append(item)
            occupied.update(positions)
        return selected

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
        )


def create_entity_linking_module(
    config: ModuleConfig | None = None,
    *,
    platform_client: InternalRouteClient | None = None,
) -> EntityLinkingModule:
    resolved = config or ModuleConfig()
    if resolved.entity_data_ir_url:
        if platform_client is None:
            raise ValueError("platform_client is required when entity_data_ir_url is configured")
        client: EntityDataClient = IrEntityDataClient(
            resolved.entity_data_ir_url,
            platform_client=platform_client,
            timeout_ms=resolved.timeout_ms,
        )
    else:
        client = V3MockEntityDataClient.from_paths(
            gauss_mock_path=resolved.gauss_mock_path,
            redis_mock_path=resolved.redis_mock_path,
        )
    return EntityLinkingModule(data_client=client, config=resolved)
