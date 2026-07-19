"""Opt-in no-LLM performance tests against this project's configured MySQL.

This file is intended to be executed explicitly by the follow-up coding agent.
It reads ``scripts/mysql_entity_data_mock_local.py`` through the existing mock
runner, starts the production-contract-compatible HTTP mock on an ephemeral
localhost port, and never accepts or requires another database/service address.

The suite is read-only.  It does not seed, truncate, delete, or rebuild data.
Normal regression runs skip it unless ``DV_RUN_MYSQL_PERFORMANCE=1`` is set.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_mysql_entity_data_mock import _config  # noqa: E402
from run_no_llm_low_latency_collection import (  # noqa: E402
    NoLlmRuntime,
    _write_samples,
    load_test_plan,
    run_load,
    run_preflight,
    summarize_samples,
)
from dv_entity_linking.performance_mock import (  # noqa: E402
    MySqlEntityDataMockSource,
    create_mock_app,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("DV_RUN_MYSQL_PERFORMANCE") != "1",
    reason="set DV_RUN_MYSQL_PERFORMANCE=1 to run persistent-MySQL load tests",
)

PLAN_PATH = ROOT / "samples" / "mock" / "no_llm_low_latency_test_plan.json"
PLAN = load_test_plan(PLAN_PATH)
PROFILE_NAME = os.environ.get("DV_PERF_PROFILE", "smoke")
if PROFILE_NAME not in PLAN.profiles:
    raise RuntimeError(f"unknown DV_PERF_PROFILE: {PROFILE_NAME}")
PROFILE = PLAN.profiles[PROFILE_NAME]


def _positive_int(name: str, default: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _concurrencies() -> tuple[int, ...]:
    raw = os.environ.get("DV_PERF_CONCURRENCIES")
    if raw is None:
        return PROFILE.concurrencies
    values = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    if not values or any(value <= 0 for value in values) or len(set(values)) != len(values):
        raise RuntimeError("DV_PERF_CONCURRENCIES must contain unique positive integers")
    return values


CONCURRENCIES = _concurrencies()
DURATION_SECONDS = _positive_int(
    "DV_PERF_DURATION_SECONDS",
    PROFILE.duration_seconds,
)
TIMEOUT_MS = _positive_int("DV_PERF_TIMEOUT_MS", 30_000)
POOL_SIZE = _positive_int(
    "DV_PERF_POOL_SIZE",
    max(CONCURRENCIES) + 10,
)


def _output_dir() -> Path:
    configured = os.environ.get("DV_PERF_OUTPUT_DIR")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else ROOT / path
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "outputs" / "performance" / f"pytest_no_llm_{PROFILE_NAME}_{timestamp}"


@pytest.fixture(scope="session")
def performance_context(pytestconfig):
    if os.environ.get("PYTEST_XDIST_WORKER"):
        pytest.fail("do not run this performance file with pytest-xdist/-n")
    try:
        from werkzeug.serving import make_server
    except ImportError:
        pytest.fail('install the local performance dependencies: pip install -e ".[performance-mock]"')

    output_dir = _output_dir()
    samples_dir = output_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    source = MySqlEntityDataMockSource(_config(POOL_SIZE))
    server = None
    server_thread = None
    runtime = None
    context: dict[str, Any] = {
        "output_dir": output_dir,
        "runs": [],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "stats": None,
        "preflight": None,
    }
    try:
        # These calls are read-only and prove that the existing configured
        # database is reachable before a local HTTP server is exposed.
        source.health()
        stats = source.stats()
        context["stats"] = {
            "entity_count": stats.entity_count,
            "entity_word_count": stats.entity_word_count,
            "data_version": stats.data_version,
        }

        server = make_server(
            "127.0.0.1",
            0,
            create_mock_app(source),
            threaded=True,
        )
        server_thread = threading.Thread(
            target=server.serve_forever,
            name="dv-performance-local-http",
            daemon=True,
        )
        server_thread.start()
        runtime = NoLlmRuntime(
            f"http://127.0.0.1:{server.server_port}",
            timeout_ms=TIMEOUT_MS,
            top_k=3,
        )
        context["runtime"] = runtime
        context["preflight"] = run_preflight(
            runtime,
            PLAN.cases,
            ("remote_match", "query_recall"),
        )
        (output_dir / "preflight.json").write_text(
            json.dumps(context["preflight"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not context["preflight"]["passed"]:
            pytest.fail(f"no-LLM correctness preflight failed; see {output_dir / 'preflight.json'}")
        yield context
    finally:
        if runtime is not None:
            runtime.close()
        if server is not None:
            server.shutdown()
            server.server_close()
        if server_thread is not None:
            server_thread.join(timeout=5)
        source.close()
        manifest = {
            "schema": "dv.pytest-no-llm-mysql-performance.1",
            "profile": PROFILE_NAME,
            "llm_enabled": False,
            "database_source": "current_project_ignored_local_config",
            "database_mutation": False,
            "local_mock_host": "127.0.0.1",
            "local_mock_port_recorded": False,
            "concurrencies": list(CONCURRENCIES),
            "duration_seconds_per_run": DURATION_SECONDS,
            "pool_size": POOL_SIZE,
            "started_at_utc": context["started_at_utc"],
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "stats": context["stats"],
            "preflight_passed": bool(
                context["preflight"] and context["preflight"].get("passed")
            ),
            "runs": context["runs"],
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "summary.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def test_existing_persistent_mysql_dataset_is_production_scale(performance_context) -> None:
    stats = performance_context["stats"]

    assert stats["entity_word_count"] >= 1_000_000
    assert stats["entity_count"] > 0
    assert stats["data_version"]


@pytest.mark.parametrize("concurrency", CONCURRENCIES)
def test_remote_match_latency_collection(performance_context, concurrency: int) -> None:
    _collect(performance_context, "remote_match", concurrency)


@pytest.mark.parametrize("concurrency", CONCURRENCIES)
def test_query_recall_latency_collection(performance_context, concurrency: int) -> None:
    _collect(performance_context, "query_recall", concurrency)


def _collect(context: dict[str, Any], layer: str, concurrency: int) -> None:
    samples, elapsed = run_load(
        context["runtime"],
        layer=layer,
        cases=PLAN.cases,
        concurrency=concurrency,
        duration_seconds=DURATION_SECONDS,
        warmups_per_worker=PROFILE.warmups_per_worker,
    )
    summary = summarize_samples(samples, elapsed)
    sample_name = f"{layer}_c{concurrency}.jsonl.gz"
    _write_samples(context["output_dir"] / "samples" / sample_name, samples)
    run_result = {
        "layer": layer,
        "concurrency": concurrency,
        "duration_seconds_requested": DURATION_SECONDS,
        "sample_file": f"samples/{sample_name}",
        **summary,
    }
    (context["output_dir"] / f"{layer}_c{concurrency}.summary.json").write_text(
        json.dumps(run_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context["runs"].append(run_result)

    assert summary["transport_errors"] == 0
    assert summary["correctness_failures"] == 0
    assert summary["data_version_stable"] is True
    assert summary["passed"] is True
