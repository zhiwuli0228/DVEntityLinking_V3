from __future__ import annotations

import json
import tomllib
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_contract_catalog_sample_schema_and_provenance():
    payload = _read_json("samples/mock/entity_catalog.json")
    entities = payload["entities"]
    entity_ids = {entity["entity_id"] for entity in entities}
    type_counts = Counter(entity["entity_type"] for entity in entities)

    assert payload["metadata"]["data_layer"] == "L0_SYNTHETIC"
    assert payload["metadata"]["source"] == "mock_catalog"
    assert len(entities) >= 20
    assert set(type_counts) == {
        "network_resource",
        "alarm_event",
        "kpi_metric",
        "topology_relation",
        "knowledge_case",
    }
    assert all(count >= 2 for count in type_counts.values())

    required_entity_fields = {
        "entity_id",
        "entity_type",
        "canonical_name",
        "aliases",
        "description",
        "attributes",
        "relations",
        "data_layer",
        "source",
    }
    required_relation_fields = {
        "target_entity_id",
        "relation_type",
        "source",
        "data_layer",
    }
    forbidden_keys = {
        "api_key",
        "api_base",
        "base_url",
        "token",
        "cookie",
        "authorization",
        "password",
        "secret",
        "endpoint_url",
        "host",
        "url",
        "traceback",
        "exception",
        "payload",
        "raw_request",
        "raw_response",
        "llm_full_log",
    }

    for entity in entities:
        assert required_entity_fields <= set(entity), entity.get("entity_id")
        assert entity["data_layer"] == "L0_SYNTHETIC"
        assert entity["source"] == "mock_catalog"
        assert isinstance(entity["aliases"], list)
        assert isinstance(entity["relations"], list)
        assert not (forbidden_keys & set(entity))
        for relation in entity["relations"]:
            assert required_relation_fields <= set(relation), entity["entity_id"]
            assert relation["target_entity_id"] in entity_ids
            assert relation["data_layer"] == "L0_SYNTHETIC"
            assert relation["source"] == "mock_catalog"


def test_contract_query_and_retrieval_samples_cover_acceptance_floor():
    payload = _read_json("samples/mock/query_samples.json")
    metadata = payload["metadata"]
    queries = payload["queries"]
    retrieval_samples = payload["retrieval_samples"]

    assert metadata["data_layer"] == "L0_SYNTHETIC"
    assert metadata["source"] == "mock_query_samples"
    assert len(queries) >= 12
    assert {"copilot", "fault_agent"} <= {item["persona"] for item in queries}
    assert {
        "exact",
        "alias",
        "fuzzy",
        "multi_entity",
        "ambiguous",
        "no_match",
    } <= {item["category"] for item in queries}

    assert len(retrieval_samples) >= 5
    assert {
        "name/alias similarity",
        "description semantic overlap",
        "same entity type",
        "topology neighbor",
        "knowledge/case relation",
    } <= {item["expected_reason"] for item in retrieval_samples}
    assert all(1 <= int(item["k"]) <= 20 for item in retrieval_samples)
    for sample in [*queries, *retrieval_samples]:
        assert sample.get("data_layer", metadata["data_layer"]) == "L0_SYNTHETIC"
        assert sample.get("source", metadata["source"]) == "mock_query_samples"


def test_contract_real_v1_startup_samples_are_minimal_and_annotated():
    entity_payload = _read_json("samples/real/entity_examples.json")
    query_payload = _read_json("samples/real/query_samples.json")

    entity_metadata = entity_payload["metadata"]
    query_metadata = query_payload["metadata"]
    entities = entity_payload["entities"]
    queries = query_payload["queries"]
    entity_ids = {entity["entity_id"] for entity in entities}

    assert set(entity_metadata) == {"schema_version", "entity_type_scope", "entity_count"}
    assert set(query_metadata) == {
        "schema_version",
        "query_count",
        "max_one_entity_mention_per_query",
    }
    assert entity_metadata["schema_version"] == "v1.alarm_entity.2"
    assert query_metadata["schema_version"] == "v1.alarm_query.2"

    assert entity_metadata["entity_type_scope"] == ["alarm"]
    assert entity_metadata["entity_count"] == 9
    assert len(entities) == 9
    assert {entity["entity_type"] for entity in entities} == {"alarm"}
    assert {
        "DV-ALM-001",
        "DV-ALM-002",
        "DV-ALM-003",
        "DV-ALM-004",
        "DV-ALM-005",
        "DV-ALM-006",
        "DV-ALM-007",
        "DV-ALM-008",
        "DV-ALM-009",
    } == entity_ids
    entity_by_id = {entity["entity_id"]: entity for entity in entities}
    assert entity_by_id["DV-ALM-001"]["canonical_name"].startswith("ALM-505001314 ")
    assert {"505001314", "ALM-505001314"} <= set(entity_by_id["DV-ALM-001"]["aliases"])
    assert entity_by_id["DV-ALM-007"]["canonical_name"].startswith("ALM-101207 ")
    assert entity_by_id["DV-ALM-008"]["canonical_name"].startswith("ALM-493011404 ")
    assert entity_by_id["DV-ALM-009"]["canonical_name"].startswith("ALM-999999993 ")
    for entity in entities:
        assert "entity_name" not in entity
        assert "attributes" not in entity
        assert "relations" not in entity
        assert "data_layer" not in entity
        assert "source" not in entity

    assert "query_list" not in query_payload
    assert query_metadata["query_count"] == 16
    assert query_metadata["max_one_entity_mention_per_query"] is True
    assert len(queries) == 16
    statuses = {query["expected_status"] for query in queries}
    assert {"linked", "ambiguous", "no_match", "not_required"} <= statuses

    for query in queries:
        assert "word2entity" not in query
        assert "query_id" not in query
        assert "query_text" not in query
        assert "id" in query
        assert "query" in query
        assert "data_layer" not in query
        assert "source" not in query
        assert "source_scene" not in query
        assert "difficulty" not in query
        assert "expected_intent" not in query
        assert len(query["mentions"]) <= 1
        if query["mentions"]:
            mention = query["mentions"][0]
            start, end = mention["span"]
            assert query["query"][start:end] == mention["text"]
            assert "expected_entity_ids" in mention
            assert "expected_entity_id" not in mention
            assert "expected_entity_type" not in mention
            assert "match_type" not in mention
        else:
            assert query["expected_status"] == "not_required"
            assert query["expected_entities"] == []
        if query["expected_status"] in {"no_match", "not_required"}:
            assert "negative_reason" in query
            assert "no_match_reason" not in query
        for expected in query["expected_entities"]:
            assert expected["entity_id"] in entity_ids
            assert set(expected) == {"entity_id"}

    query_by_id = {query["id"]: query for query in queries}
    assert query_by_id["Q-005"]["expected_status"] == "ambiguous"
    assert {
        "DV-ALM-002",
        "DV-ALM-003",
    } == set(query_by_id["Q-005"]["mentions"][0]["expected_entity_ids"])
    assert query_by_id["Q-012"]["expected_status"] == "no_match"
    assert query_by_id["Q-012"]["expected_entities"] == []
    assert query_by_id["Q-012"]["mentions"][0]["text"] == "51"
    assert query_by_id["Q-013"]["expected_status"] == "no_match"
    assert query_by_id["Q-013"]["mentions"][0]["text"] == "999"
    assert query_by_id["Q-014"]["expected_status"] == "no_match"
    assert query_by_id["Q-014"]["mentions"][0]["text"] == "ALM-5102"
    assert query_by_id["Q-015"]["expected_status"] == "not_required"
    assert query_by_id["Q-015"]["mentions"] == []
    assert query_by_id["Q-016"]["expected_status"] == "not_required"
    assert query_by_id["Q-016"]["mentions"] == []
    negative_queries = [
        query
        for query in queries
        if query["expected_status"] in {"no_match", "not_required"}
    ]
    assert len(negative_queries) >= 5
    assert {
        query_by_id["Q-008"]["expected_entities"][0]["entity_id"],
        query_by_id["Q-009"]["expected_entities"][0]["entity_id"],
        query_by_id["Q-010"]["expected_entities"][0]["entity_id"],
    } == {"DV-ALM-007", "DV-ALM-008", "DV-ALM-009"}


def test_contract_v3_storage_and_ner_artifacts_are_mocked_and_consistent():
    gauss_payload = _read_json("samples/real/v3_gauss_entities.json")
    redis_payload = _read_json("samples/real/v3_redis_entity_words.json")
    golden_payload = _read_json("samples/real/v3_ner_golden_cases.json")

    assert gauss_payload["metadata"]["schema_version"] == "v3.gauss_entities.1"
    assert redis_payload["metadata"]["schema_version"] == "v3.redis_entity_words.1"
    assert golden_payload["metadata"]["schema_version"] == "v3.ner_golden_cases.1"
    assert gauss_payload["metadata"]["entity_count"] == len(gauss_payload["entities"])
    assert redis_payload["metadata"]["word_count"] == len(redis_payload["entity_words"])
    assert golden_payload["metadata"]["query_count"] == len(golden_payload["queries"])
    assert redis_payload["metadata"]["aliases_auto_generated"] is False
    assert redis_payload["metadata"]["key_scope"] == [
        "canonical_name",
        "confirmed_aliases",
    ]

    entity_ids = {item["entity_id"] for item in gauss_payload["entities"]}
    assert all(item["entity_id"] in entity_ids for item in redis_payload["entity_words"])
    assert {
        "entity_id",
        "entity_type",
        "canonical_name",
        "aliases",
        "description",
    } <= set(gauss_payload["entities"][0])
    assert any(
        item["entity_word"] == "CPU Usage"
        and item["normalized_key"] == "cpuusage"
        and item["source"] == "canonical_name"
        for item in redis_payload["entity_words"]
    )
    assert any(query["expected_status"] == "partial" for query in golden_payload["queries"])
    serialized = json.dumps(
        {
            "gauss": gauss_payload,
            "redis": redis_payload,
            "golden": golden_payload,
        },
        ensure_ascii=False,
    ).lower()
    for forbidden in ["password", "authorization", "bearer ", "sk-secret", "jdbc:", "odbc:", "base_url"]:
        assert forbidden not in serialized
    assert (ROOT / "scripts/run_v3_evaluation.py").exists()
    assert (ROOT / "scripts/run_v3_acceptance_smoke.py").exists()
    assert not (ROOT / "scripts/run_v3_web_demo.py").exists()


def test_contract_config_and_gitignore_keep_real_dependencies_local():
    llm_config = _read_json("config/llm.example.json")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert llm_config["provider"] == "openai_compatible"
    assert llm_config["enabled"] is False
    assert llm_config["api_key_env"] == "DVEL_LLM_API_KEY"
    assert "api_key" not in llm_config
    assert "config/llm.local.json" in gitignore
    assert "samples/local_real_dv/" in gitignore
    assert "outputs/local_real_dv/" in gitignore
    assert "Flask>=3,<4" in pyproject["project"]["dependencies"]


def test_contract_document_governance_is_compact_and_versioned():
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    dv_context = (ROOT / "docs/DV_CONTEXT.md").read_text(encoding="utf-8")
    project = (ROOT / "docs/PROJECT.md").read_text(encoding="utf-8")
    data_contract = (ROOT / "docs/current/DATA_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    test_acceptance = (ROOT / "docs/current/TEST_ACCEPTANCE.md").read_text(
        encoding="utf-8"
    )
    decisions = (ROOT / "docs/current/DECISIONS.md").read_text(encoding="utf-8")
    dv_process = (ROOT / "docs/process/DV_PROCESS.md").read_text(encoding="utf-8")
    test_root_readme = (ROOT / "tests/README.md").read_text(encoding="utf-8")
    usage = (ROOT / "docs/USAGE.md").read_text(encoding="utf-8")
    v0_ir = (ROOT / "docs/baselines/v0/IR.md").read_text(encoding="utf-8")
    v0_sr = (ROOT / "docs/baselines/v0/SR.md").read_text(encoding="utf-8")
    v1_ir = (ROOT / "docs/baselines/v1/IR.md").read_text(encoding="utf-8")
    v1_sr_decomposition = (
        ROOT / "docs/baselines/v1/IR-SR-DECOMPOSITION.md"
    ).read_text(encoding="utf-8")
    v1_sr = (ROOT / "docs/baselines/v1/SR.md").read_text(encoding="utf-8")
    v2_ir = (ROOT / "docs/baselines/v2/IR.md").read_text(encoding="utf-8")
    v2_frontend_ir = (
        ROOT / "docs/baselines/v2/IR-FRONTEND-REMEDIATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_ir = (
        ROOT / "docs/baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_review = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_sr = (
        ROOT / "docs/baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_design_review = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_design_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_design_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_implementation = (
        ROOT / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_implementation_review = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_implementation_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_implementation_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_test_design = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_test_review = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_test_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_test_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_visual_acceptance_precheck = (
        ROOT
        / "docs/baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md"
    ).read_text(encoding="utf-8")
    v2_frontend_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_sr_decomposition = (
        ROOT / "docs/baselines/v2/IR-SR-DECOMPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_sr = (ROOT / "docs/baselines/v2/SR.md").read_text(encoding="utf-8")
    v2_frontend_sr = (
        ROOT / "docs/baselines/v2/SR-FRONTEND-REMEDIATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_design_review = (
        ROOT / "docs/baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_design_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_design_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_implementation = (
        ROOT / "docs/baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_implementation_review = (
        ROOT / "docs/baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_implementation_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_implementation_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_test_design = (
        ROOT / "docs/baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md"
    ).read_text(encoding="utf-8")
    v2_frontend_test_review = (
        ROOT / "docs/baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW.md"
    ).read_text(encoding="utf-8")
    v2_frontend_test_disposition = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_test_closure = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_frontend_acceptance_precheck = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md"
    ).read_text(encoding="utf-8")
    v2_frontend_acceptance_precheck_verification = (
        ROOT
        / "docs/baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v2_tc = (ROOT / "docs/baselines/v2/TC-DVEntityLinking-V2-test-cases.md").read_text(
        encoding="utf-8"
    )
    v2_test_disposition = (
        ROOT / "docs/baselines/v2/TEST-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v0_release = (ROOT / "docs/releases/V0.md").read_text(encoding="utf-8")
    v1_release = (ROOT / "docs/releases/V1.md").read_text(encoding="utf-8")
    v2_release = (ROOT / "docs/releases/V2.md").read_text(encoding="utf-8")
    v3_ir = (ROOT / "docs/baselines/v3/IR.md").read_text(encoding="utf-8")
    v3_sr = (ROOT / "docs/baselines/v3/SR.md").read_text(encoding="utf-8")
    v3_sr_decomposition = (
        ROOT / "docs/baselines/v3/IR-SR-DECOMPOSITION.md"
    ).read_text(encoding="utf-8")
    v3_requirement_review = (
        ROOT / "docs/baselines/v3/REQUIREMENT-REVIEW.md"
    ).read_text(encoding="utf-8")
    v3_requirement_review_disposition = (
        ROOT / "docs/baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v3_requirement_closure = (
        ROOT / "docs/baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v3_function_design_review = (
        ROOT / "docs/baselines/v3/FUNCTION-DESIGN-REVIEW.md"
    ).read_text(encoding="utf-8")
    v3_function_design_disposition = (
        ROOT / "docs/baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v3_function_design_closure = (
        ROOT / "docs/baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v3_implementation = (
        ROOT / "docs/baselines/v3/IMPLEMENTATION.md"
    ).read_text(encoding="utf-8")
    v3_implementation_review = (
        ROOT / "docs/baselines/v3/IMPLEMENTATION-REVIEW.md"
    ).read_text(encoding="utf-8")
    v3_implementation_disposition = (
        ROOT / "docs/baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v3_implementation_closure = (
        ROOT / "docs/baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v3_test_design = (
        ROOT / "docs/baselines/v3/TEST-DESIGN.md"
    ).read_text(encoding="utf-8")
    v3_test_review = (
        ROOT / "docs/baselines/v3/TEST-REVIEW.md"
    ).read_text(encoding="utf-8")
    v3_test_disposition = (
        ROOT / "docs/baselines/v3/TEST-REVIEW-DISPOSITION.md"
    ).read_text(encoding="utf-8")
    v3_test_closure = (
        ROOT / "docs/baselines/v3/TEST-CLOSURE-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v3_acceptance_precheck = (
        ROOT / "docs/baselines/v3/ACCEPTANCE-PRECHECK.md"
    ).read_text(encoding="utf-8")
    v3_acceptance_precheck_verification = (
        ROOT / "docs/baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md"
    ).read_text(encoding="utf-8")
    v3_release = (ROOT / "docs/releases/V3.md").read_text(encoding="utf-8")
    v3_confirmation = _read_json(
        "docs/confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json"
    )

    assert (
        "V3 acceptance candidate prepared; pending user acceptance; not accepted/closed"
        in root_readme
    )
    assert (
        "V3 acceptance candidate prepared; pending user acceptance; not accepted/closed"
        in project
    )
    assert "V3 验收候选前置核查和核验已通过" in project
    assert "before 同场景截图或替代 before 证据口径未确认" in project
    assert "docs/baselines/v0/" in root_readme
    assert "docs/baselines/v1/" in root_readme
    assert "docs/baselines/v2/" in root_readme
    assert "docs/baselines/v3/" in root_readme
    assert "评审输入、闭环输入" in docs_readme
    assert "IR、SR 主输出件按版本保留" in docs_readme
    assert "baselines/v2/IR.md" in docs_readme
    assert "baselines/v3/IR.md" in docs_readme
    assert "baselines/v3/IR-SR-DECOMPOSITION.md" in docs_readme
    assert "baselines/v3/REQUIREMENT-REVIEW.md" in docs_readme
    assert "baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md" in docs_readme
    assert "baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md" in docs_readme
    assert "baselines/v3/SR.md" in docs_readme
    assert "baselines/v3/FUNCTION-DESIGN-REVIEW.md" in docs_readme
    assert "baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md" in docs_readme
    assert "baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md" in docs_readme
    assert "baselines/v3/IMPLEMENTATION.md" in docs_readme
    assert "baselines/v3/IMPLEMENTATION-REVIEW.md" in docs_readme
    assert "baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md" in docs_readme
    assert "baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md" in docs_readme
    assert "baselines/v3/TEST-DESIGN.md" in docs_readme
    assert "baselines/v3/TEST-REVIEW.md" in docs_readme
    assert "baselines/v3/TEST-REVIEW-DISPOSITION.md" in docs_readme
    assert "baselines/v3/TEST-CLOSURE-VERIFICATION.md" in docs_readme
    assert "baselines/v3/ACCEPTANCE-PRECHECK.md" in docs_readme
    assert "baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md" in docs_readme
    assert "releases/V3.md" in docs_readme
    assert "IR-FRONTEND-REMEDIATION.md" in docs_readme
    assert "IR-FRONTEND-VISUAL-REMEDIATION.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md" in docs_readme
    assert "SR-FRONTEND-VISUAL-REMEDIATION.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md" in docs_readme
    assert (
        "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md"
        in docs_readme
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md"
        in docs_readme
    )
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md" in docs_readme
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md"
        in docs_readme
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md"
        in docs_readme
    )
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in docs_readme
    assert "FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md" in docs_readme
    assert "FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md" in docs_readme
    assert "SR-FRONTEND-REMEDIATION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md" in docs_readme
    assert "FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW.md" in docs_readme
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-TEST-DESIGN.md" in docs_readme
    assert "FRONTEND-REMEDIATION-TEST-REVIEW.md" in docs_readme
    assert "FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in docs_readme
    assert "FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md" in docs_readme
    assert "FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md" in docs_readme
    assert "V1 已确认 `alarm` 告警知识实体" in dv_context
    assert "V1 alarm-only demo 使用最小字段样例" in dv_context
    assert "V2 已确认拆为 `ne_type` 和 `ne_name`" in dv_context
    assert "V2 已确认拆为 `kpi_task_name`" in dv_context
    assert "当前数据契约" in data_contract
    assert "v1.alarm_entity.2" in data_contract
    assert "v1.alarm_query.2" in data_contract
    assert "V2 Contract Direction" in data_contract
    assert "V3 Contract Direction" in data_contract
    assert "V3-SR.2-closed" in data_contract
    assert "V3-IMPL.1" in data_contract
    assert "v3.entity_word_norm.1" in data_contract
    assert "v3.gauss_entities.1" in data_contract
    assert "v3.redis_entity_words.1" in data_contract
    assert "v3.ner_golden_cases.1" in data_contract
    assert "Redis Mock" in data_contract
    assert "高斯 Mock" in data_contract
    assert "mentions[].entity_word_key" in data_contract
    assert "`ne_type`" in data_contract
    assert "`ne_name`" in data_contract
    assert "`kpi_task_name`" in data_contract
    assert "`kpi_meas_type_key`" in data_contract
    assert "别名规则" in data_contract
    assert "data_layer" in data_contract
    assert "不要求" in data_contract
    assert "precision" in test_acceptance
    assert "recall" in test_acceptance
    assert "negative false positive" in test_acceptance
    assert "V2 已验证结果" in test_acceptance
    assert "V3 验收候选口径" in test_acceptance
    assert "测试评审闭环验证" in test_acceptance
    assert "验收候选已准备" in test_acceptance
    assert "TEST-REVIEW.md" in test_acceptance
    assert "TEST-REVIEW-DISPOSITION.md" in test_acceptance
    assert "TEST-CLOSURE-VERIFICATION.md" in test_acceptance
    assert "ACCEPTANCE-PRECHECK.md" in test_acceptance
    assert "ACCEPTANCE-PRECHECK-VERIFICATION.md" in test_acceptance
    assert "releases/V3.md" in test_acceptance
    assert "V3 已验证结果" in test_acceptance
    assert "python scripts\\run_v3_evaluation.py" in test_acceptance
    assert "python scripts\\run_v3_acceptance_smoke.py" in test_acceptance
    assert "12 passed" in test_acceptance
    assert "30 passed" in test_acceptance
    assert "93 passed" in test_acceptance
    assert "negative_false_positive=0" in test_acceptance
    assert "Redis Mock" in test_acceptance
    assert "高斯 Mock" in test_acceptance
    assert "NER pipeline" in test_acceptance
    assert "browser_evidence_fresh=false" in test_acceptance
    assert "按 D072 不作为 V3 阻塞项" in test_acceptance
    assert "IR-FRONTEND-REMEDIATION.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-TEST-DESIGN.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md" in test_acceptance
    assert "FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md" in test_acceptance
    assert "IR-FRONTEND-VISUAL-REMEDIATION.md" in test_acceptance
    assert "SR-FRONTEND-VISUAL-REMEDIATION.md" in test_acceptance
    assert "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md" in test_acceptance
    assert (
        "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md"
        in test_acceptance
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md"
        in test_acceptance
    )
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md" in test_acceptance
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md" in test_acceptance
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md"
        in test_acceptance
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md"
        in test_acceptance
    )
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md" in test_acceptance
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md" in test_acceptance
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in test_acceptance
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in test_acceptance
    assert "FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md" in test_acceptance
    assert "V2 前端视觉风格补救验收前置核查已生成" in test_acceptance
    assert "TC-V2-FE-VIS-009" in test_acceptance
    assert "版本专用 Web demo 入口拒绝回归" in test_acceptance
    assert "FE-VIS-IMPL-001" in test_acceptance
    assert "FE-VIS-IMPL-003" in test_acceptance
    assert "browser_screenshot_images_valid=true" in test_acceptance
    assert "d003_scan_ok=true" in test_acceptance
    assert "FE-VIS-TEST-003/P2" in test_acceptance
    assert "visual_traceability_statuses=[\"implemented\",\"needs_user_decision\"]" in test_acceptance
    assert "visual_traceability_blocking_ac_ids=[\"AC-V2-FE-VIS-007\",\"AC-V2-FE-VIS-008\"]" in test_acceptance
    assert "视觉风格不足" in test_acceptance
    assert "Chrome CDP browser-equivalent evidence" in test_acceptance
    assert "traceability_ac_v2_fe_004_status=implemented" in test_acceptance
    assert "traceability_decision_d041_status=implemented" in test_acceptance
    assert "71 passed" in test_acceptance
    assert "77 passed" in test_acceptance
    assert "80 passed" in test_acceptance
    assert "V1验收完成" in decisions
    assert "文档治理采用精简结构" in decisions
    assert "V2 正式启动需求分析" in decisions
    assert "实体结构暂不升级" in decisions
    assert "运行时接口 Mock 独立成 SR" in decisions
    assert "KPI 类实体不再笼统使用 `kpi_metric`" in decisions
    assert "新增 KPI/网元类实体的 `aliases` 默认都为空" in decisions
    assert "V2 IR 独立评审、处置和 no-context/sealed 闭环验证已完成" in decisions
    assert "V2 SR 功能设计初稿已形成" in decisions
    assert "V2 SR 功能设计评审闭环验证已完成，结论为 closed" in decisions
    assert "V2 初始代码实现已完成本地验证" in decisions
    assert "V2 初始代码实现独立评审处置已完成" in decisions
    assert "V2 初始代码实现评审 no-context/sealed 闭环验证已完成" in decisions
    assert "V2 测试设计与测试开发已完成" in decisions
    assert "V2 独立测试评审已完成且无 P0/P1" in decisions
    assert "V2 测试评审处置 no-context/sealed 闭环验证已完成" in decisions
    assert "V2 进入验收阶段" in decisions
    assert "Web demo 启动脚本简化为只维护 `scripts\\run_web_demo.py`" in decisions
    assert "排除前述第 1 项和第 3 项" in decisions
    assert "V2 验收候选撤回并标记为 blocked" in decisions
    assert "V2 前端改造补救重新进入 DV 流程" in decisions
    assert "V2 前端补救 no-context 独立需求评审已完成" in decisions
    assert "V2 前端补救需求评审闭环验证已通过" in decisions
    assert "V2 前端补救功能设计草稿" in decisions
    assert "V2 前端补救独立功能设计评审已完成" in decisions
    assert "V2 前端补救功能设计评审闭环验证已通过" in decisions
    assert "V2 前端补救代码实现已完成" in decisions
    assert "V2 前端补救独立实现评审已完成" in decisions
    assert "AC-V2-FE-004" in decisions
    assert "V2 前端补救实现评审闭环验证已通过" in decisions
    assert "V2 前端补救测试设计与测试开发已完成" in decisions
    assert "V2 前端补救独立测试评审已完成" in decisions
    assert "unsafe attributes 负例" in decisions
    assert "V2 前端补救测试评审闭环验证已通过" in decisions
    assert "验收候选前反向核查" in decisions
    assert "D041 未进入 traceability artifact" in decisions
    assert "V2 前端补救验收候选前反向核查独立核验已通过" in decisions
    assert "补救后验收候选已准备" in decisions
    assert "D058" in decisions
    assert "V2 前端视觉风格补救 DV 流程" in decisions
    assert "IR-FRONTEND-VISUAL-REMEDIATION.md" in decisions
    assert "D059" in decisions
    assert "visual traceability artifact schema" in decisions
    assert "D060" in decisions
    assert "closed with recorded residual risk" in decisions
    assert "D061" in decisions
    assert "V2 前端视觉风格补救功能设计草稿" in decisions
    assert "D062" in decisions
    assert "V2 前端视觉风格补救功能设计 no-context 独立评审已完成" in decisions
    assert "D063" in decisions
    assert "V2 前端视觉风格补救功能设计评审闭环验证已通过" in decisions
    assert "D064" in decisions
    assert "V2 前端视觉风格补救代码实现已完成" in decisions
    assert "D065" in decisions
    assert "V2 前端视觉风格补救独立实现评审已完成" in decisions
    assert "browser_screenshot_images_valid=true" in decisions
    assert "D066" in decisions
    assert "V2 前端视觉风格补救实现评审 no-context 独立闭环验证已通过" in decisions
    assert "implementation review findings closed with recorded residual acceptance gates" in decisions
    assert "D067" in decisions
    assert "V2 前端视觉风格补救测试设计/开发已完成" in decisions
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md" in decisions
    assert "D068" in decisions
    assert "V2 前端视觉风格补救 no-context 独立测试评审已完成" in decisions
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md" in decisions
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in decisions
    assert "D069" in decisions
    assert "V2 前端视觉风格补救测试评审 no-context 独立闭环验证已通过" in decisions
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in decisions
    assert "test review findings closed with recorded residual acceptance gates" in decisions
    assert "17 passed" in decisions
    assert "D070" in decisions
    assert "V2 前端视觉风格补救验收前置核查已生成" in decisions
    assert "FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md" in decisions
    assert "v2_visual_acceptance_after_desktop_1366x768.png" in decisions
    assert "v2_visual_acceptance_after_narrow_390x844.png" in decisions
    assert "hasHorizontalOverflow=false" in decisions
    assert "d003_scan_ok=true" in decisions
    assert "manual_user_acceptance_status=pending" in decisions
    assert "AC-V2-FE-VIS-007" in decisions
    assert "D071" in decisions
    assert "当前 after 视觉可以 accepted" in decisions
    assert "manual_user_acceptance_status=accepted" in decisions
    assert "`AC-V2-FE-VIS-008` 继续 blocking" in decisions
    assert "D072" in decisions
    assert "搁置 V2 遗留问题，进入 V3" in decisions
    assert "D073" in decisions
    assert "两层存储" in decisions
    assert "D074" in decisions
    assert "key 是实体词，value 是实体 ID" in decisions
    assert "D075" in decisions
    assert "NER 部分需要详细设计" in decisions
    assert "D076" in decisions
    assert "V3 启动时只进入需求分析草稿阶段" in decisions
    assert "D077" in decisions
    assert "V3 GUI 决策确认已完成" in decisions
    assert "冲突数据加载 fail-closed" in decisions
    assert "canonical_name" in decisions
    assert "D078" in decisions
    assert "V3 需求评审、评审处置和闭环验证已完成" in decisions
    assert "D079" in decisions
    assert "V3 SR 功能设计草稿已形成" in decisions
    assert "D080" in decisions
    assert "V3 SR 功能设计评审已完成" in decisions
    assert "D081" in decisions
    assert "V3 SR 功能设计评审闭环验证已完成" in decisions
    assert "V3-SR.2-closed" in decisions
    assert "D082" in decisions
    assert "V3 初始代码实现已完成" in decisions
    assert "IMPLEMENTATION.md" in decisions
    assert "D083" in decisions
    assert "V3 初始代码实现评审和处置已完成" in decisions
    assert "IMPLEMENTATION-REVIEW.md" in decisions
    assert "IMPLEMENTATION-REVIEW-DISPOSITION.md" in decisions
    assert "90 passed" in decisions
    assert "D084" in decisions
    assert "V3 初始代码实现评审闭环验证已完成" in decisions
    assert "IMPLEMENTATION-CLOSURE-VERIFICATION.md" in decisions
    assert "D085" in decisions
    assert "V3 测试设计与测试开发已完成" in decisions
    assert "TEST-DESIGN.md" in decisions
    assert "D086" in decisions
    assert "V3 测试评审和处置已完成" in decisions
    assert "TEST-REVIEW.md" in decisions
    assert "TEST-REVIEW-DISPOSITION.md" in decisions
    assert "V3-TEST-REVIEW-001/P1" in decisions
    assert "V3-TEST-REVIEW-002/P2" in decisions
    assert "93 passed" in decisions
    assert "D087" in decisions
    assert "V3 测试评审闭环验证已完成" in decisions
    assert "TEST-CLOSURE-VERIFICATION.md" in decisions
    assert "验收候选前置准备" in decisions
    assert "D088" in decisions
    assert "V3 验收候选前置核查和核验已完成" in decisions
    assert "ACCEPTANCE-PRECHECK.md" in decisions
    assert "ACCEPTANCE-PRECHECK-VERIFICATION.md" in decisions
    assert "browser_evidence_fresh=false" in decisions
    assert "D089" in decisions
    assert "V3 验收候选记录已准备" in decisions
    assert "Acceptance candidate prepared; pending user acceptance; not accepted/closed" in decisions
    assert "V2 前端补救代码实现" in decisions
    assert "IR 必须完成需求分解" in dv_process
    assert "用户确认需求追踪矩阵" in dv_process
    assert "静默降级禁止" in dv_process
    assert "验收候选前反向核查" in dv_process
    assert "docs/baselines/<version>/IR.md" in dv_process
    assert "V1 alarm-only 自动化测试" in test_root_readme
    assert "V1 已通过用户验收并关闭" in test_root_readme
    assert "V3 验收候选已准备" in test_root_readme
    assert "Gauss duplicate/missing field fail-closed" in test_root_readme
    assert "93 passed" in test_root_readme
    assert "scripts\\run_web_demo.py" in usage
    assert "当前默认加载 V2 样例" in usage
    assert "run_web_demo.py --storage-mode v3_mock" in usage
    assert "scripts\\run_v3_acceptance_smoke.py" in usage
    assert "scripts\\run_v3_evaluation.py" in usage
    assert "samples\\real\\v2_entity_examples.json" in usage
    assert "scripts\\run_v2_acceptance_smoke.py" in usage
    assert "scripts\\run_v2_evaluation.py" in usage
    assert "scripts\\run_v1_web_demo.py" not in usage
    assert "outputs/logs/" in usage
    assert "DigitalView-SW DVEntityLinking V0 需求分析文档" in v0_ir
    assert "DVEntityLinking V0 功能设计说明书" in v0_sr
    assert "DigitalView-SW DVEntityLinking V1 需求分析文档" in v1_ir
    assert "Web demo 支持切换和配置 LLM 模式" in v1_ir
    assert "准确率和召回率同等重要" in v1_ir
    assert "SR-V1-A01" in v1_sr_decomposition
    assert "SR-V1-A08" in v1_sr_decomposition
    assert "precision = TP / (TP + FP)" in v1_sr_decomposition
    assert "fail-closed" in v1_sr_decomposition
    assert "DVEntityLinking V1 功能设计说明书" in v1_sr
    assert "V1.3" in v1_sr
    assert "ModeRequest" in v1_sr
    assert "alarm_index.py" in v1_sr
    assert "DigitalView-SW DVEntityLinking V2 需求分析文档" in v2_ir
    assert "实体字段结构暂不升级" in v2_ir
    assert "`kpi_task_name`" in v2_ir
    assert "`ne_type`" in v2_ir
    assert "别名只能特殊标注并经确认" in v2_ir
    assert "数据预处理作为统一入口" in v2_ir
    assert "运行时接口 Mock 独立 SR" in v2_ir
    assert "方案 C" in v2_ir
    assert "DigitalView-SW DVEntityLinking V3 需求分析文档" in v3_ir
    assert "Redis 接口 Mock" in v3_ir
    assert "高斯数据库接口 Mock" in v3_ir
    assert "NER 是 V3 重中之重" in v3_ir
    assert "V3-HD-001" in v3_ir
    assert "Confirmed" in v3_ir
    assert "V3.1-draft" in v3_ir
    assert "SR-V3-A05" in v3_ir
    assert "DigitalView-SW DVEntityLinking V3 功能设计说明书" in v3_sr
    assert "V3-SR.2-closed" in v3_sr
    assert "功能设计评审闭环已通过，可作为代码实现输入" in v3_sr
    assert "EntityWordCache" in v3_sr
    assert "StructuredEntityStore" in v3_sr
    assert "NerPipeline" in v3_sr
    assert "TC-V3-NER-003" in v3_sr
    assert "DigitalView-SW DVEntityLinking V3 SR 分解需求分析" in v3_sr_decomposition
    assert "SR-V3-A01" in v3_sr_decomposition
    assert "SR-V3-A06" in v3_sr_decomposition
    assert "NER pipeline 详细设计和重构策略" in v3_sr_decomposition
    assert "V3.1-addendum-draft" in v3_sr_decomposition
    assert "Human Decision Gate 确认结果" in v3_sr_decomposition
    assert "复用 V1/V2 样例" in v3_sr_decomposition
    assert "DVEntityLinking V3 独立需求评审记录" in v3_requirement_review
    assert "V3-REQ-REVIEW-001" in v3_requirement_review
    assert "Ready for disposition with findings" in v3_requirement_review
    assert "DVEntityLinking V3 需求评审处置记录" in v3_requirement_review_disposition
    assert "Accepted" in v3_requirement_review_disposition
    assert "ready for independent closure verification" in v3_requirement_review_disposition
    assert "DVEntityLinking V3 需求评审闭环验证记录" in v3_requirement_closure
    assert "Closed with recorded residual risk" in v3_requirement_closure
    assert "可进入 V3 功能设计阶段" in v3_requirement_closure
    assert "DVEntityLinking V3 功能设计评审记录" in v3_function_design_review
    assert "V3-SR-REVIEW-001" in v3_function_design_review
    assert "Ready for disposition with P3 documentation finding" in v3_function_design_review
    assert "DVEntityLinking V3 功能设计评审处置记录" in v3_function_design_disposition
    assert "function design review disposition completed" in v3_function_design_disposition
    assert "V3-SR-REVIEW-001" in v3_function_design_disposition
    assert "DVEntityLinking V3 功能设计评审闭环验证记录" in v3_function_design_closure
    assert "Closed" in v3_function_design_closure
    assert "可进入 V3 代码实现阶段" in v3_function_design_closure
    assert "DVEntityLinking V3 初始代码实现记录" in v3_implementation
    assert "V3-IMPL.1" in v3_implementation
    assert "RedisEntityWordCacheMock" in v3_implementation
    assert "GaussEntityStoreMock" in v3_implementation
    assert "NerPipeline" in v3_implementation
    assert "run_v3_evaluation.py" in v3_implementation
    assert "run_v3_acceptance_smoke.py" in v3_implementation
    assert "90 passed" in v3_implementation
    assert "实现评审闭环已通过，可进入测试设计/开发" in v3_implementation
    assert "IMPLEMENTATION-REVIEW.md" in v3_implementation
    assert "IMPLEMENTATION-REVIEW-DISPOSITION.md" in v3_implementation
    assert "IMPLEMENTATION-CLOSURE-VERIFICATION.md" in v3_implementation
    assert "DVEntityLinking V3 初始代码实现评审记录" in v3_implementation_review
    assert "V3-IMPL-REVIEW-001" in v3_implementation_review
    assert "V3-IMPL-REVIEW-002" in v3_implementation_review
    assert "Ready for disposition with one P2 and one P3 finding" in v3_implementation_review
    assert "DVEntityLinking V3 初始代码实现评审处置记录" in v3_implementation_disposition
    assert "implementation review disposition completed" in v3_implementation_disposition
    assert "V3-IMPL-REVIEW-001" in v3_implementation_disposition
    assert "V3-IMPL-REVIEW-002" in v3_implementation_disposition
    assert "90 passed" in v3_implementation_disposition
    assert "DVEntityLinking V3 初始代码实现评审闭环验证记录" in v3_implementation_closure
    assert "V3-IMPL-REVIEW-001/P2" in v3_implementation_closure
    assert "V3-IMPL-REVIEW-002/P3" in v3_implementation_closure
    assert "Closed with recorded residual future-work risks" in v3_implementation_closure
    assert "可进入 V3 测试设计/开发阶段" in v3_implementation_closure
    assert "DVEntityLinking V3 测试设计与测试开发记录" in v3_test_design
    assert "V3-TEST.1" in v3_test_design
    assert "TC-V3-STORAGE-001" in v3_test_design
    assert "TC-V3-STORAGE-002" in v3_test_design
    assert "TC-V3-STORAGE-003" in v3_test_design
    assert "TC-V3-NER-003" in v3_test_design
    assert "TC-V3-NER-004" in v3_test_design
    assert "TC-V3-REG-001" in v3_test_design
    assert "test_v3_gauss_duplicate_entity_id_fails_closed" in v3_test_design
    assert "test_v3_gauss_missing_required_field_fails_closed" in v3_test_design
    assert "test_v3_ner_pipeline_blank_query_is_invalid_input" in v3_test_design
    assert "12 passed" in v3_test_design
    assert "30 passed" in v3_test_design
    assert "93 passed" in v3_test_design
    assert "测试评审闭环验证已通过，可进入验收候选前置准备" in v3_test_design
    assert "TEST-CLOSURE-VERIFICATION.md" in v3_test_design
    assert "DVEntityLinking V3 测试设计与测试开发评审记录" in v3_test_review
    assert "V3-TEST-REVIEW-001" in v3_test_review
    assert "V3-TEST-REVIEW-002" in v3_test_review
    assert "Ready for disposition with one P1 and one P2 finding" in v3_test_review
    assert "DVEntityLinking V3 测试评审处置记录" in v3_test_disposition
    assert "test review disposition completed; independent closure verification passed" in v3_test_disposition
    assert "TEST-CLOSURE-VERIFICATION.md" in v3_test_disposition
    assert "V3-TEST-REVIEW-001" in v3_test_disposition
    assert "V3-TEST-REVIEW-002" in v3_test_disposition
    assert "12 passed" in v3_test_disposition
    assert "30 passed" in v3_test_disposition
    assert "93 passed" in v3_test_disposition
    assert "DVEntityLinking V3 测试评审闭环验证记录" in v3_test_closure
    assert "V3-TEST-REVIEW-001/P1" in v3_test_closure
    assert "V3-TEST-REVIEW-002/P2" in v3_test_closure
    assert "Closed" in v3_test_closure
    assert "test review findings closed with recorded future-work risks" in v3_test_closure
    assert "12 passed" in v3_test_closure
    assert "30 passed" in v3_test_closure
    assert "93 passed" in v3_test_closure
    assert "验收候选前置准备" in v3_test_closure
    assert "DVEntityLinking V3 验收候选前置核查记录" in v3_acceptance_precheck
    assert "acceptance precheck passed" in v3_acceptance_precheck
    assert "AC-V3-001" in v3_acceptance_precheck
    assert "AC-V3-011" in v3_acceptance_precheck
    assert "browser_evidence_fresh=false" in v3_acceptance_precheck
    assert "按 D072 不作为 V3 阻塞项" in v3_acceptance_precheck
    assert "DVEntityLinking V3 验收候选前置核查独立核验记录" in v3_acceptance_precheck_verification
    assert "passed; V3 acceptance candidate can be prepared" in v3_acceptance_precheck_verification
    assert "D073" in v3_acceptance_precheck_verification
    assert "D077" in v3_acceptance_precheck_verification
    assert "未发现" in v3_acceptance_precheck_verification
    assert "DVEntityLinking V3 Acceptance Candidate Record" in v3_release
    assert "Acceptance candidate prepared; pending user acceptance; not accepted/closed" in v3_release
    assert "AC-V3-001" in v3_release
    assert "AC-V3-011" in v3_release
    assert "Redis Mock" in v3_release
    assert "Gauss Mock" in v3_release
    assert "storage-backed NER pipeline" in v3_release
    assert "python scripts\\run_v3_evaluation.py" in v3_release
    assert "python scripts\\run_v3_acceptance_smoke.py" in v3_release
    assert "browser_evidence_fresh=false" in v3_release
    assert "accepted with recorded residual risk and closed" in v3_release
    assert v3_confirmation["schema_version"] == "v3.decision_confirmation.1"
    assert v3_confirmation["signoff_name"] == "SL"
    assert "确认以上 V3 决策" in v3_confirmation["signoff_decision"]
    assert "DVEntityLinking V2 前端改造补救需求分析文档" in v2_frontend_ir
    assert "用户确认需求追踪矩阵" in v2_frontend_ir
    assert "静默降级" in v2_frontend_ir
    assert "SR-V2-FE-A06" in v2_frontend_ir
    assert "V2-FE.2-closed" in v2_frontend_ir
    assert "LLM 交互式安全解释" in v2_frontend_ir
    assert "AC-V2-FE-008" in v2_frontend_ir
    assert "1366x768" in v2_frontend_ir
    assert "390x844" in v2_frontend_ir
    assert "需求评审闭环已通过，可作为功能设计输入" in v2_frontend_ir
    assert "DVEntityLinking V2 前端视觉风格补救需求分析文档" in v2_frontend_visual_ir
    assert "原型吸收矩阵" in v2_frontend_visual_ir
    assert "SigNoz" in v2_frontend_visual_ir
    assert "OpenGenerativeUI" in v2_frontend_visual_ir
    assert "Tambo" in v2_frontend_visual_ir
    assert "AC-V2-FE-VIS-007" in v2_frontend_visual_ir
    assert "AC-V2-FE-VIS-008" in v2_frontend_visual_ir
    assert "AC-V2-FE-VIS-009" in v2_frontend_visual_ir
    assert "before/after" in v2_frontend_visual_ir
    assert "Forbidden weak proof" in v2_frontend_visual_ir
    assert "Visual traceability artifact 最小 schema" in v2_frontend_visual_ir
    assert "same_viewport_and_query" in v2_frontend_visual_ir
    assert "D003 安全边界" in v2_frontend_visual_ir
    assert "SR-V2-FE-VIS-A06" in v2_frontend_visual_ir
    assert "captured on 2026-06-02" in v2_frontend_visual_ir
    assert "V2-FE-VIS.2-closed" in v2_frontend_visual_ir
    assert "需求评审闭环已通过，可作为功能设计输入" in v2_frontend_visual_ir
    assert "进入代码实现、验收候选或版本关闭仍需后续 DV 门禁" in v2_frontend_visual_ir
    assert "DVEntityLinking V2 前端视觉风格补救功能设计说明书" in v2_frontend_visual_sr
    assert "V2-FE-VIS-SR.2-closed" in v2_frontend_visual_sr
    assert "功能设计评审闭环已通过，可作为代码实现输入" in v2_frontend_visual_sr
    assert "visual-workbench-shell" in v2_frontend_visual_sr
    assert "status-band" in v2_frontend_visual_sr
    assert "query-command-zone" in v2_frontend_visual_sr
    assert "result-stream" in v2_frontend_visual_sr
    assert "llm-explanation-component" in v2_frontend_visual_sr
    assert "VisualWorkbenchState" in v2_frontend_visual_sr
    assert "LinkResultVisualAdapter" in v2_frontend_visual_sr
    assert "mention_results[].mention.text" in v2_frontend_visual_sr
    assert "不得为了满足视觉设计新增与 `mention_results[]` 并行" in v2_frontend_visual_sr
    assert "v2.frontend_visual_traceability.1" in v2_frontend_visual_sr
    assert "items[].ac_ids" in v2_frontend_visual_sr
    assert "summary.blocking_ac_ids" in v2_frontend_visual_sr
    assert "d003_content_inventory[]" in v2_frontend_visual_sr
    assert "no_unconfirmed_real_dv_content" in v2_frontend_visual_sr
    assert "no_text_overlap_or_clipping_narrow" in v2_frontend_visual_sr
    assert "DowngradeClassification" in v2_frontend_visual_sr
    assert "weak_marker_only" in v2_frontend_visual_sr
    assert "api_only" in v2_frontend_visual_sr
    assert "no_visual_delta" in v2_frontend_visual_sr
    assert "Check ALM-51020 and CPU Usage." in v2_frontend_visual_sr
    assert "DV-KPI-MTK-001" in v2_frontend_visual_sr
    assert "AC-V2-FE-VIS-009" in v2_frontend_visual_sr
    assert "D003 真实 DV 内容和 Mock 边界保护" in v2_frontend_visual_sr
    assert "status=no_match" in v2_frontend_visual_sr
    assert "v2_frontend_traceability_check.json" in v2_frontend_visual_sr
    assert "v2_frontend_visual_traceability_check.json" in v2_frontend_visual_sr
    assert "进入验收候选或 accepted/closed 仍需后续实现、测试、评审、视觉证据和用户验收门禁" in v2_frontend_visual_sr
    assert "DVEntityLinking V2 前端视觉风格补救功能设计独立评审记录" in v2_frontend_visual_design_review
    assert "FE-VIS-SR-001" in v2_frontend_visual_design_review
    assert "FE-VIS-SR-006" in v2_frontend_visual_design_review
    assert "Ready for disposition" in v2_frontend_visual_design_review
    assert (
        "DVEntityLinking V2 前端视觉风格补救功能设计评审处置记录"
        in v2_frontend_visual_design_disposition
    )
    assert "接受全部 3 个 P1 和 3 个 P2" in v2_frontend_visual_design_disposition
    assert "V2-FE-VIS-SR.1-draft" in v2_frontend_visual_design_disposition
    assert "mention_results[]" in v2_frontend_visual_design_disposition
    assert "d003_content_inventory[]" in v2_frontend_visual_design_disposition
    assert "待独立闭环验证" in v2_frontend_visual_design_disposition
    assert (
        "DVEntityLinking V2 前端视觉风格补救功能设计评审闭环验证记录"
        in v2_frontend_visual_design_closure
    )
    assert "FE-VIS-SR-001" in v2_frontend_visual_design_closure
    assert "FE-VIS-SR-006" in v2_frontend_visual_design_closure
    assert "Closed with recorded residual risk" in v2_frontend_visual_design_closure
    assert "可作为代码实现输入" in v2_frontend_visual_design_closure
    assert "DVEntityLinking V2 前端视觉风格补救需求独立评审记录" in v2_frontend_visual_review
    assert "FE-VIS-REQ-001" in v2_frontend_visual_review
    assert "FE-VIS-REQ-002" in v2_frontend_visual_review
    assert "Ready for disposition" in v2_frontend_visual_review
    assert "DVEntityLinking V2 前端视觉风格补救需求评审处置记录" in v2_frontend_visual_disposition
    assert "FE-VIS-REQ-001" in v2_frontend_visual_disposition
    assert "FE-VIS-REQ-002" in v2_frontend_visual_disposition
    assert "requirement review disposition completed" in v2_frontend_visual_disposition
    assert "DVEntityLinking V2 前端视觉风格补救需求评审闭环验证记录" in v2_frontend_visual_closure
    assert "FE-VIS-REQ-001" in v2_frontend_visual_closure
    assert "FE-VIS-REQ-005" in v2_frontend_visual_closure
    assert "Closed with recorded residual risk" in v2_frontend_visual_closure
    assert "允许进入 V2 前端视觉风格补救功能设计阶段" in v2_frontend_visual_closure
    assert "DVEntityLinking V2 前端视觉风格补救代码实现记录" in v2_frontend_visual_implementation
    assert "V2-FE-VIS-IMPL.2-closure-verified" in v2_frontend_visual_implementation
    assert "实现评审闭环已通过，待测试设计/开发" in v2_frontend_visual_implementation
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md" in v2_frontend_visual_implementation
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md"
        in v2_frontend_visual_implementation
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md"
        in v2_frontend_visual_implementation
    )
    assert "visual-workbench-shell" in v2_frontend_visual_implementation
    assert "status-band" in v2_frontend_visual_implementation
    assert "query-command-zone" in v2_frontend_visual_implementation
    assert "result-stream" in v2_frontend_visual_implementation
    assert "llm-explanation-component" in v2_frontend_visual_implementation
    assert "v2.frontend_visual_traceability.1" in v2_frontend_visual_implementation
    assert "manual_user_acceptance_status=pending" in v2_frontend_visual_implementation
    assert "visual_traceability_statuses=[\"implemented\",\"needs_user_decision\"]" in v2_frontend_visual_implementation
    assert "visual_traceability_blocking_ac_ids=[\"AC-V2-FE-VIS-007\",\"AC-V2-FE-VIS-008\"]" in v2_frontend_visual_implementation
    assert "no_text_overlap_or_clipping_narrow=true" in v2_frontend_visual_implementation
    assert "AC-V2-FE-VIS-007" in v2_frontend_visual_implementation
    assert "needs_user_decision" in v2_frontend_visual_implementation
    assert (
        "DVEntityLinking V2 前端视觉风格补救代码实现独立评审记录"
        in v2_frontend_visual_implementation_review
    )
    assert "Ready for disposition with findings" in v2_frontend_visual_implementation_review
    assert "FE-VIS-IMPL-001" in v2_frontend_visual_implementation_review
    assert "FE-VIS-IMPL-003" in v2_frontend_visual_implementation_review
    assert (
        "DVEntityLinking V2 前端视觉风格补救代码实现评审处置记录"
        in v2_frontend_visual_implementation_disposition
    )
    assert (
        "implementation review disposition completed; pending independent closure verification"
        in v2_frontend_visual_implementation_disposition
    )
    assert "FE-VIS-IMPL-001" in v2_frontend_visual_implementation_disposition
    assert "FE-VIS-IMPL-003" in v2_frontend_visual_implementation_disposition
    assert "browser_screenshot_images_valid=true" in v2_frontend_visual_implementation_disposition
    assert "6 passed" in v2_frontend_visual_implementation_disposition
    assert (
        "DVEntityLinking V2 前端视觉风格补救实现评审闭环验证记录"
        in v2_frontend_visual_implementation_closure
    )
    assert "no-context independent verifier Sagan" in v2_frontend_visual_implementation_closure
    assert "FE-VIS-IMPL-001" in v2_frontend_visual_implementation_closure
    assert "FE-VIS-IMPL-003" in v2_frontend_visual_implementation_closure
    assert "Closed" in v2_frontend_visual_implementation_closure
    assert "implementation review findings closed with recorded residual acceptance gates" in v2_frontend_visual_implementation_closure
    assert "manual_user_acceptance_status=pending" in v2_frontend_visual_implementation_closure
    assert "不是 `v2_frontend_browser_evidence.json` 原生字段" in v2_frontend_visual_implementation_closure
    assert "DVEntityLinking V2 前端视觉风格补救测试设计与测试开发记录" in v2_frontend_visual_test_design
    assert "test review closure verified" in v2_frontend_visual_test_design
    assert "TC-V2-FE-VIS-001" in v2_frontend_visual_test_design
    assert "TC-V2-FE-VIS-009" in v2_frontend_visual_test_design
    assert "test_v2_acceptance_smoke_rejects_non_image_browser_screenshots" in v2_frontend_visual_test_design
    assert "test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots" in v2_frontend_visual_test_design
    assert "test_v2_visual_d003_scan_flags_runtime_sensitive_values" in v2_frontend_visual_test_design
    assert "test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance" in v2_frontend_visual_test_design
    assert "test_v2_visual_smoke_rejects_versioned_web_demo_entries" in v2_frontend_visual_test_design
    assert "12 passed" in v2_frontend_visual_test_design
    assert "80 passed" in v2_frontend_visual_test_design
    assert "d003_scan_ok=true" in v2_frontend_visual_test_design
    assert "AC-V2-FE-VIS-007" in v2_frontend_visual_test_design
    assert "manual_user_acceptance_status=pending" in v2_frontend_visual_test_design
    assert "独立测试评审输入包" in v2_frontend_visual_test_design
    assert "DVEntityLinking V2 前端视觉风格补救测试独立评审记录" in v2_frontend_visual_test_review
    assert "FE-VIS-TEST-001" in v2_frontend_visual_test_review
    assert "FE-VIS-TEST-003" in v2_frontend_visual_test_review
    assert "ready for disposition" in v2_frontend_visual_test_review
    assert "DVEntityLinking V2 前端视觉风格补救测试评审处置记录" in v2_frontend_visual_test_disposition
    assert "test review disposition completed" in v2_frontend_visual_test_disposition
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in v2_frontend_visual_test_disposition
    assert "FE-VIS-TEST-001" in v2_frontend_visual_test_disposition
    assert "FE-VIS-TEST-003" in v2_frontend_visual_test_disposition
    assert "d003_scan_ok=true" in v2_frontend_visual_test_disposition
    assert "12 passed" in v2_frontend_visual_test_disposition
    assert "80 passed" in v2_frontend_visual_test_disposition
    assert (
        "DVEntityLinking V2 前端视觉风格补救测试评审闭环验证记录"
        in v2_frontend_visual_test_closure
    )
    assert "no-context independent verifier Carver" in v2_frontend_visual_test_closure
    assert "FE-VIS-TEST-001" in v2_frontend_visual_test_closure
    assert "FE-VIS-TEST-003" in v2_frontend_visual_test_closure
    assert "Closed" in v2_frontend_visual_test_closure
    assert "test review closure verified" in v2_frontend_visual_test_closure
    assert "17 passed" in v2_frontend_visual_test_closure
    assert "manual_user_acceptance_status=pending" in v2_frontend_visual_test_closure
    assert "AC-V2-FE-VIS-007" in v2_frontend_visual_test_closure
    assert (
        "DVEntityLinking V2 前端视觉风格补救验收前置核查记录"
        in v2_frontend_visual_acceptance_precheck
    )
    assert "acceptance precheck partially passed" in v2_frontend_visual_acceptance_precheck
    assert "scripts/run_web_demo.py" in v2_frontend_visual_acceptance_precheck
    assert "v2_visual_acceptance_after_desktop_1366x768.png" in v2_frontend_visual_acceptance_precheck
    assert "v2_visual_acceptance_after_narrow_390x844.png" in v2_frontend_visual_acceptance_precheck
    assert "hasHorizontalOverflow=false" in v2_frontend_visual_acceptance_precheck
    assert "before 同场景截图" in v2_frontend_visual_acceptance_precheck
    assert "manual_user_acceptance_status=accepted" in v2_frontend_visual_acceptance_precheck
    assert "visual_traceability_blocking_ac_ids=[\"AC-V2-FE-VIS-008\"]" in v2_frontend_visual_acceptance_precheck
    assert "`AC-V2-FE-VIS-007` 可关闭" in v2_frontend_visual_acceptance_precheck
    assert "AC-V2-FE-VIS-008" in v2_frontend_visual_acceptance_precheck
    assert "DVEntityLinking V2 前端改造补救需求评审处置记录" in v2_frontend_disposition
    assert "4 个 P1，3 个 P2" in v2_frontend_disposition
    assert "独立闭环验证已通过" in v2_frontend_disposition
    assert "DVEntityLinking V2 前端改造补救需求评审闭环验证记录" in v2_frontend_closure
    assert "Requirement review closure verified" in v2_frontend_closure
    assert "4 个 P1 和 3 个 P2 全部 Closed" in v2_frontend_closure
    assert "SR-V2-A01" in v2_sr_decomposition
    assert "数据预处理与实体目录统一管控" in v2_sr_decomposition
    assert "SR-V2-A02" in v2_sr_decomposition
    assert "运行时接口 Mock" in v2_sr_decomposition
    assert "LLM-based 抽取、分类、解释和 rerank" in v2_sr_decomposition
    assert "explicit alias annotation rule" in v2_sr_decomposition
    assert "DVEntityLinking V2 功能设计说明书" in v2_sr
    assert "RuntimeEntitySource" in v2_sr
    assert "MultiMentionLinker" in v2_sr
    assert "Query 级 `partial`" in v2_sr
    assert "V2.2" in v2_sr
    assert "功能设计评审闭环已通过，可作为代码实现输入" in v2_sr
    assert "DVEntityLinking V2 前端改造补救功能设计说明书" in v2_frontend_sr
    assert "V2-FE-SR.2-closed" in v2_frontend_sr
    assert "SR-V2-FE-D05" in v2_frontend_sr
    assert "TC-V2-FE-WEB-007" in v2_frontend_sr
    assert "TC-V2-FE-WEB-010" in v2_frontend_sr
    assert "TC-V2-FE-WEB-011" in v2_frontend_sr
    assert "TC-V2-FE-WEB-012" in v2_frontend_sr
    assert "AC-V2-FE-008" in v2_frontend_sr
    assert "llm_explanations[]" in v2_frontend_sr
    assert "attributes_safe[]" in v2_frontend_sr
    assert "v2_frontend_traceability_check.json" in v2_frontend_sr
    assert "功能设计评审闭环已通过，可作为代码实现输入" in v2_frontend_sr
    assert "DVEntityLinking V2 前端改造补救功能设计独立评审记录" in v2_frontend_design_review
    assert "P1-FE-SR-001" in v2_frontend_design_review
    assert "Ready for disposition" in v2_frontend_design_review
    assert "DVEntityLinking V2 前端改造补救功能设计评审处置记录" in v2_frontend_design_disposition
    assert "4 个 P1，1 个 P2" in v2_frontend_design_disposition
    assert "独立闭环验证已通过" in v2_frontend_design_disposition
    assert "DVEntityLinking V2 前端改造补救功能设计评审闭环验证记录" in v2_frontend_design_closure
    assert "Closed with recorded residual risk" in v2_frontend_design_closure
    assert "允许进入 V2 前端补救代码实现阶段" in v2_frontend_design_closure
    assert "DVEntityLinking V2 前端改造补救代码实现记录" in v2_frontend_implementation
    assert "implementation review disposition completed" in v2_frontend_implementation
    assert "second_mention_selected" in v2_frontend_implementation
    assert "card_text_readable" in v2_frontend_implementation
    assert "DV-KPI-MTK-001" in v2_frontend_implementation
    assert "traceability_ac_v2_fe_004_status=implemented" in v2_frontend_implementation
    assert "browser_evidence_fresh=true" in v2_frontend_implementation
    assert "DVEntityLinking V2 前端改造补救实现独立评审记录" in v2_frontend_implementation_review
    assert "P1" in v2_frontend_implementation_review
    assert "AC-V2-FE-004" in v2_frontend_implementation_review
    assert "DVEntityLinking V2 前端改造补救实现评审处置记录" in v2_frontend_implementation_disposition
    assert "FE-IMPL-001" in v2_frontend_implementation_disposition
    assert "FE-IMPL-002" in v2_frontend_implementation_disposition
    assert "待独立闭环验证" in v2_frontend_implementation_disposition
    assert "DVEntityLinking V2 前端改造补救实现评审闭环验证记录" in v2_frontend_implementation_closure
    assert "closed with recorded residual risk" in v2_frontend_implementation_closure
    assert "FE-IMPL-001" in v2_frontend_implementation_closure
    assert "FE-IMPL-002" in v2_frontend_implementation_closure
    assert "DVEntityLinking V2 前端改造补救测试设计与测试开发记录" in v2_frontend_test_design
    assert "test review closure verified" in v2_frontend_test_design
    assert "test_web_entity_detail_omits_forbidden_attributes_and_values" in v2_frontend_test_design
    assert "TC-V2-FE-WEB-010" in v2_frontend_test_design
    assert "browser_evidence_fresh" in v2_frontend_test_design
    assert "FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in v2_frontend_test_design
    assert "DVEntityLinking V2 前端改造补救测试独立评审记录" in v2_frontend_test_review
    assert "1 个 P1" in v2_frontend_test_review
    assert "attributes_safe[]" in v2_frontend_test_review
    assert "DVEntityLinking V2 前端改造补救测试评审处置记录" in v2_frontend_test_disposition
    assert "FE-TEST-001" in v2_frontend_test_disposition
    assert "test_web_entity_detail_omits_forbidden_attributes_and_values" in v2_frontend_test_disposition
    assert "独立闭环验证已通过" in v2_frontend_test_disposition
    assert "DVEntityLinking V2 前端改造补救测试评审闭环验证记录" in v2_frontend_test_closure
    assert "FE-TEST-001" in v2_frontend_test_closure
    assert "Closed" in v2_frontend_test_closure
    assert "17 passed" in v2_frontend_test_closure
    assert "DVEntityLinking V2 前端改造补救验收候选前反向核查记录" in v2_frontend_acceptance_precheck
    assert "PRECHECK-001" in v2_frontend_acceptance_precheck
    assert "traceability_decision_d041_status=implemented" in v2_frontend_acceptance_precheck
    assert "D041" in v2_frontend_acceptance_precheck
    assert (
        "DVEntityLinking V2 前端改造补救验收前反向核查独立核验记录"
        in v2_frontend_acceptance_precheck_verification
    )
    assert "6 passed" in v2_frontend_acceptance_precheck_verification
    assert "可以进入 V2 补救后验收候选准备" in v2_frontend_acceptance_precheck_verification
    assert "DVEntityLinking V2 测试设计与测试开发记录" in v2_tc
    assert "TC-V2-EVAL-002" in v2_tc
    assert "TC-V2-XTYPE-001" in v2_tc
    assert "TC-V2-INDEX-001" in v2_tc
    assert "独立测试评审闭环已通过" in v2_tc
    assert "DVEntityLinking V2 测试评审处置记录" in v2_test_disposition
    assert "Closed with recorded residual risk" in v2_test_disposition
    assert "V0 accepted and closed" in v0_release
    assert "AF-001" in v0_release
    assert "AF-002" in v0_release
    assert "V1 accepted and closed" in v1_release
    assert "V1验收完成" in v1_release
    assert "AC-V1-008" in v1_release
    assert "59 passed" in v1_release
    assert "DVEntityLinking V2 Acceptance Candidate Record" in v2_release
    assert (
        "Frontend visual remediation acceptance precheck partially passed; after visual accepted, pending before same-scenario screenshot or replacement decision"
        in v2_release
    )
    assert "视觉风格原型吸收不足" in v2_release
    assert "IR-FRONTEND-REMEDIATION.md" in v2_release
    assert "IR-FRONTEND-VISUAL-REMEDIATION.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md" in v2_release
    assert "SR-FRONTEND-VISUAL-REMEDIATION.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md" in v2_release
    assert (
        "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md"
        in v2_release
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md"
        in v2_release
    )
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md" in v2_release
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md"
        in v2_release
    )
    assert (
        "FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md"
        in v2_release
    )
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in v2_release
    assert "FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md" in v2_release
    assert "FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md" in v2_release
    assert "FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md" in v2_release
    assert "SR-FRONTEND-REMEDIATION.md" in v2_release
    assert "FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md" in v2_release
    assert "FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md" in v2_release
    assert "FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md" in v2_release
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION.md" in v2_release
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW.md" in v2_release
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md" in v2_release
    assert "FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md" in v2_release
    assert "FRONTEND-REMEDIATION-TEST-DESIGN.md" in v2_release
    assert "FRONTEND-REMEDIATION-TEST-REVIEW.md" in v2_release
    assert "FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md" in v2_release
    assert "FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md" in v2_release
    assert "FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md" in v2_release
    assert "FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md" in v2_release
    assert "V2 前端视觉风格补救验收前置核查已生成" in v2_release
    assert "v2_visual_acceptance_after_desktop_1366x768.png" in v2_release
    assert "v2_visual_acceptance_after_narrow_390x844.png" in v2_release
    assert "d003_scan_ok=true" in v2_release
    assert "用户确认当前 after 视觉 `accepted`" in v2_release
    assert "visual_traceability_blocking_ac_ids=[\"AC-V2-FE-VIS-008\"]" in v2_release
    assert "`AC-V2-FE-VIS-007` 可关闭" in v2_release
    assert "`AC-V2-FE-VIS-008` 继续 blocking" in v2_release
    assert "traceability_decision_d041_status=implemented" in v2_release
    assert "12 passed" in v2_release
    assert "17 passed" in v2_release
    assert "80 passed" in v2_release
    assert "AC-V2-011" in v2_release
    assert "DVEntityLinking V3 Acceptance Candidate Record" in v3_release
    assert "docs/PROJECT_MEMORY.md" not in root_readme
    assert not (ROOT / "docs/PROJECT_MEMORY.md").exists()
    assert (ROOT / "docs/confirmations").exists()
    assert not (ROOT / "docs/requirements").exists()
    assert not (ROOT / "docs/design").exists()
    assert not (ROOT / "docs/implementation").exists()
    assert not (ROOT / "docs/tests").exists()
