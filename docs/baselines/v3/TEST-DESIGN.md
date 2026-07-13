# DVEntityLinking V3 测试设计与测试开发记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| test_design_version | V3-TEST.1 |
| test_object | V3 Redis/Gauss Mock 两层存储与 storage-backed NER pipeline |
| requirement_baseline | [IR.md](./IR.md)、[IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md) |
| design_baseline | [SR.md](./SR.md) `V3-SR.2-closed` |
| implementation_baseline | [IMPLEMENTATION.md](./IMPLEMENTATION.md)、[IMPLEMENTATION-CLOSURE-VERIFICATION.md](./IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| mode | test plan + automation evidence |
| status | 测试评审闭环验证已通过，可进入验收候选前置准备 |

## 2 Test Positioning and Boundaries

| Layer | Boundary | Current assets |
| --- | --- | --- |
| Independent contract/document tests | 验证 V3 docs、sample artifacts、脚本入口和安全边界，不证明运行时执行。 | `tests/test_contract_artifacts.py` |
| Implementation-level integration tests | 调用 storage、NER pipeline、service 和 Web/API，验证真实模块行为。 | `tests/test_v3_storage_ner.py` |
| Script/evaluation tests | 运行 V3 evaluation 和 smoke 脚本，验证命令行入口与 JSON summary。 | `scripts/run_v3_evaluation.py`、`scripts/run_v3_acceptance_smoke.py`、`tests/test_v3_storage_ner.py` |
| Regression tests | 防止 V3 改造破坏 V1/V2、Web/API 和现有文档治理。 | `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` |

## 3 Scope and Out of Scope

In scope:

- Redis Mock entity-word KV schema、normalization、duplicate key、dangling ID、confirmed source 和 `key_scope` fail-closed。
- Gauss Mock minimal entity schema 和按 `entity_id` 查询。
- Cross-layer Redis hit -> Gauss hit、Redis miss、partial、no_match、not_required。
- NER pipeline stage trace、mention-level storage lookup、安全 Web/API projection。
- V3 `llm_enabled_demo` 在没有实际 `llm` stage 时不误报 `llm_used=true`。
- V3 golden cases evaluation、acceptance smoke、V1/V2 回归、文档治理和敏感信息边界。

Out of scope:

- 真实 Redis、真实 GaussDB、真实 DV 生产接口。
- 真实 LLM 分类、解释、rerank 的功能验收。
- V2 前端视觉 before 证据遗留项。
- 生产级性能、并发、可用性和部署验证。

## 4 Test Case Overview

| Test ID | Name | Acceptance item | Priority | Automation |
| --- | --- | --- | --- | --- |
| TC-V3-STORAGE-001 | Gauss/Redis 两层正常加载与 lookup | SR-V3-A01/A02/A03/A04 | P1 | `test_v3_storage_repository_loads_two_layers` |
| TC-V3-STORAGE-002 | Gauss duplicate entity ID fail-closed | SR-V3-A03/A04 | P1 | `test_v3_gauss_duplicate_entity_id_fails_closed` |
| TC-V3-STORAGE-003 | Gauss missing required field fail-closed | SR-V3-A03/A04 | P1 | `test_v3_gauss_missing_required_field_fails_closed` |
| TC-V3-STORAGE-004 | Redis duplicate normalized key 多实体冲突 fail-closed | SR-V3-A02/A04 | P1 | `test_v3_redis_duplicate_key_conflict_fails_closed` |
| TC-V3-STORAGE-005 | Redis dangling entity ID fail-closed | SR-V3-A02/A03/A04 | P1 | `test_v3_redis_dangling_entity_id_fails_closed` |
| TC-V3-STORAGE-006 | Redis metadata `key_scope` 异常 fail-closed | SR-V3-A02/A04 | P2 | `test_v3_redis_key_scope_metadata_fails_closed` |
| TC-V3-NER-001 | 多 mention linked 与 storage trace | SR-V3-A05 | P1 | `test_v3_ner_pipeline_links_and_exposes_storage_trace` |
| TC-V3-NER-002 | partial、no_match、not_required 状态语义 | SR-V3-A05 | P1 | `test_v3_ner_pipeline_partial_no_match_and_not_required` |
| TC-V3-NER-003 | blank query invalid-input query validation | SR-V3-A05 | P2 | `test_v3_ner_pipeline_blank_query_is_invalid_input` |
| TC-V3-NER-004 | Web/API storage-backed safe projection | SR-V3-A05/A06 | P1 | `test_v3_web_api_uses_storage_backed_projection` |
| TC-V3-NER-005 | V3 LLM-enabled mode 不误报 LLM usage | SR-V3-A05/A06 | P2 | `test_v3_web_api_does_not_claim_llm_used_without_llm_stage` |
| TC-V3-EVAL-001 | V3 golden cases precision/recall/negative FP | SR-V3-A06 | P1 | `run_v3_evaluation.py` and `test_v3_evaluation_and_smoke_scripts_run_offline` |
| TC-V3-SMOKE-001 | V3 acceptance smoke offline path | SR-V3-A06 | P1 | `run_v3_acceptance_smoke.py` and `test_v3_evaluation_and_smoke_scripts_run_offline` |
| TC-V3-DOC-001 | V3 artifacts/docs/scripts governance | D003、D077、SR-V3-A06 | P2 | `test_contract_v3_storage_and_ner_artifacts_are_mocked_and_consistent`、`test_contract_document_governance_is_compact_and_versioned` |
| TC-V3-REG-001 | V1/V2/Web/API full regression | Regression floor | P1 | `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` |

## 5 Test-to-Automation Mapping

| Artifact | Covered semantics |
| --- | --- |
| `tests/test_v3_storage_ner.py` | Two-layer storage loading, Gauss duplicate/missing field fail-closed, Redis conflict fail-closed, dangling ID fail-closed, key_scope fail-closed, NER linked/partial/no_match/not_required/invalid_input, Web/API projection, V3 script execution. |
| `tests/test_contract_artifacts.py` | V3 sample schema, confirmed key scope, sensitive data scan, script presence, no version-specific Web demo entry, V3 review/disposition/closure and test design navigation. |
| `tests/test_demo_scripts.py` | Single Web demo entry help exposes V3 storage mode and mock path flags while preserving V1/V2 script behavior. |
| `scripts/run_v3_evaluation.py` | Golden case scoring for 6 V3 queries, precision/recall, negative false positive and span/normalization checks. |
| `scripts/run_v3_acceptance_smoke.py` | API smoke for linked, partial, no_match, not_required, stage trace and Redis storage status. |

## 6 Key Case Details

### TC-V3-STORAGE-002/003 Gauss fail-closed

- 构造 duplicate `entity_id` 的 Gauss Mock artifact，期望加载阶段抛出 `StorageError` 且 error code 为 `duplicate_entity_id`。
- 构造缺失 `description` 的 Gauss Mock artifact，期望加载阶段抛出 `StorageError` 且 error code 为 `missing_required_field`。

### TC-V3-STORAGE-004 duplicate key conflict

- 构造两个 Gauss entity 共享 confirmed alias `Shared-Key`。
- Redis Mock 中同一 `normalized_key` 指向两个不同 entity ID。
- 期望：`EntityStorageRepository.load_from_paths()` 抛出 `StorageError`，error code 为 `duplicate_key`，不进入链接链路。

### TC-V3-NER-002 partial/no_match/not_required

- `Show CPU Usage for CloudHost-VM-1-1-000000.`：`CPU Usage` linked，未知 entity-shaped token no_match，Query 级 `partial`。
- `Open the operations dashboard.`：无 mention 且无实体链接必要，Query 级 `not_required`，不访问 storage。
- `Show metrics for UnknownApp-999.`：检测 entity-shaped token，Redis miss，Query 级 `no_match`。

### TC-V3-NER-003 blank query validation

- 输入空白 Query。
- 期望 Query 级 `invalid_input`，`error_code=invalid_input`，`stage_trace[0].stage=query_validation`。

### TC-V3-NER-005 LLM status projection

- 构造已配置 LLM client 的 V3 service，并以 `llm_enabled_demo` 请求 `/api/link`。
- 当前 V3 pipeline 无真实 LLM stage，期望 API 返回 `llm_enabled=true` 且 `llm_used=false`，避免误报。

## 7 Executable Commands and Evidence

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-v3 tests\test_v3_storage_ner.py` | 通过，`12 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-targeted tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py` | 通过，`30 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`93 passed`。 |
| `python -m compileall -q src scripts` | 通过。 |
| `python scripts\run_v3_evaluation.py` | 通过，`total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0`。 |
| `python scripts\run_v3_acceptance_smoke.py` | 通过，`ok=true`、`entity_count=7`、`linked_storage_redis_statuses=["hit","hit"]`、`partial_status=partial`。 |
| `git diff --check` | 通过；仅输出 LF-to-CRLF 工作区警告。 |

## 8 Review Input Package

测试评审与闭环记录：

- 本测试设计与测试开发记录。
- [TEST-REVIEW.md](./TEST-REVIEW.md)
- [TEST-REVIEW-DISPOSITION.md](./TEST-REVIEW-DISPOSITION.md)
- [TEST-CLOSURE-VERIFICATION.md](./TEST-CLOSURE-VERIFICATION.md)
- [SR.md](./SR.md)
- [IMPLEMENTATION.md](./IMPLEMENTATION.md)
- [IMPLEMENTATION-CLOSURE-VERIFICATION.md](./IMPLEMENTATION-CLOSURE-VERIFICATION.md)
- `tests/test_v3_storage_ner.py`
- `tests/test_contract_artifacts.py`
- `tests/test_demo_scripts.py`
- `scripts/run_v3_evaluation.py`
- `scripts/run_v3_acceptance_smoke.py`
- `samples/real/v3_gauss_entities.json`
- `samples/real/v3_redis_entity_words.json`
- `samples/real/v3_ner_golden_cases.json`

## 9 Residual Risks

| 风险 | 当前处理 |
| --- | --- |
| 真实 LLM V3 stage 未实现 | 明确为后续可选增强；当前测试只验证不误报 LLM usage。 |
| 真实 Redis/Gauss adapter 未实现 | 明确为后续真实接入范围；当前测试只覆盖 Mock contract 与 fail-closed。 |
| V3 初始样例规模较小 | 作为启动样例范围记录；后续扩容需继续通过 D003 和 confirmed alias 规则。 |

## 10 Conclusion

V3 测试设计与测试开发、测试评审、评审处置和闭环验证已完成；测试评审发现均已关闭。当前可进入 V3 验收候选前置准备；正式进入 V3 验收候选或 accepted/closed 仍需后续验收记录和用户确认。
