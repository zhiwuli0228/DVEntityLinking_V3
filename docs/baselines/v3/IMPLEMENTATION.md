# DVEntityLinking V3 初始代码实现记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| implementation_version | V3-IMPL.1 |
| implementation_basis | [SR.md](./SR.md) `V3-SR.2-closed` |
| requirement_closure | [REQUIREMENT-CLOSURE-VERIFICATION.md](./REQUIREMENT-CLOSURE-VERIFICATION.md) |
| function_design_closure | [FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| status | 实现评审闭环已通过，可进入测试设计/开发 |
| implementation_review | [IMPLEMENTATION-REVIEW.md](./IMPLEMENTATION-REVIEW.md) |
| implementation_review_disposition | [IMPLEMENTATION-REVIEW-DISPOSITION.md](./IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| implementation_closure_verification | [IMPLEMENTATION-CLOSURE-VERIFICATION.md](./IMPLEMENTATION-CLOSURE-VERIFICATION.md) |

## 2 实现范围

| SR | 实现内容 |
| --- | --- |
| SR-V3-A01 | 在 `models.py` 新增 V3 storage/NER 相关 enum、lookup result、startup report 和 trace 字段。 |
| SR-V3-A02 | 新增 `RedisEntityWordCacheMock`，支持实体词到单实体 ID 的 hit/miss/invalid/dependency 状态和 schema 校验。 |
| SR-V3-A03 | 新增 `GaussEntityStoreMock`，支持按 `entity_id` 查询最小结构化实体字段。 |
| SR-V3-A04 | 新增 `EntityStorageRepository`，按先高斯后 Redis 的顺序加载，并校验 duplicate key、dangling ID、schema 和 confirmed key 来源。 |
| SR-V3-A05 | 新增 `NerPipeline`，覆盖 query validation、need-linking、mention detection、normalization、Redis lookup、Gauss lookup、candidate construction 和 status aggregation。 |
| SR-V3-A06 | 新增 V3 mock artifacts、golden cases、evaluation/smoke 脚本和 focused tests；保留 V1/V2 回归。 |

## 3 关键代码与样例

| 类型 | 文件 |
| --- | --- |
| Storage mocks | [../../../src/dv_entity_linking/storage.py](../../../src/dv_entity_linking/storage.py) |
| NER pipeline | [../../../src/dv_entity_linking/ner_pipeline.py](../../../src/dv_entity_linking/ner_pipeline.py) |
| Service integration | [../../../src/dv_entity_linking/service.py](../../../src/dv_entity_linking/service.py) |
| Web/API safe projection | [../../../src/dv_entity_linking/web.py](../../../src/dv_entity_linking/web.py) |
| Web single-entry V3 mode | [../../../scripts/run_web_demo.py](../../../scripts/run_web_demo.py) |
| V3 evaluation | [../../../scripts/run_v3_evaluation.py](../../../scripts/run_v3_evaluation.py) |
| V3 smoke | [../../../scripts/run_v3_acceptance_smoke.py](../../../scripts/run_v3_acceptance_smoke.py) |
| Gauss mock artifact | [../../../samples/real/v3_gauss_entities.json](../../../samples/real/v3_gauss_entities.json) |
| Redis mock artifact | [../../../samples/real/v3_redis_entity_words.json](../../../samples/real/v3_redis_entity_words.json) |
| NER golden cases | [../../../samples/real/v3_ner_golden_cases.json](../../../samples/real/v3_ner_golden_cases.json) |
| Focused implementation tests | [../../../tests/test_v3_storage_ner.py](../../../tests/test_v3_storage_ner.py) |

## 4 行为摘要

- 默认 Web demo 仍使用 `legacy_catalog`，保持 V2 默认体验；V3 通过 `scripts/run_web_demo.py --storage-mode v3_mock` 显式启用。
- Redis Mock key 来源限定为 `canonical_name` 和经确认 `aliases`；value 为单实体 ID。
- `normalized_key` 运行时按 Unicode NFKC、`casefold()`、移除 whitespace 重新计算并比对。
- Redis duplicate normalized key 指向不同 entity ID、dangling entity ID、schema version 不支持、字段缺失和未经确认 key 来源均 fail-closed。
- NER pipeline 输出顶层 `stage_trace` 和 mention 级 `storage_lookup`，Web/API 只投影安全状态、error code、schema/normalization version 摘要，不展示真实连接信息。
- `not_required` 不访问 storage；`no_match` 不制造候选；多 mention 中部分命中时返回 `partial`。

## 5 Verification Results

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-v3 tests\test_v3_storage_ner.py` | 通过，`9 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-targeted tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py` | 通过，`27 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`90 passed`。 |
| `python -m compileall -q src scripts` | 通过。 |
| `python scripts\run_v3_evaluation.py` | 通过，`total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0`。 |
| `python scripts\run_v3_acceptance_smoke.py` | 通过，`ok=true`、`entity_count=7`、`linked_storage_redis_statuses=["hit","hit"]`、`partial_status=partial`。 |
| `git diff --check` | 通过；仅输出既有 LF-to-CRLF 工作区警告。 |

## 6 残余风险和后续评审输入

| 风险 | 当前处理 |
| --- | --- |
| V3 初始 artifact 只覆盖首批 confirmed subset | 作为初始实现范围记录；后续扩充实体必须继续遵守 D003 和 confirmed alias 规则。 |
| LLM 在 V3 pipeline 中仍为可选增强，当前实现默认 deterministic | 符合 D077；真实 LLM 分类/解释/rerank 需要后续单独补实现和评审。 |
| 真实 Redis/Gauss adapter 未实现 | 符合 V3 范围；真实接入需另行确认连接、认证、失败语义和脱敏边界。 |

## 7 Review Input Package

实现评审建议输入：

- [SR.md](./SR.md)
- [FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FUNCTION-DESIGN-CLOSURE-VERIFICATION.md)
- 本实现记录
- `src/dv_entity_linking/storage.py`
- `src/dv_entity_linking/ner_pipeline.py`
- `src/dv_entity_linking/service.py`
- `src/dv_entity_linking/web.py`
- `scripts/run_web_demo.py`
- `scripts/run_v3_evaluation.py`
- `scripts/run_v3_acceptance_smoke.py`
- `samples/real/v3_gauss_entities.json`
- `samples/real/v3_redis_entity_words.json`
- `samples/real/v3_ner_golden_cases.json`
- `tests/test_v3_storage_ner.py`
- `tests/test_contract_artifacts.py`
- `tests/test_demo_scripts.py`

## 8 Conclusion

V3 初始代码实现已完成并通过本地验证；实现评审闭环验证已通过，当前可进入 V3 测试设计/开发。完成测试设计/开发、测试评审、处置和闭环验证前，不进入 V3 验收候选或 accepted/closed。
