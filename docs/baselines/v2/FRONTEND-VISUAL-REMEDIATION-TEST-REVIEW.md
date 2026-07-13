# DVEntityLinking V2 前端视觉风格补救测试独立评审记录

日期：2026-06-04

状态：ready for disposition。本文为 no-context 独立只读评审记录，不是评审处置、闭环验证、验收候选或版本关闭记录。

## 基本信息

| 项 | 内容 |
| --- | --- |
| 评审类型 | test artifact review |
| 评审对象 | [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) |
| 评审人 | no-context independent reviewer Epicurus |
| 评审模式 | no-context，只读；不继承本轮聊天上下文 |
| 结论 | ready for disposition；无 P0，2 个 P1，1 个 P2 |

## 评审输入

| 类别 | 输入 |
| --- | --- |
| 测试设计/开发记录 | [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) |
| 需求/设计基线 | [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)、[SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) |
| 实现与评审链 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md)、[FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md)、[FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)、[FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| 当前状态文档 | [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md)、[../../current/DECISIONS.md](../../current/DECISIONS.md) |
| 测试与脚本 | `tests/test_web.py`、`tests/test_demo_scripts.py`、`tests/test_contract_artifacts.py`、`scripts/run_v2_acceptance_smoke.py`、`scripts/run_web_demo.py` |
| Evidence | `outputs/logs/v2_frontend_browser_evidence.json`、`outputs/logs/v2_frontend_visual_traceability_check.json` |

## 评审方法

- 按 [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) 中 `TC-V2-FE-VIS-001` 至 `TC-V2-FE-VIS-009` 与 AC 映射逐项交叉核对。
- 检查 implementation-level tests、black-box smoke/artifact tests、contract docs tests 和 browser-equivalent evidence 的层级边界。
- 复核 `manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007/008` blocking 语义是否被保留。
- 只运行允许的只读验证命令；未修改任何文件。

## Findings

### P0

未发现。

### P1

| ID | Finding |
| --- | --- |
| FE-VIS-TEST-001 | Issue -> 截图校验未充分证明“可由 image decoder 解码”。 Current artifact behavior -> 测试设计要求伪 PNG/任意字节必须失败；但 validator 对 PNG 仅检查 magic bytes 并读取 IHDR 宽高，未校验 CRC、IDAT/IEND 或真实解码。负例测试只覆盖 `b"not-a-decodable-image"`，未覆盖“带合法 PNG 头和尺寸、但无有效图像数据”的伪 PNG。 Impact -> browser evidence 可能被弱图片头部伪造绕过，削弱 TC-V2-FE-VIS-003/007/008 的视觉证据可信度。 Recommended correction -> 使用真实图片解码库或完整 PNG/JPEG 结构校验；新增“合法头部但不可解码”负例，确保 `browser_evidence_ok=false` 且 AC-V2-FE-VIS-007/008 继续 blocking。 |
| FE-VIS-TEST-002 | Issue -> D003/content inventory 覆盖仍偏静态，未达到 SR 要求的 HTML/API/artifact/logs 扫描强度。 Current artifact behavior -> `d003_content_inventory[]` 由脚本硬编码 3 类条目；`safe_content_ok` 主要扫描 HTML 中少量 forbidden substrings；测试覆盖了 entity detail 的 unsafe attributes 负例，但未系统扫描 `/api/status`、`/api/link`、`/api/entities`、`/api/entities/<id>`、`/api/retrieve` 或 smoke/artifact 文案来源。 Impact -> 新增真实感 DV copy、metric/topology/interface label、raw prompt/base URL/token-like value 可能未进入 inventory，也未触发 `needs_d003_confirmation=true`，影响 AC-V2-FE-VIS-005/009 的测试可信度。 Recommended correction -> 增加离线 Flask/API 扫描和 artifact/log 扫描；由扫描结果生成或核对 inventory；补 raw prompt、真实 base URL、token-like、未确认真实感 label 的负例，并要求 AC-V2-FE-VIS-009 blocking。 |

### P2

| ID | Finding |
| --- | --- |
| FE-VIS-TEST-003 | Issue -> blocker 语义主要依赖 `item.status != implemented`，未独立断言 forbidden downgrade classification 必阻塞。 Current artifact behavior -> 当前产物正确保持 `manual_user_acceptance_status=pending`，且 AC-V2-FE-VIS-007/008 blocking；但 summary blocking 计算没有单独基于 `weak_marker_only/api_only/no_visual_delta/needs_user_decision` 做防漂移断言。 Impact -> 未来 schema 或生成逻辑漂移时，可能出现 `status=implemented` 但 `downgrade_classification=api_only` 仍未阻塞的弱证明组合。 Recommended correction -> 增加 contract/smoke 负例：任一 forbidden downgrade classification 必须导致 `accepted_closed_allowed=false`、`blocking_count>0`，并映射到相应 AC。 |

### P3

未发现。

## 视角摘要

| 视角 | 摘要 |
| --- | --- |
| 需求/设计覆盖 | `TC-V2-FE-VIS-001` 至 `TC-V2-FE-VIS-009` 均在测试设计中映射；`TC-V2-FE-VIS-007/008` 的人工视觉接受和 before/after gate 未被过度声明为完成。 |
| 测试层级边界 | `test_web.py`、`test_demo_scripts.py`、`test_contract_artifacts.py` 分层基本清楚；browser evidence 未被直接等同为最终用户视觉接受。 |
| 可执行证据 | 已验证 smoke 和指定 pytest slice 通过。 |
| 视觉 blocker 严格性 | 当前 `manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007/008` blocking 语义有效；仍建议补 downgrade 漂移负例。 |
| 残余门禁 | before/after 人工对比、用户视觉接受、测试评审处置和后续独立验证仍是硬门禁；当前证据不得 overclaim final visual acceptance。 |

## 已运行命令

| 命令 | 结果 |
| --- | --- |
| `python scripts/run_v2_acceptance_smoke.py --log-dir outputs/logs` | 通过；`ok=true`、`browser_evidence_ok=true`、`browser_screenshot_images_valid=true`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |
| `python -m pytest -p no:cacheprovider tests/test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests/test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots tests/test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries tests/test_contract_artifacts.py` | 通过，`8 passed` |

## Disposition Readiness

结论：ready for disposition。存在 P1 findings，需本轮处置后再进入测试闭环验证；当前不能宣称测试 closure、V2 accepted/closed 或最终用户视觉接受。
