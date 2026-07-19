"""Volume x query-length x concurrency x cold/warm matrix benchmark.

Read-only against the configured remote MySQL. Provisions four independent
databases (50k/100k/200k/500k entity words) by injecting custom presets into
the existing seeder, then drives the production-contract-compatible local HTTP
mock through the no-LLM runtime for every matrix cell.

Phases:
  --phase seed   provision the four databases (idempotent)
  --phase run    execute the full matrix (resumable; skips completed cells)
  --phase all    seed then run (default)
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for _p in (str(SCRIPTS), str(SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from run_mysql_entity_data_mock import _config  # noqa: E402
from run_no_llm_low_latency_collection import (  # noqa: E402
    NoLlmRuntime,
    TestCase,
    run_load,
    summarize_samples,
)
from dv_entity_linking.performance_mock import (  # noqa: E402
    DATA_PRESETS,
    DataPreset,
    MySqlEntityDataMockSource,
    MySqlMockDataSeeder,
    create_mock_app,
)

import waitress  # noqa: E402


VOLUMES = [
    ("50k", 50_000),
    ("100k", 100_000),
    ("200k", 200_000),
    ("500k", 500_000),
]
LENGTHS = [
    ("short", 25),
    ("medium", 100),
    ("long", 300),
    ("ultra", 600),
]
CONCURRENCIES = [1, 5, 10, 20]
TEMPS = ["cold", "warm"]
LAYERS = ["remote_match", "query_recall"]

DURATION = int(__import__("os").environ.get("DV_MATRIX_DURATION", "10"))
WARMUPS = int(__import__("os").environ.get("DV_MATRIX_WARMUPS", "3"))
TIMEOUT_MS = 120_000
POOL_SIZE = max(CONCURRENCIES) + 10

ENTITY_KEY = "cpuusage000001001"
ENTITY_ID = "DV-MOCK-000000334"


def _db_name(label: str) -> str:
    return f"dv_entity_data_mock_{label}"


def _build_query(target_len: int) -> tuple[str, str]:
    pad = max(0, target_len - len(ENTITY_KEY))
    before = pad // 2
    after = pad - before
    raw = ("x " * before + "CPU Usage 000001001" + " y" * after).strip()
    normalized = "x" * before + ENTITY_KEY + "y" * after
    return raw, normalized


def _make_case(len_label: str, target_len: int) -> TestCase:
    raw, norm = _build_query(target_len)
    return TestCase(
        name=f"len_{len_label}",
        raw_query=raw,
        normalized_query=norm,
        entity_types=(),
        layers=("remote_match", "query_recall"),
        weight=1,
        expected_remote_match_count=(1, 1),
        expected_recall_status="linked",
        expected_remote_entity_ids=(ENTITY_ID,),
        expected_recall_entity_ids=(ENTITY_ID,),
    )


def _output_dir() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "outputs" / "performance" / f"volume_matrix_{ts}"


def _provision() -> dict[str, Any]:
    report: dict[str, Any] = {}
    base = _config(1)
    for label, count in VOLUMES:
        preset_name = f"vol_{label}"
        if preset_name not in DATA_PRESETS:
            DATA_PRESETS[preset_name] = DataPreset(preset_name, count)
        db = _db_name(label)
        cfg = dataclasses.replace(base, database=db)
        seeder = MySqlMockDataSeeder(cfg)
        t0 = time.perf_counter()
        result = seeder.prepare(preset_name, batch_size=5_000)
        elapsed = round(time.perf_counter() - t0, 1)
        report[label] = {
            "database": db,
            "entity_word_count": result.entity_word_count,
            "entity_count": result.entity_count,
            "data_version": result.data_version,
            "reused": result.reused_existing_data,
            "elapsed_seconds": elapsed,
        }
        print(
            f"[seed] {label}: {result.entity_word_count} words "
            f"({'reused' if result.reused_existing_data else 'seeded'} in {elapsed}s)",
            file=sys.stderr,
            flush=True,
        )
    return report


def _verify() -> dict[str, Any]:
    report: dict[str, Any] = {}
    base = _config(1)
    for label, count in VOLUMES:
        db = _db_name(label)
        cfg = dataclasses.replace(base, database=db)
        source = MySqlEntityDataMockSource(cfg)
        try:
            stats = source.stats()
            ok = stats.entity_word_count == count
            report[label] = {
                "database": db,
                "expected": count,
                "actual": stats.entity_word_count,
                "entity_count": stats.entity_count,
                "data_version": stats.data_version,
                "ok": ok,
            }
            print(
                f"[verify] {label}: {stats.entity_word_count}/{count} "
                f"{'OK' if ok else 'MISMATCH'}",
                file=sys.stderr,
                flush=True,
            )
        finally:
            source.close()
    return report


def _flush_tables(cfg) -> None:
    import pymysql

    conn = pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        connect_timeout=cfg.connect_timeout_seconds,
        read_timeout=30,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("FLUSH TABLES el_entity_word, el_entity")
        conn.commit()
    finally:
        conn.close()


def _cell_id(vol: str, length: str, conc: int, temp: str, layer: str) -> str:
    return f"{vol}|{length}|{conc}|{temp}|{layer}"


def _load_existing(matrix_path: Path) -> dict[str, dict[str, Any]]:
    if not matrix_path.exists():
        return {}
    try:
        data = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {item["cell_id"]: item for item in data.get("cells", [])}


def _save_matrix(
    matrix_path: Path,
    cells: list[dict[str, Any]],
    meta: dict[str, Any],
) -> None:
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**meta, "cells": cells}
    matrix_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_volume(
    label: str,
    count: int,
    runtime: NoLlmRuntime,
    cfg,
    log,
    on_cell,
    existing_ids: set[str],
) -> None:
    total = len(LAYERS) * len(LENGTHS) * len(CONCURRENCIES) * len(TEMPS)
    idx = 0
    for layer in LAYERS:
        for len_label, len_target in LENGTHS:
            case = _make_case(len_label, len_target)
            for conc in CONCURRENCIES:
                for temp in TEMPS:
                    idx += 1
                    cid = _cell_id(label, len_label, conc, temp, layer)
                    if cid in existing_ids:
                        continue
                    warmups = 0 if temp == "cold" else WARMUPS
                    if temp == "cold":
                        _flush_tables(cfg)
                    t0 = time.perf_counter()
                    try:
                        samples, elapsed = run_load(
                            runtime,
                            layer=layer,
                            cases=[case],
                            concurrency=conc,
                            duration_seconds=DURATION,
                            warmups_per_worker=warmups,
                        )
                        summary = summarize_samples(samples, elapsed)
                        err = None
                    except Exception as exc:  # noqa: BLE001
                        summary = {
                            "requests": 0,
                            "p50_ms": 0.0,
                            "p95_ms": 0.0,
                            "p99_ms": 0.0,
                            "mean_ms": 0.0,
                            "max_ms": 0.0,
                            "qps": 0.0,
                            "transport_errors": 0,
                            "correctness_failures": 0,
                            "passed": False,
                            "elapsed_seconds": round(time.perf_counter() - t0, 3),
                            "status_counts": {},
                            "error_codes": {"collector_error": type(exc).__name__},
                        }
                        err = type(exc).__name__
                    cell = {
                        "cell_id": _cell_id(label, len_label, conc, temp, layer),
                        "volume": label,
                        "volume_rows": count,
                        "length": len_label,
                        "normalized_len": len_target,
                        "concurrency": conc,
                        "temp": temp,
                        "layer": layer,
                        "requests": summary.get("requests", 0),
                        "p50_ms": summary.get("p50_ms", 0.0),
                        "p95_ms": summary.get("p95_ms", 0.0),
                        "p99_ms": summary.get("p99_ms", 0.0),
                        "mean_ms": summary.get("mean_ms", 0.0),
                        "max_ms": summary.get("max_ms", 0.0),
                        "qps": summary.get("qps", 0.0),
                        "transport_errors": summary.get("transport_errors", 0),
                        "correctness_failures": summary.get("correctness_failures", 0),
                        "passed": bool(summary.get("passed", False)),
                        "elapsed_seconds": summary.get("elapsed_seconds", 0.0),
                        "status_counts": summary.get("status_counts", {}),
                        "error_codes": summary.get("error_codes", {}),
                        "collector_error": err,
                    }
                    line = (
                        f"[{label} {idx}/{total}] {layer} {len_label} "
                        f"c{conc} {temp} -> N={cell['requests']} "
                        f"p50={cell['p50_ms']:.1f} p95={cell['p95_ms']:.1f} "
                        f"max={cell['max_ms']:.1f} qps={cell['qps']:.2f} "
                        f"err={cell['transport_errors']}/{cell['correctness_failures']} "
                        f"{'OK' if cell['passed'] else 'FAIL'}"
                    )
                    print(line, file=sys.stderr, flush=True)
                    log.write(line + "\n")
                    log.flush()
                    on_cell(cell)


def _run_matrix(output_dir: Path, resume: bool, match_strategy: str = "instr") -> Path:
    cells_dir = output_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "matrix.json"
    log_path = output_dir / "run.log"
    log = log_path.open("a", encoding="utf-8")

    if resume and matrix_path.exists():
        previous = json.loads(matrix_path.read_text(encoding="utf-8"))
        previous_strategy = previous.get("match_strategy", "instr")
        if previous_strategy != match_strategy:
            log.close()
            raise ValueError(
                "output directory already contains a different match strategy"
            )
    existing = _load_existing(matrix_path) if resume else {}
    if existing:
        print(f"[resume] {len(existing)} cells already completed, skipping", file=sys.stderr, flush=True)

    meta = {
        "schema": "dv.volume-matrix-benchmark.1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds_per_cell": DURATION,
        "warmups_per_worker": WARMUPS,
        "timeout_ms": TIMEOUT_MS,
        "pool_size": POOL_SIZE,
        "match_strategy": match_strategy,
        "volumes": [v[0] for v in VOLUMES],
        "lengths": [l[0] for l in LENGTHS],
        "concurrencies": CONCURRENCIES,
        "temps": TEMPS,
        "layers": LAYERS,
        "cold_note": "FLUSH TABLES el_entity_word, el_entity; approximate (InnoDB buffer pool may retain pages)",
    }

    all_cells: list[dict[str, Any]] = list(existing.values())

    def on_cell(cell: dict[str, Any]) -> None:
        all_cells.append(cell)
        (cells_dir / f"cell_{cell['volume']}_{cell['length']}_c{cell['concurrency']}_{cell['temp']}_{cell['layer']}.json").write_text(
            json.dumps(cell, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _save_matrix(matrix_path, all_cells, meta)

    base_cfg = _config(POOL_SIZE)

    for label, count in VOLUMES:
        remaining = False
        for layer in LAYERS:
            for len_label, len_target in LENGTHS:
                for conc in CONCURRENCIES:
                    for temp in TEMPS:
                        cid = _cell_id(label, len_label, conc, temp, layer)
                        if cid not in existing:
                            remaining = True
                            break
                    if remaining:
                        break
                if remaining:
                    break
            if remaining:
                break
        if not remaining:
            print(f"[run] {label}: all cells already done, skipping", file=sys.stderr, flush=True)
            continue

        db = _db_name(label)
        cfg = dataclasses.replace(base_cfg, database=db)
        source = MySqlEntityDataMockSource(cfg, match_strategy=match_strategy)
        try:
            source.health()
            matcher = source.prepare_matcher()
            server = waitress.create_server(
                create_mock_app(source), host="127.0.0.1", port=0
            )
            server_thread = threading.Thread(
                target=server.run, name=f"dv-matrix-{label}", daemon=True
            )
            server_thread.start()
            runtime = NoLlmRuntime(
                f"http://127.0.0.1:{server.effective_port}",
                timeout_ms=TIMEOUT_MS,
                top_k=3,
            )
            print(
                f"[run] {label}: mock on 127.0.0.1:{server.effective_port}, "
                f"strategy={match_strategy}, "
                f"matcher={dataclasses.asdict(matcher) if matcher else None}, "
                f"collecting {len(LAYERS)*len(LENGTHS)*len(CONCURRENCIES)*len(TEMPS)} cells...",
                file=sys.stderr,
                flush=True,
            )
            try:
                _run_volume(label, count, runtime, cfg, log, on_cell, set(existing.keys()))
            finally:
                runtime.close()
                server.close()
                server_thread.join(timeout=5)
        finally:
            source.close()

        print(f"[run] {label}: done -> {matrix_path}", file=sys.stderr, flush=True)

    meta["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    _save_matrix(matrix_path, all_cells, meta)
    log.close()
    return matrix_path


def _write_csv(matrix_path: Path) -> Path:
    data = json.loads(matrix_path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    csv_path = matrix_path.parent / "matrix.csv"
    fields = [
        "volume", "volume_rows", "length", "normalized_len", "concurrency",
        "temp", "layer", "requests", "p50_ms", "p95_ms", "p99_ms", "mean_ms",
        "max_ms", "qps", "transport_errors", "correctness_failures", "passed",
        "elapsed_seconds",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for cell in cells:
            writer.writerow({k: cell.get(k, "") for k in fields})
    return csv_path


def _pivot(cells, value_key, row_filter, col_key, row_key, col_order, row_order):
    grid: dict[str, dict[str, str]] = {}
    for cell in cells:
        if not all(str(cell.get(k)) == str(v) for k, v in row_filter.items()):
            continue
        row = str(cell.get(row_key))
        col = str(cell.get(col_key))
        if row not in grid:
            grid[row] = {}
        val = cell.get(value_key)
        grid[row][col] = f"{val:.1f}" if isinstance(val, (int, float)) else str(val)
    header = [row_key] + [str(c) for c in col_order]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in row_order:
        rs = str(r)
        row = [rs]
        for c in col_order:
            row.append(grid.get(rs, {}).get(str(c), "-"))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _write_report(matrix_path: Path, verify_report: dict | None) -> Path:
    data = json.loads(matrix_path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    report_path = matrix_path.parent / "report.md"

    def find(vol=None, length=None, conc=None, temp=None, layer=None):
        for c in cells:
            if vol and c["volume"] != vol:
                continue
            if length and c["length"] != length:
                continue
            if conc is not None and c["concurrency"] != conc:
                continue
            if temp and c["temp"] != temp:
                continue
            if layer and c["layer"] != layer:
                continue
            return c
        return None

    lines: list[str] = []
    lines.append("# Volume x Length x Concurrency x Cold/Warm Matrix Benchmark\n")
    lines.append(f"- started: {data.get('started_at_utc')}")
    lines.append(f"- finished: {data.get('finished_at_utc')}")
    lines.append(f"- duration/cell: {data.get('duration_seconds_per_cell')}s, warmups: {data.get('warmups_per_worker')}")
    lines.append(f"- cold note: {data.get('cold_note')}")
    lines.append(f"- total cells: {len(cells)}")
    if verify_report:
        lines.append("\n## Data volumes\n")
        lines.append("| volume | entity_words | entities | data_version |")
        lines.append("|---|---|---|---|")
        for label, _ in VOLUMES:
            v = verify_report.get(label, {})
            lines.append(
                f"| {label} | {v.get('actual')} | {v.get('entity_count')} | "
                f"{v.get('data_version')} |"
            )

    lines.append("\n## 1. Volume scaling (remote_match, warm, c=1, p50 ms)\n")
    lines.append(_pivot(
        cells, "p50_ms",
        {"concurrency": 1, "temp": "warm", "layer": "remote_match"},
        "length", "volume",
        [l[0] for l in LENGTHS], [v[0] for v in VOLUMES],
    ))

    lines.append("\n## 2. Concurrency scaling (remote_match, warm, 500k, p50 ms)\n")
    lines.append(_pivot(
        cells, "p50_ms",
        {"volume": "500k", "temp": "warm", "layer": "remote_match"},
        "length", "concurrency",
        [l[0] for l in LENGTHS], [str(c) for c in CONCURRENCIES],
    ))

    lines.append("\n## 3. Concurrency scaling (remote_match, warm, 500k, QPS)\n")
    lines.append(_pivot(
        cells, "qps",
        {"volume": "500k", "temp": "warm", "layer": "remote_match"},
        "length", "concurrency",
        [l[0] for l in LENGTHS], [str(c) for c in CONCURRENCIES],
    ))

    lines.append("\n## 4. Length sensitivity (remote_match, warm, c=1, p50/p95/max ms)\n")
    length_rows = []
    for len_label, len_target in LENGTHS:
        c = find(length=len_label, conc=1, temp="warm", layer="remote_match")
        if c:
            length_rows.append(f"| {len_label} ({len_target}) | {c['p50_ms']:.1f} | {c['p95_ms']:.1f} | {c['max_ms']:.1f} |")
    lines.append("| length (chars) | p50 | p95 | max |")
    lines.append("|---|---|---|---|")
    lines.extend(length_rows)

    lines.append("\n## 5. Cold vs warm (remote_match, c=1, medium, p50 ms)\n")
    lines.append("| volume | cold p50 | warm p50 | cold max | warm max | ratio (warm/cold) |")
    lines.append("|---|---|---|---|---|---|")
    for label, _ in VOLUMES:
        cold = find(vol=label, length="medium", conc=1, temp="cold", layer="remote_match")
        warm = find(vol=label, length="medium", conc=1, temp="warm", layer="remote_match")
        if cold and warm and warm["p50_ms"] > 0:
            ratio = warm["p50_ms"] / cold["p50_ms"] if cold["p50_ms"] > 0 else 0
            lines.append(
                f"| {label} | {cold['p50_ms']:.1f} | {warm['p50_ms']:.1f} | "
                f"{cold['max_ms']:.1f} | {warm['max_ms']:.1f} | {ratio:.2f} |"
            )

    lines.append("\n## 6. remote_match vs query_recall (warm, c=1, medium, p50 ms)\n")
    lines.append("| volume | remote_match p50 | query_recall p50 | ratio (qr/rm) |")
    lines.append("|---|---|---|---|")
    for label, _ in VOLUMES:
        rm = find(vol=label, length="medium", conc=1, temp="warm", layer="remote_match")
        qr = find(vol=label, length="medium", conc=1, temp="warm", layer="query_recall")
        if rm and qr and rm["p50_ms"] > 0:
            ratio = qr["p50_ms"] / rm["p50_ms"]
            lines.append(
                f"| {label} | {rm['p50_ms']:.1f} | {qr['p50_ms']:.1f} | {ratio:.2f} |"
            )

    failed = [c for c in cells if not c.get("passed")]
    lines.append(f"\n## Failures: {len(failed)}/{len(cells)}\n")
    if failed:
        lines.append("| volume | length | conc | temp | layer | N | transport_err | correctness_fail | error_codes |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for c in failed:
            lines.append(
                f"| {c['volume']} | {c['length']} | {c['concurrency']} | {c['temp']} | "
                f"{c['layer']} | {c['requests']} | {c['transport_errors']} | "
                f"{c['correctness_failures']} | {c.get('error_codes')} |"
            )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["seed", "run", "all"], default="all")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument(
        "--match-strategy", choices=("instr", "ac"), default="instr"
    )
    args = parser.parse_args()

    output_dir = args.output_dir or _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[matrix] output_dir = {output_dir}", file=sys.stderr, flush=True)

    verify_report: dict | None = None
    if args.phase in ("seed", "all"):
        report = _provision()
        (output_dir / "provisioning.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if args.phase in ("run", "all"):
        verify_report = _verify()
        (output_dir / "verification.json").write_text(
            json.dumps(verify_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        bad = [k for k, v in verify_report.items() if not v.get("ok")]
        if bad:
            print(f"[matrix] volume mismatch for {bad}, aborting run", file=sys.stderr, flush=True)
            return 1
        matrix_path = _run_matrix(
            output_dir,
            resume=not args.no_resume,
            match_strategy=args.match_strategy,
        )
        csv_path = _write_csv(matrix_path)
        report_path = _write_report(matrix_path, verify_report)
        print(
            json.dumps(
                {
                    "status": "completed",
                    "matrix": str(matrix_path),
                    "csv": str(csv_path),
                    "report": str(report_path),
                    "cells": len(json.loads(matrix_path.read_text(encoding="utf-8")).get("cells", [])),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
