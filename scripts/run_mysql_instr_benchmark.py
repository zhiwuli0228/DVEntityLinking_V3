"""Run a bounded MySQL benchmark for the MATCH_WORDS INSTR query shape.

The benchmark creates one uniquely named ``dv_el_perf_*`` database, writes only
synthetic data to it, and removes the database in a ``finally`` block. Connection
credentials are accepted through environment variables and are never printed.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import statistics
import sys
import threading
import time
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


SCHEMA_PREFIX = "dv_el_perf_"
SAFE_SCHEMA = re.compile(r"^dv_el_perf_[0-9]{14}_[0-9a-f]{8}$")
SELECT_COLUMNS = """entity_word_id, entity_id, entity_type, entity_word,
       normalized_key, source, match_mode, min_context_required,
       context_keywords_json, priority"""


@dataclass(frozen=True)
class QueryCase:
    name: str
    normalized_query: str
    entity_type: str | None = None


def _parse_positive_csv(raw: str, *, option: str) -> tuple[int, ...]:
    try:
        values = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} must contain integers") from exc
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError(f"{option} must contain positive integers")
    return values


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[rank], 3)


def _entity_type(index: int) -> str:
    bucket = index % 20
    if bucket < 16:
        return "metric"
    return ("alarm", "application", "device", "service")[bucket - 16]


def _normalized_key(index: int) -> str:
    variant = index % 4
    if variant == 0:
        return f"kpi{index:09d}"
    if variant == 1:
        return f"cpuusage{index:09d}"
    if variant == 2:
        return f"alm51020node{index:09d}"
    return f"distributedservicemetric{index:09d}"


def _find_query_index(maximum: int, *, entity_type: str | None = None) -> int:
    start = max(1, maximum // 2)
    for index in range(start, maximum + 1):
        if entity_type is None or _entity_type(index) == entity_type:
            return index
    raise RuntimeError("unable to select a synthetic entity word")


def _query_cases(size: int) -> tuple[QueryCase, ...]:
    first = _find_query_index(size)
    second = _find_query_index(max(1, size // 3))
    device = _find_query_index(size, entity_type="device")
    first_key = _normalized_key(first)
    second_key = _normalized_key(second)
    device_key = _normalized_key(device)
    return (
        QueryCase("no_match", "nomatchingentityword" + "x" * 64),
        QueryCase("single_hit", f"prefix{first_key}suffix"),
        QueryCase("multi_hit", f"prefix{first_key}middle{second_key}suffix"),
        QueryCase("repeated_hit", f"{first_key}and{first_key}and{first_key}"),
        QueryCase("long_query", "x" * 512 + first_key + "y" * 512),
        QueryCase("type_filtered", f"prefix{device_key}suffix", "device"),
    )


def _rows(start: int, stop: int) -> Iterable[tuple[Any, ...]]:
    for index in range(start, stop):
        key = _normalized_key(index)
        yield (
            index,
            f"DV-{index:09d}",
            _entity_type(index),
            key,
            key,
            "entity_name" if index % 3 == 0 else "alias",
            "exact",
            0 if index % 5 else 1,
            "[]" if index % 5 else '["system", "node"]',
            100 - (index % 100),
        )


def _connect(pymysql: Any, config: dict[str, Any], *, database: str | None = None) -> Any:
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=config["connect_timeout"],
        read_timeout=config["read_timeout"],
        write_timeout=config["write_timeout"],
    )


def _create_schema(connection: Any, schema: str) -> None:
    if not SAFE_SCHEMA.fullmatch(schema):
        raise RuntimeError("refusing to create an unsafe benchmark schema name")
    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_0900_ai_ci"
        )
        cursor.execute(
            f"""
            CREATE TABLE `{schema}`.`el_entity_word` (
                entity_word_id BIGINT NOT NULL,
                entity_id VARCHAR(64) NOT NULL,
                entity_type VARCHAR(32) NOT NULL,
                entity_word VARCHAR(255) NOT NULL,
                normalized_key VARCHAR(255) NOT NULL,
                source VARCHAR(32) NOT NULL,
                match_mode VARCHAR(32) NOT NULL,
                min_context_required TINYINT NOT NULL,
                context_keywords_json JSON NOT NULL,
                priority INT NOT NULL,
                PRIMARY KEY (entity_word_id),
                KEY idx_entity_type (entity_type),
                KEY idx_entity_id (entity_id)
            ) ENGINE=InnoDB
            """
        )


def _drop_schema(connection: Any, schema: str) -> None:
    if not SAFE_SCHEMA.fullmatch(schema):
        raise RuntimeError("refusing to drop an unsafe benchmark schema name")
    with connection.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS `{schema}`")


def _load_rows(connection: Any, schema: str, start: int, stop: int, batch_size: int) -> float:
    connection.ping(reconnect=True)
    statement = f"""
        INSERT INTO `{schema}`.`el_entity_word` (
            entity_word_id, entity_id, entity_type, entity_word, normalized_key,
            source, match_mode, min_context_required, context_keywords_json,
            priority
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    started = time.perf_counter()
    with connection.cursor() as cursor:
        pending: list[tuple[Any, ...]] = []
        for row in _rows(start, stop):
            pending.append(row)
            if len(pending) == batch_size:
                cursor.executemany(statement, pending)
                pending.clear()
        if pending:
            cursor.executemany(statement, pending)
        cursor.execute(f"ANALYZE TABLE `{schema}`.`el_entity_word`")
        cursor.fetchall()
    return round(time.perf_counter() - started, 3)


def _execute_case(connection: Any, schema: str, case: QueryCase) -> tuple[float, int]:
    statement = f"""
        SELECT {SELECT_COLUMNS}
        FROM `{schema}`.`el_entity_word`
        WHERE INSTR(%s, normalized_key) > 0
    """
    params: tuple[Any, ...] = (case.normalized_query,)
    if case.entity_type is not None:
        statement += " AND entity_type = %s"
        params += (case.entity_type,)
    started = time.perf_counter()
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        rows = cursor.fetchall()
    return (time.perf_counter() - started) * 1000.0, len(rows)


def _worker(
    connection: Any,
    schema: str,
    cases: Sequence[QueryCase],
    iterations: int,
    offset: int,
) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        for iteration in range(iterations):
            case = cases[(offset + iteration) % len(cases)]
            try:
                latency_ms, row_count = _execute_case(connection, schema, case)
                samples.append(
                    {"case": case.name, "latency_ms": round(latency_ms, 3), "rows": row_count}
                )
            except Exception as exc:  # pragma: no cover - integration failure evidence
                error_code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else "unknown"
                errors.append(f"{type(exc).__name__}:{error_code}")
    finally:
        connection.close()
    return {"samples": samples, "errors": errors}


def _benchmark_concurrency(
    pymysql: Any,
    config: dict[str, Any],
    schema: str,
    cases: Sequence[QueryCase],
    concurrency: int,
    target_requests: int,
    warmups_per_connection: int,
) -> dict[str, Any]:
    connection_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        connections = list(
            executor.map(
                lambda _: _connect(pymysql, config, database=schema),
                range(concurrency),
            )
        )
    connection_setup_seconds = time.perf_counter() - connection_started

    for index, connection in enumerate(connections):
        for warmup in range(warmups_per_connection):
            _execute_case(connection, schema, cases[(index + warmup) % len(cases)])

    iterations = max(1, math.ceil(target_requests / concurrency))
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_worker, connection, schema, cases, iterations, index)
            for index, connection in enumerate(connections)
        ]
        worker_results = [future.result() for future in futures]
    elapsed = time.perf_counter() - started

    samples = [sample for result in worker_results for sample in result["samples"]]
    errors = [error for result in worker_results for error in result["errors"]]
    latencies = [sample["latency_ms"] for sample in samples]
    by_case: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_samples = [sample for sample in samples if sample["case"] == case.name]
        case_latencies = [sample["latency_ms"] for sample in case_samples]
        by_case[case.name] = {
            "requests": len(case_samples),
            "p50_ms": _percentile(case_latencies, 0.50),
            "p95_ms": _percentile(case_latencies, 0.95),
            "p99_ms": _percentile(case_latencies, 0.99),
            "max_rows": max((sample["rows"] for sample in case_samples), default=0),
        }
    return {
        "concurrency": concurrency,
        "requests": len(samples),
        "errors": len(errors),
        "error_types": sorted(set(errors)),
        "elapsed_seconds": round(elapsed, 3),
        "connection_setup_seconds": round(connection_setup_seconds, 3),
        "qps": round(len(samples) / elapsed, 3) if elapsed else 0.0,
        "p50_ms": _percentile(latencies, 0.50),
        "p95_ms": _percentile(latencies, 0.95),
        "p99_ms": _percentile(latencies, 0.99),
        "mean_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "cases": by_case,
    }


def _explain(connection: Any, schema: str, case: QueryCase) -> dict[str, Any]:
    connection.ping(reconnect=True)
    statement = f"""
        SELECT {SELECT_COLUMNS}
        FROM `{schema}`.`el_entity_word`
        WHERE INSTR(%s, normalized_key) > 0
    """
    params: tuple[Any, ...] = (case.normalized_query,)
    if case.entity_type is not None:
        statement += " AND entity_type = %s"
        params += (case.entity_type,)
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN FORMAT=JSON " + statement, params)
        explain_json = json.loads(cursor.fetchone()[0])
        cursor.execute("EXPLAIN ANALYZE " + statement, params)
        analyze_lines = [str(row[0]) for row in cursor.fetchall()]
    table = explain_json["query_block"]["table"]
    return {
        "case": case.name,
        "access_type": table.get("access_type"),
        "possible_keys": table.get("possible_keys", []),
        "key": table.get("key"),
        "rows_examined_per_scan": table.get("rows_examined_per_scan"),
        "rows_produced_per_join": table.get("rows_produced_per_join"),
        "filtered_percent": table.get("filtered"),
        "analyze": analyze_lines,
    }


def _server_metadata(connection: Any) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT VERSION(), @@character_set_server, @@collation_server, "
            "@@max_connections, @@innodb_buffer_pool_size, @@wait_timeout, "
            "@@net_read_timeout, @@net_write_timeout, @@max_execution_time"
        )
        (
            version,
            charset,
            collation,
            max_connections,
            buffer_pool,
            wait_timeout,
            net_read_timeout,
            net_write_timeout,
            max_execution_time,
        ) = cursor.fetchone()
    return {
        "version": version,
        "character_set_server": charset,
        "collation_server": collation,
        "max_connections": int(max_connections),
        "innodb_buffer_pool_bytes": int(buffer_pool),
        "wait_timeout_seconds": int(wait_timeout),
        "net_read_timeout_seconds": int(net_read_timeout),
        "net_write_timeout_seconds": int(net_write_timeout),
        "max_execution_time_ms": int(max_execution_time),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="10000,50000,100000")
    parser.add_argument("--concurrencies", default="1,10,25")
    parser.add_argument("--target-requests", type=int, default=60)
    parser.add_argument("--warmups-per-connection", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--connect-timeout", type=int, default=15)
    parser.add_argument("--read-timeout", type=int, default=60)
    parser.add_argument("--write-timeout", type=int, default=60)
    args = parser.parse_args()
    args.sizes = _parse_positive_csv(args.sizes, option="--sizes")
    args.concurrencies = _parse_positive_csv(args.concurrencies, option="--concurrencies")
    if tuple(sorted(args.sizes)) != args.sizes or len(set(args.sizes)) != len(args.sizes):
        parser.error("--sizes must be unique and ascending")
    if args.target_requests <= 0 or args.warmups_per_connection < 0 or args.batch_size <= 0:
        parser.error("request, warmup, and batch values are invalid")
    return args


def main() -> int:
    args = _parse_args()
    try:
        import pymysql
    except ImportError:
        print("PyMySQL is required: python -m pip install PyMySQL", file=sys.stderr)
        return 2

    required = ("DV_MYSQL_HOST", "DV_MYSQL_USER", "DV_MYSQL_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing), file=sys.stderr)
        return 2
    config = {
        "host": os.environ["DV_MYSQL_HOST"],
        "port": int(os.environ.get("DV_MYSQL_PORT", "3306")),
        "user": os.environ["DV_MYSQL_USER"],
        "password": os.environ["DV_MYSQL_PASSWORD"],
        "connect_timeout": args.connect_timeout,
        "read_timeout": args.read_timeout,
        "write_timeout": args.write_timeout,
    }
    schema = SCHEMA_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:8]
    result: dict[str, Any] = {
        "benchmark_kind": "bounded_preliminary_mysql_instr",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema": schema,
        "schema_cleanup": "pending",
        "data_generation": {
            "sizes": list(args.sizes),
            "entity_type_distribution": {"metric": 0.8, "alarm": 0.05, "application": 0.05, "device": 0.05, "service": 0.05},
            "source_distribution": {"entity_name": 1 / 3, "alias": 2 / 3},
            "key_variants": ["short_code", "business_name", "structured_alarm", "long_service_metric"],
        },
        "runs": [],
        "execution_plans": [],
    }
    admin = None
    schema_created = False
    exit_code = 0
    try:
        admin = _connect(pymysql, config)
        result["server"] = _server_metadata(admin)
        _create_schema(admin, schema)
        schema_created = True
        current_size = 0
        for size in args.sizes:
            admin.ping(reconnect=True)
            load_seconds = _load_rows(admin, schema, current_size + 1, size + 1, args.batch_size)
            current_size = size
            cases = _query_cases(size)
            scale_result: dict[str, Any] = {
                "total_entity_words": size,
                "incremental_load_seconds": load_seconds,
                "concurrency_results": [],
            }
            for concurrency in args.concurrencies:
                scale_result["concurrency_results"].append(
                    _benchmark_concurrency(
                        pymysql,
                        config,
                        schema,
                        cases,
                        concurrency,
                        args.target_requests,
                        args.warmups_per_connection,
                    )
                )
            result["runs"].append(scale_result)
        final_cases = _query_cases(args.sizes[-1])
        result["execution_plans"] = [
            _explain(admin, schema, next(case for case in final_cases if case.name == "no_match")),
            _explain(admin, schema, next(case for case in final_cases if case.name == "type_filtered")),
        ]
    except Exception as exc:  # pragma: no cover - integration failure evidence
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
        exit_code = 1
    finally:
        if admin is not None:
            if schema_created:
                try:
                    admin.ping(reconnect=True)
                    _drop_schema(admin, schema)
                    result["schema_cleanup"] = "dropped"
                except Exception as cleanup_exc:  # pragma: no cover
                    result["cleanup_reconnect_reason"] = type(cleanup_exc).__name__
                    try:
                        admin.close()
                        admin = _connect(pymysql, config)
                        _drop_schema(admin, schema)
                        result["schema_cleanup"] = "dropped_after_reconnect"
                    except Exception as reconnect_exc:  # pragma: no cover
                        result["schema_cleanup"] = "failed"
                        result["cleanup_failure_type"] = type(reconnect_exc).__name__
                        exit_code = 1
            admin.close()
        result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
