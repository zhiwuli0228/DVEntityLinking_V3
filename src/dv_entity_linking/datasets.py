"""V1 query dataset loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .catalog import CatalogRepository
from .models import ErrorCode, Status


class QueryDatasetError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("query dataset validation failed")
        self.error_code = ErrorCode.QUERY_DATASET_LOAD_FAILED
        self.errors = errors


@dataclass(frozen=True)
class QueryMentionExpectation:
    text: str
    span: tuple[int, int]
    expected_entity_ids: list[str]
    expected_status: Status = Status.LINKED
    expected_entity_type: str = ""
    match_type: str = ""


@dataclass(frozen=True)
class QuerySample:
    id: str
    query: str
    expected_status: Status
    mentions: list[QueryMentionExpectation]
    expected_entities: list[dict[str, Any]]
    negative_reason: str = ""


@dataclass(frozen=True)
class QueryDataset:
    metadata: dict[str, Any]
    queries: list[QuerySample] = field(default_factory=list)


class QueryDatasetLoader:
    V1_SCHEMA_VERSIONS = {"v1.alarm_query.1", "v1.alarm_query.2"}
    V2_SCHEMA_VERSIONS = {"v2.query_samples.1"}
    SUPPORTED_SCHEMA_VERSIONS = V1_SCHEMA_VERSIONS | V2_SCHEMA_VERSIONS
    V1_ALLOWED_STATUSES = {
        Status.LINKED,
        Status.AMBIGUOUS,
        Status.NO_MATCH,
        Status.NOT_REQUIRED,
    }
    V2_ALLOWED_STATUSES = V1_ALLOWED_STATUSES | {Status.PARTIAL, Status.DEPENDENCY_FAILED}

    def load(self, path: str | Path, catalog: CatalogRepository) -> QueryDataset:
        resolved = Path(path)
        errors: list[dict[str, str]] = []
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            raise QueryDatasetError(
                [{"field": "path", "message": f"query dataset file not found: {resolved}"}]
            ) from None
        except json.JSONDecodeError as exc:
            raise QueryDatasetError(
                [{"field": "json", "message": f"invalid query dataset JSON: {exc.msg}"}]
            ) from exc

        if not isinstance(payload, dict):
            raise QueryDatasetError([{"field": "root", "message": "query dataset root must be object"}])
        metadata = payload.get("metadata")
        raw_queries = payload.get("queries")
        if not isinstance(metadata, dict):
            errors.append({"field": "metadata", "message": "metadata must be object"})
            metadata = {}
        if not isinstance(raw_queries, list):
            errors.append({"field": "queries", "message": "queries must be list"})
            raw_queries = []

        self._validate_metadata(metadata, len(raw_queries), errors)
        samples = self._parse_queries(raw_queries, catalog, errors)
        if errors:
            raise QueryDatasetError(errors)
        return QueryDataset(metadata=metadata, queries=samples)

    def _validate_metadata(
        self,
        metadata: dict[str, Any],
        actual_query_count: int,
        errors: list[dict[str, str]],
    ) -> None:
        schema_version = metadata.get("schema_version")
        if schema_version not in self.SUPPORTED_SCHEMA_VERSIONS:
            errors.append(
                {
                    "field": "metadata.schema_version",
                    "message": "schema_version must be v1.alarm_query.1, v1.alarm_query.2, or v2.query_samples.1",
                }
            )
            return
        if schema_version in self.V1_SCHEMA_VERSIONS and metadata.get("max_one_entity_mention_per_query") is not True:
            errors.append(
                {
                    "field": "metadata.max_one_entity_mention_per_query",
                    "message": "max_one_entity_mention_per_query must be true",
                }
            )
        if schema_version in self.V2_SCHEMA_VERSIONS:
            if metadata.get("query_language") != "en":
                errors.append(
                    {
                        "field": "metadata.query_language",
                        "message": "v2 query_language must be en",
                    }
                )
            if metadata.get("multi_mention_supported") is not True:
                errors.append(
                    {
                        "field": "metadata.multi_mention_supported",
                        "message": "v2 multi_mention_supported must be true",
                    }
                )
        if metadata.get("query_count") != actual_query_count:
            errors.append(
                {
                    "field": "metadata.query_count",
                    "message": "query_count does not match queries[] length",
                }
            )

    def _parse_queries(
        self,
        raw_queries: list[Any],
        catalog: CatalogRepository,
        errors: list[dict[str, str]],
    ) -> list[QuerySample]:
        samples: list[QuerySample] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(raw_queries):
            field_prefix = f"queries[{index}]"
            if not isinstance(item, dict):
                errors.append({"field": field_prefix, "message": "query item must be object"})
                continue
            raw_query_id = item.get("id")
            query_id = raw_query_id if isinstance(raw_query_id, str) else ""
            if not query_id:
                errors.append({"field": f"{field_prefix}.id", "message": "id is required"})
            elif query_id in seen_ids:
                errors.append({"field": f"{field_prefix}.id", "message": f"duplicate id: {query_id}"})
            seen_ids.add(query_id)

            query_text = item.get("query")
            if not isinstance(query_text, str) or not query_text:
                errors.append({"field": f"{field_prefix}.query", "message": "query is required"})
                query_text = ""

            status = self._parse_status(item.get("expected_status"), field_prefix, errors)
            mentions = self._parse_mentions(
                item.get("mentions"),
                query_text,
                catalog,
                field_prefix,
                errors,
                default_mention_status=status or Status.LINKED,
            )
            expected_entities = self._parse_expected_entities(
                item.get("expected_entities"),
                catalog,
                field_prefix,
                errors,
            )
            self._validate_status_contract(
                status,
                mentions,
                expected_entities,
                str(item.get("negative_reason", "")),
                field_prefix,
                errors,
            )
            if status is not None:
                samples.append(
                    QuerySample(
                        id=query_id,
                        query=query_text,
                        expected_status=status,
                        mentions=mentions,
                        expected_entities=expected_entities,
                        negative_reason=str(item.get("negative_reason", "")),
                    )
                )
        return samples

    def _parse_status(
        self,
        raw_status: Any,
        field_prefix: str,
        errors: list[dict[str, str]],
    ) -> Status | None:
        try:
            status = Status(raw_status)
        except ValueError:
            errors.append(
                {
                    "field": f"{field_prefix}.expected_status",
                    "message": f"invalid expected_status: {raw_status!r}",
                }
            )
            return None
        allowed_statuses = self.V2_ALLOWED_STATUSES
        if status not in allowed_statuses:
            errors.append(
                {
                    "field": f"{field_prefix}.expected_status",
                    "message": f"unsupported expected_status: {status.value}",
                }
            )
        return status

    def _parse_mentions(
        self,
        raw_mentions: Any,
        query_text: str,
        catalog: CatalogRepository,
        field_prefix: str,
        errors: list[dict[str, str]],
        default_mention_status: Status = Status.LINKED,
    ) -> list[QueryMentionExpectation]:
        if not isinstance(raw_mentions, list):
            errors.append({"field": f"{field_prefix}.mentions", "message": "mentions must be list"})
            return []
        schema_version = str(catalog.metadata.get("schema_version", ""))
        is_v1 = schema_version in CatalogRepository.V1_SCHEMA_VERSIONS
        if is_v1 and len(raw_mentions) > 1:
            errors.append({"field": f"{field_prefix}.mentions", "message": "V1 allows at most one mention"})
        mentions: list[QueryMentionExpectation] = []
        for mention_index, mention in enumerate(raw_mentions):
            mention_prefix = f"{field_prefix}.mentions[{mention_index}]"
            if not isinstance(mention, dict):
                errors.append({"field": mention_prefix, "message": "mention must be object"})
                continue
            raw_text = mention.get("text")
            text = raw_text if isinstance(raw_text, str) else ""
            if not text:
                errors.append({"field": f"{mention_prefix}.text", "message": "text is required"})
            span = self._parse_span(mention.get("span"), query_text, text, mention_prefix, errors)
            expected_ids = self._mention_expected_ids(mention, mention_prefix, errors)
            for entity_id in expected_ids:
                if catalog.get(entity_id) is None:
                    errors.append(
                        {
                            "field": f"{mention_prefix}.expected_entity_ids",
                            "message": f"unknown expected entity: {entity_id}",
                        }
                    )
            expected_status = self._parse_mention_status(
                mention.get("expected_status"),
                mention_prefix,
                errors,
                default_status=default_mention_status,
            )
            expected_type = str(mention.get("expected_entity_type", "") or "")
            if is_v1 and not expected_type:
                expected_type = "alarm"
            if is_v1 and expected_type != "alarm":
                errors.append(
                    {
                        "field": f"{mention_prefix}.expected_entity_type",
                        "message": "expected_entity_type must be alarm",
                    }
                )
            if not is_v1 and expected_ids:
                expected_types = {
                    catalog.get(entity_id).entity_type.value
                    for entity_id in expected_ids
                    if catalog.get(entity_id) is not None
                }
                if len(expected_types) == 1 and not expected_type:
                    expected_type = next(iter(expected_types))
            mentions.append(
                QueryMentionExpectation(
                    text=text,
                    span=span,
                    expected_entity_ids=expected_ids,
                    expected_status=expected_status or Status.LINKED,
                    expected_entity_type=expected_type,
                    match_type=str(mention.get("match_type", "")),
                )
            )
        return mentions

    @staticmethod
    def _mention_expected_ids(
        mention: dict[str, Any],
        field_prefix: str,
        errors: list[dict[str, str]],
    ) -> list[str]:
        raw_ids = mention.get("expected_entity_ids", [])
        if not isinstance(raw_ids, list):
            errors.append(
                {
                    "field": f"{field_prefix}.expected_entity_ids",
                    "message": "expected_entity_ids must be list",
                }
            )
            raw_ids = []
        ids = [item for item in raw_ids if isinstance(item, str)]
        if len(ids) != len(raw_ids):
            errors.append(
                {
                    "field": f"{field_prefix}.expected_entity_ids",
                    "message": "expected_entity_ids values must be strings",
                }
            )
        raw_single = mention.get("expected_entity_id")
        if raw_single:
            if not isinstance(raw_single, str):
                errors.append(
                    {
                        "field": f"{field_prefix}.expected_entity_id",
                        "message": "expected_entity_id must be string",
                    }
                )
            elif raw_single not in ids:
                ids.append(raw_single)
        return ids

    @staticmethod
    def _parse_span(
        raw_span: Any,
        query_text: str,
        text: str,
        field_prefix: str,
        errors: list[dict[str, str]],
    ) -> tuple[int, int]:
        if (
            not isinstance(raw_span, list)
            or len(raw_span) != 2
            or not all(isinstance(item, int) for item in raw_span)
        ):
            errors.append({"field": f"{field_prefix}.span", "message": "span must be [start, end] integers"})
            return (0, 0)
        start, end = raw_span
        if start < 0 or end < start or end > len(query_text):
            errors.append({"field": f"{field_prefix}.span", "message": "span is out of range"})
            return (start, end)
        if query_text[start:end] != text:
            errors.append(
                {
                    "field": f"{field_prefix}.span",
                    "message": "span text does not equal mention text",
                }
            )
        return (start, end)

    @staticmethod
    def _parse_expected_entities(
        raw_entities: Any,
        catalog: CatalogRepository,
        field_prefix: str,
        errors: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        if not isinstance(raw_entities, list):
            errors.append(
                {"field": f"{field_prefix}.expected_entities", "message": "expected_entities must be list"}
            )
            return []
        entities: list[dict[str, Any]] = []
        for entity_index, entity in enumerate(raw_entities):
            entity_prefix = f"{field_prefix}.expected_entities[{entity_index}]"
            if not isinstance(entity, dict):
                errors.append({"field": entity_prefix, "message": "expected entity must be object"})
                continue
            entity_id = str(entity.get("entity_id", ""))
            if not entity_id:
                errors.append({"field": f"{entity_prefix}.entity_id", "message": "entity_id is required"})
            elif catalog.get(entity_id) is None:
                errors.append(
                    {
                        "field": f"{entity_prefix}.entity_id",
                        "message": f"unknown expected entity: {entity_id}",
                    }
                )
            expected_type = entity.get("entity_type")
            actual = catalog.get(entity_id) if entity_id else None
            if expected_type and actual and expected_type != actual.entity_type.value:
                errors.append(
                    {
                        "field": f"{entity_prefix}.entity_type",
                        "message": "expected entity_type does not match catalog",
                    }
                )
            entities.append(dict(entity))
        return entities

    def _parse_mention_status(
        self,
        raw_status: Any,
        field_prefix: str,
        errors: list[dict[str, str]],
        default_status: Status = Status.LINKED,
    ) -> Status | None:
        if raw_status is None:
            return default_status
        try:
            status = Status(raw_status)
        except ValueError:
            errors.append(
                {
                    "field": f"{field_prefix}.expected_status",
                    "message": f"invalid expected_status: {raw_status!r}",
                }
            )
            return None
        if status not in self.V2_ALLOWED_STATUSES:
            errors.append(
                {
                    "field": f"{field_prefix}.expected_status",
                    "message": f"unsupported mention expected_status: {status.value}",
                }
            )
        return status

    @staticmethod
    def _validate_status_contract(
        status: Status | None,
        mentions: list[QueryMentionExpectation],
        expected_entities: list[dict[str, Any]],
        negative_reason: str,
        field_prefix: str,
        errors: list[dict[str, str]],
    ) -> None:
        if status is None:
            return
        expected_ids = {str(entity.get("entity_id", "")) for entity in expected_entities}
        mention_ids = {
            entity_id
            for mention in mentions
            for entity_id in mention.expected_entity_ids
        }
        if mentions and mention_ids != expected_ids:
            errors.append(
                {
                    "field": field_prefix,
                    "message": "mention expected_entity_ids union must equal expected_entities entity_id set",
                }
            )
        if status == Status.LINKED:
            if not mentions or not expected_entities:
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "linked sample must have mentions and expected entities",
                    }
                )
            if any(mention.expected_status != Status.LINKED for mention in mentions):
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "linked sample must have only linked expected mentions",
                    }
                )
        elif status == Status.AMBIGUOUS:
            if len(mentions) != 1 or len(expected_entities) < 2:
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "ambiguous sample must have one mention and at least two expected entities",
                    }
                )
        elif status == Status.PARTIAL:
            if not mentions or not expected_entities:
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "partial sample must have mentions and at least one expected entity",
                    }
                )
            if not any(mention.expected_status == Status.LINKED for mention in mentions):
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "partial sample must include at least one linked mention",
                    }
                )
            if not any(mention.expected_status != Status.LINKED for mention in mentions):
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "partial sample must include at least one non-linked mention",
                    }
                )
        elif status == Status.NO_MATCH:
            if expected_entities:
                errors.append(
                    {"field": f"{field_prefix}.expected_entities", "message": "no_match expects no entities"}
                )
            if not negative_reason:
                errors.append(
                    {"field": f"{field_prefix}.negative_reason", "message": "negative_reason is required"}
                )
        elif status == Status.NOT_REQUIRED:
            if mentions or expected_entities:
                errors.append(
                    {
                        "field": field_prefix,
                        "message": "not_required must have empty mentions and expected_entities",
                    }
                )
            if not negative_reason:
                errors.append(
                    {"field": f"{field_prefix}.negative_reason", "message": "negative_reason is required"}
                )
