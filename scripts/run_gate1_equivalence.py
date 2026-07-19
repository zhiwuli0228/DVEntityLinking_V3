"""Gate 1: diversified golden-query AC≡INSTR equivalence test.

Runs both `instr` and `ac` match_words against every volume for a diversified
golden query set (test-plan cases + edge cases) and asserts result-set
equality (entity_id sets + ordered (entity_word_id, entity_id) tuples + counts).
0 mismatch = pass. Requires MySQL.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from run_mysql_entity_data_mock import _config  # noqa: E402
from dv_entity_linking.performance_mock import MySqlEntityDataMockSource  # noqa: E402

VOLUMES = ["50k", "100k", "200k", "500k"]
OUT = ROOT / "outputs" / "performance" / "gate1_equivalence"


def _golden_queries() -> list[dict]:
    plan = json.loads(
        (ROOT / "samples" / "mock" / "no_llm_low_latency_test_plan.json").read_text(
            encoding="utf-8"
        )
    )
    queries = []
    for case in plan["cases"]:
        if "remote_match" in case["layers"]:
            queries.append(
                {
                    "name": case["name"],
                    "normalized_query": case["normalized_query"],
                    "entity_types": tuple(case.get("entity_types", [])),
                    "category": "plan",
                }
            )
    queries.append({"name": "edge_partial_prefix", "normalized_query": "cpuusage00000100", "entity_types": (), "category": "edge"})
    queries.append({"name": "edge_cjk", "normalized_query": "查询cpuusage000001001告警", "entity_types": (), "category": "edge"})
    queries.append({"name": "edge_2k_long", "normalized_query": "x" * 1000 + "cpuusage000001001" + "y" * 1000, "entity_types": (), "category": "edge"})
    queries.append({"name": "edge_single_char", "normalized_query": "c", "entity_types": (), "category": "edge"})
    queries.append({"name": "edge_type_mismatch", "normalized_query": "checkcpuusage000001001now", "entity_types": ("device",), "category": "edge"})
    queries.append({"name": "edge_all_padding", "normalized_query": "xxxxxxxxxxxxxxxxxxxxxxxx", "entity_types": (), "category": "edge"})
    return queries


def _fingerprint(matches):
    return tuple((m["entity_word_id"], m["entity_id"]) for m in matches)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    queries = _golden_queries()
    print(f"== Gate 1: AC≡INSTR equivalence ({len(queries)} queries × {len(VOLUMES)} volumes) ==", flush=True)
    mismatches = 0
    total = 0
    rows = []
    for label in VOLUMES:
        db = f"dv_entity_data_mock_{label}"
        cfg = dataclasses.replace(_config(5), database=db)
        src_in = MySqlEntityDataMockSource(cfg, match_strategy="instr")
        src_ac = MySqlEntityDataMockSource(cfg, match_strategy="ac")
        vol_mismatch = 0
        try:
            src_ac.prepare_matcher()
            for q in queries:
                r_in = src_in.match_words(q["normalized_query"], entity_types=q["entity_types"])
                r_ac = src_ac.match_words(q["normalized_query"], entity_types=q["entity_types"])
                ids_in = tuple(sorted(m["entity_id"] for m in r_in.matches))
                ids_ac = tuple(sorted(m["entity_id"] for m in r_ac.matches))
                fp_in = _fingerprint(r_in.matches)
                fp_ac = _fingerprint(r_ac.matches)
                ok = (ids_in == ids_ac) and (fp_in == fp_ac) and (len(r_in.matches) == len(r_ac.matches))
                total += 1
                if not ok:
                    mismatches += 1
                    vol_mismatch += 1
                rows.append({
                    "volume": label, "name": q["name"], "category": q["category"],
                    "count_instr": len(r_in.matches), "count_ac": len(r_ac.matches),
                    "ids_instr": list(ids_in), "ids_ac": list(ids_ac),
                    "order_match": fp_in == fp_ac, "ok": ok,
                })
        finally:
            src_in.close()
            src_ac.close()
        print(f"  {label}: {len(queries)} queries, mismatches={vol_mismatch}", flush=True)

    report = {
        "schema": "dv.gate1-equivalence.1",
        "total_comparisons": total,
        "mismatches": mismatches,
        "passed": mismatches == 0,
        "queries": queries,
        "rows": rows,
    }
    path = OUT / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n== {'PASS' if mismatches == 0 else 'FAIL'}: {total} comparisons, {mismatches} mismatches ==", flush=True)
    if mismatches:
        for r in rows:
            if not r["ok"]:
                print(f"  MISMATCH {r['volume']}/{r['name']}: instr={r['ids_instr']} ac={r['ids_ac']} order={r['order_match']}", flush=True)
    print(f"report -> {path}", flush=True)
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
