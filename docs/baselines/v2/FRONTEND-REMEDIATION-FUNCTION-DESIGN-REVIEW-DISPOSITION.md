# DVEntityLinking V2 前端改造补救功能设计评审处置记录

---

## 1 基本信息

| 项目 | 内容 |
| --- | --- |
| 版本范围 | V2 frontend remediation |
| 被评审对象 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| 输入评审 | [FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| 评审结论 | Ready for disposition；无 P0，4 个 P1，1 个 P2 |
| 处置负责人 | Codex |
| 当前结论 | 功能设计评审处置已完成；独立闭环验证已通过，见 [FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |

本文只处置 V2 前端改造补救功能设计评审发现；功能设计评审闭环结论由独立只读验证记录给出。

## 2 处置总览

| ID | 严重级别 | 评审发现摘要 | 处置结论 | 主要改动 | 残余风险 |
| --- | --- | --- | --- | --- | --- |
| P1-FE-SR-001 | P1 | AC-V2-FE-009 缺少可实现的反向核查 schema。 | Accepted | 在 SR-V2-FE-D05 中定义 `v2_frontend_traceability_check.json/.md`、条目 schema、status enum、downgrade classification、reviewer result 和 blocking rule；测试映射新增 TC-V2-FE-WEB-012。 | 后续实现/测试阶段必须生成真实 evidence 文件；outputs 不入库，只在 release 记录脱敏摘要。 |
| P1-FE-SR-002 | P1 | LLM 交互式解释缺少 mention/candidate 关联字段。 | Accepted | 定义 `llm_explanations[]` schema，包含 context、mention/candidate/entity 关联键、stage、stage_status、safe_summary、fallback_reason、error_code、redaction_note；补 click resolution 和 empty-state rules；`/api/link` 最低字段补 `llm_explanations[]`。 | 后续实现需保证 offline mode 也有安全空状态，不得显示无关全局摘要。 |
| P1-FE-SR-003 | P1 | AC-V2-FE-004 缺 standalone `no_match`/`not_required` UI 测试。 | Accepted | 新增 TS/TC-V2-FE-010、011，分别覆盖 standalone no_match 和 not_required browser UI；AC-V2-FE-004 映射到这些用例。 | 后续测试设计需绑定具体样例 query。 |
| P1-FE-SR-004 | P1 | Entity detail `attributes` 字段开放，缺 fail-closed schema。 | Accepted | 替换为 `attributes_safe[]` 和 `omitted_attribute_count`；定义属性白名单、值类型、禁止键、未知 key fail-closed 和 omission summary。 | 后续实现如需更多属性 key，必须更新白名单并接受评审。 |
| P2-FE-SR-001 | P2 | Catalog API 命名与主 V2 SR `/api/catalog` 不一致。 | Accepted | 明确本补救以当前实际 `/api/entities`、`/api/entities/<entity_id>` 为 Web catalog 接口；主 SR `/api/catalog` 作为早期逻辑命名，本补救不新增第二套 endpoint；接口表修正 `/api/retrieve` 为 POST。 | 主 SR 历史文字仍保留为旧基线，后续引用需以本补救 SR 为准。 |

## 3 修改摘要

| 文件 | 修改内容 |
| --- | --- |
| [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) | 升级至 `V2-FE-SR.1-draft`；补齐反向核查 schema、LLM explanation association、negative UI tests、safe attributes fail-closed、catalog endpoint boundary 和评审记录。 |
| [FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) | 固化独立功能设计评审 findings。 |
| [../../current/DECISIONS.md](../../current/DECISIONS.md) | 记录 D048：功能设计评审处置完成，待独立闭环验证。 |
| [../../PROJECT.md](../../PROJECT.md) | 更新当前阶段和当前基线链接。 |
| [../../../README.md](../../../README.md) | 更新根 README 当前状态。 |
| [../../README.md](../../README.md) | 更新文档导航，登记设计评审和处置记录。 |
| [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) | 更新进入实现前的阻塞条件。 |
| [../../releases/V2.md](../../releases/V2.md) | 保持 V2 blocked，补充前端补救当前状态。 |
| [../../../tests/test_contract_artifacts.py](../../../tests/test_contract_artifacts.py) | 补充文档治理契约断言，防止设计处置状态和关键 schema 漂移。 |

## 4 验证记录

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed` |
| `python -m pytest -p no:cacheprovider` | 通过，`71 passed` |
| `python -m compileall -q src scripts` | 通过 |
| `git diff --check` | 通过，仅有 LF/CRLF 提示 |

## 5 闭环验证输入包

请独立闭环验证者只读复核以下输入：

- 原始评审记录：[FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md)
- 本处置记录：[FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md)
- 修订后设计文档：[SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md)
- 需求基线：[IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md)
- 需求闭环：[FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md)
- 流程和状态：[../../process/DV_PROCESS.md](../../process/DV_PROCESS.md)、[../../current/DECISIONS.md](../../current/DECISIONS.md)、[../../PROJECT.md](../../PROJECT.md)
- 契约测试：[../../../tests/test_contract_artifacts.py](../../../tests/test_contract_artifacts.py)
- 验证命令和结果：见本文第 4 节。

闭环验证要求：

- 逐项判断 4 个 P1 和 1 个 P2 是否 closed、partially closed、not closed 或 needs user decision。
- 复核 P1 处置是否由实际设计文本支撑，而不是处置记录声明。
- 复核状态文档是否没有误写为“可实现”或“V2 accepted”。
- 若任一 P1 未关闭，阻塞进入代码实现。

## 6 处置结论

本次功能设计评审发现全部接受并已完成设计处置。独立闭环验证已通过，功能设计可作为 V2 前端补救代码实现输入；后续仍不得跳过实现评审、测试评审和验收反向核查直接关闭 V2。
