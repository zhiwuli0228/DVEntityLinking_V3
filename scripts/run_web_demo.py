from __future__ import annotations

import argparse

from demo_runtime import build_service, ensure_src_path, resolve_path, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the DVEntityLinking Web demo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5015)
    parser.add_argument("--mode", choices=["offline_demo", "llm_enabled_demo"], default="offline_demo")
    parser.add_argument(
        "--catalog",
        default="samples/real/v2_entity_examples.json",
        help="Catalog JSON path for the current Web demo version.",
    )
    parser.add_argument(
        "--samples",
        default="samples/real/v2_query_samples.json",
        help="Query samples JSON path for the current Web demo version.",
    )
    parser.add_argument(
        "--storage-mode",
        choices=["legacy_catalog", "v3_mock"],
        default="legacy_catalog",
        help="Use the legacy catalog chain or the V3 Redis/Gauss mock storage chain.",
    )
    parser.add_argument(
        "--gauss-mock",
        default="samples/real/v3_gauss_entities.json",
        help="V3 Gauss mock artifact path when --storage-mode=v3_mock.",
    )
    parser.add_argument(
        "--redis-mock",
        default="samples/real/v3_redis_entity_words.json",
        help="V3 Redis mock artifact path when --storage-mode=v3_mock.",
    )
    parser.add_argument("--llm-config", default="config/llm.local.json")
    parser.add_argument("--log-dir", default="outputs/logs")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger, log_file = setup_logging(args.log_dir, "web-demo")
    ensure_src_path()
    from dv_entity_linking.legacy.web import create_app

    service, run_mode = build_service(
        catalog_path=args.catalog,
        mode=args.mode,
        llm_config_path=args.llm_config,
        logger=logger,
        storage_mode=args.storage_mode,
        gauss_mock_path=args.gauss_mock,
        redis_mock_path=args.redis_mock,
    )
    app = create_app(
        service,
        samples_path=resolve_path(args.samples),
        default_mode=run_mode,
    )
    logger.info("Log file: %s", log_file)
    logger.info(
        "Open http://%s:%s/?query=Run%%20Network%%20quality%%20monitoring%%20for%%20onlinecharging_docker.",
        args.host,
        args.port,
    )
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
