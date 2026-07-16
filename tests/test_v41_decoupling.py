"""V4.1 isolation, compatibility and migration validation tests."""

from __future__ import annotations

import ast
from dataclasses import fields
import json
from pathlib import Path

import pytest

from dv_entity_linking import LinkRequestV1, LinkResponseV1, ModuleConfig, create_entity_linking_module
from dv_entity_linking.domain.ports import EntityDataDependencyError
from dv_entity_linking.v41 import V41ValidationError, build_entity_migration_bundle, validate_v41_config


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "dv_entity_linking"


def _entity(entity_id: str, *, name: str, alias: list[str] | None = None, relationships=None):
    return {
        "entity_id": entity_id,
        "entity_type": "metric",
        "entity_name": name,
        "alias": alias or [],
        "desc": "safe summary",
        "attributes": {"unit": "%"},
        "relationships": relationships or [],
    }


def test_v41_production_modules_do_not_import_legacy_runtime() -> None:
    offenders: list[str] = []
    for path in PACKAGE.rglob("*.py"):
        if "legacy" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = ""
            if isinstance(node, ast.Import):
                module = " ".join(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
            if ".legacy" in module or module.startswith("dv_entity_linking.legacy") or "v3_mock" in module:
                offenders.append(f"{path.relative_to(ROOT)}:{module}")
    assert offenders == []


def test_v41_public_contract_manifest_matches_dataclasses() -> None:
    manifest = json.loads((ROOT / "docs" / "baselines" / "v4.1" / "PUBLIC_CONTRACT.json").read_text(encoding="utf-8"))
    assert manifest["contract_version"] == "v4.link-response.1"
    assert manifest["request_fields"] == [field.name for field in fields(LinkRequestV1)]
    assert manifest["response_fields"] == [field.name for field in fields(LinkResponseV1)]
    assert set(manifest["statuses"]) == {
        "linked", "partial", "ambiguous", "no_match", "not_required", "dependency_failed", "invalid_input"
    }


def test_v41_factory_dependency_failure_does_not_fall_back_to_historical_data() -> None:
    class _UnavailablePlatformClient:
        def invoke(self, *, url, payload, timeout_ms):
            raise EntityDataDependencyError("transport_failed", "simulated")

    module = create_entity_linking_module(
        ModuleConfig(entity_data_ir_url="ir://entity-data/service", startup_failure_policy="DEGRADED"),
        platform_client=_UnavailablePlatformClient(),
    )
    result = module.link(LinkRequestV1(query="Check CPU Usage"))
    assert result.status == "dependency_failed"
    assert result.error_code == "startup_health_failed"


def test_v41_migration_builds_deterministic_safe_bundle() -> None:
    bundle = build_entity_migration_bundle(
        [
            _entity("metric-1", name="CPU Usage", alias=["CPU"], relationships=[{"relation_type": "depends_on", "target_entity_id": "metric-2"}]),
            _entity("metric-2", name="Memory Usage"),
        ],
        source_version="v4-accepted",
    )
    assert [(word.entity_word, word.source) for word in bundle.entity_words] == [
        ("CPU Usage", "entity_name"),
        ("CPU", "confirmed_alias"),
        ("Memory Usage", "entity_name"),
    ]
    assert bundle.report == {
        "report_version": "v4.1",
        "source_version": "v4-accepted",
        "dry_run": True,
        "entity_count": 2,
        "active_entity_count": 2,
        "entity_word_count": 3,
        "conflict_count": 0,
        "relationship_count": 1,
        "validation": "passed",
    }
    assert "safe summary" not in json.dumps(bundle.report)


@pytest.mark.parametrize(
    ("entities", "message"),
    [
        ([_entity("one", name="CPU Usage"), _entity("two", name=" CPU  Usage ")], "active normalized entity word conflict"),
        ([_entity("one", name="CPU Usage", relationships=[{"relation_type": "depends_on", "target_entity_id": "missing"}])], "unknown target"),
    ],
)
def test_v41_migration_fails_closed(entities, message) -> None:
    with pytest.raises(V41ValidationError, match=message):
        build_entity_migration_bundle(entities, source_version="v4-accepted")


def test_v41_configuration_rejects_deprecated_runtime_settings() -> None:
    with pytest.raises(V41ValidationError, match="redis_mock_path"):
        validate_v41_config({"entity_data_ir_url": "ir://entity-data/service", "redis_mock_path": "ignored.json"})
    assert validate_v41_config({"entity_data_ir_url": "ir://entity-data/service"}) == {
        "config_version": "v4.1",
        "dry_run": True,
        "accepted_keys": ["entity_data_ir_url"],
        "startup_failure_policy": "DEGRADED",
    }
