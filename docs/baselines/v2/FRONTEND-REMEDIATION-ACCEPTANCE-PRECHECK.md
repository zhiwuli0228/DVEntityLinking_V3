# DVEntityLinking V2 前端改造补救验收候选前反向核查记录

日期：2026-06-02

状态：acceptance precheck independently verified，可进入验收候选准备。

## 目的

本记录执行 DV 流程中的“验收候选前反向核查”：从用户确认项倒查到 IR、SR、实现文件、测试用例和验收 evidence，确认 V2 前端补救没有再次静默降级为 Web/API projection。

本记录不声明 V2 accepted，也不关闭 V2。

## 输入

| 类型 | 文件/证据 |
| --- | --- |
| 用户决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| 前端补救需求 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 前端补救功能设计 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| 实现评审闭环 | [FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| 测试评审闭环 | [FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md) |
| 反向核查独立核验 | [FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md](./FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md) |
| 反向核查 JSON | `outputs/logs/v2_frontend_traceability_check.json` |
| 反向核查 Markdown | `outputs/logs/v2_frontend_traceability_check.md` |
| Browser evidence | `outputs/logs/v2_frontend_browser_evidence.json`、`outputs/logs/v2_frontend_desktop_1366x768.png`、`outputs/logs/v2_frontend_narrow_390x844.png` |

## 核查方法

- 执行 `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs`，生成最新 traceability artifact。
- 校验 `traceability_statuses == ["implemented"]`、`traceability_downgraded_count == 0`。
- 校验 P0/P1 AC-V2-FE-001 至 AC-V2-FE-009 均为 `implemented`。
- 校验关键用户确认决策 D024、D028、D041、D042、D043、D003 均在 traceability artifact 中有实现、测试和 evidence 映射。

## 反向核查结果

| 决策来源 | 用户确认项 | AC | 实现 | 测试/evidence | 结果 |
| --- | --- | --- | --- | --- | --- |
| D024 | V2 前端采用运维工作台式演示，不做过度产品化 | AC-V2-FE-001、AC-V2-FE-007 | `src/dv_entity_linking/web.py` | `tests/test_web.py::test_web_ui_visibility_smoke`、browser evidence `all_sections_visible` / `debug_collapsed` | pass |
| D024、D043 | Query、mention、候选、实体详情和 LLM 交互式解释可见 | AC-V2-FE-002、003、005、006 | `src/dv_entity_linking/web.py` | `test_web_api_link_exposes_workbench_safe_projection`、browser evidence `llm_explanation_observed` | pass |
| D028、D043 | V2 必须支持多 mention Query，且前端可观察 | AC-V2-FE-002、003 | `src/dv_entity_linking/web.py` | `tests/test_v2_runtime.py`、browser evidence `second_mention_selected` / `candidate_and_entity_detail_observed` | pass |
| D043 | no_match / not_required 不展示伪候选或伪 linked entity | AC-V2-FE-004 | `src/dv_entity_linking/web.py`、`scripts/run_v2_acceptance_smoke.py` | `test_web_api_negative_states_do_not_emit_pseudo_entities`、traceability item `AC-V2-FE-004` | pass |
| D042、D043 | 前端改造不得静默降级为 Web/API projection | AC-V2-FE-008、009 | `scripts/run_v2_acceptance_smoke.py`、`src/dv_entity_linking/web.py` | `v2_frontend_traceability_check.json/.md`、browser evidence freshness | pass |
| D041 | Web demo 只维护 `scripts\run_web_demo.py` 一个入口 | AC-V2-FE-001、008 | `scripts/run_web_demo.py`、`docs/USAGE.md` | `test_web_demo_script_has_pycharm_friendly_help`、contract docs test、traceability item `D041` | pass |
| D003、D042 | 敏感配置和完整 LLM 请求响应不得展示或提交 | AC-V2-FE-006、008 | `src/dv_entity_linking/web.py` | safe attributes tests、debug collapsed、smoke log no raw sensitive fields | pass |

## 本次核查发现和处置

| ID | 发现 | 处置 | 当前状态 |
| --- | --- | --- | --- |
| PRECHECK-001 | 初次核查发现 `v2_frontend_traceability_check.json` 未单独覆盖 D041“只维护 `scripts\run_web_demo.py` 一个入口”。 | `scripts/run_v2_acceptance_smoke.py` 新增 D041 traceability item 和 `traceability_decision_d041_status`；`tests/test_demo_scripts.py` 新增断言；重新执行 smoke 后 `traceability_decision_d041_status=implemented`。 | closed |

## 命令和结果

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline` | 通过，`1 passed` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`traceability_decision_d041_status=implemented`、`traceability_ac_v2_fe_004_status=implemented`、`traceability_downgraded_count=0`、`browser_evidence_ok=true`、`browser_evidence_fresh=true` |

## 结论

验收候选前反向核查已完成本地修复和证据刷新，且独立只读核验已通过，未发现未实现、降级或需用户确认项。当前可以进入 V2 前端补救验收候选准备；最终 accepted/closed 仍需用户确认。
