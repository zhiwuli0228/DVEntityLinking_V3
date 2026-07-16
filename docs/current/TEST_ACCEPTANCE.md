# 当前测试与验收策略

最后更新：2026-06-26

本文档记录当前项目的测试入口、验收阈值和回归要求。

## 默认验证命令

```powershell
python -m pytest
python -m compileall -q src scripts
python scripts\run_v1_evaluation.py
python scripts\run_v1_acceptance_smoke.py --mode offline_demo
python scripts\run_v2_evaluation.py
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
python scripts\run_v3_evaluation.py
python scripts\run_v3_acceptance_smoke.py
git diff --check
```

敏感字段扫描需排除 `config/llm.local.json` 和 `outputs/**`，并确认没有真实 key、token、Authorization bearer、真实 base URL 或完整 LLM 日志进入提交。

V3 功能设计评审闭环、初始代码实现评审闭环、测试设计、测试评审处置、测试评审闭环验证、验收候选前置核查和前置核查核验均已完成；当前 V3 验收候选已准备，等待用户验收确认。默认验证继续保留 V1/V2 技术回归，并新增 Redis Mock、高斯 Mock、两层存储集成、NER pipeline、V3 evaluation 和 V3 acceptance smoke 专项测试。

说明：`python scripts\run_v2_acceptance_smoke.py --mode offline_demo` 当前可能因 V2 legacy visual browser evidence freshness 输出 `ok=false`；该问题按 D072 搁置为 V2 遗留诊断项，不作为 V3 验收候选阻塞项。

## V1 验收阈值

| 指标 | 阈值 |
| --- | --- |
| 样例总数 | 16 |
| 全样例 pass | 必须 |
| negative false positive | 0 |
| precision | 1.0 |
| recall | 1.0 |
| linked | Top-1 `entity_id` 命中唯一期望实体 |
| ambiguous | Top-5 去重候选覆盖全部期望实体，状态保持 `ambiguous` |
| no_match | 不返回任何实体候选 |
| not_required | 不进入候选召回或返回空候选 |

## V1 已验证结果

| 验证 | 结果 |
| --- | --- |
| `python -m pytest` | 通过，`71 passed` |
| `python scripts\run_v1_evaluation.py` | 通过，`total=16`、`pass=16`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v1_acceptance_smoke.py --mode offline_demo` | 通过，`ok=true` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过 |
| 敏感字段扫描 | 通过 |

## 测试分层

| 层级 | 目的 |
| --- | --- |
| Contract tests | 样例 schema、文档治理、配置边界和安全边界 |
| Unit/integration tests | catalog、linking、retrieval、LLM fallback、Web/API |
| Evaluation script | V1 16 条 Query 和 V2 12 条 Query 的准确率、召回率和负例误报 |
| Acceptance smoke | PyCharm/命令行可执行的默认离线 demo 验收 |
| Conditional LLM smoke | 用户本地真实 OpenAI-compatible 配置补证，不进入默认回归 |

## 后续迭代要求

- 新实体类型必须先补样例、数据契约和验收阈值。
- 多实体 Query 必须新增 mention/linking/evaluator 规则后再实现。
- 真实 DV 运行时接口必须先确认 Mock 方式、失败语义和脱敏边界。
- 真实 LLM live smoke 若进入常态化，需要新增脱敏报告模板和稳定的本地配置检查。
- V3 Redis/Gauss 两层存储必须先完成 Mock 契约、错误语义和一致性测试设计，再进入代码实现。
- V3 NER 重构必须先完成 pipeline 设计、阶段输出契约和回归矩阵，确保 V1/V2 已验证能力不被破坏。

## V3 验收候选口径

V3 已由用户确认启动，V2 `AC-V2-FE-VIS-008` 遗留视觉证据问题搁置，不作为 V3 启动阻塞。V3 GUI 决策确认已完成，当前主输出已包含 [../baselines/v3/IR.md](../baselines/v3/IR.md)、[../baselines/v3/IR-SR-DECOMPOSITION.md](../baselines/v3/IR-SR-DECOMPOSITION.md)、[../baselines/v3/SR.md](../baselines/v3/SR.md)、[../baselines/v3/IMPLEMENTATION.md](../baselines/v3/IMPLEMENTATION.md)、[../baselines/v3/IMPLEMENTATION-REVIEW.md](../baselines/v3/IMPLEMENTATION-REVIEW.md)、[../baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md](../baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md)、[../baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md](../baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md)、[../baselines/v3/TEST-DESIGN.md](../baselines/v3/TEST-DESIGN.md)、[../baselines/v3/TEST-REVIEW.md](../baselines/v3/TEST-REVIEW.md)、[../baselines/v3/TEST-REVIEW-DISPOSITION.md](../baselines/v3/TEST-REVIEW-DISPOSITION.md)、[../baselines/v3/TEST-CLOSURE-VERIFICATION.md](../baselines/v3/TEST-CLOSURE-VERIFICATION.md)、[../baselines/v3/ACCEPTANCE-PRECHECK.md](../baselines/v3/ACCEPTANCE-PRECHECK.md)、[../baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md](../baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md) 和 [../releases/V3.md](../releases/V3.md)；V3 当前为验收候选已准备，等待用户验收确认，尚未 accepted/closed。

| 类别 | V3 验收关注 |
| --- | --- |
| Redis Mock | 覆盖 `entity_name` + 经确认 `alias` 到单实体 ID value 的 hit、miss、重复 key、非法 value、引用不存在 entity ID；冲突数据加载 fail-closed。 |
| 高斯 Mock | 覆盖按 entity ID 查询结构化实体、miss、重复 ID、字段缺失、schema 错误。 |
| 两层集成 | 覆盖 Redis hit + 高斯 hit、Redis hit + 高斯 miss、Redis miss、任一层 dependency failed。 |
| NER pipeline | 覆盖 need-linking、mention detection、span、type classification、entity-word normalization、storage lookup、内部 schema trace、多 mention、partial、ambiguous、no_match、not_required。 |
| 样例与 golden cases | 复用 V1/V2 已确认样例，新增 Redis/Gauss Mock artifacts 和 NER golden cases；新增样例必须脱敏并遵守 D003。 |
| LLM | 默认验收不依赖真实 LLM；LLM 仅作为可选分类、解释或 rerank 增强的条件补证。 |
| 回归 | V1 evaluation/smoke、V2 evaluation/smoke 和 `python -m pytest` 继续作为 V3 改造底线。 |
| 安全 | 不提交真实 Redis/Gauss 连接串、账号、密码、token、真实 DV payload 或完整 LLM 请求响应。 |

## V3 已验证结果

| 验证 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-v3 tests\test_v3_storage_ner.py` | 通过，`12 passed` |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-targeted tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py` | 通过，`30 passed` |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`93 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `python scripts\run_v3_evaluation.py` | 通过，`total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0` |
| `python scripts\run_v3_acceptance_smoke.py` | 通过，`ok=true`、`entity_count=7`、`linked_storage_redis_statuses=["hit","hit"]`、`partial_status=partial` |
| `git diff --check` | 通过；仅输出既有 LF-to-CRLF 工作区警告 |
| V3 acceptance precheck | 通过，见 [../baselines/v3/ACCEPTANCE-PRECHECK.md](../baselines/v3/ACCEPTANCE-PRECHECK.md) |
| V3 acceptance precheck verification | 通过，见 [../baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md](../baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md) |
| V3 acceptance candidate record | 已准备，见 [../releases/V3.md](../releases/V3.md)；pending user acceptance; not accepted/closed |

## V2 已验证结果

V2 初始代码实现评审处置和 no-context/sealed 闭环验证已完成，结论为 closed with residual risk；当前残余风险为跨类型同名歧义补强、runtime mock adapter 深化和真实 LLM live smoke 常态化决策。

V2 测试设计与测试开发已完成，测试用例、覆盖矩阵和评审输入包见 [../baselines/v2/TC-DVEntityLinking-V2-test-cases.md](../baselines/v2/TC-DVEntityLinking-V2-test-cases.md)。独立测试评审已完成且无 P0/P1，处置和 no-context/sealed 闭环验证已完成，结论为 closed with recorded residual risk；记录见 [../baselines/v2/TEST-REVIEW-DISPOSITION.md](../baselines/v2/TEST-REVIEW-DISPOSITION.md)。

V2 原验收候选记录曾撤回，见 [../releases/V2.md](../releases/V2.md)。默认离线命令仍作为技术验证证据保留；上一轮前端功能补救验收候选经用户复核后确认视觉风格不足，不能 accepted and closed。当前 V2 前端视觉风格补救验收前置核查已生成，需求文档见 [../baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md](../baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md)，功能设计见 [../baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md](../baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md)，功能设计评审见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md)，处置见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md)，闭环验证见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md)，实现记录见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md)，实现评审见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md)，实现评审处置见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)，实现评审闭环验证见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)，测试设计/开发见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md)，测试评审见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md)，测试评审处置见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)，测试评审闭环验证见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)，验收前置核查见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md)。after 证据已补采且用户已 accepted；before 同场景截图或替代 before 证据口径仍缺失。

V2 前端功能补救已完成需求、设计、实现、测试和反向核查链路，相关历史证据仍保留：需求文档见 [../baselines/v2/IR-FRONTEND-REMEDIATION.md](../baselines/v2/IR-FRONTEND-REMEDIATION.md)，功能设计见 [../baselines/v2/SR-FRONTEND-REMEDIATION.md](../baselines/v2/SR-FRONTEND-REMEDIATION.md)，实现记录见 [../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md](../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md)，实现评审处置见 [../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)，实现闭环见 [../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)，测试设计见 [../baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md](../baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md)，测试评审处置见 [../baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md)，测试闭环见 [../baselines/v2/FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)，反向核查见 [../baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md](../baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md)，独立核验见 [../baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md](../baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md)。但该链路未把“参考原型后的视觉风格变化”做成可验收门禁，当前不能作为最终验收候选。

V2 前端视觉风格补救的当前验收方向：需求评审已确认 [../baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md](../baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md) 需要补强 D003 安全边界、visual traceability artifact schema、before/after canonical scenario、首屏结构边界和参考源 capture metadata；处置记录见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md)，闭环验证见 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md)。当前测试评审闭环已通过，闭环接受 FE-VIS-TEST-001/P1、FE-VIS-TEST-002/P1、FE-VIS-TEST-003/P2 的处置证据，图片结构校验、D003 runtime scan 和 forbidden downgrade blocker 均已关闭。进入验收关闭仍需 before/after 对比和用户视觉接受。

| 验证 | 结果 |
| --- | --- |
| `python scripts\run_v2_evaluation.py` | 通过，`total=12`、`pass=12`、`precision=1.0`、`recall=1.0`，包含 `type_metrics` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo` | 通过，`ok=true`、`entity_count=25`、`partial_status=partial` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo` 2026-06-26 V3 precheck rerun | V2 legacy visual evidence 诊断项：核心 API、D003 scan、截图文件结构校验通过；`browser_evidence_fresh=false` 导致 `ok=false`，按 D072 不作为 V3 阻塞项 |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 前端补救验收前反向核查后通过，`ok=true`、`traceability_statuses=["implemented"]`、`traceability_ac_v2_fe_004_status=implemented`、`traceability_decision_d041_status=implemented`、`browser_evidence_ok=true`、`browser_evidence_fresh=true` |
| Chrome CDP browser-equivalent evidence | 前端补救实现后通过，`outputs/logs/v2_frontend_browser_evidence.json` 中 `ok=true`，覆盖 `1366x768`、`390x844`、第二个 mention `CPU Usage`、`DV-KPI-MTK-001` 候选/实体详情、candidate 级安全解释、卡片文字可读、debug 默认折叠和无横向溢出 |
| V2 frontend focused test slice | `python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py` 测试评审处置后通过，`28 passed`；单文件 `tests\test_web.py` 通过，`12 passed` |
| V2 frontend remediation full regression | `python -m pytest -p no:cacheprovider` 测试评审处置后通过，`75 passed`；视觉测试设计/开发后通过，`77 passed`；视觉测试评审处置后通过，`80 passed`；`python -m compileall -q src scripts` 通过 |
| V2 frontend acceptance precheck independent verification | `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_contract_artifacts.py` 通过，`6 passed` |
| V2 frontend visual remediation implementation review disposition | 已生成 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) 和 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)，接受并修复 FE-VIS-IMPL-001/P1、FE-VIS-IMPL-002/P2、FE-VIS-IMPL-003/P2；`python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` 通过，`browser_screenshot_images_valid=true`、`visual_traceability_statuses=["implemented","needs_user_decision"]`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |
| V2 frontend visual remediation implementation closure verification | 已生成 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)，FE-VIS-IMPL-001 至 FE-VIS-IMPL-003 均 Closed；`manual_user_acceptance_status=pending` 和 `AC-V2-FE-VIS-007/008` 仍保持阻塞 |
| V2 frontend visual remediation test review disposition | 已生成 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md) 和 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)；覆盖 `TC-V2-FE-VIS-001` 至 `TC-V2-FE-VIS-009`，包含版本专用 Web demo 入口拒绝回归；接受 FE-VIS-TEST-001/P1、FE-VIS-TEST-002/P1、FE-VIS-TEST-003/P2；`tests\test_demo_scripts.py` 通过，`12 passed`；`python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` 通过，`d003_scan_ok=true`、`browser_screenshot_images_valid=true`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |
| V2 frontend visual remediation test review closure verification | 已生成 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)，FE-VIS-TEST-001 至 FE-VIS-TEST-003 均 Closed；no-context verifier 复跑 `tests\test_demo_scripts.py` 为 `12 passed`、`tests\test_demo_scripts.py tests\test_contract_artifacts.py` 为 `17 passed`、全量回归为 `80 passed`；`manual_user_acceptance_status=pending` 和 `AC-V2-FE-VIS-007/008` 仍保持阻塞 |
| V2 frontend visual remediation acceptance precheck | 已生成 [../baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md)；单入口 `scripts\run_web_demo.py` 启动；after 截图已补采为 `outputs/logs/v2_visual_acceptance_after_desktop_1366x768.png` 和 `outputs/logs/v2_visual_acceptance_after_narrow_390x844.png`；浏览器检查 `hasWorkbench=true`、`hasStatusBand=true`、`hasQueryZone=true`、窄屏 `hasHorizontalOverflow=false`；用户确认当前 after 视觉 `accepted`，smoke 输出 `manual_user_acceptance_status=accepted`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-008"]`，`AC-V2-FE-VIS-007` 可关闭；before 同场景截图或替代 before 证据口径仍缺失，`AC-V2-FE-VIS-008` 继续 blocking |
| V2 focused test slice | `python -m pytest -p no:cacheprovider tests\test_v2_runtime.py tests\test_demo_scripts.py` 通过，`16 passed` |
| V1 回归 | `python scripts\run_v1_evaluation.py` 和 `python scripts\run_v1_acceptance_smoke.py --mode offline_demo` 均通过 |

## V2 验收方向

V2 SR 功能设计已闭环，初始代码实现已通过实现评审闭环，测试设计与测试开发以及独立测试评审闭环均已完成；前端视觉风格补救验收前置核查已生成。当前 after 视觉已由用户 accepted，`AC-V2-FE-VIS-007` 可关闭；`AC-V2-FE-VIS-008` 仍因 before 同场景截图或替代 before 证据口径未确认而阻塞，V2 当前 blocked。后续补救或扩展实现按以下方向继续验证：

| 类别 | V2 验收关注 |
| --- | --- |
| V1 回归 | V1 16 条 alarm Query 继续通过，避免多类型改造破坏已关闭能力。 |
| 多类型覆盖 | Unified catalog 覆盖 `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key`；`kpi_meas_objects` 本轮先忽略。 |
| 负例覆盖 | no_match 和 not_required 继续作为验收重点，false positive 必须显式统计。 |
| 多 mention | V2 必须支持多 mention Query；启动样例中每条 Query 最多 2 个 mention。 |
| partial 状态 | Query 级 `partial` 表示至少一个 mention 链接成功且至少一个 mention no_match、ambiguous 或降级；评测需保留 mention-level 结果。 |
| 跨类型歧义 | V2 最终评测需覆盖跨类型歧义，或在测试设计中显式记录非阻塞延期理由和残余风险。 |
| 英文 Query | V2 补充 Query 全部使用英文，便于先稳定 span 和 LLM schema。 |
| LLM 对比 | 区分 offline deterministic、LLM enabled、fallback used 和 LLM schema/error 状态。 |
| 数据来源 | 预置数据、DVKnowledge KPI/网元类型候选和运行时 Mock 输出均需可校验；新增类型别名默认空且不得自动生成。 |
| 安全边界 | 真实 API key、token、base URL、完整 DV payload 和完整 LLM 日志不得进入提交。 |
