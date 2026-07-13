# DVEntityLinking V2 前端视觉风格补救代码实现记录

---

> 文档治理说明：本文承接已闭环的 [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)，记录本轮 V2 前端视觉风格补救代码实现、测试和证据输出。独立实现评审、评审处置和闭环验证已完成；本文不是测试设计、测试评审或验收记录。V2 仍不得 accepted/closed。

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 特性名称 | V2 frontend visual remediation implementation |
| 版本号 | V2-FE-VIS-IMPL.2-closure-verified |
| 日期 | 2026-06-02 |
| 实现人 | Codex |
| 状态 | 实现评审闭环已通过，待测试设计/开发 |

## 输入基线

| 类型 | 文件 |
| --- | --- |
| 需求分析 | [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md) |
| 需求评审处置 | [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| 需求闭环验证 | [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |
| 功能设计 | [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md), `V2-FE-VIS-SR.2-closed` |
| 功能设计评审 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| 功能设计评审处置 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md) |
| 功能设计闭环验证 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| 实现评审 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) |
| 实现评审处置 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| 实现评审闭环验证 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |

## 实现范围

| 文件 | 实现内容 |
| --- | --- |
| `src/dv_entity_linking/web.py` | 将 V2 页面重构为 visual workbench shell：`visual-workbench-shell`、`status-band`、`query-command-zone`、`result-stream`、`entity-detail-zone`、`llm-explanation-component`、`catalog-filter-zone`；新增工作台状态带、三列桌面网格、窄屏稳定栈式布局、prototype absorption labels、mention/candidate/catalog 选中态、LLM component kicker、文本换行和无横向溢出约束。 |
| `src/dv_entity_linking/web.py` | 保留旧 `runtime-status`、`query-panel`、`result-summary`、`mention-summary`、`candidate-list`、`entity-detail`、`entity-catalog`、`retrieval-result`、`llm-safe-explanation-panel` 等契约锚点；页面启动后自动用当前 Query 执行一次前端 link，保证服务端预渲染内容和 JS selection state/事件监听器接通。 |
| `scripts/run_v2_acceptance_smoke.py` | 增加 V2 视觉证据必需 browser checks：`visual_workbench_shell_observed`、`status_band_observed`、`query_command_zone_observed`、`result_stream_observed`、`llm_explanation_component_observed`、`catalog_filter_zone_observed`、`no_text_overlap_or_clipping_narrow`。 |
| `scripts/run_v2_acceptance_smoke.py` | 生成新视觉追踪证据 `outputs/logs/v2_frontend_visual_traceability_check.json` 和 `.md`，schema 固定为 `v2.frontend_visual_traceability.1`；记录 `items[].ac_ids`、`summary.blocking_ac_ids`、`d003_content_inventory[]`、`manual_user_acceptance_status=pending`。 |
| `tests/test_web.py` | 增加前端视觉锚点、prototype absorption labels、布局 CSS、mention/candidate card 语义和文本换行约束断言。 |
| `tests/test_demo_scripts.py` | 增加视觉 browser evidence required checks 和 visual traceability artifact 断言，确认 `visual_traceability_statuses=["implemented","needs_user_decision"]`，且 `AC-V2-FE-VIS-007`、`AC-V2-FE-VIS-008` 因用户视觉接受和 before/after 对比仍阻塞。 |

## AC 覆盖

| AC | 实现/证据状态 | 说明 |
| --- | --- | --- |
| AC-V2-FE-VIS-001 | implemented | 视觉实现明确吸收 SigNoz、OpenGenerativeUI、Tambo 的信息密度、结构化解释组件和 schema/state 可追踪原则。 |
| AC-V2-FE-VIS-002 | implemented | 桌面 `1366x768` 形成 cohesive workbench shell，含 status band、command zone、result stream、detail/explanation zone 和 catalog filter zone。 |
| AC-V2-FE-VIS-003 | implemented | mention/candidate/entity detail/catalog/LLM explanation 的 selection state 可见，第二个 mention `CPU Usage` 可联动 `DV-KPI-MTK-001`。 |
| AC-V2-FE-VIS-004 | implemented | `llm-explanation-component` 展示 context、stage summary、safe explanation、fallback/offline empty state。 |
| AC-V2-FE-VIS-005 | implemented | 页面仍只展示 safe projection、empty config placeholders 和 redacted/safe summary，不输出真实 secret、token、raw prompt、raw response 或完整 LLM 日志。 |
| AC-V2-FE-VIS-006 | implemented | Web demo 启动入口继续只维护 `scripts/run_web_demo.py`；未新增版本专用 web 启动脚本。 |
| AC-V2-FE-VIS-007 | needs_user_decision | 自动化截图、browser evidence 和 visual artifact 已生成，但顶层 `manual_user_acceptance_status=pending`，验收关闭前必须由用户视觉确认。 |
| AC-V2-FE-VIS-008 | needs_user_decision | 本轮已生成 after 桌面/窄屏截图和视觉 artifact，但 before/after 人工视觉对比仍需作为验收候选前门禁补齐。 |
| AC-V2-FE-VIS-009 | implemented | `d003_content_inventory[]` 无 `needs_d003_confirmation=true`；新增工作台文案均为 synthetic UI copy、project-safe copy 或已确认 V2 样例。 |

## 浏览器证据

| 证据 | 路径/结果 |
| --- | --- |
| Browser evidence JSON | `outputs/logs/v2_frontend_browser_evidence.json`, `ok=true` |
| Desktop screenshot | `outputs/logs/v2_frontend_desktop_1366x768.png` |
| Narrow screenshot | `outputs/logs/v2_frontend_narrow_390x844.png` |
| Visual traceability JSON | `outputs/logs/v2_frontend_visual_traceability_check.json`, `schema_version=v2.frontend_visual_traceability.1` |
| Visual traceability MD | `outputs/logs/v2_frontend_visual_traceability_check.md` |
| Browser checks | `all_sections_visible=true`、`visual_workbench_shell_observed=true`、`status_band_observed=true`、`query_command_zone_observed=true`、`result_stream_observed=true`、`llm_explanation_component_observed=true`、`catalog_filter_zone_observed=true`、`multi_mention_observed=true`、`second_mention_selected=true`、`candidate_and_entity_detail_observed=true`、`llm_explanation_observed=true`、`catalog_filter_observed=true`、`card_text_readable=true`、`debug_collapsed=true`、`no_section_overlap=true`、`no_horizontal_overflow=true`、`no_text_overlap_or_clipping_narrow=true` |

## 验证命令

| 命令 | 结果 |
| --- | --- |
| `python -m py_compile src\dv_entity_linking\web.py` | 通过 |
| `python -m py_compile scripts\run_v2_acceptance_smoke.py` | 通过 |
| `python -m pytest -p no:cacheprovider tests\test_web.py` | 通过，`12 passed` |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_web.py` | 通过，`13 passed` |
| `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` | 通过，`ok=true`、`browser_evidence_ok=true`、`browser_evidence_fresh=true`、`visual_traceability_statuses=["implemented","needs_user_decision"]`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_contract_artifacts.py` | 实现评审处置后通过，`6 passed`；覆盖 FE-VIS-IMPL-001 至 FE-VIS-IMPL-003 的 schema、单 Web 入口和截图图片/尺寸校验。 |
| `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` | 实现评审处置后通过，`browser_screenshot_images_valid=true`、`browser_screenshot_dimension_checks.desktop_1366x768=true`、`browser_screenshot_dimension_checks.narrow_390x844=true`。 |
| no-context 独立闭环验证 Sagan | FE-VIS-IMPL-001、FE-VIS-IMPL-002、FE-VIS-IMPL-003 均 Closed；记录见 [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)。 |
| `python -m pytest -p no:cacheprovider` | 通过，`75 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 实现偏差说明

| 项 | 结论 |
| --- | --- |
| 后端 API 语义 | 未改变；`/api/link` 仍以 `mention_results[]` 作为权威多 mention projection，视觉层只通过 adapter/renderer 消费。 |
| `/api/entities/<id>` 错误语义 | 未改变；仍保留现有 `status=no_match`、`no_match_reason` 语义。 |
| Web 启动入口 | 未新增脚本；继续只维护 `scripts/run_web_demo.py`。 |
| 真实 DV 内容 | 未新增真实 DV 字段、接口、拓扑、生产 metric label 或真实 runtime payload。 |
| 验收语义 | 未把 `manual_user_acceptance_status=pending` 伪装为 pass；visual artifact 明确阻塞验收关闭。 |

## 残余风险和下一门禁

| 风险 | 状态 | 下一步 |
| --- | --- | --- |
| 独立实现评审闭环 | 已通过 | FE-VIS-IMPL-001 至 FE-VIS-IMPL-003 均 Closed；下一步进入测试设计/开发。 |
| 用户视觉接受未完成 | 阻塞 accepted/closed | 用户需在浏览器/截图基础上确认视觉风格是否接受；确认前 `AC-V2-FE-VIS-007` 保持阻塞。 |
| before/after 人工视觉对比未完成 | 阻塞验收候选关闭 | 验收候选前需对比旧白卡片表单堆叠和当前 workbench shell，并记录结论；确认前 `AC-V2-FE-VIS-008` 保持阻塞。 |
| V2 整体状态 | 仍 blocked | 测试设计/开发、测试评审闭环、验收候选前反向核查、before/after 对比和用户视觉确认均完成前，不得 accepted/closed。 |
