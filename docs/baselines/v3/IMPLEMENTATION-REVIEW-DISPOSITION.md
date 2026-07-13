# DVEntityLinking V3 初始代码实现评审处置记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| disposition_type | implementation review disposition |
| input_review | [IMPLEMENTATION-REVIEW.md](./IMPLEMENTATION-REVIEW.md) |
| reviewed_implementation | [IMPLEMENTATION.md](./IMPLEMENTATION.md) |
| baseline | [SR.md](./SR.md) `V3-SR.2-closed` |
| status | implementation review disposition completed; pending independent closure verification |

## 2 Overall Handling Conclusion

实现评审发现 1 个 P2 和 1 个 P3，均接受并已完成处置：

- V3-IMPL-REVIEW-001/P2：修正 V3 `llm_enabled_demo` 下未实际调用 LLM 时的 `llm_used` 投影语义，并补 Web/API 回归测试。
- V3-IMPL-REVIEW-002/P3：补 Redis Mock metadata `key_scope` 强校验，并补 fail-closed 回归测试。

本记录不声明闭环关闭；当前处置包已准备进入独立闭环验证。

## 3 Finding Disposition Table

| Finding | Priority | Decision | Accepted changes | Verification | Residual risk |
| --- | --- | --- | --- | --- | --- |
| V3-IMPL-REVIEW-001 | P2 | Accepted | `src/dv_entity_linking/web.py` 中 `_build_mode_status()` 在存在显式 `stage_trace` 时根据实际 `llm` stage 判断 `llm_used`；V3 当前无 LLM stage 时保持 `llm_enabled=true` 但 `llm_used=false`。新增 `test_v3_web_api_does_not_claim_llm_used_without_llm_stage`。 | `tests\test_v3_storage_ner.py` 通过，`9 passed`；目标组合通过，`27 passed`；全量通过，`90 passed`。 | 未来真正实现 V3 LLM 分类/解释/rerank 时，需要新增明确 `llm` stage 和对应测试。 |
| V3-IMPL-REVIEW-002 | P3 | Accepted | `src/dv_entity_linking/storage.py` 新增 `EXPECTED_KEY_SCOPE` 并强校验 `metadata.key_scope == ["canonical_name","confirmed_aliases"]`；新增 `test_v3_redis_key_scope_metadata_fails_closed`。 | `tests\test_v3_storage_ner.py` 通过，`9 passed`；目标组合通过，`27 passed`；全量通过，`90 passed`。 | 无阻塞性残余风险；后续扩展 key scope 仍需 GUI/决策确认。 |

## 4 Changed Files

| 文件 | 变更 |
| --- | --- |
| [../../../src/dv_entity_linking/web.py](../../../src/dv_entity_linking/web.py) | 修正 `ModeStatus.llm_used` 的 V3 stage trace 投影语义。 |
| [../../../src/dv_entity_linking/storage.py](../../../src/dv_entity_linking/storage.py) | 增加 Redis Mock `metadata.key_scope` 强校验。 |
| [../../../tests/test_v3_storage_ner.py](../../../tests/test_v3_storage_ner.py) | 新增 V3 LLM 使用状态投影回归和 Redis key scope fail-closed 回归。 |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | 更新实现状态、验证结果和评审/处置链接。 |
| [../../current/DECISIONS.md](../../current/DECISIONS.md) | 新增 D083 记录实现评审处置状态。 |
| [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) | 更新 V3 已验证结果为 `9 passed`、`27 passed`、`90 passed`。 |
| [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) | 修正 V3 normalization version 文档口径为 `v3.entity_word_norm.1`。 |
| [../../README.md](../../README.md)、[../../PROJECT.md](../../PROJECT.md)、[../../USAGE.md](../../USAGE.md)、[../../../README.md](../../../README.md)、[../../../samples/README.md](../../../samples/README.md)、[../../../scripts/README.md](../../../scripts/README.md)、[../../../tests/README.md](../../../tests/README.md) | 同步 V3 实现、脚本、样例、测试和状态导航。 |
| [../../../tests/test_contract_artifacts.py](../../../tests/test_contract_artifacts.py) | 增加 V3 实现评审/处置和最新验证结果的文档治理断言。 |

## 5 Commands and Results

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-v3 tests\test_v3_storage_ner.py` | 通过，`9 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-targeted tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py` | 通过，`27 passed`。 |
| `python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full` | 通过，`90 passed`。 |

补充验证将在闭环验证前继续执行：`python -m compileall -q src scripts`、`python scripts\run_v3_evaluation.py`、`python scripts\run_v3_acceptance_smoke.py` 和 `git diff --check`。

## 6 Deferred Items

| 项 | 非阻塞原因 |
| --- | --- |
| 真实 V3 LLM 分类/解释/rerank | D077 已确认 LLM 是可选增强，默认验收仍为离线 deterministic；本轮只修正未实际使用 LLM 时的投影语义。 |
| 真实 Redis/Gauss adapter | V3 初始范围明确为接口 Mock；真实接入需后续确认连接、认证、失败语义和脱敏边界。 |

## 7 Closure Verification Input Bundle

建议闭环验证读取：

- [IMPLEMENTATION-REVIEW.md](./IMPLEMENTATION-REVIEW.md)
- 本处置记录
- [IMPLEMENTATION.md](./IMPLEMENTATION.md)
- [SR.md](./SR.md)
- `src/dv_entity_linking/web.py`
- `src/dv_entity_linking/storage.py`
- `tests/test_v3_storage_ner.py`
- `tests/test_contract_artifacts.py`
- `docs/current/DECISIONS.md`
- `docs/current/TEST_ACCEPTANCE.md`
- `docs/current/DATA_CONTRACT.md`

建议复跑：

```powershell
python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-v3 tests\test_v3_storage_ner.py
python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-targeted tests\test_contract_artifacts.py tests\test_demo_scripts.py tests\test_v3_storage_ner.py
python -m pytest -p no:cacheprovider --basetemp=.pytest-basetemp-full
python -m compileall -q src scripts
python scripts\run_v3_evaluation.py
python scripts\run_v3_acceptance_smoke.py
git diff --check
```

## 8 Conclusion

V3 初始代码实现评审处置已完成。当前无 P0/P1/P2 阻塞遗留；处置包可进入独立闭环验证。闭环验证完成前，V3 仍不得进入验收候选或 accepted/closed。
