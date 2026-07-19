"""Provision and serve the standalone MySQL-backed Entity Data performance mock."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dv_entity_linking.performance_mock import (  # noqa: E402
    DATA_PRESETS,
    MockMySqlConfig,
    MySqlEntityDataMockSource,
    MySqlMockDataSeeder,
    create_mock_app,
)

try:
    from mysql_entity_data_mock_local import MYSQL_MOCK_CONFIG
except ImportError:
    MYSQL_MOCK_CONFIG: dict[str, object] = {}


def _setting(name: str, environment_name: str, default: object) -> object:
    if name in MYSQL_MOCK_CONFIG:
        return MYSQL_MOCK_CONFIG[name]
    return os.environ.get(environment_name, default)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _config(pool_size: int) -> MockMySqlConfig:
    return MockMySqlConfig(
        host=str(_setting("host", "DV_MOCK_MYSQL_HOST", "127.0.0.1")),
        port=int(_setting("port", "DV_MOCK_MYSQL_PORT", 3306)),
        user=str(_setting("user", "DV_MOCK_MYSQL_USER", "root")),
        password=str(_setting("password", "DV_MOCK_MYSQL_PASSWORD", "")),
        database=str(
            _setting(
                "database",
                "DV_MOCK_MYSQL_DATABASE",
                "dv_entity_data_mock",
            )
        ),
        pool_size=pool_size,
        pool_wait_seconds=float(
            _setting("pool_wait_seconds", "DV_MOCK_POOL_WAIT_SECONDS", 5)
        ),
        connect_timeout_seconds=int(
            _setting(
                "connect_timeout_seconds",
                "DV_MOCK_CONNECT_TIMEOUT_SECONDS",
                5,
            )
        ),
        read_timeout_seconds=int(
            _setting("read_timeout_seconds", "DV_MOCK_READ_TIMEOUT_SECONDS", 30)
        ),
        write_timeout_seconds=int(
            _setting("write_timeout_seconds", "DV_MOCK_WRITE_TIMEOUT_SECONDS", 30)
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("presets", help="print deterministic data presets")

    prepare = subparsers.add_parser("prepare", help="create and seed mock tables")
    prepare.add_argument("--preset", choices=tuple(DATA_PRESETS), default="large")
    prepare.add_argument("--batch-size", type=_positive_int, default=5_000)
    prepare.add_argument("--max-attempts", type=_positive_int, default=20)

    status = subparsers.add_parser("status", help="show safe mock data counts")
    status.add_argument("--pool-size", type=_positive_int, default=1)
    status.add_argument("--match-strategy", choices=("instr", "ac"), default="instr")

    serve = subparsers.add_parser("serve", help="start the remote-interface mock")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=_positive_int, default=8089)
    serve.add_argument("--threads", type=_positive_int, default=32)
    serve.add_argument("--pool-size", type=_positive_int, default=32)
    serve.add_argument("--match-strategy", choices=("instr", "ac"), default="instr")
    return parser


def _print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    args = _parser().parse_args()
    if args.command == "presets":
        _print(
            {
                name: {
                    "entity_count": preset.entity_count,
                    "entity_word_count": preset.entity_word_count,
                    "words_per_entity": preset.words_per_entity,
                }
                for name, preset in DATA_PRESETS.items()
            }
        )
        return 0

    try:
        if args.command == "prepare":
            for attempt in range(1, args.max_attempts + 1):
                try:
                    report = MySqlMockDataSeeder(_config(1)).prepare(
                        args.preset,
                        batch_size=args.batch_size,
                    )
                    break
                except Exception as exc:
                    retryable = type(exc).__name__ in {
                        "InterfaceError",
                        "OperationalError",
                    }
                    if not retryable or attempt == args.max_attempts:
                        raise
                    _print(
                        {
                            "status": "retrying",
                            "attempt": attempt,
                            "error_type": type(exc).__name__,
                        }
                    )
                    time.sleep(1)
            _print({"status": "ready", **asdict(report)})
            return 0

        if args.command == "status":
            source = MySqlEntityDataMockSource(
                _config(args.pool_size), match_strategy=args.match_strategy
            )
            try:
                source.prepare_matcher()
                _print({"status": "ready", **asdict(source.stats())})
            finally:
                source.close()
            return 0

        if args.command == "serve":
            try:
                from waitress import serve
            except ImportError as exc:
                raise RuntimeError(
                    "waitress is required; install dv-entity-linking[performance-mock]"
                ) from exc
            source = MySqlEntityDataMockSource(
                _config(args.pool_size), match_strategy=args.match_strategy
            )
            try:
                source.health()
                matcher = source.prepare_matcher()
                _print(
                    {
                        "status": "serving",
                        "url": f"http://{args.host}:{args.port}/v1/entity-data:execute",
                        "threads": args.threads,
                        "pool_size": args.pool_size,
                        "match_strategy": args.match_strategy,
                        "matcher": asdict(matcher) if matcher else None,
                    }
                )
                serve(
                    create_mock_app(source),
                    host=args.host,
                    port=args.port,
                    threads=args.threads,
                )
            finally:
                source.close()
            return 0
    except (RuntimeError, ValueError) as exc:
        _print({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
        return 1
    except Exception as exc:
        _print({"status": "failed", "error_type": type(exc).__name__})
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
