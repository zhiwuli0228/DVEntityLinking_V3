# DVEntityLinking V2 前端改造补救需求评审闭环验证记录

---

## 1 基本信息

| 项目 | 内容 |
| --- | --- |
| 版本范围 | V2 frontend remediation |
| 验证对象 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 原始评审 | no-context 独立需求评审 Harvey，2026-06-01 |
| 处置记录 | [FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| 闭环验证者 | independent subagent Erdos |
| Independence mode | Sealed review mode；只读复核，未修改文件 |
| 当前结论 | Requirement review closure verified；可进入 V2 前端补救功能设计 |

## 2 输入包

闭环验证只读复核以下输入：

- [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md)
- [FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md)
- [IR.md](./IR.md)
- [SR.md](./SR.md)
- [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- [../../PROJECT.md](../../PROJECT.md)
- [../../README.md](../../README.md)
- [../../../README.md](../../../README.md)
- [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md)
- [../../releases/V2.md](../../releases/V2.md)
- [../../../tests/test_contract_artifacts.py](../../../tests/test_contract_artifacts.py)

## 3 Findings 闭环结果

| ID | 严重级别 | 闭环状态 | 验证结论 |
| --- | --- | --- | --- |
| P1-FE-REQ-001 | P1 | Closed | 用户确认需求追踪矩阵已补决策来源列，验收列不再是 TBD，并映射 D024/D028/D041/D042/D043/D003 到 AC-V2-FE-001 至 AC-V2-FE-009；实现/测试列保留为后续阶段填入，且 IR 明确不得在需求阶段伪关闭。 |
| P1-FE-REQ-002 | P1 | Closed | AC-V2-FE-008 已要求真实浏览器或等价浏览器级断言，覆盖 desktop/narrow viewport、Query submit、candidate/entity detail linkage、catalog type filter、debug collapsed、截图/布局证据和单 Web 入口；marker/API projection 只能作为补充证据。 |
| P1-FE-REQ-003 | P1 | Closed | IR 已恢复 LLM 交互式安全解释最低交互要求：点击 mention、候选或 LLM 状态后展示关联脱敏解释和阶段摘要；不要求实时流式 UI。 |
| P1-FE-REQ-004 | P1 | Closed | AC-V2-FE-002/003 已明确逐 mention 展示 `text`、`entity_type` 或 `predicted_type`、`status`、`span`、`linked_entity`、候选或 no-candidate reason，并区分 partial 原因、候选归属和降级状态。 |
| P2-FE-REQ-001 | P2 | Closed | 安全边界已区分禁止真实 secret/API key/token/base URL/raw prompt/raw response/完整日志，以及允许字段名、password input 类型、环境变量名、redacted/empty 配置状态。 |
| P2-FE-REQ-002 | P2 | Closed | SR-V2-FE-A06 已纳入反静默降级评审输入包要求：用户决策来源、当前差异文件清单、测试映射、逐项降级状态、无法满足项的用户确认记录；DV_PROCESS 也存在一致门禁。 |
| P2-FE-REQ-003 | P2 | Closed | AC-V2-FE-001/007 已定义 desktop `1366x768` 和 narrow `390x844`，并规定第一屏关键区块、窄屏滚动可访问、无关键文本重叠、debug JSON 默认折叠。 |

## 4 验证命令与证据

闭环验证者未执行命令，只核对处置记录中的声明和文档/测试断言。处置阶段已执行并记录：

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed` |
| `python -m pytest -p no:cacheprovider` | 通过，`71 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

闭环验证者确认 `tests/test_contract_artifacts.py` 对 `LLM 交互式安全解释`、`AC-V2-FE-008`、`1366x768`、`390x844`、`待独立闭环验证` 等关键文档状态提供防漂移断言；这些断言支撑文档治理，不替代后续测试设计阶段的浏览器级行为测试。

## 5 文档卫生结果

Passed。

- `README.md`、`docs/PROJECT.md`、`docs/current/DECISIONS.md`、`docs/current/TEST_ACCEPTANCE.md` 和 `docs/releases/V2.md` 已保持 V2 前端补救处置状态一致。
- `docs/README.md` 已登记前端补救 IR 和处置记录。
- V2 release 仍保持 withdrawn/blocked，未被处置记录错误解封。
- 未发现把“处置完成”误写为“验收通过”或“V2 accepted”的记录。

## 6 结论

V2 前端改造补救需求评审闭环验证通过。原 4 个 P1 和 3 个 P2 全部 Closed，无 Needs user decision，无必须修正项。

当前允许进入 V2 前端补救功能设计阶段；后续实现、测试和验收仍需按本文 AC-V2-FE-001 至 AC-V2-FE-009 反向追踪，不能把前端改造再次降级为 Web/API projection。
