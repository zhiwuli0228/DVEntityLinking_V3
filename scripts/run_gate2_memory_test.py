"""Gate 2: AC index memory test — RSS, rebuild peak, multi-process.

Builds the Aho-Corasick index from locally-generated 500k patterns (same
seeder _word logic, no MySQL needed since index memory is pattern-driven).
Measures single-process RSS + build peak, then 1/2/4 process RSS to verify
linear scaling (AC index is per-process, not shared).
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import psutil
from dv_entity_linking.performance_mock.seeder import _word
from dv_entity_linking.performance_mock.ac_matcher import AhoCorasickSnapshot

N_PATTERNS = 500_000
OUT = ROOT / "outputs" / "performance" / "gate2_memory"


def _patterns(n: int):
    for i in range(1, n + 1):
        yield i, _word(i)[1]


def _build_index():
    return AhoCorasickSnapshot.build("gate2-mem", _patterns(N_PATTERNS))


def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1048576


def single_process() -> dict:
    proc = psutil.Process()
    baseline = proc.memory_info().rss
    peak = {"v": baseline}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            v = proc.memory_info().rss
            if v > peak["v"]:
                peak["v"] = v
            time.sleep(0.001)

    t = threading.Thread(target=sampler, daemon=True)
    t.start()
    t0 = time.perf_counter()
    snap = _build_index()
    build_s = time.perf_counter() - t0
    stop.set()
    t.join(timeout=2)
    steady = proc.memory_info().rss
    return {
        "baseline_rss_mb": round(baseline / 1048576, 2),
        "steady_rss_mb": round(steady / 1048576, 2),
        "peak_rss_mb": round(peak["v"] / 1048576, 2),
        "index_rss_delta_mb": round((steady - baseline) / 1048576, 2),
        "index_size_bytes": snap.stats.size_bytes,
        "index_size_mb": round((snap.stats.size_bytes or 0) / 1048576, 2),
        "pattern_count": snap.stats.pattern_count,
        "build_seconds": round(build_s, 3),
    }


def _child(queue, event):
    try:
        snap = _build_index()
        rss = psutil.Process().memory_info().rss
        queue.put({
            "pid": mp.current_process().pid,
            "steady_rss_mb": round(rss / 1048576, 2),
            "index_size_mb": round((snap.stats.size_bytes or 0) / 1048576, 2),
            "build_seconds": round(snap.stats.build_seconds, 3),
        })
        event.wait(timeout=120)
    except Exception as exc:
        queue.put({"pid": mp.current_process().pid, "error": type(exc).__name__})


def multi_process(n: int) -> dict:
    queue: mp.Queue = mp.Queue()
    event = mp.Event()
    procs = [mp.Process(target=_child, args=(queue, event), daemon=True) for _ in range(n)]
    for p in procs:
        p.start()
    results = []
    for _ in range(n):
        results.append(queue.get(timeout=120))
    time.sleep(0.5)
    total = sum(r.get("steady_rss_mb", 0) for r in results)
    event.set()
    for p in procs:
        p.join(timeout=10)
    return {
        "n_processes": n,
        "per_process": results,
        "total_rss_mb": round(total, 2),
        "avg_per_process_mb": round(total / n, 2) if n else 0,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("== Gate 2: AC index memory test ==", flush=True)
    print(f"patterns: {N_PATTERNS}", flush=True)

    print("\n[1/2] single-process build...", flush=True)
    single = single_process()
    print(json.dumps(single, ensure_ascii=False, indent=2), flush=True)

    print("\n[2/2] multi-process (1/2/4)...", flush=True)
    multi = {}
    for n in (1, 2, 4):
        print(f"  spawning {n} process(es)...", flush=True)
        multi[f"n{n}"] = multi_process(n)
        m = multi[f"n{n}"]
        print(f"  n={n}: total_rss={m['total_rss_mb']}MB avg={m['avg_per_process_mb']}MB", flush=True)

    single_child_rss = multi["n1"]["avg_per_process_mb"]
    print("\n== linearity check ==", flush=True)
    print(f"single-process steady RSS: {single['steady_rss_mb']}MB (index delta {single['index_rss_delta_mb']}MB)", flush=True)
    for n in (1, 2, 4):
        m = multi[f"n{n}"]
        expected = single_child_rss * n
        ratio = m["total_rss_mb"] / expected if expected else 0
        print(f"  n={n}: total={m['total_rss_mb']}MB, expected~{expected:.1f}MB, ratio={ratio:.2f}", flush=True)

    report = {
        "schema": "dv.gate2-memory.1",
        "patterns": N_PATTERNS,
        "single_process": single,
        "multi_process": multi,
        "note": "index built from locally-generated seeder patterns; index memory is pattern-driven and independent of MySQL. Multi-process simulates N independent workers (AC index is per-process, not shared).",
    }
    path = OUT / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nreport -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
