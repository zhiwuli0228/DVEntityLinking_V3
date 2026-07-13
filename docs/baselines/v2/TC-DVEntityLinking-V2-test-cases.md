# DVEntityLinking V2 测试设计与测试开发记录

---

## 基本信息

| 项 | 内容 |
| --- | --- |
| 版本 | V2 |
| 文档编号 | TC-DVEntityLinking-V2 |
| 日期 | 2026-06-01 |
| 编写人 | Codex |
| 当前状态 | 测试设计与测试开发完成，独立测试评审闭环已通过，结论为 closed with recorded residual risk |
| 测试对象 | V2 multi-type、multi-mention entity linking initial slice |
| 测试模式 | test plan only + automation implementation + execution/reporting |

## 输入基线

| 输入 | 文件 |
| --- | --- |
| V2 IR | [IR.md](./IR.md) |
| V2 SR 功能设计 | [SR.md](./SR.md) |
| V2 初始实现评审处置与闭环 | [IMPLEMENTATION-REVIEW-DISPOSITION.md](./IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| 当前数据契约 | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| 当前测试与验收策略 | [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) |
| 当前决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| V2 entity samples | `samples/real/v2_entity_examples.json` |
| V2 query samples | `samples/real/v2_query_samples.json` |

V2 SR 中保留了启动阶段 11 条 Query 的历史描述；实现评审处置后新增 `V2-Q-012` alarm + KPI unified regression Query。当前权威数量以 `DATA_CONTRACT.md` 和 `samples/real/v2_query_samples.json` 为准：V2 Query 共 12 条。

## 测试定位和边界

| 项 | 说明 |
| --- | --- |
| 范围内 | V1 回归、V2 unified catalog、英文多 mention Query、mention-level scoring、Query-level `partial`、negative false positive、LLM fallback/error path、Web/API safe projection、acceptance smoke、测试文档治理。 |
| 范围外 | 真实 DV 接口直连、真实 LLM 默认验收、生产级向量库/数据库、未确认的实体字段升级、`kpi_meas_objects` 本轮实例化样例。 |
| 默认依赖 | 默认回归只使用本地文件和 deterministic/offline 链路。 |
| 条件依赖 | 真实 OpenAI-compatible LLM 仅作为本地条件补证，不进入默认回归。 |

## 分层策略

| 层级 | 目标 | 当前自动化 |
| --- | --- | --- |
| Independent contract test | 文档、样例 schema、枚举、状态和安全边界 | `tests/test_contract_artifacts.py`、V1/V2 dataset loader fail-closed tests |
| Black-box artifact test | 验证脚本输出、smoke log 和可重放摘要 | `tests/test_demo_scripts.py` |
| Implementation-level integration test | 通过真实模块调用验证 catalog、extractor、linker、evaluator、Web/API | `tests/test_v2_runtime.py`、`tests/test_linking.py`、`tests/test_web.py` |

## 覆盖矩阵

| SR/关注点 | 验收语义 | 测试用例 | 自动化状态 |
| --- | --- | --- | --- |
| SR-V2-A01 数据预处理与 catalog | V2 catalog 合并 V1 alarm，新增实体 aliases 默认空，计数和类型正确 | TC-V2-CATALOG-001、TC-V2-CATALOG-002 | Automated |
| SR-V2-A02 runtime mock 边界 | 当前 confirmed-sample startup slice 可运行；runtime adapter 深化延期 | TC-V2-RUNTIME-001 | Deferred with residual risk |
| SR-V2-A03 分层分类 NER | 英文 Query 多 mention span 与类型识别稳定 | TC-V2-NER-001 | Automated |
| SR-V2-A04 LLM-based/fallback | LLM timeout/http/auth/schema error 结构化降级；非法 rerank 不强制 linked | TC-V2-LLM-001、TC-V2-LLM-002、TC-V2-LLM-003 | Automated |
| SR-V2-A05 多类型链接和消歧 | 多 mention linked、`partial`、no_match/not_required、跨 V1 alarm+KPI Query | TC-V2-LINK-001 到 TC-V2-LINK-005 | Automated |
| SR-V2-A05 跨类型同名歧义 | 同 span 多类型候选保留 | TC-V2-XTYPE-001 | Deferred with residual risk |
| SR-V2-A06 内存索引/检索 | 类型过滤、候选排序和 V1 alarm-only 回归不破坏 | TC-V2-INDEX-001 | Automated |
| SR-V2-A07 Web/API demo | V2 API 输出 mention_results、mode_status、degraded stage summary；页面含核心区域 | TC-V2-WEB-001、TC-V2-WEB-002 | Automated |
| SR-V2-A08 evaluation/report | Query-level、mention-level、type-level metrics，negative false positive=0 | TC-V2-EVAL-001、TC-V2-EVAL-002 | Automated |
| 安全边界 | 不提交真实 key、token、base URL、raw request/response、完整 LLM log | TC-V2-SAFE-001 | Automated |

## 测试用例清单

| 用例 ID | 名称 | 优先级 | 层级 | 自动化映射 | 状态 |
| --- | --- | --- | --- | --- | --- |
| TC-V2-CATALOG-001 | Unified catalog includes V1 alarm and V2 entities | P0 | Integration | `tests/test_v2_runtime.py::test_v2_catalog_and_query_dataset_load` | Automated |
| TC-V2-CATALOG-002 | V2 aliases default empty and alias guard | P1 | Contract/Integration | `tests/test_v2_runtime.py::test_v2_catalog_and_query_dataset_load`、catalog validation tests | Automated |
| TC-V2-NER-001 | English multi mention span extraction | P0 | Integration | `tests/test_v2_runtime.py` V2 linked/partial cases | Automated |
| TC-V2-LINK-001 | All-linked multi mention Query | P0 | Integration | `test_v2_unified_catalog_links_alarm_and_new_type_in_one_query` | Automated |
| TC-V2-LINK-002 | Query-level `partial` aggregation | P0 | Integration | `test_v2_multi_mention_partial_linking` | Automated |
| TC-V2-LINK-003 | no_match/not_required zero false positive | P0 | Evaluation/Smoke | `run_v2_evaluation.py`、`run_v2_acceptance_smoke.py` | Automated |
| TC-V2-LINK-004 | Degraded linked result aggregates to `partial` for V2 | P1 | Integration | `test_v2_degraded_all_linked_result_becomes_partial` | Automated |
| TC-V2-LINK-005 | Unexpected actual mention counts as FP | P0 | Evaluation | `test_v2_evaluator_counts_unexpected_extra_mentions_as_false_positive` | Automated |
| TC-V2-XTYPE-001 | Cross-type same-name ambiguity candidate retention | P2 | Integration | Not implemented in startup slice | Deferred |
| TC-V2-INDEX-001 | Type-filtered candidate retrieval and stable ranking do not break V1/V2 regression | P1 | Integration/Evaluation | `tests/test_linking.py::test_fuzzy_mention_returns_ordered_candidates`、`tests/test_v1_alarm_runtime.py::test_v1_alarm_startup_dataset_reaches_acceptance_threshold`、`tests/test_v2_runtime.py::test_v2_query_dataset_reaches_startup_threshold` | Automated |
| TC-V2-LLM-001 | LLM extraction schema/error fallback | P1 | Integration | `tests/test_linking.py` LLM fallback tests | Automated |
| TC-V2-LLM-002 | LLM rerank rejects non-candidate | P1 | Integration | `test_llm_disambiguation_rejects_non_candidate_selection` | Automated |
| TC-V2-LLM-003 | LLM dependency failed when fallback disabled | P1 | Integration/API | `test_llm_dependency_failed_when_fallback_disabled`、Web mode tests | Automated |
| TC-V2-EVAL-001 | V2 report includes mention/query metrics | P0 | Evaluation | `test_v2_query_dataset_reaches_startup_threshold` | Automated |
| TC-V2-EVAL-002 | V2 report includes type-level metrics | P1 | Evaluation | `test_v2_query_dataset_reaches_startup_threshold` | Automated |
| TC-V2-DATASET-001 | V2 dataset metadata fails closed | P1 | Contract | `test_v2_query_dataset_loader_fails_closed_on_metadata_contract` | Automated |
| TC-V2-WEB-001 | V2 API returns multi mention projection | P1 | API Integration | `test_v2_web_api_returns_multi_mention_projection` | Automated |
| TC-V2-WEB-002 | Web/API mode_status exposes degraded stage summary | P1 | API Integration | `test_v2_web_mode_status_includes_degraded_stage_summary` | Automated |
| TC-V2-SMOKE-001 | V2 acceptance smoke covers catalog/link/partial/no_match/not_required | P0 | Black-box | `test_v2_acceptance_smoke_script_runs_offline` | Automated |
| TC-V2-SAFE-001 | Smoke artifacts and run records avoid sensitive leakage | P0 | Contract/Black-box | `tests/test_run_repository.py`、`test_v2_acceptance_smoke_script_runs_offline` | Automated |

## 残余风险和延期项

| 项 | 状态 | 非阻塞理由 | 后续要求 |
| --- | --- | --- | --- |
| Cross-type same-name ambiguity | Deferred with residual risk | 启动样例未包含同 span 跨类型同名冲突；实现评审闭环已接受其作为 P2 残余风险。 | 完整 V2 验收前新增样例并实现同 span 多类型候选保留。 |
| Runtime mock adapter 深化 | Deferred | 当前实现是 confirmed-sample startup slice，尚未引入独立 runtime source adapter。 | 接入真实/模拟 runtime 文件前补 required/optional source lifecycle 和失败语义测试。 |
| 真实 LLM live smoke 常态化 | Deferred | 默认验收必须 deterministic，不依赖外部服务。 | 若用户决定纳入条件验收，新增脱敏报告和本地配置检查。 |

## 执行证据

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider` | 通过，`71 passed`；覆盖 contract、linking、Web/API、run repository、V1/V2 runtime 和 demo scripts |
| `python -m pytest -p no:cacheprovider tests\test_v2_runtime.py tests\test_demo_scripts.py` | 通过，`16 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `python scripts\run_v1_evaluation.py` | 通过，`total=16`、`pass=16`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v2_evaluation.py` | 通过，`total=12`、`pass=12`、`negative_false_positive=0`、`precision=1.0`、`recall=1.0`，包含 `type_metrics` |
| `python scripts\run_v1_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`entity_count=9` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`entity_count=25`、`partial_status=partial` |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 独立测试评审输入包

请独立测试评审者只读复核以下输入：

- 本测试设计与测试开发记录。
- V2 IR、V2 SR、V2 初始实现评审处置与闭环记录。
- `docs/current/DATA_CONTRACT.md`、`docs/current/TEST_ACCEPTANCE.md`、`docs/current/DECISIONS.md`。
- `samples/real/v2_entity_examples.json`、`samples/real/v2_query_samples.json`。
- `src/dv_entity_linking/evaluation.py`、`src/dv_entity_linking/datasets.py`、`src/dv_entity_linking/linking.py`、`src/dv_entity_linking/extraction.py`、`src/dv_entity_linking/web.py`。
- `tests/test_v2_runtime.py`、`tests/test_demo_scripts.py`、`tests/test_linking.py`、`tests/test_web.py`、`tests/test_run_repository.py`、`tests/test_contract_artifacts.py`。

评审重点：

- 测试设计是否覆盖 V2 IR/SR 关键验收语义。
- 自动化分层是否合理，是否误把某层证据当作另一层证据。
- P0/P1 行为是否有可执行自动化覆盖。
- 已记录残余风险是否可接受且不会误导后续验收。
- 执行证据是否足以进入评审处置/闭环阶段。
