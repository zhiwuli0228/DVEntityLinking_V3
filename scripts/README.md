# Scripts

本目录用于存放后续运行、数据准备、验证和 demo 辅助脚本。

当前状态：Web demo 只维护 `run_web_demo.py` 一个入口；当前默认加载 V2 样例，V3 通过 `--storage-mode v3_mock` 显式启用两层存储 Mock。验收 smoke 和 evaluation 可按版本保留独立脚本。

## 当前脚本

| 脚本 | 用途 |
| --- | --- |
| `run_web_demo.py` | PyCharm 或命令行直接启动当前版本 Web demo，当前默认加载 V2 样例；使用 `--storage-mode v3_mock` 时加载 V3 Redis/Gauss Mock。 |
| `run_acceptance_smoke.py` | PyCharm 或命令行直接运行 V0 验收 smoke，输出 JSON 摘要并写日志。 |
| `run_v1_acceptance_smoke.py` | PyCharm 或命令行直接运行 V1 alarm-only 验收 smoke，输出 JSON 摘要并写日志。 |
| `run_v1_evaluation.py` | 运行 V1 16 条启动 Query 的 precision/recall 验收评测。 |
| `run_v2_acceptance_smoke.py` | PyCharm 或命令行直接运行 V2 multi-type/multi-mention 验收 smoke，输出 JSON 摘要并写日志。 |
| `run_v2_evaluation.py` | 运行 V2 12 条启动 Query 的 query-level、mention-level 和 type-level 验收评测。 |
| `run_v3_acceptance_smoke.py` | PyCharm 或命令行直接运行 V3 两层存储 + NER pipeline smoke，输出 JSON 摘要并写日志。 |
| `run_v3_evaluation.py` | 运行 V3 NER golden cases 的 precision/recall 和负例误报评测。 |

日志默认写入 `outputs/logs/`，该目录被 `.gitignore` 忽略。

## 示例

```powershell
python scripts\run_web_demo.py --mode offline_demo --port 5015
python scripts\run_acceptance_smoke.py --mode offline_demo
python scripts\run_v1_acceptance_smoke.py --mode offline_demo
python scripts\run_v1_evaluation.py
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
python scripts\run_v2_evaluation.py
python scripts\run_v3_acceptance_smoke.py
python scripts\run_v3_evaluation.py
```

如需回看历史 V1 Web 样例，仍使用同一个入口并显式传参：

```powershell
python scripts\run_web_demo.py --catalog samples\real\entity_examples.json --samples samples\real\query_samples.json --mode offline_demo --port 5015
```

如需启动 V3 两层存储 Mock Web demo：

```powershell
python scripts\run_web_demo.py --storage-mode v3_mock --mode offline_demo --port 5015
```
