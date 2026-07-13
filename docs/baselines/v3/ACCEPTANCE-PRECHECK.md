# DVEntityLinking V3 验收候选前置核查记录

日期：2026-06-26

状态：acceptance precheck passed; ready for V3 acceptance candidate preparation。

## 目的

本记录执行 V3 验收候选前置核查：从用户确认项、V3 IR/SR、实现闭环、测试闭环和本地验证命令反向核查，确认 V3 两层存储和 NER 重构范围没有静默降级。

本记录不声明 V3 accepted，也不关闭 V3。

## 输入

| 类型 | 文件/证据 |
| --- | --- |
| 用户决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| V3 需求分析 | [IR.md](./IR.md)、[IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md) |
| V3 功能设计 | [SR.md](./SR.md) |
| V3 需求闭环 | [REQUIREMENT-CLOSURE-VERIFICATION.md](./REQUIREMENT-CLOSURE-VERIFICATION.md) |
| V3 功能设计闭环 | [FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| V3 实现闭环 | [IMPLEMENTATION-CLOSURE-VERIFICATION.md](./IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| V3 测试闭环 | [TEST-CLOSURE-VERIFICATION.md](./TEST-CLOSURE-VERIFICATION.md) |
| V3 Redis Mock artifact | `samples/real/v3_redis_entity_words.json` |
| V3 Gauss Mock artifact | `samples/real/v3_gauss_entities.json` |
| V3 NER golden cases | `samples/real/v3_ner_golden_cases.json` |
| V3 验证脚本 | `scripts/run_v3_evaluation.py`、`scripts/run_v3_acceptance_smoke.py` |

## 核查方法

- 反向核查 D073、D074、D075 和 D077 是否从 IR/SR 追踪到实现、测试和验收证据。
- 复查 Redis Mock 是否保持实体词 key 到单实体 ID value，且 duplicate key、dangling ID、`metadata.key_scope` 错误均 fail-closed。
- 复查 Gauss Mock 是否支持按实体 ID 查询结构化实体，且 duplicate ID、缺失必需字段和 schema 错误均 fail-closed。
- 复查 NER pipeline 是否覆盖 query validation、need-linking、mention detection、normalization、Redis lookup、Gauss lookup、candidate construction 和状态聚合。
- 复查默认离线 deterministic 路径不依赖真实 Redis、真实 GaussDB、真实 DV 生产接口或真实 LLM。
- 复跑 V1/V2/V3 evaluation、V1/V3 acceptance smoke、compileall 和全量 pytest；V2 acceptance smoke 当前仅作为 V2 legacy visual evidence 诊断项，不作为 V3 阻塞项。

## 验收核查清单

| ID | 验收项 | 结果 | 证据 |
| --- | --- | --- | --- |
| AC-V3-001 | Redis Mock artifact 可加载，`entity_word` 规范化到单实体 ID value | 通过 | `v3.redis_entity_words.1`、`test_contract_v3_storage_and_ner_artifacts_are_mocked_and_consistent` |
| AC-V3-002 | Redis key 仅来自 `canonical_name` + confirmed aliases，不自动生成别名 | 通过 | `metadata.key_scope=["canonical_name","confirmed_aliases"]`、`aliases_auto_generated=false` |
| AC-V3-003 | Redis duplicate key、dangling ID、key scope 错误均 fail-closed | 通过 | `tests/test_v3_storage_ner.py` |
| AC-V3-004 | Gauss Mock 支持按 entity ID 查询结构化实体 | 通过 | `GaussEntityStoreMock`、V3 smoke `entity_count=7` |
| AC-V3-005 | Gauss duplicate ID、缺失必需字段、schema 错误均 fail-closed | 通过 | `test_v3_gauss_duplicate_entity_id_fails_closed`、`test_v3_gauss_missing_required_field_fails_closed` |
| AC-V3-006 | NER pipeline 覆盖 linked、partial、no_match、not_required | 通过 | `python scripts\run_v3_evaluation.py`、`python scripts\run_v3_acceptance_smoke.py` |
| AC-V3-007 | blank query 返回 `invalid_input`，不进入误链接 | 通过 | `test_v3_ner_pipeline_blank_query_is_invalid_input` |
| AC-V3-008 | Web/API storage projection 暴露 storage trace，但不暴露敏感运行时配置 | 通过 | V3 smoke `linked_stage_names`、D003 文档和 contract tests |
| AC-V3-009 | 默认离线 deterministic，不依赖真实 LLM；无 `llm` stage 时不误报 `llm_used=true` | 通过 | V3 implementation review disposition 和 closure evidence |
| AC-V3-010 | V1/V2 技术回归不被 V3 改造破坏；V2 visual legacy evidence 仍按 D072 搁置 | 通过，带记录风险 | V1/V2/V3 evaluation；V2 smoke 当前 `browser_evidence_fresh=false` 为 V2 legacy visual evidence |
| AC-V3-011 | 不提交真实 Redis/Gauss 连接串、账号、密码、token、真实 DV payload 或完整 LLM 请求响应 | 通过 | contract artifact scan、D003 runtime scan |

## 命令和结果

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`93 passed in 15.52s` |
| `python -m compileall -q src scripts` | 通过 |
| `python scripts\run_v1_evaluation.py` | 通过，`total=16`、`pass=16`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0` |
| `python scripts\run_v1_acceptance_smoke.py --mode offline_demo` | 通过，`ok=true`、`entity_count=9`、`sample_count=16` |
| `python scripts\run_v2_evaluation.py` | 通过，`total=12`、`pass=12`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo` | V2 legacy visual evidence 诊断项：核心 API、D003 scan、截图文件结构校验均通过；因 `browser_evidence_fresh=false` 导致 `ok=false`，按 D072 不作为 V3 阻塞项 |
| `python scripts\run_v3_evaluation.py` | 通过，`total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0` |
| `python scripts\run_v3_acceptance_smoke.py` | 通过，`ok=true`、`entity_count=7`、`linked_storage_redis_statuses=["hit","hit"]`、`partial_status=partial` |

## 核查结论

V3 验收候选前置核查通过。当前未发现 V3 范围内的 downgraded、not implemented 或 needs user decision 项。真实 Redis/Gauss 适配器、真实 LLM 常态化、类型专属 Gauss 字段扩展仍属于后续工作，不是 V3 当前 mock/deterministic 验收阻塞项。

V2 前端视觉 before 证据遗留项继续按 D072 搁置，不作为 V3 验收候选准备阻塞；V2 本身仍不得标记为 accepted/closed。
