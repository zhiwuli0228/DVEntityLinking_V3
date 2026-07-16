# V4.1 追踪与验收证据

最后更新：2026-07-16  
OpenSpec 变更：[decouple-v4-runtime](../../../openspec/changes/decouple-v4-runtime/tasks.md)

## 需求—实现—验证映射

| IR / SR | OpenSpec 任务 | 实现或文档 | 验证证据 | 状态 |
| --- | --- | --- | --- | --- |
| IR-V4.1-001 / SR-V4.1-A01 | 1.1、1.3 | `src/dv_entity_linking/module.py`、生产依赖扫描 | `tests/test_v41_decoupling.py::test_v41_production_modules_do_not_import_legacy_runtime`、`::test_v41_factory_dependency_failure_does_not_fall_back_to_historical_data` | 已实现 |
| IR-V4.1-002 / SR-V4.1-A02 | 1.2 | `PUBLIC_CONTRACT.json` | `tests/test_v41_decoupling.py::test_v41_public_contract_manifest_matches_dataclasses` 与 V4 contract tests | 已实现 |
| IR-V4.1-003 / SR-V4.1-A03 | 2.1–2.3 | `src/dv_entity_linking/v41.py` | `tests/test_v41_decoupling.py::test_v41_migration_*`、`::test_v41_configuration_rejects_deprecated_runtime_settings` | 已实现 |
| IR-V4.1-004 / SR-V4.1-A04 | 3.2 | 既有 V4 black-box contract suites | `tests/test_v4_module.py`、`tests/test_v4_final_pipeline_contract.py`、全量测试 | 已验证 |
| IR-V4.1-005 / SR-V4.1-A05、A06 | 3.1、3.3 | 本文件、`COMPATIBILITY_DIFFERENCES.md`、`DEPRECATION_REGISTER.md` | 文档评审与全量测试记录 | 已实现；生产切换证据待补充 |

## 验证记录

| 记录 ID | 命令 | 结果 | 状态 |
| --- | --- | --- | --- |
| TEST-V4.1-001 | `python -m pytest tests/test_v41_decoupling.py tests/test_v4_module.py tests/test_v4_final_pipeline_contract.py -q` | 33 passed | 通过 |
| TEST-V4.1-002 | `python -m pytest -q` | 132 passed | 通过 |

## 迁移证据要求

生产切换前需追加 `MIG-V4.1-*` 记录，至少包含：输入/输出数据版本、dry-run 报告、记录数与词条数、冲突/缺失计数、授权执行者、Entity Data IR 冒烟结果及回退目标。不得在此文件记录凭据、IR URL 或完整上游 payload。
