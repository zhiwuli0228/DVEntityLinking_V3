# DVEntityLinking V2 前端改造补救需求评审处置记录

---

## 1 基本信息

| 项目 | 内容 |
| --- | --- |
| 版本范围 | V2 frontend remediation |
| 被评审对象 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 输入评审 | no-context 独立需求评审 Harvey，2026-06-01 |
| 评审结论 | Ready for disposition；无 P0，4 个 P1，3 个 P2 |
| 处置负责人 | Codex |
| 当前结论 | 需求评审处置已完成；独立闭环验证已通过，见 [FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |

本文只处置 V2 前端改造补救需求评审发现；需求评审闭环结论由独立只读验证记录给出。

## 2 处置总览

| ID | 严重级别 | 评审发现摘要 | 处置结论 | 主要改动 | 残余风险 |
| --- | --- | --- | --- | --- | --- |
| P1-FE-REQ-001 | P1 | 用户确认需求追踪矩阵的验收列存在 TBD，未把每个用户确认项映射到 AC；决策来源不完整。 | Accepted | 追踪矩阵新增决策来源列，映射 D024/D028/D041/D042/D043/D003 到 AC-V2-FE-001 至 AC-V2-FE-009。 | 实现、测试列仍需在后续阶段填具体文件和用例，不能在 IR 阶段伪关闭。 |
| P1-FE-REQ-002 | P1 | 验收证据仍可能降级为 marker/API projection；缺浏览器级行为和截图/布局证据。 | Accepted | AC-V2-FE-008 升级为真实浏览器或等价浏览器级断言，覆盖 desktop/narrow viewport、Query submit、candidate/entity detail linkage、catalog type filter、debug collapsed 和截图/布局证据。 | 后续测试设计必须选择具体执行工具和 evidence 文件。 |
| P1-FE-REQ-003 | P1 | 原确认的 LLM 交互式高亮/解释被弱化为 safe summary，缺少用户确认。 | Accepted | 将需求术语、用例、SR、AC 和风险项改为 LLM 交互式安全解释；最低要求为点击 mention、candidate 或 LLM status 展示关联脱敏解释和阶段摘要。 | 不要求实时流式 UI；若功能设计再缩减必须回到用户确认。 |
| P1-FE-REQ-004 | P1 | 多 mention 验收字段不足，无法证明 entity_type/predicted_type、span、per-mention candidates/no-candidate reason 和 partial reason。 | Accepted | AC-V2-FE-002/003 明确每个 mention 必须展示 text、entity_type 或 predicted_type、status、span、linked_entity、候选或 no-candidate reason，以及原因/候选归属/降级状态。 | 后续实现需补浏览器断言证明字段实际可见。 |
| P2-FE-REQ-001 | P2 | 安全 wording 过宽，可能误伤 UI 字段名 `base_url`、`api_key`、`api_key_env`。 | Accepted | 安全边界澄清为禁止真实 secret/API key、真实 base URL、raw prompt、raw response 和完整日志；字段名、password input、环境变量名和 redacted/empty 配置状态可展示。 | 后续安全扫描需按真实值而非字段名设计。 |
| P2-FE-REQ-002 | P2 | 反静默降级的评审输入要求未完全进入 IR。 | Accepted | SR-V2-FE-A06 要求评审输入包包含用户决策来源、差异文件清单、测试映射、每项降级状态和无法满足项的用户确认记录。 | 后续每个阶段必须维护输入包，否则阻塞下游。 |
| P2-FE-REQ-003 | P2 | 第一屏和窄屏缺少可测试 viewport 定义。 | Accepted | AC-V2-FE-001/007 明确 desktop `1366x768` 和 narrow `390x844`，并规定关键区块访问和无重叠要求。 | 视觉精细程度仍由功能设计定义，但不得降低可测性。 |

## 3 修改摘要

| 文件 | 修改内容 |
| --- | --- |
| [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) | 升级至 `V2-FE.1-draft`；补齐追踪矩阵、AC、LLM 交互式安全解释、安全边界、viewport 和评审输入包要求。 |
| [../../current/DECISIONS.md](../../current/DECISIONS.md) | 记录需求评审处置完成且待独立闭环验证。 |
| [../../PROJECT.md](../../PROJECT.md) | 更新当前阶段和当前基线链接。 |
| [../../../README.md](../../../README.md) | 更新根 README 当前状态，避免误导为可进入设计或验收。 |
| [../../README.md](../../README.md) | 更新文档导航，登记补救需求评审处置记录。 |
| [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) | 更新 V2 前端补救当前状态和阻塞条件。 |
| [../../releases/V2.md](../../releases/V2.md) | 保持 V2 blocked，补充前端补救需求处置状态。 |
| [../../../tests/test_contract_artifacts.py](../../../tests/test_contract_artifacts.py) | 补充文档治理契约断言，防止状态和关键 AC 漂移。 |

## 4 验证记录

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed` |
| `python -m pytest -p no:cacheprovider` | 通过，`71 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 5 闭环验证输入包

请独立闭环验证者只读复核以下输入：

- 原始评审发现：Harvey no-context 独立需求评审，2026-06-01；结论为无 P0、4 个 P1、3 个 P2，ready for disposition。
- 本处置记录：[FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md)
- 修订后需求文档：[IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md)
- 基线文件：[IR.md](./IR.md)、[SR.md](./SR.md)、[../../process/DV_PROCESS.md](../../process/DV_PROCESS.md)、[../../current/DECISIONS.md](../../current/DECISIONS.md)
- 验证命令和结果：见本文第 4 节。

闭环验证要求：

- 逐项判断 4 个 P1 和 3 个 P2 是否 closed、partially closed、not closed 或 needs user decision。
- 复核本文处置声明是否能从实际文档和测试证据中找到证据。
- 复核文档状态是否一致，且未把“处置完成”误写为“闭环完成”。
- 若任一 P1 未关闭，阻塞进入功能设计。

## 6 处置结论

本次需求评审发现全部接受并已完成文档处置。独立闭环验证已通过，需求阶段可作为 V2 前端补救功能设计输入；后续仍不得跳过功能设计评审、处置和闭环直接进入实现或验收。
