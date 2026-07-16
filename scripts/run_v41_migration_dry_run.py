"""Validate a canonical entity export for V4.1 without publishing it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Keep this helper directly runnable from a fresh checkout, like the other
# repository scripts, without requiring a prior editable package install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dv_entity_linking.v41 import V41ValidationError, build_entity_migration_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a V4.1 canonical entity migration dry run")
    parser.add_argument("--input", type=Path, required=True, help="Canonical entity JSON export")
    parser.add_argument("--source-version", required=True, help="Safe source data version identifier")
    parser.add_argument("--report", type=Path, help="Optional path for the sanitized JSON report")
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        entities = payload["entities"] if isinstance(payload, dict) else payload
        bundle = build_entity_migration_bundle(entities, source_version=args.source_version, dry_run=True)
    except (OSError, json.JSONDecodeError, KeyError, V41ValidationError) as exc:
        print(json.dumps({"validation": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    output = {
        "report": bundle.report,
        "entity_words": [
            {
                "entity_id": word.entity_id,
                "entity_type": word.entity_type,
                "entity_word": word.entity_word,
                "normalized_key": word.normalized_key,
                "source": word.source,
            }
            for word in bundle.entity_words
        ],
    }
    encoded = json.dumps(output, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
