from __future__ import annotations

import json

from dv_entity_linking.evaluation import (
    FORBIDDEN_KEY_PARTS,
    RunRepository,
    build_run_record,
)
from dv_entity_linking.models import RunMode


def test_run_repository_redacts_forbidden_keys(tmp_path):
    output = tmp_path / "runs.jsonl"
    repository = RunRepository(output)
    record = build_run_record(
        mode=RunMode.OFFLINE_DEMO,
        query="RAN-A1 的 ASR 最近如何",
        result={
            "summary": {"status": "linked", "entity_ids": ["NE-DV-RAN-001"]},
            "api_key": "should-not-leak",
            "nested": {"raw_response": "full llm response"},
        },
        llm_used=False,
        degraded=False,
    )

    repository.append(record)

    payload = json.loads(output.read_text(encoding="utf-8").strip())
    assert payload["result"]["api_key"] == "[REDACTED]"
    assert payload["result"]["nested"]["raw_response"] == "[REDACTED]"
    assert "should-not-leak" not in output.read_text(encoding="utf-8")


def test_run_repository_redacts_all_forbidden_key_parts(tmp_path):
    output = tmp_path / "runs.jsonl"
    repository = RunRepository(output)
    result = {key: f"leak-{key}" for key in FORBIDDEN_KEY_PARTS}
    result["nested"] = [
        {"safe": "visible"},
        {"authorization_header": "leak-authorization-header"},
        {"llm_full_log_value": "leak-llm-full-log"},
        {"base_url": "https://should-not-leak.example"},
        {"traceback": "stack should not leak"},
    ]
    record = build_run_record(
        mode=RunMode.OFFLINE_DEMO,
        query="RAN-A1 的 ASR 最近如何",
        result=result,
        llm_used=False,
        degraded=False,
    )

    repository.append(record)

    text = output.read_text(encoding="utf-8")
    payload = json.loads(text.strip())
    for key in FORBIDDEN_KEY_PARTS:
        assert payload["result"][key] == "[REDACTED]"
        assert f"leak-{key}" not in text
    assert payload["result"]["nested"][0]["safe"] == "visible"
    assert payload["result"]["nested"][1]["authorization_header"] == "[REDACTED]"
    assert payload["result"]["nested"][2]["llm_full_log_value"] == "[REDACTED]"
    assert payload["result"]["nested"][3]["base_url"] == "[REDACTED]"
    assert payload["result"]["nested"][4]["traceback"] == "[REDACTED]"
    assert "leak-authorization-header" not in text
    assert "leak-llm-full-log" not in text
    assert "should-not-leak.example" not in text
    assert "stack should not leak" not in text
