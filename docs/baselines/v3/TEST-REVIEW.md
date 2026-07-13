# DVEntityLinking V3 测试设计与测试开发评审记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| review_type | test review |
| review_object | [TEST-DESIGN.md](./TEST-DESIGN.md) and V3 test automation |
| baseline_documents | [SR.md](./SR.md) `V3-SR.2-closed`、[IMPLEMENTATION-CLOSURE-VERIFICATION.md](./IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| scope | V3 test case coverage, test layer boundaries, executable commands, automation mapping, abnormal path coverage, documentation hygiene |
| out_of_scope | 真实 Redis/GaussDB adapter、真实 LLM stage、V3 acceptance candidate、V2 legacy visual evidence |
| review_mode | main-agent sealed/read-only review；未使用 no-context subagent，因为当前工具规则要求只有用户明确要求代理/并行代理时才可 spawn sub-agent |
| conclusion | Ready for disposition with one P1 and one P2 finding |

## 2 Findings

### P1

#### V3-TEST-REVIEW-001 - Gauss Mock fail-closed abnormal paths are under-tested

Issue -> [TEST-DESIGN.md](./TEST-DESIGN.md) declares V3 storage contract coverage, and [TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) lists Gauss Mock miss、duplicate ID、字段缺失、schema error as V3 acceptance concerns. Current `tests/test_v3_storage_ner.py` covers normal Gauss load through repository lookup and Redis dangling ID, but does not directly test Gauss duplicate `entity_id` or missing required fields/schema fail-closed.

Current artifact behavior -> `GaussEntityStoreMock.load()` contains duplicate ID and required field validation, but the V3 focused automation does not assert those paths.

Impact -> A regression in Gauss artifact validation could slip through while Redis abnormal tests still pass, weakening the credibility of the two-layer storage acceptance floor.

Recommended correction -> Add focused fail-closed tests for Gauss duplicate entity ID and missing required field/schema validation, and update [TEST-DESIGN.md](./TEST-DESIGN.md) with explicit Gauss abnormal test cases.

### P2

#### V3-TEST-REVIEW-002 - NER query validation abnormal path lacks focused V3 automation

Issue -> SR-V3-A05 includes query validation as the first NER stage, and `NerPipeline.run()` returns `invalid_input` for empty queries. Current V3 focused tests cover linked、partial、no_match and not_required, but do not assert empty/blank query validation.

Current artifact behavior -> The implementation has a structured `query_validation` invalid path, but tests do not protect its status/error/stage semantics.

Impact -> Non-blocking for normal V3 smoke, but a regression in invalid input semantics could affect API robustness and documentation claims about structured error behavior.

Recommended correction -> Add a focused test for blank query -> `Status.INVALID_INPUT`、`ErrorCode.INVALID_INPUT` and `query_validation` stage trace, and update [TEST-DESIGN.md](./TEST-DESIGN.md).

## 3 Perspective Summary

| Perspective | Review result |
| --- | --- |
| Requirement/design coverage | Normal flow and Redis abnormal flow are strong; Gauss abnormal and query validation need focused automation. |
| Test layer boundary | Contract, integration, script and regression layers are separated clearly. |
| Executable evidence | Commands are concrete and have passing results. |
| Test-to-automation mapping | Mapping is clear but needs additional Gauss and invalid-input cases. |
| Documentation hygiene | V3 test design is indexed and status labels are consistent. |

## 4 Verified Commands

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-targeted tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py` | 通过，`27 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`90 passed`。 |
| `python -m compileall -q src scripts` | 通过。 |
| `python scripts\run_v3_evaluation.py` | 通过，`total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0`。 |
| `python scripts\run_v3_acceptance_smoke.py` | 通过，`ok=true`。 |
| `git diff --check` | 通过；仅输出 LF-to-CRLF 工作区警告。 |

## 5 Recommended Closure Actions

| Finding | Closure action |
| --- | --- |
| V3-TEST-REVIEW-001 | Add Gauss duplicate ID and missing required field/schema fail-closed tests; update test design coverage matrix and evidence. |
| V3-TEST-REVIEW-002 | Add blank query invalid-input focused test; update test design coverage matrix and evidence. |

## 6 Disposition Readiness

测试评审发现 1 个 P1 和 1 个 P2，均可在当前 V3 测试开发范围内处置，无需新增用户方向决策。完成处置和独立闭环验证前，不进入 V3 验收候选或 accepted/closed。
