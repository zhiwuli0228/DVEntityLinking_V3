# V5 追踪记录

| IR / SR | OpenSpec 任务 | 证据 | 状态 |
| --- | --- | --- | --- |
| IR-V5-003 | 2.1–2.3 | `infrastructure/rest_tool.py`、V4 Entity Data adapter 回归 | 已实现 |
| IR-V5-009 | 1.3–1.4、3.1–3.3 | `query_recall.py`、`tests/test_v5_query_recall.py` | 已实现 |
| IR-V5-001/002 | 1.2、4.1–4.4 | `entity_build_plugin.py`、`v5_interface_responses.json`、`tests/test_v5_entity_build_plugin.py` | 部分实现（发布服务真实对账待接入） |
| IR-V5-004/005 | 5.x | lifecycle/scheduler | 待实现 |

已执行：`python -m pytest tests/test_v5_query_recall.py tests/test_v5_entity_build_plugin.py tests/test_rest_tool.py -q`，10 passed；`python -m pytest -q`，全量通过（覆盖既有 V0–V4.1 与新增 V5 用例）。
