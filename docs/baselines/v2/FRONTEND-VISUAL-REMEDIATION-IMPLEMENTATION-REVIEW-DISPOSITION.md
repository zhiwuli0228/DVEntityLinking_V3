# DVEntityLinking V2 前端视觉风格补救代码实现评审处置记录

---

> 文档治理说明：本文处理 [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) 的独立实现评审发现。本文不是闭环验证记录；最终关闭需由独立闭环验证完成。

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 处置对象 | V2 frontend visual remediation implementation review |
| 输入评审 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) |
| 日期 | 2026-06-02 |
| 处置人 | Codex |
| 状态 | implementation review disposition completed; pending independent closure verification |

## 总体结论

独立实现评审发现 1 个 P1 和 2 个 P2。全部接受并在当前轮完成修订：

- FE-VIS-IMPL-001/P1：已补齐 `v2.frontend_visual_traceability.1` 的 SR 最小 schema 字段和 D003 inventory 字段。
- FE-VIS-IMPL-002/P2：已将单 Web 入口检查从硬编码改为扫描 `scripts/run_*web_demo.py`。
- FE-VIS-IMPL-003/P2：已新增 PNG/JPEG 截图解码和 viewport 尺寸校验；测试 helper 改为生成真实 PNG。

`manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 仍按设计保持阻塞，等待 before/after 对比和用户视觉接受确认；本处置未将其静默降级为 pass。

## Findings 处置表

| Finding | Priority | Decision | 处置说明 | 修改文件 | 验证 |
| --- | --- | --- | --- | --- | --- |
| FE-VIS-IMPL-001 | P1 | Accepted | `scripts/run_v2_acceptance_smoke.py` 生成的 visual traceability item 现在包含 `prototype_ref`、`absorbed_principle`、`target_ui_regions`、`before_screenshot`、`after_screenshot`、`same_viewport_and_query`、`automated_visual_semantic_checks`；顶层补 `scenario`、`manual_user_acceptance_evidence`；`d003_content_inventory[]` 补 `text_or_label`、`classification`、`source_reference`、`decision_id`。测试补字段级断言。 | `scripts/run_v2_acceptance_smoke.py`; `tests/test_demo_scripts.py`; `tests/test_contract_artifacts.py`; `outputs/logs/v2_frontend_visual_traceability_check.json`; `outputs/logs/v2_frontend_visual_traceability_check.md` | `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_contract_artifacts.py` -> `6 passed`; `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` -> `ok=true` |
| FE-VIS-IMPL-002 | P2 | Accepted | 新增 `_web_demo_single_entry_ok()`，扫描 `scripts/run_*web_demo.py` 并仅允许 `scripts/run_web_demo.py`，防止后续版本专用 web 启动脚本静默通过。 | `scripts/run_v2_acceptance_smoke.py` | `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` -> `ok=true` |
| FE-VIS-IMPL-003 | P2 | Accepted | 新增 `_image_dimensions()`、`_jpeg_dimensions()` 和 `_dimension_matches_expected()`，要求截图可解码为 PNG/JPEG 且尺寸匹配 evidence key 声明 viewport；考虑浏览器滚动条，宽度允许少一个滚动条范围。测试 helper 生成真实 PNG。 | `scripts/run_v2_acceptance_smoke.py`; `tests/test_demo_scripts.py` | `browser_screenshot_images_valid=true`; `browser_screenshot_dimension_checks.desktop_1366x768=true`; `browser_screenshot_dimension_checks.narrow_390x844=true` |

## 验证命令

| 命令 | 结果 |
| --- | --- |
| `python -m py_compile scripts\run_v2_acceptance_smoke.py` | 通过 |
| `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_contract_artifacts.py` | 通过，`6 passed` |
| `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` | 通过，`ok=true`、`browser_evidence_ok=true`、`browser_screenshot_images_valid=true`、`visual_traceability_statuses=["implemented","needs_user_decision"]`、`visual_traceability_blocking_ac_ids=["AC-V2-FE-VIS-007","AC-V2-FE-VIS-008"]` |

## 残余风险

| 风险 | 状态 | 说明 |
| --- | --- | --- |
| 用户视觉接受 | 仍阻塞验收关闭 | `manual_user_acceptance_status=pending`，不得 accepted/closed。 |
| before/after 对比 | 仍阻塞验收关闭 | `AC-V2-FE-VIS-008` 保持 `needs_user_decision`，后续需同 canonical scenario 对比。 |
| 独立闭环验证 | 待执行 | 需 no-context 独立闭环验证确认 FE-VIS-IMPL-001 至 FE-VIS-IMPL-003 真正关闭。 |

## Closure Verification 输入包

| 项 | 内容 |
| --- | --- |
| 原始评审 | [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) |
| 处置记录 | 本文 |
| 代码与测试 | `scripts/run_v2_acceptance_smoke.py`, `tests/test_demo_scripts.py`, `tests/test_contract_artifacts.py` |
| 证据 | `outputs/logs/v2_frontend_browser_evidence.json`, `outputs/logs/v2_frontend_visual_traceability_check.json`, `outputs/logs/v2_frontend_visual_traceability_check.md` |
| 建议验证命令 | `python -m pytest -p no:cacheprovider tests\test_demo_scripts.py::test_v2_acceptance_smoke_script_runs_offline tests\test_contract_artifacts.py`; `python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` |

