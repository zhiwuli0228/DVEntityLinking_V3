# DVEntityLinking 精简 DV 流程

最后更新：2026-06-01

本文档定义本项目后续迭代采用的精简 DV 流程和文档规则。

## 阶段链路

```text
context/sample intake
  -> IR 需求分析和 SR 分解
  -> IR 独立评审、处置、闭环
  -> SR 功能设计
  -> SR 独立评审、处置、闭环
  -> code implementation
  -> implementation review、处置、闭环
  -> test design/development
  -> test review、处置、闭环
  -> demo/acceptance
  -> release closure
```

## IR 阶段要求

- IR 必须完成需求分解，形成可指导功能设计的 SR 输入。
- IR 独立评审必须站在功能设计视角检查 SR 拆分是否合理。
- 若功能设计阶段发现 SR 缺失或边界错误，应回到 IR 增补、评审、处置和闭环验证。
- 新范围、真实 DV 内容、LLM 依赖、验收语义和样例数据必须进入决策台账。

## 阶段门禁补充

- 用户确认需求追踪矩阵：用户明确确认的重要需求，必须追踪到 `IR -> SR -> 实现文件 -> 测试用例 -> 验收项`；任一环缺失，不得进入验收候选。
- 静默降级禁止：不得把已确认的重要需求静默降级为较弱实现、较弱测试或较弱验收项；如需降级、延期或缩小范围，必须先获得用户确认并记录到决策台账。
- 评审输入包增强：实现评审和测试评审必须包含用户决策台账、IR/SR 中所有 P0/P1/P2 用户确认项、当前实现 diff/文件列表和测试映射；评审者必须逐项判定 `已实现 / 未实现 / 降级 / 需用户确认`。
- 验收候选前反向核查：生成 release/acceptance record 前，必须从用户确认项倒查实现和验收；发现漏项时状态只能是 `blocked`，不能是 `acceptance candidate`。
- 残余风险分级限制：用户明确标记为重要的需求，默认不得作为普通 residual risk 放行；除非用户明确确认延期，否则视为验收阻塞项。

## 文档产出规则

| 阶段 | 输出位置 |
| --- | --- |
| IR 主输出 | `docs/baselines/<version>/IR.md` |
| IR SR 分解主输出 | `docs/baselines/<version>/IR-SR-DECOMPOSITION.md`，仅在需要时存在 |
| SR 主输出 | `docs/baselines/<version>/SR.md` |
| 当前数据契约 | `docs/current/DATA_CONTRACT.md` |
| 当前测试与验收 | `docs/current/TEST_ACCEPTANCE.md` |
| 用户决策 | `docs/current/DECISIONS.md` |
| 版本关闭 | `docs/releases/<version>.md` |

评审输入、闭环输入、临时过程记录、重复 README 和机器可读确认 JSON 不再作为长期 HEAD 文档保留。必要细节通过 Git 历史追溯。

## 关闭门

版本关闭前必须满足：

- 主 IR/SR 输出件存在且状态明确。
- 评审、处置和闭环结论已汇总到 release 文档。
- 用户确认需求追踪矩阵已完成，且无未确认降级。
- 自动化测试、评测脚本、acceptance smoke 和敏感扫描已执行并记录。
- 用户验收结论已记录到 `docs/current/DECISIONS.md` 和 release 文档。
- README 和文档导航只指向当前权威结构。
