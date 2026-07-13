# DVEntityLinking V2 前端视觉风格补救测试设计与测试开发记录

日期：2026-06-04

状态：test review closure verified，待 before/after 对比和用户视觉接受。V2 not accepted/closed。

> 文档治理说明：本文承接已闭环的 [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md) 和 [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)，记录本轮 V2 前端视觉风格补救的测试设计、测试开发和测试证据映射。本文不是测试评审、闭环验证、验收候选或版本关闭记录。

## 测试模式

本记录合并三类测试工作：

- test plan only：形成视觉风格补救测试用例、覆盖矩阵、门禁语义和证据映射。
- automation implementation：补充或确认自动化测试、smoke artifact 检查、browser evidence 图片/尺寸校验、visual traceability blocker 检查和单一 Web 入口回归。
- execution/reporting：记录已执行命令、结果和产物；未完成的人工视觉接受与 before/after 对比保持阻塞。

## 输入基线

| 类型 | 文件 | 状态 |
| --- | --- | --- |
| 前端视觉风格补救需求 | [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md) | `V2-FE-VIS.2-closed` |
| 前端视觉风格补救功能设计 | [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) | `V2-FE-VIS-SR.2-closed` |
| 需求评审闭环 | [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) | closed with recorded residual risk |
| 功能设计评审闭环 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) | closed with recorded residual risk |
| 代码实现记录 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md) | implementation completed |
| 实现评审 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) | ready for disposition |
| 实现评审处置 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md) | accepted findings applied |
| 实现评审闭环 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) | implementation review findings closed with recorded residual acceptance gates |

## 范围

本轮测试覆盖：

- SigNoz、OpenGenerativeUI、Tambo 调研原则到 UI/state/evidence 的可追踪映射。
- `1366x768` 桌面首屏 workbench shell、status band、query command zone、result stream、entity detail zone、LLM explanation component 和 catalog filter zone。
- `390x844` 窄屏布局顺序、无横向溢出、无关键文本重叠或不可读裁剪。
- 多 mention Query 中 `CPU Usage` 到 `DV-KPI-MTK-001` 的 mention/candidate/entity detail/LLM explanation 联动。
- LLM safe explanation 的 global、mention、candidate context states。
- D003 内容边界、`d003_content_inventory[]`、safe projection、Mock/真实 DV 内容边界和 forbidden value 不外露。
- `outputs/logs/v2_frontend_visual_traceability_check.json` 的 schema、blocking AC、downgrade classification 和 manual user acceptance gate。
- before/after canonical screenshot metadata 与人工视觉对比门禁。
- 用户要求的单一 Web demo 入口：只维护 `scripts/run_web_demo.py`，不得新增版本专用 web demo 启动脚本。

不覆盖：

- V2 最终验收通过、accepted/closed 或发布关闭。
- 用户视觉接受结论；当前仍为 `manual_user_acceptance_status=pending`。
- before/after 人工视觉对比结论；当前 `AC-V2-FE-VIS-008` 仍阻塞。
- 真实 DV 生产接口直连或生产级前端框架迁移。
- 真实 LLM live smoke 常态化；默认仍为 offline demo。

## 测试分层

| 层级 | 测试资产 | 说明 |
| --- | --- | --- |
| Independent contract test | `tests/test_contract_artifacts.py` | 验证文档导航、阶段状态、关键基线、测试设计记录和门禁记录一致。 |
| Implementation-level integration test | `tests/test_web.py` | 调用 Flask/API 和页面 HTML，验证视觉锚点、safe projection、负例语义、D003/forbidden attributes 边界。 |
| Black-box artifact test | `tests/test_demo_scripts.py` | 执行 V2 smoke，检查输出 JSON/MD、traceability、browser evidence、图片/尺寸校验和单一 Web 入口。 |
| Browser-equivalent evidence | `outputs/logs/v2_frontend_browser_evidence.json` 和截图 | 记录桌面/窄屏截图、必需 checks、freshness、可解码图片和尺寸下限。 |
| Visual traceability evidence | `outputs/logs/v2_frontend_visual_traceability_check.json` 和 `.md` | 记录 `items[].ac_ids`、`summary.blocking_ac_ids`、`d003_content_inventory[]`、`manual_user_acceptance_status=pending`。 |

## 测试用例总览

| ID | 名称 | 覆盖 AC | 优先级 | 自动化状态 |
| --- | --- | --- | --- | --- |
| TC-V2-FE-VIS-001 | Prototype principle to UI/state/evidence mapping | AC-V2-FE-VIS-001 | P0 | automated + artifact |
| TC-V2-FE-VIS-002 | Desktop first viewport visual shell check | AC-V2-FE-VIS-002、AC-V2-FE-VIS-008 | P0 | browser-equivalent + smoke validator |
| TC-V2-FE-VIS-003 | Narrow viewport overflow, clipping, and flow check | AC-V2-FE-VIS-002、AC-V2-FE-VIS-008 | P1 | browser-equivalent + smoke validator |
| TC-V2-FE-VIS-004 | CPU Usage mention to DV-KPI-MTK-001 linkage | AC-V2-FE-VIS-003 | P0 | automated + browser-equivalent |
| TC-V2-FE-VIS-005 | LLM explanation component global/mention/candidate states | AC-V2-FE-VIS-004 | P1 | automated + browser-equivalent |
| TC-V2-FE-VIS-006 | D003 forbidden content inventory and mock boundary scan | AC-V2-FE-VIS-005、AC-V2-FE-VIS-009 | P0 | automated + artifact |
| TC-V2-FE-VIS-007 | Visual traceability artifact schema and blocker check | AC-V2-FE-VIS-007 | P0 | automated smoke validator |
| TC-V2-FE-VIS-008 | Before/after canonical screenshot metadata check | AC-V2-FE-VIS-008 | P0 | partial automated, user decision blocked |
| TC-V2-FE-VIS-009 | Single `run_web_demo.py` entry regression | AC-V2-FE-VIS-006 | P0 | automated |

## 用例到自动化映射

| 测试用例 | 自动化/证据 |
| --- | --- |
| TC-V2-FE-VIS-001 | `tests/test_web.py::test_web_ui_visibility_smoke`、`outputs/logs/v2_frontend_visual_traceability_check.json` prototype absorption items |
| TC-V2-FE-VIS-002 | `outputs/logs/v2_frontend_browser_evidence.json` required checks: `visual_workbench_shell_observed`、`status_band_observed`、`query_command_zone_observed`、`result_stream_observed`、`llm_explanation_component_observed`、`catalog_filter_zone_observed`、`all_sections_visible` |
| TC-V2-FE-VIS-003 | Browser evidence required checks: `no_section_overlap`、`no_horizontal_overflow`、`no_text_overlap_or_clipping_narrow`、`card_text_readable`；smoke validates screenshots as structurally valid images with expected dimensions；`tests/test_demo_scripts.py::test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots` rejects PNG headers without decodable IDAT image data |
| TC-V2-FE-VIS-004 | `tests/test_web.py::test_web_api_link_exposes_workbench_safe_projection`、browser evidence `second_mention_selected=true`、`candidate_and_entity_detail_observed=true` |
| TC-V2-FE-VIS-005 | `tests/test_web.py::test_web_api_link_exposes_workbench_safe_projection`、browser evidence `llm_explanation_observed=true` |
| TC-V2-FE-VIS-006 | `tests/test_web.py::test_web_entity_detail_uses_safe_attributes`、`tests/test_web.py::test_web_entity_detail_omits_forbidden_attributes_and_values`、runtime D003 scan over HTML/API/artifact/log evidence、visual traceability `d003_content_inventory[]`、`tests/test_demo_scripts.py::test_v2_visual_d003_scan_flags_runtime_sensitive_values` |
| TC-V2-FE-VIS-007 | `tests/test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline`、`tests/test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots`、`tests/test_demo_scripts.py::test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance` |
| TC-V2-FE-VIS-008 | `scripts/run_v2_acceptance_smoke.py --log-dir outputs\logs` asserts `manual_user_acceptance_status=pending` and `AC-V2-FE-VIS-008` remains blocking until before/after comparison is accepted |
| TC-V2-FE-VIS-009 | `tests/test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries`、`scripts/run_v2_acceptance_smoke.py::_web_demo_single_entry_ok` |

## 关键用例细节

### TC-V2-FE-VIS-003 窄屏布局与截图有效性

输入：canonical scenario 在 `390x844` viewport 下打开并滚动。

预期：

- 关键区域按 query/result/detail/explanation/catalog 顺序稳定展示。
- 无横向 overflow；无关键文本重叠或不可读裁剪。
- 截图文件必须存在、非空、可由 image decoder 解码，且尺寸符合 desktop/narrow 期望。
- 若截图只是伪 PNG 或任意字节，smoke 必须失败，且不能把 visual traceability 当作可验收证据。
- 若截图只有合法 PNG signature/IHDR/IEND、但没有可解压 IDAT image data，smoke 必须失败。

证据：

- `tests/test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots`
- `tests/test_demo_scripts.py::test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots`
- `browser_screenshot_images_valid=false` 时 `browser_evidence_ok=false`
- `visual_traceability_blocking_ac_ids` 至少包含 `AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008`

### TC-V2-FE-VIS-004 多 mention 视觉联动

输入：`Check ALM-51020 and CPU Usage.`

预期：

- mention strip 至少包含 `ALM-51020` 和 `CPU Usage`。
- 选择第二个 mention 后候选面板显示 `DV-KPI-MTK-001 CPU Usage`。
- 实体详情面板同步显示 `DV-KPI-MTK-001`。
- LLM safe explanation 面板切换为 candidate 级 `CPU Usage` 解释。

证据：`outputs/logs/v2_frontend_browser_evidence.json` 中 `second_mention_selected=true`、`candidate_and_entity_detail_observed=true`、`llm_explanation_observed=true`。

### TC-V2-FE-VIS-006 D003 内容边界

预期：

- 页面和 API 只展示 synthetic UI copy、project-safe copy 或已确认 V2 样例。
- `d003_content_inventory[]` 不得出现 `needs_d003_confirmation=true`。
- forbidden key、token-like value、raw prompt、raw response、完整 LLM 日志和真实 secret 不外露。
- D003 runtime scan 必须覆盖 HTML、`/api/status`、`/api/samples`、`/api/entities`、`/api/entities/<id>`、`/api/retrieve`、多类 `/api/link` payload、traceability artifact 和 smoke log；如发现 raw payload key、concrete base URL、authorization bearer 或 secret-like token，必须产生 `needs_d003_confirmation=true`。
- 如新增真实感 DV 内容，必须回到需求确认，不能由测试或实现阶段静默通过。

证据：`tests/test_web.py::test_web_entity_detail_omits_forbidden_attributes_and_values`、`tests/test_demo_scripts.py::test_v2_visual_d003_scan_flags_runtime_sensitive_values`、visual traceability artifact。

### TC-V2-FE-VIS-007/008 验收门禁

预期：

- Visual traceability schema 固定为 `v2.frontend_visual_traceability.1`。
- `manual_user_acceptance_status=pending` 时，`AC-V2-FE-VIS-007` 必须保持 blocking。
- before/after 人工视觉对比未完成时，`AC-V2-FE-VIS-008` 必须保持 blocking。
- 不允许通过 `weak_marker_only`、`api_only`、`no_visual_delta` 或伪图片 evidence 降级替代视觉证据。
- 任一 P0/P1 item 即使 `status=implemented`，只要 `downgrade_classification` 属于 forbidden downgrade set，仍必须阻塞验收关闭。

证据：`scripts/run_v2_acceptance_smoke.py --log-dir outputs\logs` 输出 `visual_traceability_statuses=["implemented","needs_user_decision"]`，且 blocking AC 包含 `AC-V2-FE-VIS-007`、`AC-V2-FE-VIS-008`；`tests/test_demo_scripts.py::test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance` 覆盖 forbidden downgrade 漂移负例。

### TC-V2-FE-VIS-009 单一 Web Demo 入口

预期：

- 只维护 `scripts/run_web_demo.py` 作为 web demo 启动入口。
- 不允许新增 `run_v2_web_demo.py`、`run_v3_web_demo.py` 等版本专用 web 启动脚本。
- 每个版本通过 `run_web_demo.py` 的参数、默认数据和内容切换承载。

证据：`tests/test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries`。

## 执行记录

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots tests\test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries` | 初始测试设计/开发后通过，`2 passed` |
| `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` | 测试评审处置后通过，`ok=true`、`browser_screenshot_images_valid=true`、`d003_scan_ok=true`、`d003_scan_finding_count=0`、`visual_traceability_statuses=["implemented","needs_user_decision"]`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py` | 测试评审处置后通过，`12 passed` |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots tests\test_demo_scripts.py::test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots tests\test_demo_scripts.py::test_v2_visual_d003_scan_flags_runtime_sensitive_values tests\test_demo_scripts.py::test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance tests\test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries` | 测试评审处置后通过，`6 passed` |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots tests\test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries tests\test_contract_artifacts.py` | 初始测试设计/开发后通过，`8 passed` |
| `python -m pytest -p no:cacheprovider` | 初始测试设计/开发后通过，`77 passed`；测试评审处置后通过，`80 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `python scripts\run_v1_evaluation.py` | 通过，`total=16`、`pass=16`、`precision=1.0`、`recall=1.0` |
| `python scripts\run_v2_evaluation.py` | 通过，`total=12`、`pass=12`、`precision=1.0`、`recall=1.0` |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 残余门禁

| 门禁 | 当前状态 | 说明 |
| --- | --- | --- |
| 独立测试评审 | completed | 记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md)，无 P0，2 个 P1，1 个 P2。 |
| 测试评审处置 | completed | 记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)，3 个 finding 均 Accepted 并完成处置。 |
| 测试评审闭环验证 | completed | 记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)，FE-VIS-TEST-001 至 FE-VIS-TEST-003 均 Closed。 |
| `AC-V2-FE-VIS-007` | blocking | `manual_user_acceptance_status=pending`；用户视觉接受未完成。 |
| `AC-V2-FE-VIS-008` | blocking | before/after canonical visual comparison 未人工接受。 |
| V2 accepted/closed | blocked | before/after 对比、用户视觉接受和验收候选前核查完成前不得关闭。 |

## 独立测试评审输入包

请独立测试评审者只读复核以下输入：

- [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md)
- [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md)
- [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)
- [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)
- [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)
- [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md)
- [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md)
- [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)
- [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)
- [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- `tests/test_web.py`
- `tests/test_demo_scripts.py`
- `tests/test_contract_artifacts.py`
- `scripts/run_v2_acceptance_smoke.py`
- `scripts/run_web_demo.py`
- `outputs/logs/v2_frontend_browser_evidence.json`
- `outputs/logs/v2_frontend_visual_traceability_check.json`

## 结论

V2 前端视觉风格补救测试设计/开发、测试评审处置和独立闭环验证已完成。当前自动化已新增伪图片截图失败回归、结构伪 PNG 截图失败回归、D003 runtime sensitive value 扫描负例、forbidden downgrade blocker 负例和单一 Web demo 入口回归，且保留 `manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007`、`AC-V2-FE-VIS-008` 的验收阻塞语义。V2 仍 not accepted/closed。
