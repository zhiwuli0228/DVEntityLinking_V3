# DVEntityLinking V3 初始代码实现评审记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| review_type | implementation review |
| review_object | V3 初始代码实现与 [IMPLEMENTATION.md](./IMPLEMENTATION.md) |
| baseline_documents | [SR.md](./SR.md) `V3-SR.2-closed`、[FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FUNCTION-DESIGN-CLOSURE-VERIFICATION.md)、[IMPLEMENTATION.md](./IMPLEMENTATION.md) |
| scope | Redis/Gauss Mock 两层存储、storage-backed NER pipeline、Web/API 安全投影、V3 artifacts、evaluation/smoke、focused tests、文档治理同步 |
| out_of_scope | 真实 Redis/GaussDB adapter、真实 DV 生产接口、生产级 LLM 分类/解释/rerank、V2 遗留视觉验收 |
| review_mode | main-agent sealed/read-only review；未使用 no-context subagent，因为当前工具规则要求只有用户明确要求代理/并行代理时才可 spawn sub-agent |
| conclusion | Ready for disposition with one P2 and one P3 finding |

## 2 Review Input Bundle

| 类别 | 文件 |
| --- | --- |
| Design baseline | [SR.md](./SR.md) |
| Design closure | [FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| Implementation record | [IMPLEMENTATION.md](./IMPLEMENTATION.md) |
| Storage implementation | [../../../src/dv_entity_linking/storage.py](../../../src/dv_entity_linking/storage.py) |
| NER implementation | [../../../src/dv_entity_linking/ner_pipeline.py](../../../src/dv_entity_linking/ner_pipeline.py) |
| Service integration | [../../../src/dv_entity_linking/service.py](../../../src/dv_entity_linking/service.py) |
| Web/API projection | [../../../src/dv_entity_linking/web.py](../../../src/dv_entity_linking/web.py) |
| Runtime scripts | [../../../scripts/demo_runtime.py](../../../scripts/demo_runtime.py)、[../../../scripts/run_web_demo.py](../../../scripts/run_web_demo.py)、[../../../scripts/run_v3_evaluation.py](../../../scripts/run_v3_evaluation.py)、[../../../scripts/run_v3_acceptance_smoke.py](../../../scripts/run_v3_acceptance_smoke.py) |
| V3 artifacts | [../../../samples/real/v3_gauss_entities.json](../../../samples/real/v3_gauss_entities.json)、[../../../samples/real/v3_redis_entity_words.json](../../../samples/real/v3_redis_entity_words.json)、[../../../samples/real/v3_ner_golden_cases.json](../../../samples/real/v3_ner_golden_cases.json) |
| Tests | [../../../tests/test_v3_storage_ner.py](../../../tests/test_v3_storage_ner.py)、[../../../tests/test_contract_artifacts.py](../../../tests/test_contract_artifacts.py)、[../../../tests/test_demo_scripts.py](../../../tests/test_demo_scripts.py) |

## 3 Findings

### P2

#### V3-IMPL-REVIEW-001 - V3 LLM-enabled mode status can overstate actual LLM usage

Issue -> V3 pipeline accepts `mode` and `allow_fallback`, but `NerPipeline.run()` remains deterministic and does not invoke the configured LLM client. `_build_mode_status()` computes `llm_used=True` whenever `mode=llm_enabled_demo` and an LLM client exists, even when V3 `stage_trace` contains no LLM stage.

Current artifact behavior -> `EntityLinkingService.from_v3_mock()` can be combined with an LLM client through `scripts/run_web_demo.py --storage-mode v3_mock --mode llm_enabled_demo --llm-config ...`; in that path, Web/API status may claim LLM usage although the V3 path only used storage-backed deterministic NER.

Impact -> Default offline V3 acceptance is not blocked, but LLM-enabled demo telemetry becomes misleading and can weaken later comparison between deterministic V3 NER and future LLM classification/explanation/rerank.

Recommended correction -> Derive `llm_used` from actual stage trace or explicit result metadata when `stage_trace` is present. For current V3, no `llm` stage means `llm_used=false` and stage statuses should remain storage/deterministic. Add a focused regression test for V3 `llm_enabled_demo` projection with a dummy configured client or direct mode-status construction.

### P3

#### V3-IMPL-REVIEW-002 - Redis metadata `key_scope` is documented and sampled but not enforced by loader

Issue -> V3 contract and sample metadata state `key_scope=["canonical_name","confirmed_aliases"]`, but `RedisEntityWordCacheMock.load()` does not validate the metadata `key_scope` field.

Current artifact behavior -> Record-level validation still enforces `source in {"canonical_name","confirmed_alias"}` and checks the word against the referenced Gauss entity, so unsafe words do not enter the link path. However, a malformed Redis artifact with misleading `metadata.key_scope` can still load if each record itself is valid.

Impact -> Low runtime risk, but schema governance is weaker than the documented contract and can confuse future artifact producers.

Recommended correction -> Validate `metadata.key_scope` exactly as `["canonical_name","confirmed_aliases"]` and add a focused fail-closed test.

## 4 Perspective Summary

| Perspective | Review result |
| --- | --- |
| Main flow coverage | V3 startup, linked, partial, no_match and not_required paths are covered by tests and scripts. |
| Module responsibility | Storage validation, NER linking, service integration and Web projection are separated cleanly. |
| Schema and status semantics | Redis/Gauss schema checks and storage lookup statuses are mostly enforced; LLM-used projection needs correction for V3 LLM-enabled mode. |
| Structured errors | Duplicate Redis key, dangling Redis entity ID, schema mismatch and dependency failure use structured error/status values. |
| External dependency isolation | V3 defaults to local JSON Mock artifacts and does not connect to real Redis, GaussDB, DV production API or real LLM by default. |
| Test coverage | Focused tests and scripts cover default V3 implementation; add targeted tests for LLM usage projection and Redis metadata `key_scope`. |
| Documentation hygiene | V3 implementation docs, current data contract, test acceptance, samples/scripts README and governance tests are updated; one normalization label typo was fixed during review preparation. |

## 5 Verified Commands

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-v3 tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py` | 通过，`25 passed`。此前未提权运行失败原因是 pytest 临时目录删除被沙箱拒绝，不是测试断言失败。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`88 passed`。 |
| `python -m compileall -q src scripts` | 通过。 |
| `python scripts\run_v3_evaluation.py` | 通过，`total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0`。 |
| `python scripts\run_v3_acceptance_smoke.py` | 通过，`ok=true`、`entity_count=7`、`linked_storage_redis_statuses=["hit","hit"]`、`partial_status=partial`。 |
| `git diff --check` | 通过；仅输出 LF-to-CRLF 工作区警告。 |

## 6 Recommended Closure Actions

| Finding | Closure action |
| --- | --- |
| V3-IMPL-REVIEW-001 | 修正 V3 LLM-enabled mode 的 `llm_used` 投影语义，并补测试。 |
| V3-IMPL-REVIEW-002 | 强校验 Redis metadata `key_scope`，并补 fail-closed 测试。 |

## 7 Disposition Readiness

本实现评审发现 1 个 P2 和 1 个 P3。无 P0/P1；默认离线 V3 初始实现可继续处置并复验。完成处置和独立闭环验证前，不进入 V3 验收候选或 accepted/closed。
