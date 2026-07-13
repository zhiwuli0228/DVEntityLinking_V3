# DVEntityLinking V2 前端改造补救测试独立评审记录

日期：2026-06-02

状态：review completed，存在 1 个 P1，需处置后进入闭环验证。

## 基本信息

| 项 | 内容 |
| --- | --- |
| Review type | test review |
| Review object | DVEntityLinking V2 frontend remediation test design/development |
| Review mode | no-context independent subagent read-only review |
| Reviewer | Hilbert |
| 是否修改文件 | 否 |

## 输入包

| 类型 | 文件 |
| --- | --- |
| 需求基线 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 功能设计基线 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| 实现评审闭环 | [FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| 测试设计与测试开发 | [FRONTEND-REMEDIATION-TEST-DESIGN.md](./FRONTEND-REMEDIATION-TEST-DESIGN.md) |
| 被评审测试/脚本 | `tests/test_web.py`、`tests/test_demo_scripts.py`、`tests/test_v2_runtime.py`、`tests/test_contract_artifacts.py`、`scripts/run_v2_acceptance_smoke.py` |
| 被评审证据 | `outputs/logs/v2_frontend_traceability_check.json`、`outputs/logs/v2_frontend_browser_evidence.json` |

## 评审执行

| 命令/证据 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py` | 通过，`27 passed in 20.67s` |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed in 0.35s` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`traceability_ac_v2_fe_004_status=implemented`、`browser_evidence_ok=true`、`browser_evidence_fresh=true` |

## Findings

### P1

Issue -> `attributes_safe[]` 的 fail-closed 目前只被正例安全投影覆盖，没有专门的带禁用键或危险值输入的负例回归。

Current artifact behavior -> `tests/test_web.py::test_web_entity_detail_uses_safe_attributes` 只断言一个已知安全实体的 `attributes_safe` 和 `omitted_attribute_count`，并检查 `mock_field` 不出现在序列化结果中；`tests/test_contract_artifacts.py` 约束样例 catalog 本身不含禁用键，但没有直接验证投影函数对 unsafe key/value 的拒绝行为。

Impact -> 如果后续回归把 forbidden key 或 token-like value 漏进 `attributes_safe[]`，当前测试组合仍可能放行，因为它验证的是干净样例能展示，不是脏输入一定被省略。

Recommended correction -> 增加一个直接针对 `_safe_attributes()` 或 `/api/entities/<id>` 的负例测试，喂入至少一种 forbidden key 和一种 forbidden value，断言它们被省略、`omitted_attribute_count` 增加、且输出里没有原始 key/value。

## 已核验且无新增 finding 的点

- `AC-V2-FE-004` 负例覆盖到位，`no_match` 和 `not_required` 不返回伪 `linked_entity`、伪 candidate 或伪 mention，并进入 traceability artifact。
- 第二个 mention `CPU Usage` 到 `DV-KPI-MTK-001` 的联动已由 runtime test 和 browser evidence 覆盖。
- Browser evidence freshness 分层正确，smoke 校验 required checks、截图存在性和相对 `web.py` 的 freshness。
- Traceability 未 downgrade，当前 traceability statuses 为 `implemented`，`traceability_downgraded_count=0`。

## 结论

评审结论：存在 P1，必须接受并完成处置后提交独立闭环验证。V2 仍保持 blocked，不能直接进入验收。
