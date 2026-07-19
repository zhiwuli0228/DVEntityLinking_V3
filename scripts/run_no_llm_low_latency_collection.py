"""Collect low-latency MATCH_WORDS and Query Recall evidence with LLM disabled.

The collector is intentionally read-only.  It exercises the persistent MySQL
mock through its production-compatible HTTP contract and never deletes, resets,
or mutates seeded entity data.  Raw request samples are written as gzip JSONL;
the compact summary contains no endpoint host, query text, or credentials.
"""

from __future__ import annotations

import argparse
from collections import Counter
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import http.client
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import threading
import time
from typing import Any, Sequence
from urllib.error import URLError
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dv_entity_linking.domain.normalization import normalize_query  # noqa: E402
from dv_entity_linking.infrastructure.entity_data_rest import (  # noqa: E402
    RestEntityDataClient,
)
from dv_entity_linking.module import EntityLinkingModule  # noqa: E402
from dv_entity_linking.query_recall import (  # noqa: E402
    QueryRecallFacade,
    RecallConfigProvider,
)


PLAN_SCHEMA = "dv.no-llm-low-latency-test-plan.1"
RESULT_SCHEMA = "dv.no-llm-low-latency-result.1"
SUPPORTED_LAYERS = ("remote_match", "query_recall")


@dataclass(frozen=True)
class TestCase:
    name: str
    raw_query: str
    normalized_query: str
    entity_types: tuple[str, ...]
    layers: tuple[str, ...]
    weight: int
    expected_remote_match_count: tuple[int, int] | None
    expected_recall_status: str | None
    expected_remote_entity_ids: tuple[str, ...] | None
    expected_recall_entity_ids: tuple[str, ...] | None


@dataclass(frozen=True)
class TestProfile:
    name: str
    duration_seconds: int
    concurrencies: tuple[int, ...]
    warmups_per_worker: int


@dataclass(frozen=True)
class TestPlan:
    schema: str
    profiles: dict[str, TestProfile]
    cases: tuple[TestCase, ...]
    llm_enabled: bool
    llm_enforcement: tuple[str, ...]


class _BufferedResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self._body


class PersistentHttpOpener:
    """urllib-compatible opener with one persistent connection per load thread."""

    def __init__(self) -> None:
        self._local = threading.local()

    def begin_measurement(self) -> None:
        self._local.response_bytes = 0
        self._local.request_count = 0

    def end_measurement(self) -> tuple[int, int]:
        return (
            int(getattr(self._local, "response_bytes", 0)),
            int(getattr(self._local, "request_count", 0)),
        )

    def _connection(self, scheme: str, host: str, port: int, timeout: float):
        origin = (scheme, host, port)
        connection = getattr(self._local, "connection", None)
        if connection is not None and getattr(self._local, "origin", None) != origin:
            connection.close()
            connection = None
        if connection is None:
            connection_type = (
                http.client.HTTPSConnection
                if scheme == "https"
                else http.client.HTTPConnection
            )
            connection = connection_type(host, port, timeout=timeout)
            self._local.connection = connection
            self._local.origin = origin
        else:
            connection.timeout = timeout
        return connection

    def __call__(self, request, timeout: float):
        parsed = urlsplit(request.full_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise URLError("unsupported endpoint")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection = self._connection(
            parsed.scheme,
            parsed.hostname,
            port,
            timeout,
        )
        try:
            connection.request(
                request.get_method(),
                path,
                body=request.data,
                headers=dict(request.header_items()),
            )
            response = connection.getresponse()
            body = response.read()
        except (OSError, http.client.HTTPException) as exc:
            self.close_current()
            raise URLError("transport failure") from exc
        self._local.response_bytes = int(
            getattr(self._local, "response_bytes", 0)
        ) + len(body)
        self._local.request_count = int(
            getattr(self._local, "request_count", 0)
        ) + 1
        return _BufferedResponse(response.status, body)

    def close_current(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None
            self._local.origin = None


def _positive_csv(value: str, *, option: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} must contain integers") from exc
    if not parsed or any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError(f"{option} must contain positive integers")
    if len(set(parsed)) != len(parsed):
        raise argparse.ArgumentTypeError(f"{option} must not contain duplicates")
    return parsed


def _nullable_ids(value: Any, *, field: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be null or a string array")
    return tuple(value)


def load_test_plan(path: str | Path) -> TestPlan:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema") != PLAN_SCHEMA:
        raise ValueError("unsupported test plan schema")
    llm = raw.get("llm")
    if not isinstance(llm, dict) or llm.get("enabled") is not False:
        raise ValueError("test plan must explicitly disable LLM")
    enforcement = llm.get("enforcement")
    if not isinstance(enforcement, list) or len(enforcement) < 3:
        raise ValueError("test plan must declare all no-LLM enforcement controls")

    profiles: dict[str, TestProfile] = {}
    for name, value in raw.get("profiles", {}).items():
        if not isinstance(value, dict):
            raise ValueError("profile must be an object")
        duration = int(value["duration_seconds"])
        concurrencies = tuple(int(item) for item in value["concurrencies"])
        warmups = int(value["warmups_per_worker"])
        if (
            duration <= 0
            or not concurrencies
            or any(item <= 0 for item in concurrencies)
            or len(set(concurrencies)) != len(concurrencies)
            or warmups < 0
        ):
            raise ValueError(f"invalid profile: {name}")
        profiles[name] = TestProfile(
            name,
            duration,
            concurrencies,
            warmups,
        )
    if not profiles:
        raise ValueError("at least one profile is required")

    cases: list[TestCase] = []
    names: set[str] = set()
    for value in raw.get("cases", []):
        if not isinstance(value, dict):
            raise ValueError("case must be an object")
        name = str(value["name"])
        raw_query = str(value["raw_query"])
        normalized_query = str(value["normalized_query"])
        if name in names:
            raise ValueError(f"duplicate case: {name}")
        names.add(name)
        if normalize_query(raw_query).normalized_text != normalized_query:
            raise ValueError(f"normalized query mismatch: {name}")
        layers = tuple(str(item) for item in value["layers"])
        if not layers or any(item not in SUPPORTED_LAYERS for item in layers):
            raise ValueError(f"unsupported layer in case: {name}")
        weight = int(value.get("weight", 1))
        if weight < 0:
            raise ValueError(f"negative case weight: {name}")
        count_range = value.get("expected_remote_match_count")
        expected_count = None
        if count_range is not None:
            if (
                not isinstance(count_range, list)
                or len(count_range) != 2
                or any(not isinstance(item, int) or item < 0 for item in count_range)
                or count_range[0] > count_range[1]
            ):
                raise ValueError(f"invalid match count range: {name}")
            expected_count = (count_range[0], count_range[1])
        recall_status = value.get("expected_recall_status")
        if recall_status is not None and not isinstance(recall_status, str):
            raise ValueError(f"invalid recall status: {name}")
        cases.append(
            TestCase(
                name=name,
                raw_query=raw_query,
                normalized_query=normalized_query,
                entity_types=tuple(str(item) for item in value.get("entity_types", [])),
                layers=layers,
                weight=weight,
                expected_remote_match_count=expected_count,
                expected_recall_status=recall_status,
                expected_remote_entity_ids=_nullable_ids(
                    value.get("expected_remote_entity_ids"),
                    field="expected_remote_entity_ids",
                ),
                expected_recall_entity_ids=_nullable_ids(
                    value.get("expected_recall_entity_ids"),
                    field="expected_recall_entity_ids",
                ),
            )
        )
    if not cases:
        raise ValueError("at least one test case is required")
    return TestPlan(
        schema=PLAN_SCHEMA,
        profiles=profiles,
        cases=tuple(cases),
        llm_enabled=False,
        llm_enforcement=tuple(str(item) for item in enforcement),
    )


class NoLlmRuntime:
    """Read-only runtime that structurally excludes both LLM extension points."""

    def __init__(self, base_url: str, *, timeout_ms: int, top_k: int) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="dv-no-llm-")
        policy_path = Path(self._temporary.name) / "recall.json"
        policy_path.write_text(
            json.dumps(
                {
                    "recall": {
                        "use_llm": False,
                        "top_k": top_k,
                        "allow_fallback": True,
                        "entity_types": [],
                    }
                }
            ),
            encoding="utf-8",
        )
        self.opener = PersistentHttpOpener()
        self.client = RestEntityDataClient(
            base_url,
            timeout_ms=timeout_ms,
            opener=self.opener,
        )
        # No enhancer and no reranker are attached.  The explicit false override
        # below is a second guard even if the policy file were modified.
        linker = EntityLinkingModule(data_client=self.client)
        self.facade = QueryRecallFacade(linker, RecallConfigProvider(policy_path))
        self.top_k = top_k

    def close(self) -> None:
        self.opener.close_current()
        self._temporary.cleanup()

    def execute(self, layer: str, case: TestCase) -> dict[str, Any]:
        self.opener.begin_measurement()
        if layer == "remote_match":
            response = self.client.match_words(
                case.normalized_query,
                entity_types=case.entity_types,
            )
            response_bytes, remote_calls = self.opener.end_measurement()
            return {
                "status": "success",
                "match_count": len(response.matches),
                "mention_count": 0,
                "entity_ids": sorted({item.entity_id for item in response.matches}),
                "data_version": response.data_version,
                "response_bytes": response_bytes,
                "remote_calls": remote_calls,
            }
        if layer == "query_recall":
            result = self.facade.recall(
                case.raw_query,
                use_llm=False,
                top_k=self.top_k,
            )
            response_bytes, remote_calls = self.opener.end_measurement()
            entity_ids = {
                item.entity_id
                for item in result.candidates
            }
            for mention in result.mentions:
                if mention.entity_id:
                    entity_ids.add(mention.entity_id)
                entity_ids.update(item.entity_id for item in mention.candidates)
            return {
                "status": result.status,
                "match_count": 0,
                "mention_count": len(result.mentions),
                "entity_ids": sorted(entity_ids),
                "data_version": "",
                "response_bytes": response_bytes,
                "remote_calls": remote_calls,
                "error_code": result.error_code,
                "degraded": result.degraded,
            }
        raise ValueError("unsupported layer")


def validate_observation(
    case: TestCase,
    layer: str,
    observation: dict[str, Any],
) -> tuple[bool, str | None]:
    if layer == "remote_match":
        expected_count = case.expected_remote_match_count
        if expected_count is None:
            return False, "missing_remote_expectation"
        count = int(observation["match_count"])
        if not expected_count[0] <= count <= expected_count[1]:
            return False, "remote_match_count_mismatch"
        expected_ids = case.expected_remote_entity_ids
    elif layer == "query_recall":
        if observation.get("status") != case.expected_recall_status:
            return False, "recall_status_mismatch"
        expected_ids = case.expected_recall_entity_ids
    else:
        return False, "unsupported_layer"
    if expected_ids is None:
        return False, "missing_entity_id_expectation"
    if tuple(sorted(observation.get("entity_ids", ()))) != tuple(sorted(expected_ids)):
        return False, "entity_ids_mismatch"
    if layer == "query_recall" and observation.get("degraded"):
        return False, "unexpected_degradation"
    return True, None


def _safe_error_code(exc: Exception) -> str:
    value = getattr(exc, "code", None)
    return str(value) if isinstance(value, str) else type(exc).__name__


def execute_sample(
    runtime: NoLlmRuntime,
    layer: str,
    case: TestCase,
    *,
    started_at: float,
) -> dict[str, Any]:
    offset_ms = round((time.perf_counter() - started_at) * 1000, 3)
    request_started = time.perf_counter()
    try:
        observation = runtime.execute(layer, case)
        latency_ms = round((time.perf_counter() - request_started) * 1000, 3)
        correct, validation_error = validate_observation(case, layer, observation)
        return {
            "case": case.name,
            "started_offset_ms": offset_ms,
            "latency_ms": latency_ms,
            "transport_success": True,
            "correct": correct,
            "validation_error": validation_error,
            "error_code": observation.get("error_code"),
            "status": observation.get("status"),
            "match_count": observation.get("match_count", 0),
            "mention_count": observation.get("mention_count", 0),
            "response_bytes": observation.get("response_bytes", 0),
            "remote_calls": observation.get("remote_calls", 0),
            "data_version": observation.get("data_version", ""),
        }
    except Exception as exc:
        response_bytes, remote_calls = runtime.opener.end_measurement()
        return {
            "case": case.name,
            "started_offset_ms": offset_ms,
            "latency_ms": round((time.perf_counter() - request_started) * 1000, 3),
            "transport_success": False,
            "correct": False,
            "validation_error": None,
            "error_code": _safe_error_code(exc),
            "status": "exception",
            "match_count": 0,
            "mention_count": 0,
            "response_bytes": response_bytes,
            "remote_calls": remote_calls,
            "data_version": "",
        }


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[rank], 3)


def summarize_samples(samples: Sequence[dict[str, Any]], elapsed: float) -> dict[str, Any]:
    latencies = [float(item["latency_ms"]) for item in samples]
    transport_errors = sum(not item["transport_success"] for item in samples)
    correctness_failures = sum(
        item["transport_success"] and not item["correct"] for item in samples
    )
    data_versions = sorted(
        {str(item["data_version"]) for item in samples if item.get("data_version")}
    )

    def metrics(values: Sequence[dict[str, Any]]) -> dict[str, Any]:
        local_latencies = [float(item["latency_ms"]) for item in values]
        return {
            "requests": len(values),
            "p50_ms": _percentile(local_latencies, 0.50),
            "p95_ms": _percentile(local_latencies, 0.95),
            "p99_ms": _percentile(local_latencies, 0.99),
            "mean_ms": round(statistics.fmean(local_latencies), 3)
            if local_latencies
            else 0.0,
            "max_ms": round(max(local_latencies), 3) if local_latencies else 0.0,
            "transport_errors": sum(not item["transport_success"] for item in values),
            "correctness_failures": sum(
                item["transport_success"] and not item["correct"] for item in values
            ),
            "mean_response_bytes": round(
                statistics.fmean(float(item["response_bytes"]) for item in values),
                1,
            )
            if values
            else 0.0,
            "mean_remote_calls": round(
                statistics.fmean(float(item["remote_calls"]) for item in values),
                3,
            )
            if values
            else 0.0,
        }

    by_case = {
        name: metrics([item for item in samples if item["case"] == name])
        for name in sorted({str(item["case"]) for item in samples})
    }
    return {
        **metrics(samples),
        "elapsed_seconds": round(elapsed, 3),
        "qps": round(len(samples) / elapsed, 3) if elapsed else 0.0,
        "error_rate": round(transport_errors / len(samples), 6) if samples else 0.0,
        "status_counts": dict(sorted(Counter(item["status"] for item in samples).items())),
        "error_codes": dict(
            sorted(
                Counter(
                    str(item["error_code"])
                    for item in samples
                    if item.get("error_code")
                ).items()
            )
        ),
        "validation_errors": dict(
            sorted(
                Counter(
                    str(item["validation_error"])
                    for item in samples
                    if item.get("validation_error")
                ).items()
            )
        ),
        "data_versions": data_versions,
        "data_version_stable": len(data_versions) <= 1,
        "passed": transport_errors == 0
        and correctness_failures == 0
        and len(data_versions) <= 1,
        "cases": by_case,
    }


def run_preflight(
    runtime: NoLlmRuntime,
    cases: Sequence[TestCase],
    layers: Sequence[str],
) -> dict[str, Any]:
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    health_started = time.perf_counter()
    try:
        health = runtime.client.health()
        health_record = {
            "passed": health.status == "healthy",
            "latency_ms": round((time.perf_counter() - health_started) * 1000, 3),
            "data_version": health.data_version,
            "error_code": None,
        }
    except Exception as exc:
        health_record = {
            "passed": False,
            "latency_ms": round((time.perf_counter() - health_started) * 1000, 3),
            "data_version": "",
            "error_code": _safe_error_code(exc),
        }
    for layer in layers:
        for case in cases:
            if layer not in case.layers:
                continue
            record = execute_sample(runtime, layer, case, started_at=started)
            records.append({"layer": layer, **record})
    runtime.opener.close_current()
    return {
        "health": health_record,
        "records": records,
        "passed": health_record["passed"]
        and all(item["transport_success"] and item["correct"] for item in records),
    }


def run_load(
    runtime: NoLlmRuntime,
    *,
    layer: str,
    cases: Sequence[TestCase],
    concurrency: int,
    duration_seconds: int,
    warmups_per_worker: int,
) -> tuple[list[dict[str, Any]], float]:
    weighted = [case for case in cases for _ in range(case.weight) if layer in case.layers]
    if not weighted:
        raise ValueError(f"no weighted cases for layer: {layer}")
    clock: dict[str, float] = {}

    def release_workers() -> None:
        clock["started"] = time.perf_counter()
        clock["deadline"] = clock["started"] + duration_seconds

    barrier = threading.Barrier(concurrency + 1, action=release_workers)

    def worker(index: int) -> list[dict[str, Any]]:
        try:
            for warmup in range(warmups_per_worker):
                try:
                    runtime.execute(layer, weighted[(index + warmup) % len(weighted)])
                except Exception:
                    # Preflight owns correctness gating.  A transient warmup
                    # failure must not strand the remaining workers at the
                    # start barrier or prevent collection of failure evidence.
                    pass
            barrier.wait()
            samples: list[dict[str, Any]] = []
            iteration = 0
            while time.perf_counter() < clock["deadline"]:
                case = weighted[(index + iteration) % len(weighted)]
                samples.append(
                    execute_sample(
                        runtime,
                        layer,
                        case,
                        started_at=clock["started"],
                    )
                )
                iteration += 1
            return samples
        finally:
            runtime.opener.close_current()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, index) for index in range(concurrency)]
        barrier.wait()
        worker_results = [future.result() for future in futures]
    elapsed = time.perf_counter() - clock["started"]
    return [item for result in worker_results for item in result], elapsed


def _write_samples(path: Path, samples: Sequence[dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for item in samples:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8089")
    parser.add_argument(
        "--plan",
        type=Path,
        default=ROOT / "samples" / "mock" / "no_llm_low_latency_test_plan.json",
    )
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--layers", default=",".join(SUPPORTED_LAYERS))
    parser.add_argument("--concurrencies")
    parser.add_argument("--duration-seconds", type=int)
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--endpoint-label", default="local-low-latency-mock")
    parser.add_argument("--cases", help="optional comma-separated case names")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        plan = load_test_plan(args.plan)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "invalid_plan", "error": str(exc)}), file=sys.stderr)
        return 2
    if args.profile not in plan.profiles:
        print(f"Unknown profile: {args.profile}", file=sys.stderr)
        return 2
    parsed_url = urlsplit(args.base_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
    ):
        print("--base-url must be an HTTP(S) URL without credentials", file=sys.stderr)
        return 2
    layers = tuple(item.strip() for item in args.layers.split(",") if item.strip())
    if not layers or any(item not in SUPPORTED_LAYERS for item in layers):
        print("--layers contains an unsupported layer", file=sys.stderr)
        return 2
    profile = plan.profiles[args.profile]
    try:
        concurrencies = (
            _positive_csv(args.concurrencies, option="--concurrencies")
            if args.concurrencies
            else profile.concurrencies
        )
    except argparse.ArgumentTypeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    duration_seconds = args.duration_seconds or profile.duration_seconds
    if duration_seconds <= 0 or args.timeout_ms <= 0 or not 1 <= args.top_k <= 100:
        print("duration, timeout, and top-k values are invalid", file=sys.stderr)
        return 2
    cases = plan.cases
    if args.cases:
        selected_names = {item.strip() for item in args.cases.split(",") if item.strip()}
        unknown = selected_names.difference(item.name for item in cases)
        if unknown:
            print("Unknown cases: " + ", ".join(sorted(unknown)), file=sys.stderr)
            return 2
        cases = tuple(item for item in cases if item.name in selected_names)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or (
        ROOT / "outputs" / "performance" / f"no_llm_{args.profile}_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    samples_dir = output_dir / "samples"
    samples_dir.mkdir(exist_ok=True)

    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile": args.profile,
        "endpoint_label": args.endpoint_label,
        "endpoint_host_recorded": False,
        "llm": {
            "enabled": False,
            "enforcement": list(plan.llm_enforcement),
        },
        "workload": {
            "layers": list(layers),
            "concurrencies": list(concurrencies),
            "duration_seconds_per_run": duration_seconds,
            "warmups_per_worker": profile.warmups_per_worker,
            "case_names": [item.name for item in cases],
        },
        "client_environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
        },
        "preflight": None,
        "runs": [],
    }
    runtime = NoLlmRuntime(
        args.base_url,
        timeout_ms=args.timeout_ms,
        top_k=args.top_k,
    )
    exit_code = 0
    try:
        if not args.skip_preflight:
            print("Running no-LLM correctness preflight...", file=sys.stderr)
            result["preflight"] = run_preflight(runtime, cases, layers)
            if not result["preflight"]["passed"]:
                result["status"] = "preflight_failed"
                exit_code = 1
            else:
                result["status"] = "collecting"
        if exit_code == 0:
            for layer in layers:
                for concurrency in concurrencies:
                    print(
                        f"Collecting layer={layer} concurrency={concurrency} "
                        f"duration={duration_seconds}s...",
                        file=sys.stderr,
                    )
                    samples, elapsed = run_load(
                        runtime,
                        layer=layer,
                        cases=cases,
                        concurrency=concurrency,
                        duration_seconds=duration_seconds,
                        warmups_per_worker=profile.warmups_per_worker,
                    )
                    sample_name = f"{layer}_c{concurrency}.jsonl.gz"
                    _write_samples(samples_dir / sample_name, samples)
                    summary = summarize_samples(samples, elapsed)
                    result["runs"].append(
                        {
                            "layer": layer,
                            "concurrency": concurrency,
                            "sample_file": f"samples/{sample_name}",
                            **summary,
                        }
                    )
                    if not summary["passed"]:
                        exit_code = 1
            result["status"] = "completed" if exit_code == 0 else "completed_with_failures"
    except Exception as exc:
        result["status"] = "collector_failed"
        result["collector_error_code"] = _safe_error_code(exc)
        exit_code = 1
    finally:
        runtime.close()
        result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["passed"] = exit_code == 0
        summary_path = output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "passed": result["passed"],
                    "summary": str(summary_path.resolve()),
                    "run_count": len(result["runs"]),
                },
                ensure_ascii=False,
            )
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
