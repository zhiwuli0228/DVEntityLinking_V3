# DVEntityLinking V2 前端改造补救功能设计独立评审记录

---

## 1 基本信息

| 项目 | 内容 |
| --- | --- |
| 评审类型 | Function design review |
| 评审对象 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| 评审者 | no-context independent reviewer Bacon |
| 评审日期 | 2026-06-02 |
| 评审模式 | independent read-only review |
| 文件修改 | 无 |
| 评审结论 | Ready for disposition；无 P0，4 个 P1，1 个 P2；P1 关闭前不得进入实现 |

## 2 输入包

| 类型 | 文件 |
| --- | --- |
| Review object | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| Requirement baseline | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| Requirement closure | [FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |
| Requirement disposition | [FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| V2 main SR baseline | [SR.md](./SR.md) |
| DV process | [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md) |
| Decisions | [../../current/DECISIONS.md](../../current/DECISIONS.md) |

## 3 Findings

### P0

None.

### P1

| ID | Issue | Current artifact behavior | Impact | Recommended correction |
| --- | --- | --- | --- | --- |
| P1-FE-SR-001 | AC-V2-FE-009 被推迟到未来 artifact，缺少可实现的反向核查 schema。 | SR 只说明 acceptance smoke 输出“反向核查摘要”，AC-V2-FE-009 映射到“后续测试设计和验收候选反向核查表”。 | 可能再次形成叙述性或 marker-level 验收，违反 DV 流程和 IR AC-V2-FE-009。 | 增加具体反向核查 schema：decision ID、用户确认项、AC IDs、设计项、实现文件、测试 ID、evidence path、status enum、downgrade classification、reviewer result 和 blocking rule。 |
| P1-FE-SR-002 | LLM 交互式解释缺少关联字段，可能降级为全局 safe summary。 | LLM projection 只有 `stage_statuses[]` 和可选 `selected_explanation`，没有绑定 `mention_index`、`candidate_id`、`entity_id`、stage 或 fallback reason。 | 前端可对所有点击展示同一个全局摘要，重复“LLM 解释弱化为状态”的失败模式。 | 定义 `llm_explanations[]` 或等价 safe projection，包含 context、mention/candidate/entity 关联键、stage、stage_status、safe_summary、fallback_reason、error_code 和 redaction_note，并定义 click resolution rules。 |
| P1-FE-SR-003 | AC-V2-FE-004 未充分映射到负例 UI 测试。 | AC-V2-FE-004 只映射到 partial scenario，缺 standalone `no_match` 和 `not_required` browser scenario。 | P0 负例验收项可能未证明 UI 不展示伪候选或伪 linked entity。 | 增加 `no_match` 和 `not_required` 独立浏览器测试，断言 query status、空 linked entity、候选行为、可见原因和 detail panel 不被伪更新。 |
| P1-FE-SR-004 | Safe entity detail projection 仍包含开放 `attributes` 字段。 | Entity detail 写为 `attributes` “若存在，仅显示非敏感字段”，未定义白名单、禁止键、序列化规则或未知属性行为。 | 实现可能泄露 unsafe 字段或不一致地丢弃属性，破坏 safe projection。 | 改为显式 whitelist 或 `attributes_safe[]`，未知 key fail-closed，敏感 key 省略，只记录非敏感 omission summary。 |

### P2

| ID | Issue | Current artifact behavior | Impact | Recommended correction |
| --- | --- | --- | --- | --- |
| P2-FE-SR-001 | Catalog API 命名与 V2 主 SR 不一致。 | 补救 SR 使用 `/api/entities`，主 V2 SR 写 `/api/catalog`。 | 实现和测试可能分裂到两个 endpoint。 | 明确 `/api/entities` 是当前实际接口，`/api/catalog` 是旧逻辑命名、alias 还是被替代，并更新接口表。 |

### P3

None.

## 4 视角摘要

| 视角 | 结论 |
| --- | --- |
| 需求覆盖 | AC-V2-FE-001/002/003/005/006/007/008 大体覆盖；AC-V2-FE-004 和 AC-V2-FE-009 需补强。 |
| 模块/接口设计 | Flask/page/API 边界合理；需要收敛 `/api/entities` 与 `/api/catalog` 命名。 |
| Safe projection/security | 意图较强；`attributes` 和 LLM explanation association 需要具体 schema。 |
| 反降级 | 浏览器证据明显强于旧失败模式；traceability 仍过度依赖未来 artifact。 |
| 浏览器证据 | desktop/narrow、query submit、catalog filter、candidate/detail、debug collapsed 已列出；负例状态和 traceability 需加强。 |

## 5 Verified Commands / Results

评审者执行只读检查：

- Read review skill instructions with `Get-Content`.
- Read all requested baseline documents with `Get-Content -Raw`.
- Used `rg -n` and line-numbered `Get-Content` slices to verify AC mappings, API contracts, LLM fields, traceability, and DV process gates.

未修改文件；未启动服务；未运行测试。

## 6 结论

功能设计评审 ready for disposition。P1 finding 关闭前，不能进入设计闭环或代码实现。
