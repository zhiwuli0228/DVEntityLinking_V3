# DVEntityLinking V2 前端改造补救测试设计与测试开发记录

日期：2026-06-02

状态：test review closure verified，待验收前反向核查。

## 测试模式

本记录合并三类测试工作：

- test plan only：形成前端补救测试用例、覆盖矩阵和证据映射。
- automation implementation：补充或确认自动化测试、smoke artifact 检查和 browser evidence freshness 检查。
- execution/reporting：记录已执行命令、结果和产物。

## 输入基线

| 类型 | 文件 | 状态 |
| --- | --- | --- |
| 前端补救需求 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) | `V2-FE.2-closed` |
| 前端补救功能设计 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) | `V2-FE-SR.2-closed` |
| 实现评审闭环 | [FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) | closed with recorded residual risk |
| 测试评审闭环 | [FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md) | closed |
| 实现记录 | [FRONTEND-REMEDIATION-IMPLEMENTATION.md](./FRONTEND-REMEDIATION-IMPLEMENTATION.md) | implementation review closure verified |

## 范围

本轮测试覆盖 V2 前端补救范围：

- Workbench 页面结构和默认信息密度。
- 英文多 mention Query 的 mention 级展示和交互切换。
- 第二个 mention `CPU Usage` 到 `DV-KPI-MTK-001` 的候选、实体详情和相似实体联动。
- LLM global / mention / candidate 安全解释。
- `no_match`、`not_required`、`partial` 的前端/API 负例语义。
- `attributes_safe[]` fail-closed 投影和 raw attributes 不外露。
- `debug-details` 默认折叠，不暴露敏感配置或完整 LLM 日志。
- 1366x768 和 390x844 浏览器等效证据、卡片可读性、无横向溢出。
- 反向追踪矩阵和 browser evidence freshness 门禁。

不覆盖：

- 真实 DV 生产接口直连。
- 真实 LLM live smoke 常态化。
- 生产级前端框架改写。
- V2 最终验收关闭。

## 测试分层

| 层级 | 测试资产 | 说明 |
| --- | --- | --- |
| Independent contract test | `tests/test_contract_artifacts.py` | 验证文档导航、阶段状态、关键基线和门禁记录一致。 |
| Implementation-level integration test | `tests/test_web.py`、`tests/test_v2_runtime.py` | 调用 Flask/API 和实体链接服务，验证 safe projection、负例、UI HTML、运行时多 mention。 |
| Black-box artifact test | `tests/test_demo_scripts.py` | 执行 smoke，检查输出 JSON/MD、log、traceability 和 browser evidence 校验结果。 |
| Browser-equivalent evidence | `outputs/logs/v2_frontend_browser_evidence.json` 和截图 | 由 Chrome CDP 步骤生成，smoke 强制校验 required checks、截图存在性和 freshness。 |

## 测试用例总览

| ID | 名称 | 覆盖 AC | 优先级 | 自动化状态 |
| --- | --- | --- | --- | --- |
| TC-V2-FE-WEB-001 | Workbench section visibility | AC-V2-FE-001、AC-V2-FE-007 | P0 | automated |
| TC-V2-FE-WEB-002 | Desktop/narrow responsive browser evidence | AC-V2-FE-008 | P0 | browser-equivalent + smoke validator |
| TC-V2-FE-WEB-003 | Multi-mention Query observable | AC-V2-FE-002、AC-V2-FE-003 | P0 | automated + browser-equivalent |
| TC-V2-FE-WEB-004 | Second mention candidate/entity linkage | AC-V2-FE-002、AC-V2-FE-004 | P0 | browser-equivalent |
| TC-V2-FE-WEB-005 | LLM safe explanation contexts | AC-V2-FE-005、AC-V2-FE-006 | P0 | automated + browser-equivalent |
| TC-V2-FE-WEB-006 | Safe entity attributes fail-closed | AC-V2-FE-006 | P0 | automated |
| TC-V2-FE-WEB-007 | no_match / not_required negative states | AC-V2-FE-004 | P0 | automated + traceability artifact |
| TC-V2-FE-WEB-008 | Debug collapsed and sensitive data boundary | AC-V2-FE-007、AC-V2-FE-008 | P0 | automated |
| TC-V2-FE-WEB-009 | Traceability artifact no downgrade | AC-V2-FE-009 | P0 | automated |
| TC-V2-FE-WEB-010 | Browser evidence freshness and screenshot presence | AC-V2-FE-008、AC-V2-FE-009 | P1 | automated validator |
| TC-V2-FE-WEB-011 | Single web demo entry preservation | AC-V2-FE-001 | P2 | contract/docs smoke |

## 用例到自动化映射

| 测试用例 | 自动化/证据 |
| --- | --- |
| TC-V2-FE-WEB-001 | `tests/test_web.py::test_web_ui_visibility_smoke` |
| TC-V2-FE-WEB-002 | `outputs/logs/v2_frontend_browser_evidence.json` required checks: `all_sections_visible`、`no_section_overlap`、`no_horizontal_overflow` |
| TC-V2-FE-WEB-003 | `tests/test_v2_runtime.py`、`scripts/run_v2_acceptance_smoke.py` summary: `linked_mention_count=2`、`partial_no_match_count=1` |
| TC-V2-FE-WEB-004 | Browser evidence required checks: `second_mention_selected`、`candidate_and_entity_detail_observed` |
| TC-V2-FE-WEB-005 | `tests/test_web.py::test_web_api_link_exposes_workbench_safe_projection`、browser evidence `llm_explanation_observed` |
| TC-V2-FE-WEB-006 | `tests/test_web.py::test_web_entity_detail_uses_safe_attributes`、`tests/test_web.py::test_web_entity_detail_omits_forbidden_attributes_and_values` |
| TC-V2-FE-WEB-007 | `tests/test_web.py::test_web_api_negative_states_do_not_emit_pseudo_entities`、traceability item `AC-V2-FE-004` |
| TC-V2-FE-WEB-008 | `tests/test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline` log/smoke assertions |
| TC-V2-FE-WEB-009 | `outputs/logs/v2_frontend_traceability_check.json`、`tests/test_demo_scripts.py` traceability assertions |
| TC-V2-FE-WEB-010 | `_validate_browser_evidence()`、`tests/test_demo_scripts.py` browser evidence fixture assertions |
| TC-V2-FE-WEB-011 | `tests/test_contract_artifacts.py`、`docs/USAGE.md` 和 `scripts/run_web_demo.py` 入口说明 |

## 关键用例细节

### TC-V2-FE-WEB-004 第二个 mention 联动

输入：`Check ALM-51020 and CPU Usage.`

预期：

- mention strip 至少包含 `ALM-51020` 和 `CPU Usage`。
- 选择第二个 mention 后候选面板显示 `DV-KPI-MTK-001 CPU Usage`。
- 实体详情面板同步显示 `DV-KPI-MTK-001`。
- LLM safe explanation 面板切换为 candidate 级 `CPU Usage` 解释。

证据：`outputs/logs/v2_frontend_browser_evidence.json` 中 `second_mention_selected=true`、`candidate_and_entity_detail_observed=true`、`llm_explanation_observed=true`。

### TC-V2-FE-WEB-007 负例状态

输入：

- `Show metrics for UnknownApp-999.`
- `Open the operations dashboard.`

预期：

- no_match 不返回伪 `linked_entity`，candidate count 为 0，显示 no-candidate reason。
- not_required 不返回伪 mention、伪 candidate 或伪 `linked_entity`，显示无需链接原因。
- traceability artifact 必须有单独 `AC-V2-FE-004` 条目且 status 为 `implemented`。

证据：`scripts/run_v2_acceptance_smoke.py` summary、`tests/test_web.py`、`outputs/logs/v2_frontend_traceability_check.json`。

### TC-V2-FE-WEB-006 Safe Attributes Fail-closed

输入：`/api/entities/<id>` 查询一个包含 `api_key`、`raw_response` 和 allowed key 中 token-like value 的实体。

预期：

- `attributes_safe[]` 只返回 allowed key 且 safe value 的属性。
- forbidden key 和 token-like value 均被省略。
- `omitted_attribute_count` 等于被省略属性数量。
- API 响应不包含原始 `attributes`、forbidden key 或 forbidden value。

证据：`tests/test_web.py::test_web_entity_detail_omits_forbidden_attributes_and_values`。

### TC-V2-FE-WEB-010 Browser Evidence Freshness

预期：

- `v2_frontend_browser_evidence.json` 存在且 `schema_version=v2.frontend_browser_evidence.1`。
- required checks 全部为 true。
- 两张截图存在且大小大于 0。
- browser evidence JSON 和截图不早于 `src/dv_entity_linking/web.py`。
- smoke 将这些检查纳入 `ok`。

证据：`scripts/run_v2_acceptance_smoke.py::_validate_browser_evidence`、`tests/test_demo_scripts.py::_write_browser_evidence`。

## 执行命令与结果

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline` | 通过，`1 passed` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`traceability_ac_v2_fe_004_status=implemented`、`browser_evidence_ok=true`、`browser_evidence_fresh=true` |
| `python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py` | 测试评审处置后通过，`28 passed` |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed` |
| `python -m pytest -p no:cacheprovider` | 测试评审处置后通过，`75 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅 LF/CRLF 提示 |
| `python -m pytest -p no:cacheprovider tests\test_web.py` | 测试评审处置后通过，`12 passed` |

## 证据产物

| 产物 | 用途 |
| --- | --- |
| `outputs/logs/v2_frontend_traceability_check.json` | AC/user decision 反向追踪矩阵，含 `AC-V2-FE-004`。 |
| `outputs/logs/v2_frontend_traceability_check.md` | 人读版追踪矩阵。 |
| `outputs/logs/v2_frontend_browser_evidence.json` | Chrome CDP browser-equivalent evidence。 |
| `outputs/logs/v2_frontend_desktop_1366x768.png` | 桌面截图。 |
| `outputs/logs/v2_frontend_narrow_390x844.png` | 窄屏截图。 |
| `outputs/logs/v2-acceptance-smoke-*.log` | smoke 执行日志，不含 key、authorization、raw_response。 |

## 残余风险

| 风险 | 分类 | 处理 |
| --- | --- | --- |
| Browser evidence 仍由独立 Chrome CDP 步骤生成，smoke 不负责生成截图 | P2 residual risk | 已由 smoke freshness/checks/screenshot validator 强制校验，非阻塞。 |
| 真实 LLM live smoke 未进入默认回归 | Future decision | 保持当前默认 offline_demo，不扩大范围。 |

## 独立测试评审与处置

| 类型 | 文件 | 状态 |
| --- | --- | --- |
| 独立测试评审 | [FRONTEND-REMEDIATION-TEST-REVIEW.md](./FRONTEND-REMEDIATION-TEST-REVIEW.md) | 1 个 P1 |
| 测试评审处置 | [FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md) | FE-TEST-001 accepted and fixed |
| 测试评审闭环 | [FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md) | FE-TEST-001 Closed |

## 独立测试评审输入包

```text
review_type: test review
review_object: V2 frontend remediation test design/development
baseline_documents:
  - docs/baselines/v2/IR-FRONTEND-REMEDIATION.md
  - docs/baselines/v2/SR-FRONTEND-REMEDIATION.md
  - docs/baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md
reviewed_artifacts:
  - docs/baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md
  - tests/test_web.py
  - tests/test_demo_scripts.py
  - tests/test_v2_runtime.py
  - tests/test_contract_artifacts.py
  - scripts/run_v2_acceptance_smoke.py
  - outputs/logs/v2_frontend_traceability_check.json
  - outputs/logs/v2_frontend_browser_evidence.json
scope:
  - verify test coverage and automation credibility for frontend remediation ACs
  - verify negative-state, multi-mention, safe projection, browser evidence, traceability, and documentation hygiene gates
out_of_scope:
  - V2 final acceptance closure
  - real DV production API integration
  - real LLM live smoke as default regression
allowed_commands:
  - python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py
  - python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py
  - python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs
expected_output:
  - independent read-only test review record with P0/P1/P2/P3 findings
```

## 当前结论

测试设计与测试开发阶段已完成；独立测试评审发现的 P1 已接受、处置并通过独立闭环验证。当前可进入验收候选前反向核查；反向核查未完成前，V2 仍保持 blocked，不能进入最终验收关闭。
