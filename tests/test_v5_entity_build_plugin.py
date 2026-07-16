from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from dv_entity_linking.entity_build_plugin import DailyRefreshScheduler, EntityBuildPlugin, EntityBuildTask, EntityBuildTaskRunner, InMemoryEntityPublisher, RestEntitySourceAdapter, build_task_runner_from_config
from dv_entity_linking.infrastructure.rest_tool import RestRequestTool, RestResponse


class _Transport:
    def __init__(self, payloads): self.payloads = payloads
    def execute(self, request):
        value = self.payloads[request.url]
        return RestResponse(200, value(request) if callable(value) else value)


class _StatusTransport:
    def __init__(self, status): self.status = status
    def execute(self, request): return RestResponse(self.status, {})


def test_v5_mock_sources_build_and_publish_v4_schema_entities() -> None:
    payloads = json.loads((Path("samples/mock/v5_interface_responses.json")).read_text(encoding="utf-8"))
    tool = RestRequestTool(_Transport({"mock://runtime": payloads["runtime"], "mock://knowledge": payloads["knowledge"]}))
    publisher = InMemoryEntityPublisher()
    plugin = EntityBuildPlugin((RestEntitySourceAdapter(tool, url="mock://runtime"), RestEntitySourceAdapter(tool, url="mock://knowledge")), publisher)
    assert plugin.start().status == "succeeded"
    assert [item["entity_id"] for item in publisher.current] == ["DV-KB-001", "DV-RUN-001"]
    knowledge = next(item for item in publisher.current if item["entity_id"] == "DV-KB-001")
    assert knowledge["attributes"] == {"severity": "major"}
    assert "source_kind" not in knowledge


def test_v5_conflict_preserves_previous_published_entities() -> None:
    class _Source:
        def __init__(self, entities): self.entities = entities
        def fetch_entities(self): return self.entities
    publisher = InMemoryEntityPublisher()
    publisher.current = ({"entity_id": "OLD", "entity_type": "alarm", "entity_name": "Old"},)
    plugin = EntityBuildPlugin((_Source([{"entity_id": "A", "entity_type": "alarm", "entity_name": "Shared"}]), _Source([{"entity_id": "B", "entity_type": "alarm", "entity_name": "Shared"}])), publisher)
    assert plugin.refresh().error_code == "entity_word_conflict"
    assert publisher.current[0]["entity_id"] == "OLD"


def test_v5_runtime_data_refresh_replaces_only_after_complete_validation() -> None:
    payloads = json.loads(Path("samples/mock/v5_interface_responses.json").read_text(encoding="utf-8"))
    tool = RestRequestTool(_Transport({"mock://runtime": payloads["runtime"]}))
    publisher = InMemoryEntityPublisher()
    plugin = EntityBuildPlugin((RestEntitySourceAdapter(tool, url="mock://runtime"),), publisher)
    assert plugin.refresh().entity_count == 1
    tool._transport.payloads["mock://runtime"] = payloads["runtime_refresh"]
    assert plugin.refresh().status == "succeeded"
    assert publisher.current[0]["entity_name"] == "ALM-200 Runtime Alarm Updated"


def test_v5_invalid_production_payload_and_source_failure_keep_old_data() -> None:
    payloads = json.loads(Path("samples/mock/v5_interface_responses.json").read_text(encoding="utf-8"))
    publisher = InMemoryEntityPublisher()
    publisher.current = ({"entity_id": "OLD", "entity_type": "alarm", "entity_name": "Old"},)
    invalid = EntityBuildPlugin((RestEntitySourceAdapter(RestRequestTool(_Transport({"mock://bad": payloads["invalid_missing_name"]})), url="mock://bad"),), publisher)
    assert invalid.refresh().error_code == "missing_required_field"
    assert publisher.current[0]["entity_id"] == "OLD"
    unavailable = EntityBuildPlugin((RestEntitySourceAdapter(RestRequestTool(_StatusTransport(503)), url="mock://down"),), publisher)
    assert unavailable.refresh().error_code == "http_error"
    assert publisher.current[0]["entity_id"] == "OLD"


def test_v5_publish_failure_and_idempotent_refresh_preserve_current_data() -> None:
    class _Source:
        def fetch_entities(self): return [{"entity_id": "A", "entity_type": "alarm", "entity_name": "A"}]
    class _FailingPublisher:
        def __init__(self): self.current = ({"entity_id": "OLD", "entity_type": "alarm", "entity_name": "Old"},)
        def replace_entities(self, entities): raise RuntimeError("write failed")
    failing = _FailingPublisher()
    assert EntityBuildPlugin((_Source(),), failing).refresh().error_code == "publication_failed"
    assert failing.current[0]["entity_id"] == "OLD"
    publisher = InMemoryEntityPublisher()
    plugin = EntityBuildPlugin((_Source(),), publisher)
    plugin.refresh(); plugin.refresh()
    assert publisher.publish_count == 1


def test_v5_separates_one_time_and_extensible_daily_tasks_without_data_loss() -> None:
    class _Source:
        def __init__(self, entity): self.entity = entity; self.calls = 0
        def fetch_entities(self): self.calls += 1; return [self.entity]
    once = _Source({"entity_id": "ONCE", "entity_type": "alarm", "entity_name": "Once"})
    daily = _Source({"entity_id": "DAILY", "entity_type": "alarm", "entity_name": "Daily"})
    publisher = InMemoryEntityPublisher()
    runner = EntityBuildTaskRunner(EntityBuildPlugin((), publisher), (EntityBuildTask("bootstrap", once, "once"), EntityBuildTask("runtime-refresh", daily, "daily")))
    assert runner.run_once().entity_count == 1
    assert runner.run_daily().entity_count == 2
    assert once.calls == 1 and daily.calls == 1
    assert [item["entity_id"] for item in publisher.current] == ["DAILY", "ONCE"]


def test_v5_daily_scheduler_runs_one_daily_batch_at_midnight_only() -> None:
    class _Source:
        def fetch_entities(self): return [{"entity_id": "D", "entity_type": "alarm", "entity_name": "Daily"}]
    publisher = InMemoryEntityPublisher()
    runner = EntityBuildTaskRunner(EntityBuildPlugin((), publisher), (EntityBuildTask("daily", _Source(), "daily"),))
    scheduler = DailyRefreshScheduler(runner)
    assert scheduler.run_if_due(datetime(2026, 7, 16, 23, 59)).error_code == "not_due"
    assert scheduler.run_if_due(datetime(2026, 7, 17, 0, 0)).status == "succeeded"
    assert scheduler.run_if_due(datetime(2026, 7, 17, 0, 0)).error_code == "already_run_today"


def test_v5_configured_endpoint_lists_need_no_per_endpoint_adapter(tmp_path) -> None:
    payloads = json.loads(Path("samples/mock/v5_interface_responses.json").read_text(encoding="utf-8"))
    config = tmp_path / "build.json"
    config.write_text(json.dumps({"entity_build": {"once_endpoints": [{"name": "bootstrap", "url": "mock://runtime"}], "daily_endpoints": [{"name": "knowledge", "url": "mock://knowledge"}]} }), encoding="utf-8")
    publisher = InMemoryEntityPublisher()
    paged = {"mock://runtime": {"items": payloads["runtime"]["entities"], "has_more": False}, "mock://knowledge": {"items": payloads["knowledge"]["entities"], "has_more": False}}
    runner = build_task_runner_from_config(EntityBuildPlugin((), publisher), RestRequestTool(_Transport(paged)), config)
    assert runner.run_once().entity_count == 1
    assert runner.run_daily().entity_count == 2


def test_v5_configured_endpoint_source_paginates_with_cursor_and_page_size(tmp_path) -> None:
    config = tmp_path / "build.json"
    config.write_text(json.dumps({"entity_build": {"page_size": 2, "daily_endpoints": [{"name": "paged", "url": "mock://paged"}]}}), encoding="utf-8")
    calls = []
    def pages(request):
        calls.append(request.params.copy())
        if "cursor" not in request.params:
            return {"items": [{"entity_id": "A", "entity_type": "alarm", "entity_name": "A"}], "has_more": True, "next_cursor": "page-2"}
        return {"items": [{"entity_id": "B", "entity_type": "alarm", "entity_name": "B"}], "has_more": False}
    publisher = InMemoryEntityPublisher()
    runner = build_task_runner_from_config(EntityBuildPlugin((), publisher), RestRequestTool(_Transport({"mock://paged": pages})), config)
    assert runner.run_daily().entity_count == 2
    assert calls == [{"page_size": "2"}, {"page_size": "2", "cursor": "page-2"}]


def test_v5_pagination_missing_cursor_preserves_previous_data(tmp_path) -> None:
    config = tmp_path / "build.json"
    config.write_text(json.dumps({"entity_build": {"daily_endpoints": [{"name": "broken", "url": "mock://broken"}]}}), encoding="utf-8")
    publisher = InMemoryEntityPublisher()
    publisher.current = ({"entity_id": "OLD", "entity_type": "alarm", "entity_name": "Old"},)
    runner = build_task_runner_from_config(EntityBuildPlugin((), publisher), RestRequestTool(_Transport({"mock://broken": {"items": [], "has_more": True}})), config)
    assert runner.run_daily().error_code == "source_refresh_failed"
    assert publisher.current[0]["entity_id"] == "OLD"


def test_v5_one_failed_endpoint_does_not_stop_later_endpoints_or_drop_cached_data(tmp_path) -> None:
    config = tmp_path / "build.json"
    config.write_text(json.dumps({"entity_build": {"daily_endpoints": [{"name": "first", "url": "mock://first"}, {"name": "broken", "url": "mock://broken"}, {"name": "last", "url": "mock://last"}]}}), encoding="utf-8")
    current = {
        "mock://first": {"items": [{"entity_id": "FIRST", "entity_type": "alarm", "entity_name": "First"}], "has_more": False},
        "mock://broken": {"items": [{"entity_id": "OLD-BROKEN", "entity_type": "alarm", "entity_name": "Old Broken"}], "has_more": False},
        "mock://last": {"items": [{"entity_id": "LAST", "entity_type": "alarm", "entity_name": "Last"}], "has_more": False},
    }
    class _SwitchingTransport:
        def __init__(self): self.fail = False; self.calls = []
        def execute(self, request):
            self.calls.append(request.url)
            if self.fail and request.url == "mock://broken": return RestResponse(503, {})
            return RestResponse(200, current[request.url])
    transport, publisher = _SwitchingTransport(), InMemoryEntityPublisher()
    runner = build_task_runner_from_config(EntityBuildPlugin((), publisher), RestRequestTool(transport), config)
    assert runner.run_daily().status == "succeeded"
    current["mock://first"] = {"items": [{"entity_id": "FIRST", "entity_type": "alarm", "entity_name": "First Updated"}], "has_more": False}
    transport.fail = True
    report = runner.run_daily()
    assert report.status == "partial"
    second_run_calls = transport.calls[3:]
    assert second_run_calls[0] == "mock://first"
    assert second_run_calls[-1] == "mock://last"
    assert second_run_calls.count("mock://broken") == 3  # initial call + two configured retries
    assert {item["entity_id"] for item in publisher.current} == {"FIRST", "OLD-BROKEN", "LAST"}
    assert next(item for item in publisher.current if item["entity_id"] == "FIRST")["entity_name"] == "First Updated"
