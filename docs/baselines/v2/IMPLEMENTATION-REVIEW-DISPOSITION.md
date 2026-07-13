# DVEntityLinking V2 初始代码实现评审处置记录

---

## 基本信息

| 项 | 内容 |
| --- | --- |
| 版本 | V2 |
| 处置日期 | 2026-06-01 |
| 处置人 | Codex |
| 输入评审 | no-context/sealed 独立实现评审 Curie |
| 当前结论 | 评审处置和 no-context/sealed 闭环验证已完成，结论为 closed with residual risk |

## 输入基线

| 输入 | 文件 |
| --- | --- |
| V2 SR 功能设计 | [SR.md](./SR.md) |
| 当前数据契约 | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| 当前测试与验收策略 | [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) |
| V2 entity samples | `samples/real/v2_entity_examples.json` |
| V2 query samples | `samples/real/v2_query_samples.json` |

## 处置总览

| Finding | 严重级别 | 处置 | 处置说明 |
| --- | --- | --- | --- |
| V2 unified catalog/evaluation 不包含 V1 `alarm` | P1 | Accepted | V2 catalog 读取 `base_entity_files` 合并 V1 alarm 基线；V2 Query 增加 alarm + KPI 多 mention 样例；V2 evaluation/smoke 更新为 unified catalog。 |
| `degraded` 聚合和 `mode_status` 与 SR 不一致 | P1 | Accepted | V2 非 alarm-only catalog 中 linked + degraded 聚合为 `partial`；Web/API `mode_status` 输出 `degraded` 和 `stage_statuses`。 |
| LLM rerank 可选择候选集外实体并强制 linked | P1 | Accepted | rerank 结果必须来自当前候选集，且 confidence 达到阈值；非法输出保持 offline ambiguous 并标记 `llm_schema_error`/degraded。 |
| evaluator 未统计额外 actual mention false positive | P1 | Accepted | evaluator 将未匹配 expected mention 的 actual mention_results 计入 FP，并使 case fail。 |
| 跨类型同名歧义未验证 | P2 | Deferred with residual risk | 初始实现保留为残余风险；完整 V2 验收前需增加同名跨类型样例并实现同 span 多类型候选保留。 |
| 统一状态/错误枚举漂移 | P2 | Partially accepted | 删除 `Status.DEGRADED`、`LLM_INVALID_RESPONSE`、`ErrorCode.NO_MATCH`；原始 LLM 非法响应统一映射为 `llm_schema_error`。 |

## 修改摘要

| 领域 | 文件 |
| --- | --- |
| Catalog/data contract | `src/dv_entity_linking/catalog.py`、`samples/real/v2_query_samples.json`、`docs/current/DATA_CONTRACT.md` |
| Linker/LLM fallback | `src/dv_entity_linking/linking.py`、`src/dv_entity_linking/llm.py`、`src/dv_entity_linking/web.py` |
| Evaluation | `src/dv_entity_linking/evaluation.py`、`tests/test_v2_runtime.py` |
| Scripts/tests | `scripts/run_v2_evaluation.py`、`scripts/run_v2_acceptance_smoke.py`、`tests/test_demo_scripts.py`、`tests/test_linking.py` |
| Documentation | `README.md`、`docs/PROJECT.md`、`docs/current/TEST_ACCEPTANCE.md`、`docs/current/DECISIONS.md`、`samples/README.md` |

## 验证结果

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider` | 通过，`71 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `python scripts\run_v1_evaluation.py` | 通过，`total=16`、`fail=0`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v2_evaluation.py` | 通过，`total=12`、`fail=0`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo` | 通过，`ok=true`、`entity_count=25` |

## 闭环验证结果

| 项 | 结论 |
| --- | --- |
| 独立验证 | no-context/sealed 闭环验证 Lorentz |
| 最终结论 | Closed with residual risk |
| P1 findings | 全部 closed |
| P2 跨类型同名歧义 | Partially closed；作为已记录残余风险非阻塞 |
| P2 枚举漂移 | Closed |

闭环验证复核命令结果：

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider` | 通过，`71 passed` |
| `python scripts\run_v1_evaluation.py` | 通过，`total=16`、`pass=16`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v2_evaluation.py` | 通过，`total=12`、`pass=12`、`negative_false_positive=0`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo` | 通过，`ok=true`、`entity_count=25`、`partial_status=partial` |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 残余风险

| 风险 | 非阻塞理由 | 后续要求 |
| --- | --- | --- |
| 跨类型同名歧义未完全落地 | 当前用户确认启动样例尚未包含同名跨类型冲突；初始实现已先保证 unified catalog、多 mention、partial 和零误报。 | 完整 V2 验收前补充同名跨类型样例，并实现同 span 多类型候选保留。 |
| Runtime mock adapter 尚未独立落地 | 当前实现是 confirmed-sample startup slice，未接真实 DV 接口，也未模拟分页/鉴权/失败。 | 后续接入 runtime mock adapter 前需补 source lifecycle 和失败语义测试。 |
| 真实 LLM live smoke 非默认验收 | 默认验收必须 deterministic，不依赖外部服务。 | 若用户决定常态化真实 LLM smoke，需补脱敏报告和稳定配置检查。 |

## 闭环验证输入包

- 本处置记录。
- Curie 原始实现评审 finding。
- 已修改代码、样例、脚本和测试。
- 验证命令结果。

结论：处置包已完成 no-context/sealed 独立闭环验证，当前可进入 V2 测试设计或后续实现扩展。
