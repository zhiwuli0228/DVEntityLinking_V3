# DVEntityLinking V2 前端改造补救实现独立评审记录

日期：2026-06-02

状态：review completed，存在 1 个 P1 和 1 个 P2，需处置后进入闭环验证。

## 基本信息

| 项 | 内容 |
| --- | --- |
| Review type | code implementation review |
| Review object | DVEntityLinking V2 frontend remediation implementation |
| Review mode | no-context independent subagent read-only review |
| Reviewer | Planck |
| 是否修改文件 | 否 |

## 输入包

| 类型 | 文件 |
| --- | --- |
| 需求基线 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 功能设计基线 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| 设计闭环验证 | [FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| 实现记录 | [FRONTEND-REMEDIATION-IMPLEMENTATION.md](./FRONTEND-REMEDIATION-IMPLEMENTATION.md) |
| 被评审代码/测试 | `src/dv_entity_linking/web.py`、`scripts/run_v2_acceptance_smoke.py`、`tests/test_web.py`、`tests/test_demo_scripts.py`、`tests/test_v2_runtime.py` |

## 评审执行

| 命令/证据 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py` | 通过，`27 passed in 17.25s` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`traceability_statuses=["implemented"]`、`traceability_downgraded_count=0` |
| `outputs/logs/v2_frontend_browser_evidence.json` | `ok=true`，覆盖 `1366x768`、`390x844`、`card_text_readable=true`、`debug_collapsed=true`、第二个 mention `CPU Usage` 和 `DV-KPI-MTK-001` 实体详情 |

## Findings

### P1

Issue -> `AC-V2-FE-004` negative-state traceability is missing from the generated implementation evidence.

Current artifact behavior -> `scripts/run_v2_acceptance_smoke.py` exercises `no_match` and `not_required` in summary checks, but generated `v2_frontend_traceability_check.json/.md` did not explicitly map them to `AC-V2-FE-004`.

Impact -> Negative-state floor could regress while traceability still appears complete, weakening the acceptance gate for no pseudo linked entity / no pseudo candidate.

Recommended correction -> Add an explicit traceability item for `AC-V2-FE-004` with `no_match` and `not_required` evidence, then assert that item is present and `implemented`.

### P2

Issue -> Browser-equivalent evidence is present, but external to the automated smoke/test path and not freshness-checked.

Current artifact behavior -> `run_v2_acceptance_smoke.py` writes traceability JSON/MD, and `tests/test_demo_scripts.py` checks smoke outputs, but neither command validates `outputs/logs/v2_frontend_browser_evidence.json` or screenshots.

Impact -> Stale or orphaned browser artifacts could survive while checked commands still pass.

Recommended correction -> Wire browser-equivalent evidence into the automated run path, or add deterministic freshness/assertion checks for JSON and screenshots.

## 视角摘要

- 多 mention 交互是真实前端行为，不是 API-only projection。
- 第二个 mention `CPU Usage` 能驱动 `DV-KPI-MTK-001` 候选和实体详情。
- 卡片文字可读、debug 默认折叠、负例不返回伪 `linked_entity`、`attributes_safe[]` fail-closed 均有实现和测试证据。
- 主要问题集中在 traceability/evidence chain，而不是 UI 主流程。

## 结论

评审结论：not ready for disposition。处置阶段需接受并修复 P1；P2 可接受修复或记录残余风险后进入闭环验证。
