from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from dv_entity_linking.performance_mock import (
    DVAIAgentServiceMock,
    EntityBatch,
    MockDataStats,
    WordMatchBatch,
)
from dv_entity_linking.performance_mock.seeder import (
    DataPreset,
    _entity_rows,
    _word_rows,
)
from scripts.run_no_llm_low_latency_collection import (
    NoLlmRuntime,
    load_test_plan,
    run_load,
    summarize_samples,
    validate_observation,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "samples" / "mock" / "no_llm_low_latency_test_plan.json"
DATA_VERSION = "mock-large-1000000-test"


class _Source:
    words = {
        "cpuusage000001001": {
            "entity_word_id": "1001",
            "entity_id": "DV-MOCK-000000334",
            "entity_type": "metric",
            "entity_word": "CPU Usage 000001001",
            "normalized_key": "cpuusage000001001",
            "source": "alias",
            "match_mode": "EXACT_WORD",
            "min_context_required": False,
            "context_keywords": [],
            "priority": 99,
        },
        "cpuusage000001005": {
            "entity_word_id": "1005",
            "entity_id": "DV-MOCK-000000335",
            "entity_type": "metric",
            "entity_word": "CPU Usage 000001005",
            "normalized_key": "cpuusage000001005",
            "source": "alias",
            "match_mode": "EXACT_WORD",
            "min_context_required": True,
            "context_keywords": ["system", "node"],
            "priority": 95,
        },
    }
    entities = {
        "DV-MOCK-000000334": {
            "entity_id": "DV-MOCK-000000334",
            "entity_type": "metric",
            "entity_name": "CPU Usage 000001000",
            "alias": ["CPU Usage 000001001"],
            "desc": "Synthetic load-test entity 334",
            "attributes": {"synthetic": True},
            "relationships": [],
        },
        "DV-MOCK-000000335": {
            "entity_id": "DV-MOCK-000000335",
            "entity_type": "metric",
            "entity_name": "Distributed Service Metric 000001003",
            "alias": ["CPU Usage 000001005"],
            "desc": "Synthetic load-test entity 335",
            "attributes": {"synthetic": True},
            "relationships": [],
        },
    }

    def health(self):
        return DATA_VERSION

    def match_words(self, normalized_query, *, entity_types=()):
        matches = tuple(
            value
            for key, value in self.words.items()
            if key in normalized_query
            and (not entity_types or value["entity_type"] in entity_types)
        )
        return WordMatchBatch(matches, DATA_VERSION)

    def batch_get(self, entity_ids):
        return EntityBatch(
            tuple(self.entities[value] for value in entity_ids if value in self.entities),
            tuple(value for value in entity_ids if value not in self.entities),
            DATA_VERSION,
        )

    def stats(self):
        return MockDataStats(333_334, 1_000_000, DATA_VERSION)


def _server(source=None):
    service = DVAIAgentServiceMock(source or _Source())

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            response = json.dumps(service.execute(request)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class _GeneratedSource:
    def __init__(self) -> None:
        preset = DataPreset("golden", 1_100)
        self.words = []
        for row in _word_rows(preset):
            self.words.append(
                {
                    "entity_word_id": str(row[0]),
                    "entity_id": row[1],
                    "entity_type": row[2],
                    "entity_word": row[3],
                    "normalized_key": row[4],
                    "source": row[5],
                    "match_mode": row[6],
                    "min_context_required": bool(row[7]),
                    "context_keywords": json.loads(row[8]),
                    "priority": row[9],
                }
            )
        self.entities = {}
        for row in _entity_rows(preset):
            self.entities[row[0]] = {
                "entity_id": row[0],
                "entity_type": row[1],
                "entity_name": row[2],
                "alias": json.loads(row[3]),
                "desc": row[4],
                "attributes": json.loads(row[5]),
                "relationships": json.loads(row[6]),
            }

    def health(self):
        return DATA_VERSION

    def match_words(self, normalized_query, *, entity_types=()):
        return WordMatchBatch(
            tuple(
                value
                for value in self.words
                if value["normalized_key"] in normalized_query
                and (not entity_types or value["entity_type"] in entity_types)
            ),
            DATA_VERSION,
        )

    def batch_get(self, entity_ids):
        return EntityBatch(
            tuple(self.entities[value] for value in entity_ids if value in self.entities),
            tuple(value for value in entity_ids if value not in self.entities),
            DATA_VERSION,
        )

    def stats(self):
        return MockDataStats(
            len(self.entities),
            1_100,
            DATA_VERSION,
        )


def test_plan_has_explicit_no_llm_guards_and_formal_gradients() -> None:
    plan = load_test_plan(PLAN)

    assert plan.llm_enabled is False
    assert len(plan.llm_enforcement) == 3
    assert plan.profiles["formal"].duration_seconds == 900
    assert plan.profiles["formal"].concurrencies == (1, 10, 25, 50, 100)
    assert {"remote_match", "query_recall"} == {
        layer for case in plan.cases for layer in case.layers
    }


def test_every_golden_case_matches_deterministic_seed_rules() -> None:
    server, thread = _server(_GeneratedSource())
    runtime = NoLlmRuntime(
        f"http://127.0.0.1:{server.server_port}",
        timeout_ms=2_000,
        top_k=3,
    )
    plan = load_test_plan(PLAN)
    try:
        for case in plan.cases:
            for layer in case.layers:
                observation = runtime.execute(layer, case)
                assert validate_observation(case, layer, observation) == (
                    True,
                    None,
                ), (case.name, layer, observation)
    finally:
        runtime.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert {case.name for case in plan.cases} >= {
        "no_match_worst_scan",
        "single_exact_hit",
        "multi_exact_hit",
        "repeated_hit",
        "long_query_hit",
        "context_rule_pass",
        "context_rule_reject",
        "structured_alarm_hit",
    }


def test_runtime_structurally_disables_llm_and_exercises_p4_and_p9() -> None:
    server, thread = _server()
    runtime = NoLlmRuntime(
        f"http://127.0.0.1:{server.server_port}",
        timeout_ms=2_000,
        top_k=3,
    )
    plan = load_test_plan(PLAN)
    single = next(case for case in plan.cases if case.name == "single_exact_hit")
    bypass = next(case for case in plan.cases if case.name == "explicit_bypass")
    try:
        linker = runtime.facade._linker
        assert linker._enhancer is None
        assert linker._reranker is None

        direct = runtime.execute("remote_match", single)
        recall = runtime.execute("query_recall", single)
        bypass_result = runtime.execute("query_recall", bypass)

        assert validate_observation(single, "remote_match", direct) == (True, None)
        assert validate_observation(single, "query_recall", recall) == (True, None)
        assert direct["remote_calls"] == 1
        assert recall["remote_calls"] == 2
        assert bypass_result["status"] == "not_required"
        assert bypass_result["remote_calls"] == 0
    finally:
        runtime.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_context_rule_is_measured_separately_from_database_recall() -> None:
    server, thread = _server()
    runtime = NoLlmRuntime(
        f"http://127.0.0.1:{server.server_port}",
        timeout_ms=2_000,
        top_k=3,
    )
    plan = load_test_plan(PLAN)
    rejected = next(case for case in plan.cases if case.name == "context_rule_reject")
    try:
        direct = runtime.execute("remote_match", rejected)
        recall = runtime.execute("query_recall", rejected)

        assert direct["match_count"] == 1
        assert recall["status"] == "no_match"
        assert validate_observation(rejected, "remote_match", direct) == (True, None)
        assert validate_observation(rejected, "query_recall", recall) == (True, None)
    finally:
        runtime.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_summary_retains_tail_latency_errors_versions_and_case_breakdown() -> None:
    samples = [
        {
            "case": "hit",
            "latency_ms": 1.0,
            "transport_success": True,
            "correct": True,
            "status": "success",
            "error_code": None,
            "validation_error": None,
            "response_bytes": 100,
            "remote_calls": 1,
            "data_version": "same",
        },
        {
            "case": "hit",
            "latency_ms": 9.0,
            "transport_success": False,
            "correct": False,
            "status": "exception",
            "error_code": "timeout",
            "validation_error": None,
            "response_bytes": 0,
            "remote_calls": 0,
            "data_version": "",
        },
    ]

    summary = summarize_samples(samples, elapsed=1.0)

    assert summary["requests"] == 2
    assert summary["p50_ms"] == 1.0
    assert summary["p99_ms"] == 9.0
    assert summary["error_rate"] == 0.5
    assert summary["error_codes"] == {"timeout": 1}
    assert summary["data_version_stable"] is True
    assert summary["passed"] is False
    assert summary["cases"]["hit"]["requests"] == 2


def test_concurrent_collector_keeps_individual_samples_and_passes() -> None:
    server, thread = _server()
    runtime = NoLlmRuntime(
        f"http://127.0.0.1:{server.server_port}",
        timeout_ms=2_000,
        top_k=3,
    )
    single = next(
        case
        for case in load_test_plan(PLAN).cases
        if case.name == "single_exact_hit"
    )
    try:
        samples, elapsed = run_load(
            runtime,
            layer="remote_match",
            cases=(single,),
            concurrency=2,
            duration_seconds=0.2,
            warmups_per_worker=1,
        )
        summary = summarize_samples(samples, elapsed)

        assert len(samples) >= 2
        assert all(item["case"] == "single_exact_hit" for item in samples)
        assert summary["passed"] is True
        assert summary["data_versions"] == [DATA_VERSION]
        assert summary["qps"] > 0
    finally:
        runtime.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
