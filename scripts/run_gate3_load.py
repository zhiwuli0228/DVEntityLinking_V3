"""Gate 3: high-concurrency + sustained load with per-DB-interaction breakdown.

Runs AC strategy at c50/c100 for 500k, short+ultra, both a 10s short matrix and
a 15-min sustained run. With DV_MOCK_TIMING=1 the mock records per-request
ac_match_ms / data_version_ms / fetch_ms; this script drains /timings per cell
and aggregates the breakdown. Requires MySQL.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import statistics
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

os.environ["DV_MOCK_TIMING"] = "1"

from run_mysql_entity_data_mock import _config  # noqa: E402
from run_no_llm_low_latency_collection import (  # noqa: E402
    NoLlmRuntime,
    run_load,
    summarize_samples,
)
from run_volume_matrix_benchmark import _make_case  # noqa: E402
from dv_entity_linking.performance_mock import (  # noqa: E402
    MySqlEntityDataMockSource,
    create_mock_app,
)
import waitress  # noqa: E402

VOLUME = "500k"
LENGTHS = ["short", "ultra"]
CONC = [50, 100]
POOL_SIZE = 110
WAITRESS_THREADS = 120
TIMEOUT_MS = 120_000
OUT = ROOT / "outputs" / "performance" / "gate3_load"


def _pct(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, __import__("math").ceil(p * len(ordered)) - 1)
    return round(ordered[rank], 3)


def _agg(timings, key):
    vals = [float(t[key]) for t in timings if key in t]
    if not vals:
        return {"n": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    return {
        "n": len(vals),
        "mean_ms": round(statistics.fmean(vals), 3),
        "p50_ms": _pct(vals, 0.50),
        "p95_ms": _pct(vals, 0.95),
        "max_ms": round(max(vals), 3),
    }


def _drain_timings(base_url):
    with urllib.request.urlopen(base_url + "/timings", timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8")).get("timings", [])


def _run_cell(runtime, base_url, length, concurrency, duration, warmups):
    case = _make_case(length, {"short": 25, "ultra": 600}[length])
    _drain_timings(base_url)
    samples, elapsed = run_load(
        runtime, layer="remote_match", cases=[case],
        concurrency=concurrency, duration_seconds=duration, warmups_per_worker=warmups,
    )
    summary = summarize_samples(samples, elapsed)
    timings = _drain_timings(base_url)
    breakdown = {
        "ac_match": _agg(timings, "ac_match_ms"),
        "data_version": _agg(timings, "data_version_ms"),
        "fetch": _agg(timings, "fetch_ms"),
    }
    sums = [float(t["ac_match_ms"]) + float(t["data_version_ms"]) + float(t["fetch_ms"]) for t in timings]
    breakdown["sum_per_request"] = {
        "n": len(sums),
        "mean_ms": round(statistics.fmean(sums), 3) if sums else 0.0,
        "p50_ms": _pct(sums, 0.50),
        "p95_ms": _pct(sums, 0.95),
    }
    return {
        "volume": VOLUME, "length": length, "concurrency": concurrency,
        "duration_seconds": duration, "requests": summary.get("requests", 0),
        "p50_ms": summary.get("p50_ms", 0.0), "p95_ms": summary.get("p95_ms", 0.0),
        "mean_ms": summary.get("mean_ms", 0.0), "max_ms": summary.get("max_ms", 0.0),
        "qps": summary.get("qps", 0.0), "transport_errors": summary.get("transport_errors", 0),
        "correctness_failures": summary.get("correctness_failures", 0),
        "passed": bool(summary.get("passed", False)),
        "breakdown": breakdown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sustained-seconds", type=int, default=900)
    parser.add_argument("--skip-sustained", action="store_true")
    parser.add_argument("--skip-short", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    db = f"dv_entity_data_mock_{VOLUME}"
    cfg = dataclasses.replace(_config(POOL_SIZE), database=db)
    source = MySqlEntityDataMockSource(cfg, match_strategy="ac")
    cells = []
    try:
        source.health()
        matcher = source.prepare_matcher()
        print(f"== Gate 3: AC c50/c100 load + breakdown (matcher patterns={matcher.pattern_count}) ==", flush=True)
        server = waitress.create_server(create_mock_app(source), host="127.0.0.1", port=0, threads=WAITRESS_THREADS)
        server_thread = threading.Thread(target=server.run, name="dv-gate3", daemon=True)
        server_thread.start()
        base_url = f"http://127.0.0.1:{server.effective_port}"
        runtime = NoLlmRuntime(base_url, timeout_ms=TIMEOUT_MS, top_k=3)
        print(f"mock on {base_url}, pool={POOL_SIZE}, threads={WAITRESS_THREADS}", flush=True)
        try:
            phases = []
            if not args.skip_short:
                phases.append(("short_matrix", 10, 3))
            if not args.skip_sustained:
                phases.append(("sustained", args.sustained_seconds, 3))
            for phase_name, duration, warmups in phases:
                for length in LENGTHS:
                    for conc in CONC:
                        label = f"[{phase_name}] {length} c{conc} {duration}s"
                        print(f"{label} ...", flush=True)
                        t0 = time.perf_counter()
                        cell = _run_cell(runtime, base_url, length, conc, duration, warmups)
                        cell["phase"] = phase_name
                        cell["elapsed_wall_seconds"] = round(time.perf_counter() - t0, 1)
                        cells.append(cell)
                        b = cell["breakdown"]
                        print(
                            f"  -> N={cell['requests']} p50={cell['p50_ms']:.1f} p95={cell['p95_ms']:.1f} qps={cell['qps']:.1f} "
                            f"| ac p50={b['ac_match']['p50_ms']:.3f} dv p50={b['data_version']['p50_ms']:.1f} "
                            f"fetch p50={b['fetch']['p50_ms']:.1f} | sum p50={b['sum_per_request']['p50_ms']:.1f} "
                            f"({'OK' if cell['passed'] else 'FAIL'})",
                            flush=True,
                        )
        finally:
            runtime.close()
            server.close()
            server_thread.join(timeout=5)
    finally:
        source.close()

    report = {
        "schema": "dv.gate3-load.1",
        "volume": VOLUME, "pool_size": POOL_SIZE, "waitress_threads": WAITRESS_THREADS,
        "timing_enabled": True, "sustained_seconds": args.sustained_seconds,
        "cells": cells,
    }
    path = OUT / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nreport -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
