# DVEntityLinking V2 前端视觉风格补救验收前置核查记录

日期：2026-06-04

状态：acceptance precheck partially passed，after 视觉证据已补采且用户已 accepted；before 同场景截图或替代 before 证据口径仍缺失。本文不是验收候选或版本关闭记录。

## 基本信息

| 项 | 内容 |
| --- | --- |
| 前置核查对象 | V2 前端视觉风格补救验收门禁 |
| 输入基线 | [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)、[SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)、[FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md) |
| Web 入口 | `scripts/run_web_demo.py --host 127.0.0.1 --port 5015 --mode offline_demo --log-dir outputs/logs` |
| Canonical query | `Check ALM-51020 and CPU Usage.` |
| Canonical viewports | desktop `1366x768`、narrow `390x844` |
| 当前结论 | after 证据已补采且用户已 accepted，`AC-V2-FE-VIS-007` 可关闭；`AC-V2-FE-VIS-008` 仍 blocking |

## 核查范围

| 范围项 | 结果 |
| --- | --- |
| 单一 Web demo 入口 | Passed；仅使用 `scripts/run_web_demo.py` 启动。 |
| 当前 after 桌面截图 | Passed；已采集 `outputs/logs/v2_visual_acceptance_after_desktop_1366x768.png`。 |
| 当前 after 窄屏截图 | Passed；已采集 `outputs/logs/v2_visual_acceptance_after_narrow_390x844.png`。 |
| after 页面结构 | Passed；浏览器现场检查存在 `visual-workbench-shell`、`status-band`、`query-command-zone`，页面可见 `CPU Usage` 和 `DV-KPI-MTK-001`。 |
| 窄屏横向溢出 | Passed；`390x844` 下 `hasHorizontalOverflow=false`。 |
| before 同场景截图 | Blocked；当前仓库和 `outputs/logs` 未发现旧版同 canonical query、同 viewport、同选中态的 before 截图。 |
| 用户视觉接受 | Passed；用户已确认“当前 after 视觉可以 accepted”，`manual_user_acceptance_status=accepted`。 |

## After 视觉证据

| 视口 | 截图 | 浏览器采样结果 |
| --- | --- | --- |
| `1366x768` | `outputs/logs/v2_visual_acceptance_after_desktop_1366x768.png` | `innerWidth=1366`、`innerHeight=768`、`hasWorkbench=true`、`hasStatusBand=true`、`hasQueryZone=true`、`textIncludesCpu=true`、`textIncludesKpi=true` |
| `390x844` | `outputs/logs/v2_visual_acceptance_after_narrow_390x844.png` | `innerWidth=390`、`innerHeight=844`、`scrollWidth=375`、`clientWidth=375`、`hasHorizontalOverflow=false`、`hasWorkbench=true`、`hasStatusBand=true`、`hasQueryZone=true` |

## Before/After 门禁判断

| AC | 要求 | 当前判断 |
| --- | --- | --- |
| `AC-V2-FE-VIS-007` | 验收候选前必须提供桌面/窄屏截图、visual traceability artifact、自动化布局/语义检查和用户视觉验收确认。 | Passed；after 截图、traceability、自动化检查和用户视觉 accepted 均已具备，可关闭该项。 |
| `AC-V2-FE-VIS-008` | 验收证据必须包含 before/after 对比，说明改造后不再是普通白卡片表单堆叠。 | Blocked；after 截图和用户此前对旧页面的文字复核结论存在，但缺少旧版同场景 before 截图，不能按已闭环需求关闭。 |

## 用户确认请求

用户已在当前浏览器和 after 截图基础上给出视觉接受结论：

- `outputs/logs/v2_visual_acceptance_after_desktop_1366x768.png`
- `outputs/logs/v2_visual_acceptance_after_narrow_390x844.png`

结论：`accepted`，当前 after 视觉风格可接受。该结论关闭 after 视觉接受门禁，但仍需处理 `AC-V2-FE-VIS-008` 的 before 证据或由用户明确确认替代 before 证据口径。

若用户希望以“此前口头/文字复核的旧页面表现”为 before 依据替代同场景截图，需要作为验收语义变更单独记录；未确认前不得关闭 `AC-V2-FE-VIS-008`。

## 后续步骤

| 步骤 | 状态 |
| --- | --- |
| 获取或恢复旧版同场景 before 截图 | pending |
| 用户确认当前 after 视觉风格是否接受 | completed；accepted |
| 根据用户结论更新 visual traceability artifact | completed；smoke 输出 `manual_user_acceptance_status=accepted`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-008"]` |
| 验收候选前独立核验 | pending |

## 更新后验证

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py tests\test_contract_artifacts.py` | 通过，`17 passed` |
| `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` | 通过，`ok=true`、`manual_user_acceptance_status=accepted`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-008"]` |
| `python -m pytest -p no:cacheprovider` | 通过，`80 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅有既有 LF/CRLF warning |

## 结论

本次验收前置核查已补齐当前 after 浏览器证据，且用户已 accepted 当前 after 视觉；`AC-V2-FE-VIS-007` 可关闭。before/after 对比仍未完成，`AC-V2-FE-VIS-008` 继续 blocking。V2 当前仍 blocked，不能 accepted/closed。
