from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    raw = b"".join(b"\x00" + (b"\xff\xff\xff" * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _png_header_only_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IEND", b"")
    )


def _write_browser_evidence(log_dir):
    desktop = log_dir / "v2_frontend_desktop_1366x768.png"
    narrow = log_dir / "v2_frontend_narrow_390x844.png"
    desktop.write_bytes(_png_bytes(1366, 768))
    narrow.write_bytes(_png_bytes(390, 844))
    evidence = {
        "schema_version": "v2.frontend_browser_evidence.1",
        "ok": True,
        "screenshots": {
            "desktop_1366x768": str(desktop),
            "narrow_390x844": str(narrow),
        },
        "checks": {
            "all_sections_visible": True,
            "visual_workbench_shell_observed": True,
            "status_band_observed": True,
            "query_command_zone_observed": True,
            "result_stream_observed": True,
            "llm_explanation_component_observed": True,
            "catalog_filter_zone_observed": True,
            "multi_mention_observed": True,
            "second_mention_selected": True,
            "candidate_and_entity_detail_observed": True,
            "llm_explanation_observed": True,
            "catalog_filter_observed": True,
            "card_text_readable": True,
            "debug_collapsed": True,
            "no_section_overlap": True,
            "no_horizontal_overflow": True,
            "no_text_overlap_or_clipping_narrow": True,
        },
    }
    (log_dir / "v2_frontend_browser_evidence.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )


def _load_v2_smoke_module():
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "run_v2_acceptance_smoke_for_tests",
        ROOT / "scripts/run_v2_acceptance_smoke.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_acceptance_smoke_script_runs_offline(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_acceptance_smoke.py",
            "--log-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["mode"] == "offline_demo"
    assert payload["entity_count"] >= 20
    assert {"NE-DV-RAN-001", "KPI-ACCESS-SUCCESS"} <= set(payload["link_entity_ids"])
    assert list(tmp_path.glob("acceptance-smoke-*.log"))


def test_web_demo_script_has_pycharm_friendly_help():
    result = subprocess.run(
        [sys.executable, "scripts/run_web_demo.py", "--help"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    assert "--mode" in result.stdout
    assert "--storage-mode" in result.stdout
    assert "--gauss-mock" in result.stdout
    assert "--redis-mock" in result.stdout
    assert "--log-dir" in result.stdout
    assert "Run the DVEntityLinking Web demo" in result.stdout
    assert "samples/real/v2_entity_examples.json" in result.stdout
    assert "samples/real/v2_query_samples.json" in result.stdout


def test_v1_evaluation_script_runs_offline():
    result = subprocess.run(
        [sys.executable, "scripts/run_v1_evaluation.py"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "v1.alarm_evaluation_report.1"
    assert payload["summary"]["passed"] is True
    assert payload["summary"]["precision"] == 1.0
    assert payload["summary"]["recall"] == 1.0


def test_v2_evaluation_script_runs_offline():
    result = subprocess.run(
        [sys.executable, "scripts/run_v2_evaluation.py"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "v2.entity_linking_evaluation_report.1"
    assert payload["summary"]["passed"] is True
    assert payload["summary"]["precision"] == 1.0
    assert payload["summary"]["recall"] == 1.0


def test_v1_acceptance_smoke_script_runs_offline(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v1_acceptance_smoke.py",
            "--log-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["mode"] == "offline_demo"
    assert payload["entity_count"] == 9
    assert payload["type_counts"] == {"alarm": 9}
    assert payload["exact_linked_entity_id"] == "DV-ALM-002"
    assert payload["shared_phrase_status"] == "linked"
    assert payload["shared_phrase_linked_entity_id"] == "DV-ALM-002"
    assert payload["short_id_no_match_status"] == "no_match"
    assert payload["not_required_status"] == "not_required"
    assert payload["html_mode_controls_present"] is True
    assert list(tmp_path.glob("v1-acceptance-smoke-*.log"))


def test_v2_acceptance_smoke_script_runs_offline(tmp_path):
    _write_browser_evidence(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance_smoke.py",
            "--log-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["mode"] == "offline_demo"
    assert payload["entity_count"] == 25
    assert set(payload["alarm_plus_kpi_entity_ids"]) == {"DV-ALM-002", "DV-KPI-MTK-001"}
    assert payload["partial_status"] == "partial"
    assert payload["no_match_status"] == "no_match"
    assert payload["no_match_has_linked_entity"] is False
    assert payload["no_match_reason_visible"] is True
    assert payload["not_required_status"] == "not_required"
    assert payload["not_required_has_linked_entity"] is False
    assert payload["not_required_mention_count"] == 0
    assert payload["not_required_reason_visible"] is True
    assert set(payload["linked_llm_explanation_contexts"]) >= {"global", "mention", "candidate"}
    assert payload["html_contains_workbench_labels"] is True
    assert payload["html_debug_collapsed"] is True
    assert payload["entity_detail_has_safe_attributes"] is True
    assert payload["entity_detail_has_raw_attributes"] is False
    assert payload["traceability_statuses"] == ["implemented"]
    assert payload["traceability_downgraded_count"] == 0
    assert payload["traceability_ac_v2_fe_004_status"] == "implemented"
    assert payload["traceability_decision_d041_status"] == "implemented"
    assert payload["visual_traceability_schema_version"] == "v2.frontend_visual_traceability.1"
    assert payload["visual_traceability_manual_user_acceptance_status"] == "accepted"
    assert payload["visual_traceability_statuses"] == ["implemented", "needs_user_decision"]
    assert payload["visual_traceability_blocking_ac_ids"] == ["AC-V2-FE-VIS-008"]
    assert payload["visual_traceability_blocking_count"] == 1
    assert payload["browser_evidence_checked"] is True
    assert payload["browser_evidence_ok"] is True
    assert payload["browser_evidence_fresh"] is True
    assert payload["browser_screenshots_present"] is True
    assert payload["browser_screenshot_images_valid"] is True
    assert payload["d003_scan_ok"] is True
    assert payload["d003_scan_finding_count"] == 0
    assert set(payload["d003_scan_sources"]) >= {
        "HTML /",
        "API /api/status",
        "API /api/link alarm_plus_kpi",
        "API /api/entities/DV-KPI-MTK-001",
        "API /api/retrieve",
    }
    assert payload["browser_evidence_missing_checks"] == []
    traceability_json = tmp_path / "v2_frontend_traceability_check.json"
    traceability_md = tmp_path / "v2_frontend_traceability_check.md"
    visual_traceability_json = tmp_path / "v2_frontend_visual_traceability_check.json"
    visual_traceability_md = tmp_path / "v2_frontend_visual_traceability_check.md"
    assert traceability_json.exists()
    assert traceability_md.exists()
    assert visual_traceability_json.exists()
    assert visual_traceability_md.exists()
    traceability_payload = json.loads(traceability_json.read_text(encoding="utf-8"))
    assert traceability_payload["schema_version"] == "v2.frontend_traceability_check.1"
    assert all(item["status"] == "implemented" for item in traceability_payload["items"])
    ac_004_items = [
        item for item in traceability_payload["items"] if "AC-V2-FE-004" in item["ac_ids"]
    ]
    assert len(ac_004_items) == 1
    assert ac_004_items[0]["status"] == "implemented"
    assert "no_match_has_linked_entity" in ac_004_items[0]["evidence_artifacts"]
    assert "not_required_has_linked_entity" in ac_004_items[0]["evidence_artifacts"]
    d041_items = [
        item for item in traceability_payload["items"] if item["decision_id"] == "D041"
    ]
    assert len(d041_items) == 1
    assert d041_items[0]["status"] == "implemented"
    assert "scripts/run_web_demo.py" in d041_items[0]["implementation_files"]
    visual_payload = json.loads(visual_traceability_json.read_text(encoding="utf-8"))
    assert visual_payload["schema_version"] == "v2.frontend_visual_traceability.1"
    assert visual_payload["scenario"]["selected_mention"] == "CPU Usage"
    assert visual_payload["scenario"]["selected_candidate"] == "DV-KPI-MTK-001"
    assert visual_payload["manual_user_acceptance_status"] == "accepted"
    assert "User confirmed current after visual" in visual_payload["manual_user_acceptance_evidence"]["note"]
    assert visual_payload["summary"]["blocking_ac_ids"] == ["AC-V2-FE-VIS-008"]
    assert visual_payload["checks"]["no_unconfirmed_real_dv_content"] is True
    assert visual_payload["checks"]["no_text_overlap_or_clipping_narrow"] is True
    assert not any(
        item["needs_d003_confirmation"]
        for item in visual_payload["d003_content_inventory"]
    )
    assert any(
        item["source_classification"] == "runtime_api_artifact_scan"
        for item in visual_payload["d003_content_inventory"]
    )
    assert all(
        {
            "text_or_label",
            "classification",
            "source_reference",
            "decision_id",
            "needs_d003_confirmation",
        }
        <= set(item)
        for item in visual_payload["d003_content_inventory"]
    )
    assert all(
        {
            "ac_ids",
            "priority",
            "evidence_type",
            "prototype_ref",
            "absorbed_principle",
            "target_ui_regions",
            "before_screenshot",
            "after_screenshot",
            "same_viewport_and_query",
            "automated_visual_semantic_checks",
            "manual_user_acceptance_status",
            "downgrade_classification",
            "reviewer_result",
        }
        <= set(item)
        for item in visual_payload["items"]
    )
    assert any(item["prototype_ref"] == "SigNoz" for item in visual_payload["items"])
    assert any(item["prototype_ref"] == "OpenGenerativeUI" for item in visual_payload["items"])
    assert any(item["prototype_ref"] == "Tambo" for item in visual_payload["items"])
    log_files = list(tmp_path.glob("v2-acceptance-smoke-*.log"))
    assert log_files
    log_text = log_files[0].read_text(encoding="utf-8")
    assert "V2 acceptance smoke result: ok=True" in log_text
    assert "api_key" not in log_text
    assert "raw_response" not in log_text
    assert "authorization" not in log_text


def test_v2_acceptance_smoke_rejects_non_image_browser_screenshots(tmp_path):
    desktop = tmp_path / "v2_frontend_desktop_1366x768.png"
    narrow = tmp_path / "v2_frontend_narrow_390x844.png"
    desktop.write_bytes(b"not-a-decodable-image")
    narrow.write_bytes(b"not-a-decodable-image")
    checks = {
        "all_sections_visible": True,
        "visual_workbench_shell_observed": True,
        "status_band_observed": True,
        "query_command_zone_observed": True,
        "result_stream_observed": True,
        "llm_explanation_component_observed": True,
        "catalog_filter_zone_observed": True,
        "multi_mention_observed": True,
        "second_mention_selected": True,
        "candidate_and_entity_detail_observed": True,
        "llm_explanation_observed": True,
        "catalog_filter_observed": True,
        "card_text_readable": True,
        "debug_collapsed": True,
        "no_section_overlap": True,
        "no_horizontal_overflow": True,
        "no_text_overlap_or_clipping_narrow": True,
    }
    (tmp_path / "v2_frontend_browser_evidence.json").write_text(
        json.dumps(
            {
                "schema_version": "v2.frontend_browser_evidence.1",
                "ok": True,
                "screenshots": {
                    "desktop_1366x768": str(desktop),
                    "narrow_390x844": str(narrow),
                },
                "checks": checks,
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance_smoke.py",
            "--log-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["ok"] is False
    assert payload["browser_evidence_ok"] is False
    assert payload["browser_screenshot_images_valid"] is False
    assert payload["browser_screenshot_dimension_checks"] == {
        "desktop_1366x768": False,
        "narrow_390x844": False,
    }
    blocking_ac_ids = set(payload["visual_traceability_blocking_ac_ids"])
    assert {"AC-V2-FE-VIS-007", "AC-V2-FE-VIS-008"} <= blocking_ac_ids
    assert payload["visual_traceability_blocking_count"] > 2


def test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots(tmp_path):
    desktop = tmp_path / "v2_frontend_desktop_1366x768.png"
    narrow = tmp_path / "v2_frontend_narrow_390x844.png"
    desktop.write_bytes(_png_header_only_bytes(1366, 768))
    narrow.write_bytes(_png_header_only_bytes(390, 844))
    checks = {
        "all_sections_visible": True,
        "visual_workbench_shell_observed": True,
        "status_band_observed": True,
        "query_command_zone_observed": True,
        "result_stream_observed": True,
        "llm_explanation_component_observed": True,
        "catalog_filter_zone_observed": True,
        "multi_mention_observed": True,
        "second_mention_selected": True,
        "candidate_and_entity_detail_observed": True,
        "llm_explanation_observed": True,
        "catalog_filter_observed": True,
        "card_text_readable": True,
        "debug_collapsed": True,
        "no_section_overlap": True,
        "no_horizontal_overflow": True,
        "no_text_overlap_or_clipping_narrow": True,
    }
    (tmp_path / "v2_frontend_browser_evidence.json").write_text(
        json.dumps(
            {
                "schema_version": "v2.frontend_browser_evidence.1",
                "ok": True,
                "screenshots": {
                    "desktop_1366x768": str(desktop),
                    "narrow_390x844": str(narrow),
                },
                "checks": checks,
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance_smoke.py",
            "--log-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["browser_evidence_ok"] is False
    assert payload["browser_screenshot_images_valid"] is False
    assert payload["browser_screenshot_dimension_checks"] == {
        "desktop_1366x768": False,
        "narrow_390x844": False,
    }
    assert {"AC-V2-FE-VIS-007", "AC-V2-FE-VIS-008"} <= set(
        payload["visual_traceability_blocking_ac_ids"]
    )


def test_v2_visual_d003_scan_flags_runtime_sensitive_values():
    module = _load_v2_smoke_module()

    evidence = module._scan_d003_sources(
        [
            ("API /api/status", '{"base_url": "https://prod.dv.example/v1"}'),
            ("artifact traceability", "Authorization: Bearer abcdefghijklmnop"),
            ("API /api/link", '{"raw_response": "should-not-leak"}'),
        ]
    )

    assert evidence["ok"] is False
    assert evidence["finding_count"] == 3
    assert {item["source_reference"] for item in evidence["inventory"]} == {
        "API /api/status",
        "artifact traceability",
        "API /api/link",
    }
    assert all(item["needs_d003_confirmation"] for item in evidence["inventory"])


def test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance():
    module = _load_v2_smoke_module()

    assert (
        module._visual_item_blocks_acceptance(
            {
                "priority": "P0",
                "status": "implemented",
                "downgrade_classification": "api_only",
            }
        )
        is True
    )
    assert (
        module._visual_item_blocks_acceptance(
            {
                "priority": "P0",
                "status": "implemented",
                "downgrade_classification": "none",
            }
        )
        is False
    )


def test_v2_visual_smoke_rejects_versioned_web_demo_entries(tmp_path, monkeypatch):
    module = _load_v2_smoke_module()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run_web_demo.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert module._web_demo_single_entry_ok() is True

    (scripts_dir / "run_v2_web_demo.py").write_text("", encoding="utf-8")

    assert module._web_demo_single_entry_ok() is False


def test_v2_acceptance_smoke_script_has_pycharm_friendly_help():
    result = subprocess.run(
        [sys.executable, "scripts/run_v2_acceptance_smoke.py", "--help"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )

    assert "Run the V2 multi-type demo acceptance smoke checks" in result.stdout
    assert "--mode" in result.stdout
    assert "--log-dir" in result.stdout
