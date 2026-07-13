# DVEntityLinking V2 前端改造补救测试评审处置记录

日期：2026-06-02

状态：test review disposition completed；独立闭环验证已通过。

## 输入

| 类型 | 文件 |
| --- | --- |
| 原始测试评审 | [FRONTEND-REMEDIATION-TEST-REVIEW.md](./FRONTEND-REMEDIATION-TEST-REVIEW.md) |
| 需求基线 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 功能设计基线 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| 实现评审闭环 | [FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| 测试设计与测试开发 | [FRONTEND-REMEDIATION-TEST-DESIGN.md](./FRONTEND-REMEDIATION-TEST-DESIGN.md) |

## 总体处置结论

独立测试评审提出 1 个 P1。本轮接受该 finding，并补充 API 级 unsafe attributes 负例回归，确保 `attributes_safe[]` 对 forbidden key 和 token-like value 均 fail-closed。独立闭环验证已通过，见 [FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)；闭环结论由该只读记录给出。

## Finding 处置表

| ID | 优先级 | 处置 | 修订内容 | 验证 | 残余风险 |
| --- | --- | --- | --- | --- | --- |
| FE-TEST-001 | P1 | Accepted | `tests/test_web.py::test_web_entity_detail_omits_forbidden_attributes_and_values` 构造含 `api_key`、`raw_response` 和 allowed key 中 token-like value 的实体，通过 `/api/entities/<id>` 验证输出只包含安全 `severity`，`omitted_attribute_count=3`，且原始 forbidden key/value 不出现在响应中。`FRONTEND-REMEDIATION-TEST-DESIGN.md` 同步将 TC-V2-FE-WEB-006 标为正负例双覆盖。 | `python -m pytest -p no:cacheprovider tests\test_web.py` 通过，`12 passed`。 | 无 |

## 变更文件

| 文件 | 变更 |
| --- | --- |
| `tests/test_web.py` | 新增 unsafe attributes API 负例，覆盖 forbidden key、forbidden raw response key 和 token-like forbidden value。 |
| `docs/baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW.md` | 记录 no-context 独立测试评审输出。 |
| `docs/baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md` | 更新测试设计状态和 TC-V2-FE-WEB-006 自动化映射。 |
| `docs/baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md` | 记录本处置。 |

## 验证命令

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_web.py` | 通过，`12 passed` |
| `python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py` | 通过，`28 passed` |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed` |
| `python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs` | 通过，`ok=true`、`traceability_ac_v2_fe_004_status=implemented`、`browser_evidence_ok=true`、`browser_evidence_fresh=true` |
| `python -m pytest -p no:cacheprovider` | 通过，`75 passed` |
| `python -m compileall -q src scripts` | 通过 |

## 文档卫生

本处置已通过独立闭环验证。项目导航、当前状态、V2 release blocked 状态和测试验收策略需同步到“待验收前反向核查”；不得直接进入最终验收关闭。

## 闭环验证输入包

```text
original_review_record:
  - docs/baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW.md
disposition_record:
  - docs/baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md
revised_artifacts:
  - tests/test_web.py
  - docs/baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md
baseline_documents:
  - docs/baselines/v2/IR-FRONTEND-REMEDIATION.md
  - docs/baselines/v2/SR-FRONTEND-REMEDIATION.md
verification_commands_and_results:
  - python -m pytest -p no:cacheprovider tests\test_web.py -> 12 passed
  - python -m pytest -p no:cacheprovider tests\test_web.py tests\test_demo_scripts.py tests\test_v2_runtime.py -> 28 passed
  - python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py -> 5 passed
  - python scripts\run_v2_acceptance_smoke.py --mode offline_demo --log-dir outputs\logs -> ok=true, AC-V2-FE-004 implemented, browser evidence ok/fresh
  - python -m pytest -p no:cacheprovider -> 75 passed
  - python -m compileall -q src scripts -> passed
scope:
  - verify closure of FE-TEST-001
out_of_scope:
  - V2 final acceptance closure
  - real DV production API integration
expected_output:
  - independent read-only closure verification result
```
