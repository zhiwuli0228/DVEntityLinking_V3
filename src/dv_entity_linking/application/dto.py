"""Stable V4 public integration DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LinkRequestV1:
    query: str
    agent_context: dict[str, Any] = field(default_factory=dict)
    entity_types: tuple[str, ...] = ()
    extraction_mode: str = "disabled"
    allow_fallback: bool = True


@dataclass(frozen=True)
class EntitySummaryV1:
    entity_id: str
    entity_type: str
    entity_name: str
    desc: str
    attributes: dict[str, Any] = field(default_factory=dict)
    relationships: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class MentionResponseV1:
    text: str
    span: tuple[int, int]
    status: str
    entity: EntitySummaryV1 | None = None
    match_mode: str = "EXACT_WORD"
    reason: str = ""


@dataclass(frozen=True)
class LinkResponseV1:
    contract_version: str
    query: str
    status: str
    mentions: tuple[MentionResponseV1, ...] = ()
    error_code: str | None = None
    degraded: bool = False
    data_version: str = ""
    service_trace: tuple[dict[str, Any], ...] = ()
