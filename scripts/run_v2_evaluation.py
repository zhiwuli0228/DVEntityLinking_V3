from __future__ import annotations

import argparse
import json

from demo_runtime import ensure_src_path, resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V2 multi-type startup dataset evaluation.")
    parser.add_argument("--catalog", default="samples/real/v2_entity_examples.json")
    parser.add_argument("--queries", default="samples/real/v2_query_samples.json")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_src_path()
    from dv_entity_linking.legacy.catalog import CatalogRepository
    from dv_entity_linking.legacy.datasets import QueryDatasetLoader
    from dv_entity_linking.legacy.evaluation import evaluate_query_dataset
    from dv_entity_linking.legacy.service import EntityLinkingService

    catalog = CatalogRepository(resolve_path(args.catalog))
    catalog.load()
    dataset = QueryDatasetLoader().load(resolve_path(args.queries), catalog)
    report = evaluate_query_dataset(EntityLinkingService(catalog), dataset)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = resolve_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
