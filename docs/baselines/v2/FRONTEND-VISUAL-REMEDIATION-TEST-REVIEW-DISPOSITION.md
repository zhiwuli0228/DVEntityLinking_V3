# DVEntityLinking V2 前端视觉风格补救测试评审处置记录

日期：2026-06-04

状态：test review disposition completed，独立闭环验证已通过，见 [FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)。本文不是验收候选或版本关闭记录。

## 基本信息

| 项 | 内容 |
| --- | --- |
| 处置对象 | [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md) |
| 被评审工件 | [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) |
| 处置人 | Codex |
| 处置结论 | 2 个 P1 和 1 个 P2 全部 Accepted；已完成代码、测试和文档处置 |
| 下一门禁 | before/after canonical visual comparison 和用户视觉接受 |

## 处置总览

| Finding | 优先级 | 决策 | 处置摘要 | 变更文件 | 残余风险 |
| --- | --- | --- | --- | --- | --- |
| FE-VIS-TEST-001 截图校验未充分证明可解码 | P1 | Accepted | 将 PNG 校验升级为 signature、chunk、CRC、IHDR、IDAT、IEND 和 IDAT zlib 解压校验；JPEG 要求 SOF 尺寸和 EOI；新增结构伪 PNG 负例。 | `scripts/run_v2_acceptance_smoke.py`、`tests/test_demo_scripts.py`、[FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) | 无阻塞残余风险；仍不替代人工视觉接受。 |
| FE-VIS-TEST-002 D003/content inventory 覆盖偏静态 | P1 | Accepted | 新增 D003 runtime scan，覆盖 HTML、`/api/status`、`/api/samples`、`/api/entities`、`/api/entities/<id>`、`/api/retrieve`、多类 `/api/link` payload、traceability artifact 和 smoke log；新增 concrete base URL、Authorization bearer、raw payload key 负例；visual traceability inventory 合并扫描结果。 | `scripts/run_v2_acceptance_smoke.py`、`tests/test_demo_scripts.py`、[FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) | 未确认真实 DV 内容仍需按 D003 回到用户确认；当前 scan finding_count=0。 |
| FE-VIS-TEST-003 forbidden downgrade classification 未独立阻塞 | P2 | Accepted | 新增 `FORBIDDEN_VISUAL_DOWNGRADE_CLASSIFICATIONS` 和 `_visual_item_blocks_acceptance()`，blocking 计算独立检查 `weak_marker_only`、`api_only`、`no_visual_delta`、`needs_user_decision` 等 forbidden downgrade；新增漂移负例。 | `scripts/run_v2_acceptance_smoke.py`、`tests/test_demo_scripts.py`、[FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) | 无阻塞残余风险；AC-V2-FE-VIS-007/008 仍因人工门禁保持 blocking。 |

## 实现变更

| 文件 | 变更 |
| --- | --- |
| `scripts/run_v2_acceptance_smoke.py` | 新增完整 PNG 结构/CRC/IDAT 解压校验；补 JPEG EOI 检查；将 `browser_screenshot_images_valid` 纳入 `ok`；新增 D003 runtime scan 和 summary 字段 `d003_scan_ok`、`d003_scan_finding_count`、`d003_scan_sources`；新增 forbidden downgrade blocker 函数。 |
| `tests/test_demo_scripts.py` | 新增 `test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots`、`test_v2_visual_d003_scan_flags_runtime_sensitive_values`、`test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance`；happy path 增加 D003 scan 断言。 |
| [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) | 更新测试映射、关键用例细节、执行记录、残余门禁和闭环输入包。 |
| [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md) | 归档 no-context 独立只读测试评审记录。 |

## 验证命令

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_demo_scripts.py::test_v2_acceptance_smoke_rejects_non_image_browser_screenshots tests\test_demo_scripts.py::test_v2_acceptance_smoke_rejects_structurally_fake_png_screenshots tests\test_demo_scripts.py::test_v2_visual_d003_scan_flags_runtime_sensitive_values tests\test_demo_scripts.py::test_v2_visual_traceability_forbidden_downgrade_blocks_acceptance tests\test_demo_scripts.py::test_v2_visual_smoke_rejects_versioned_web_demo_entries` | 通过，`6 passed` |
| `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` | 通过，`ok=true`、`browser_screenshot_images_valid=true`、`d003_scan_ok=true`、`d003_scan_finding_count=0`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py` | 通过，`12 passed` |
| `python -m pytest -p no:cacheprovider` | 通过，`80 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 文档卫生

| 文档 | 处置 |
| --- | --- |
| [../../current/DECISIONS.md](../../current/DECISIONS.md) | 已追加 D068 记录测试评审处置完成，D069 记录测试评审闭环验证通过。 |
| [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) | 已更新当前状态、验证摘要、测试评审处置记录和闭环验证记录。 |
| [../../PROJECT.md](../../PROJECT.md)、[../../README.md](../../README.md)、[../../releases/V2.md](../../releases/V2.md) | 已更新阶段状态为验收前置核查已生成，after 证据已补采，before 同场景截图和用户视觉接受仍缺失。 |
| [../../README.md](../../README.md) | 已登记测试评审、处置和闭环验证文件。 |

## 闭环验证输入包

请独立闭环验证者只读复核以下输入：

- [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md)
- [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)
- [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md)
- [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)
- [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)
- `scripts/run_v2_acceptance_smoke.py`
- `tests/test_demo_scripts.py`
- `tests/test_contract_artifacts.py`
- `outputs/logs/v2_frontend_visual_traceability_check.json`
- `outputs/logs/v2_frontend_browser_evidence.json`

## 结论

测试评审处置已完成，3 个 finding 均已 Accepted 并有代码、测试和文档处置证据。独立闭环验证已通过；在 before/after 对比和用户视觉接受完成前，V2 仍 not accepted/closed。
