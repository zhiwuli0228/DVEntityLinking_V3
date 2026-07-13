# DVEntityLinking

DVEntityLinking 是一个面向 DV 运维 Copilot 和故障 Agent 的实体链接 demo 项目。目标是沉淀所有涉及实体的基础能力，包括实体构建、实体词表、Query 实体匹配与链接、实体查询和相似度检索。

当前项目已关闭 V0 和 V1；V2 验收候选已撤回，前端视觉风格补救已完成 after 视觉接受，但 before 同场景截图或替代 before 证据口径仍未确认。用户已确认搁置 V2 遗留问题并进入 V3。V3 GUI 决策确认已完成，重点是两层存储和 NER 详细设计：实体词到实体 ID 的 KV 对走 Redis 缓存接口 Mock，结构化实体数据走高斯数据库接口 Mock 并支持按实体 ID 查询；NER 是 V3 重中之重，必要时允许在设计闭环后重构。当前 V3 验收候选已准备完成，等待用户验收确认，尚未 accepted/closed。

## 当前状态

- 当前版本状态：V3 acceptance candidate prepared; pending user acceptance; not accepted/closed。
- 当前活跃迭代：V3 验收候选前置核查和核验已通过，见 `docs/baselines/v3/ACCEPTANCE-PRECHECK.md`、`docs/baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md`；候选记录见 `docs/releases/V3.md`。
- 后续仅剩用户验收确认：accepted and closed、accepted with recorded residual risk and closed，或进入 V3 后续补强。

## 核心文档

| 路径 | 用途 |
| --- | --- |
| `docs/PROJECT.md` | 项目当前状态、范围、约束和后续规划的唯一权威入口。 |
| `docs/README.md` | 精简文档导航。 |
| `docs/DV_CONTEXT.md` | DV 背景、实体域假设、真实 DV 内容确认规则和 Mock 边界。 |
| `docs/USAGE.md` | PyCharm 启动、验收 smoke、日志和 API 示例。 |
| `docs/current/DATA_CONTRACT.md` | 当前实体、Query 和 LinkResult 数据契约。 |
| `docs/current/TEST_ACCEPTANCE.md` | 当前测试命令、验收阈值和评测口径。 |
| `docs/current/DECISIONS.md` | 用户确认、范围决策和待确认事项。 |
| `docs/baselines/v0/` | V0 IR/SR 主输出件。 |
| `docs/baselines/v1/` | V1 IR/SR 主输出件。 |
| `docs/baselines/v2/` | V2 IR、前端功能补救 IR、前端视觉风格补救 IR、前端视觉风格补救需求评审/处置/闭环、前端视觉风格补救功能设计、功能设计评审/处置/闭环、代码实现记录、实现评审、实现评审处置、实现评审闭环验证、测试设计/开发、测试评审、测试评审处置、测试评审闭环验证和验收前置核查、前端补救需求评审处置、需求闭环验证、前端补救功能设计、功能设计评审处置与闭环、前端补救实现记录、前端补救实现评审处置与闭环、前端补救测试设计、前端补救测试评审处置与闭环、前端补救验收前反向核查、IR 阶段 SR 分解、已闭环 SR 功能设计、初始实现评审闭环记录、测试设计记录和测试评审处置记录。 |
| `docs/baselines/v3/` | V3 IR、IR 阶段 SR 分解、SR 功能设计、需求评审/处置/闭环、功能设计评审/处置/闭环、初始实现、实现评审/处置/闭环、测试设计、测试评审/处置/闭环、验收候选前置核查和核验记录，覆盖两层存储、Redis Mock、高斯 Mock、NER 详细设计和必要重构边界。 |
| `docs/releases/V0.md` | V0 关闭记录。 |
| `docs/releases/V1.md` | V1 关闭记录。 |
| `docs/releases/V2.md` | V2 验收候选撤回记录，当前 blocked。 |
| `docs/releases/V3.md` | V3 验收候选记录，当前等待用户验收确认。 |

## 快速验证

```powershell
python -m pytest
python -m compileall -q src scripts
python scripts\run_v1_evaluation.py
python scripts\run_v1_acceptance_smoke.py --mode offline_demo
python scripts\run_v2_evaluation.py
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
python scripts\run_v3_evaluation.py
python scripts\run_v3_acceptance_smoke.py
```

说明：当前 V3 验收候选以 V3 evaluation/smoke、V1 回归、V2 evaluation 和全量测试作为阻塞门禁；`run_v2_acceptance_smoke.py` 如因 V2 legacy visual browser evidence freshness 失败，按 D072 记录为 V2 遗留诊断项，不作为 V3 阻塞项。

PyCharm 直接启动当前 Web demo 和验收 smoke 见 `docs/USAGE.md`。Web 入口只维护 `scripts\run_web_demo.py`。

## 安全边界

- `config/llm.local.json` 只允许本地使用，必须保持 ignored。
- 真实 API key、token、base URL、完整 LLM 请求响应日志不得提交。
- 涉及真实 DV 接口、字段、样例和 Mock 方式时，必须先确认并记录到 `docs/current/DECISIONS.md`。
