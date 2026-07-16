"""Independent V5 entity-build plugin; it never imports the V4 linker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
import re
from zoneinfo import ZoneInfo

from .infrastructure.rest_tool import RestRequest, RestRequestError, RestRequestTool


class EntityBuildError(RuntimeError):
    pass


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


@dataclass(frozen=True)
class BuildReport:
    status: str
    entity_count: int = 0
    error_code: str | None = None


class EntitySource(Protocol):
    def fetch_entities(self) -> list[dict[str, Any]]: ...


class EntityPublisher(Protocol):
    def replace_entities(self, entities: tuple[dict[str, Any], ...]) -> None: ...


@dataclass(frozen=True)
class EntityBuildTask:
    """An extensible source registration; all tasks return V4-schema entities."""

    name: str
    source: EntitySource
    mode: str  # ``once`` or ``daily``


class _StaticEntitySource:
    def __init__(self, entities: list[dict[str, Any]]) -> None:
        self._entities = entities

    def fetch_entities(self) -> list[dict[str, Any]]:
        return self._entities


class RestEntitySourceAdapter:
    """Source adapter used by both runtime and knowledge fixtures/hosts."""

    def __init__(self, tool: RestRequestTool, *, url: str) -> None:
        self._tool, self._url = tool, url

    def fetch_entities(self) -> list[dict[str, Any]]:
        body = self._tool.execute(RestRequest("GET", self._url)).body
        if not isinstance(body, dict) or not isinstance(body.get("entities"), list):
            raise EntityBuildError("source_schema_invalid")
        if not all(isinstance(item, dict) for item in body["entities"]):
            raise EntityBuildError("source_schema_invalid")
        return list(body["entities"])


@dataclass(frozen=True)
class EndpointConfig:
    name: str
    url: str
    page_size: int = 100
    retry_count: int = 2


class ConfiguredEndpointSource:
    """One generic source for any number of identically-shaped endpoints."""

    def __init__(self, tool: RestRequestTool, endpoints: tuple[EndpointConfig, ...]) -> None:
        if len({item.name for item in endpoints}) != len(endpoints):
            raise ValueError("endpoint names must be unique")
        self._tool, self._endpoints = tool, endpoints

    def fetch_entities(self) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []
        for endpoint in self._endpoints:
            cursor: str | None = None
            while True:
                params = {"page_size": str(endpoint.page_size)}
                if cursor is not None:
                    params["cursor"] = cursor
                body = self._tool.execute(RestRequest("GET", endpoint.url, params=params, retry_count=endpoint.retry_count)).body
                if not isinstance(body, dict) or not isinstance(body.get("items"), list) or not isinstance(body.get("has_more"), bool):
                    raise EntityBuildError("source_pagination_schema_invalid")
                if not all(isinstance(item, dict) for item in body["items"]):
                    raise EntityBuildError("source_schema_invalid")
                entities.extend(body["items"])
                if not body["has_more"]:
                    break
                cursor = body.get("next_cursor")
                if not isinstance(cursor, str) or not cursor:
                    raise EntityBuildError("source_pagination_cursor_missing")
        return entities


def build_task_runner_from_config(plugin: "EntityBuildPlugin", tool: RestRequestTool, path: str | Path) -> "EntityBuildTaskRunner":
    """Create the once/daily tasks from a small endpoint-only JSON config."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))["entity_build"]
    page_size = int(raw.get("page_size", 100))
    retry_count = int(raw.get("retry_count", 2))
    if not 1 <= page_size <= 1000 or not 0 <= retry_count <= 5:
        raise ValueError("invalid pagination configuration")
    def endpoints(key: str) -> tuple[EndpointConfig, ...]:
        values = raw.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f"{key} must be a list")
        return tuple(EndpointConfig(str(item["name"]), str(item["url"]), page_size, retry_count) for item in values if isinstance(item, dict))
    once, daily = endpoints("once_endpoints"), endpoints("daily_endpoints")
    tasks: list[EntityBuildTask] = []
    tasks.extend(EntityBuildTask(f"once:{item.name}", ConfiguredEndpointSource(tool, (item,)), "once") for item in once)
    tasks.extend(EntityBuildTask(f"daily:{item.name}", ConfiguredEndpointSource(tool, (item,)), "daily") for item in daily)
    return EntityBuildTaskRunner(plugin, tuple(tasks))


class EntityConstructionService:
    """Merges only V4-schema entity dictionaries and fails closed."""

    def build(self, sources: tuple[EntitySource, ...]) -> tuple[dict[str, Any], ...]:
        merged: dict[str, dict[str, Any]] = {}
        words: dict[str, str] = {}
        for source in sources:
            for entity in source.fetch_entities():
                self._validate(entity)
                entity_id = entity["entity_id"]
                existing = merged.get(entity_id)
                if existing is not None and existing != entity:
                    raise EntityBuildError("canonical_conflict")
                merged[entity_id] = entity
        for entity_id, entity in merged.items():
            for word in (entity["entity_name"], *entity.get("alias", [])):
                normalized = _key(word)
                previous = words.setdefault(normalized, entity_id)
                if previous != entity_id:
                    raise EntityBuildError("entity_word_conflict")
        return tuple(merged[key] for key in sorted(merged))

    @staticmethod
    def _validate(entity: dict[str, Any]) -> None:
        if not all(isinstance(entity.get(name), str) and entity[name].strip() for name in ("entity_id", "entity_type", "entity_name")):
            raise EntityBuildError("missing_required_field")
        if "alias" in entity and (not isinstance(entity["alias"], list) or not all(isinstance(value, str) for value in entity["alias"])):
            raise EntityBuildError("source_schema_invalid")
        forbidden = {"canonical", "source_kind", "source_record_id", "observed_at", "source_version", "data_snapshot_id"}
        if forbidden.intersection(entity):
            raise EntityBuildError("unexpected_entity_field")


class InMemoryEntityPublisher:
    """Fixture publisher that atomically replaces only a fully built set."""

    def __init__(self) -> None:
        self.current: tuple[dict[str, Any], ...] = ()
        self.publish_count = 0

    def replace_entities(self, entities: tuple[dict[str, Any], ...]) -> None:
        if entities == self.current:
            return
        self.current = entities
        self.publish_count += 1


class EntityBuildPlugin:
    def __init__(self, sources: tuple[EntitySource, ...], publisher: EntityPublisher) -> None:
        self._sources, self._publisher = sources, publisher
        self._builder = EntityConstructionService()
        self._lock = Lock()
        self.last_report = BuildReport("idle")

    def refresh(self) -> BuildReport:
        if not self._lock.acquire(blocking=False):
            self.last_report = BuildReport("skipped", error_code="refresh_skipped_in_progress")
            return self.last_report
        try:
            entities = self._builder.build(self._sources)
        except (EntityBuildError, RestRequestError) as exc:
            self.last_report = BuildReport("failed", error_code=str(exc))
        else:
            try:
                self._publisher.replace_entities(entities)
            except Exception:
                self.last_report = BuildReport("failed", error_code="publication_failed")
            else:
                self.last_report = BuildReport("succeeded", entity_count=len(entities))
        finally:
            self._lock.release()
        return self.last_report

    def start(self, *, blocking: bool = True) -> BuildReport:
        return self.refresh() if blocking else BuildReport("pending")


class EntityBuildTaskRunner:
    """Runs one-time and daily tasks separately while publishing one full set."""

    def __init__(self, plugin: EntityBuildPlugin, tasks: tuple[EntityBuildTask, ...]) -> None:
        if len({task.name for task in tasks}) != len(tasks):
            raise ValueError("entity build task names must be unique")
        if any(task.mode not in {"once", "daily"} for task in tasks):
            raise ValueError("entity build task mode must be once or daily")
        self._plugin, self._tasks = plugin, tasks
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def run_once(self) -> BuildReport:
        return self._run("once")

    def run_daily(self) -> BuildReport:
        return self._run("daily")

    def _run(self, mode: str) -> BuildReport:
        updates: dict[str, list[dict[str, Any]]] = {}
        failed = 0
        for task in self._tasks:
            if task.mode == mode:
                try:
                    updates[task.name] = task.source.fetch_entities()
                except (EntityBuildError, RestRequestError):
                    failed += 1
                    continue
        if failed and not updates and not self._cache:
            return BuildReport("failed", error_code="source_refresh_failed")
        combined = {**self._cache, **updates}
        if not combined:
            return BuildReport("skipped", error_code="no_registered_tasks")
        original = self._plugin._sources
        self._plugin._sources = tuple(_StaticEntitySource(items) for _, items in sorted(combined.items()))
        try:
            report = self._plugin.refresh()
        finally:
            self._plugin._sources = original
        if report.status == "succeeded":
            self._cache.update(updates)
            if failed:
                return BuildReport("partial", entity_count=report.entity_count, error_code="source_refresh_partial")
        return report


class DailyRefreshScheduler:
    """Deterministic midnight gate; hosts invoke it from their lifecycle timer."""

    def __init__(self, runner: EntityBuildTaskRunner, *, timezone: str = "Asia/Shanghai") -> None:
        self._runner, self._last_date = runner, None
        self._timezone = ZoneInfo(timezone)

    def run_if_due(self, now: datetime) -> BuildReport:
        local_now = now.astimezone(self._timezone) if now.tzinfo else now.replace(tzinfo=self._timezone)
        if local_now.hour != 0 or local_now.minute != 0:
            return BuildReport("skipped", error_code="not_due")
        if self._last_date == local_now.date():
            return BuildReport("skipped", error_code="already_run_today")
        self._last_date = local_now.date()
        return self._runner.run_daily()
