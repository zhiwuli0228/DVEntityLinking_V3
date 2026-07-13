# Tests

本目录用于存放 Python 自动化测试。

当前状态：V0 offline baseline 自动化测试已覆盖验收底线；V1 alarm-only 自动化测试、评测脚本和 acceptance smoke 已覆盖验收底线，V1 已通过用户验收并关闭；V2 multi-type/multi-mention、前端功能补救和前端视觉风格补救已补充评测脚本、acceptance smoke、type-level metrics、metadata fail-closed、smoke artifact、browser evidence、D003 runtime scan 和 visual traceability blocker 检查；V3 验收候选已准备，覆盖 Redis/Gauss Mock、两层存储集成、Gauss duplicate/missing field fail-closed、NER blank query invalid-input、V3 evaluation、V3 acceptance smoke、LLM 使用状态投影、Redis key scope fail-closed 测试和验收候选前置核查。当前全量回归为 `93 passed`。

当前验证命令：

```powershell
python -m pytest
```

V1 验收辅助命令：

```powershell
python scripts\run_v1_evaluation.py
python scripts\run_v1_acceptance_smoke.py --mode offline_demo
python scripts\run_v2_evaluation.py
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
python scripts\run_v3_evaluation.py
python scripts\run_v3_acceptance_smoke.py
```
