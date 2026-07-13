# DVEntityLinking V2 前端改造补救代码实现记录

日期：2026-06-02

状态：implementation review disposition completed，待独立闭环验证。V2 整体仍为 blocked，不能进入验收关闭。

## 输入基线

| 类型 | 文件 | 状态 |
| --- | --- | --- |
| 前端补救需求 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) | `V2-FE.2-closed`，需求评审闭环已通过 |
| 前端补救功能设计 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) | `V2-FE-SR.2-closed`，功能设计评审闭环已通过 |
| 设计闭环验证 | [FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) | Closed with recorded residual risk，允许进入代码实现 |

## 实现范围

| 项 | 实现内容 | 主要文件 |
| --- | --- | --- |
| V2 workbench 页面 | 将首页改造为运行状态、Query、多 mention、候选实体、实体详情、样例目录、相似实体和 LLM 安全解释面板组成的工作台 | `src/dv_entity_linking/web.py` |
| 多 mention 交互 | 支持同一 Query 中多个 mention 的可视化、点击切换、候选切换和实体详情联动；新增实体详情请求 token，避免旧异步请求覆盖新选择 | `src/dv_entity_linking/web.py` |
| 安全投影 | `/api/link` 输出 `mention_results[]`、`llm_explanations[]`、负例 `linked_entity: null`；实体详情只输出 `attributes_safe[]` 和 `omitted_attribute_count` | `src/dv_entity_linking/web.py` |
| LLM 安全解释 | 支持 global、mention、candidate 三类解释上下文；默认离线模式显示 deterministic safe explanation，不暴露完整 LLM 请求响应 | `src/dv_entity_linking/web.py` |
| 目录与检索 | 样例实体目录支持类型筛选，点击实体后联动详情和相似实体检索 | `src/dv_entity_linking/web.py` |
| 反向追踪证据 | V2 smoke 生成 `v2_frontend_traceability_check.json` 和 `.md`，要求全部 `implemented` 且无 downgraded 项 | `scripts/run_v2_acceptance_smoke.py` |
| 负例追踪门禁 | `AC-V2-FE-004` 单独进入 traceability，显式验证 `no_match` / `not_required` 不产生伪 linked entity、伪 mention 或伪 candidate | `scripts/run_v2_acceptance_smoke.py`、`tests/test_demo_scripts.py` |
| 浏览器证据 freshness | smoke 默认校验 `v2_frontend_browser_evidence.json`、required checks、截图存在性和相对 `src/dv_entity_linking/web.py` 的 freshness | `scripts/run_v2_acceptance_smoke.py`、`tests/test_demo_scripts.py` |
| 回归保护 | 增加 Web/API 投影、安全属性、负例、卡片可读色、追踪 artifact 的自动化断言 | `tests/test_web.py`、`tests/test_demo_scripts.py` |

## 设计追踪

| 需求/设计项 | 实现证据 |
| --- | --- |
| AC-V2-FE-001 / SR-V2-FE-D01：workbench 信息架构 | 页面包含 `runtime-status`、`query-panel`、`result-summary`、`mention-strip`、`candidate-detail-panel`、`entity-detail-panel`、`catalog-panel`、`retrieval-result`、`debug-panel` |
| AC-V2-FE-002 / SR-V2-FE-D02：多 mention Query | 浏览器证据验证 `Check ALM-51020 and CPU Usage.` 生成 2 个 mention，并切换到第二个 `CPU Usage` |
| AC-V2-FE-003 / SR-V2-FE-D02：mention 详情 | mention 卡展示 text、type、span、linked entity、candidate count 和原因 |
| AC-V2-FE-004 / SR-V2-FE-D03：候选实体详情 | 第二个 mention 候选显示 `DV-KPI-MTK-001 CPU Usage`，点击后实体详情同步切换 |
| AC-V2-FE-005 / SR-V2-FE-D04：LLM 交互式安全解释 | 浏览器证据验证 candidate 级解释 `candidate · CPU Usage` 可见 |
| AC-V2-FE-006 / SR-V2-FE-D05：安全属性投影 | `/api/entities/<id>` 仅暴露 `attributes_safe[]`，不返回 raw `attributes` |
| AC-V2-FE-007：调试信息默认收敛 | `debug-details` 默认折叠，浏览器证据验证 `debug_collapsed=true` |
| AC-V2-FE-008：桌面与窄屏 | Chrome CDP 证据覆盖 `1366x768` 和 `390x844`，均无横向溢出、无 section overlap |
| AC-V2-FE-009 / SR-V2-FE-D06：用户确认追踪矩阵 | smoke 输出 `outputs/logs/v2_frontend_traceability_check.json`，全部 status 为 `implemented` |

## 验证结果

| 验证 | 结果 |
| --- | --- |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`，`traceability_statuses=["implemented"]`，`traceability_ac_v2_fe_004_status=implemented`，`browser_evidence_ok=true`，`browser_evidence_fresh=true` |
| `python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py` | 通过，`27 passed` |
| Chrome CDP browser-equivalent evidence | 通过，`outputs/logs/v2_frontend_browser_evidence.json` 中 `ok=true` |
| 桌面截图 | `outputs/logs/v2_frontend_desktop_1366x768.png` |
| 窄屏截图 | `outputs/logs/v2_frontend_narrow_390x844.png` |

Chrome CDP 证据覆盖以下断言：`all_sections_visible`、`multi_mention_observed`、`second_mention_selected`、`candidate_and_entity_detail_observed`、`llm_explanation_observed`、`catalog_filter_observed`、`card_text_readable`、`debug_collapsed`、`no_section_overlap`、`no_horizontal_overflow` 全部为 `true`。

## 已发现并修复的问题

| 问题 | 修复 |
| --- | --- |
| 卡片作为 button 时继承蓝色按钮的白色文字，导致白底白字不可读 | `.item` 显式设置 `color: var(--ink)`，并在浏览器证据中加入 `card_text_readable` |
| 快速切换 mention/candidate 时，旧实体详情请求可能覆盖新选择 | `state.entityRequestToken` 保证最后一次实体详情请求胜出；点击 mention 时同步刷新候选、实体详情和相似实体 |
| 独立实现评审发现 `AC-V2-FE-004` 负例未单独进入 traceability | 新增 `AC-V2-FE-004` traceability item 和测试断言，smoke 输出 `traceability_ac_v2_fe_004_status=implemented` |
| 独立实现评审发现 browser evidence 未 freshness-check | smoke 默认校验 browser evidence JSON、required checks、截图存在性和 freshness，并将结果纳入 `ok` |

## 待独立实现评审输入包

```text
review_type: code implementation review
review_object: V2 frontend remediation implementation
baseline_documents:
  - docs/baselines/v2/IR-FRONTEND-REMEDIATION.md
  - docs/baselines/v2/SR-FRONTEND-REMEDIATION.md
  - docs/baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md
  - docs/baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md
code_and_tests:
  - src/dv_entity_linking/web.py
  - scripts/run_v2_acceptance_smoke.py
  - tests/test_web.py
  - tests/test_demo_scripts.py
scope:
  - verify implementation matches closed frontend remediation requirements and design
  - verify no silent downgrade from interactive frontend to API-only projection
  - verify safe projection, negative states, multi-mention interaction, browser evidence, and traceability artifacts
out_of_scope:
  - V2 final acceptance closure
  - real DV production API integration
  - production-grade frontend framework rewrite
allowed_commands:
  - python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py
  - python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs
expected_output:
  - independent read-only implementation review record with P0/P1/P2/P3 findings
```

## 当前结论

代码实现和实现评审处置已完成，当前可提交独立闭环验证。闭环验证和后续门禁未完成前，V2 仍保持 blocked，不能进入验收阶段或关闭。
