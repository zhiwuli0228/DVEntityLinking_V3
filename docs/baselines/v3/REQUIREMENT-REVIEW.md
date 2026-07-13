# DVEntityLinking V3 独立需求评审记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| review_type | Requirement review |
| review_object | V3 IR 与 IR 阶段 SR 分解 |
| review_mode | Main-agent read-only review；未使用 no-context subagent |
| 未使用子代理原因 | 当前多代理工具要求用户明确授权子代理后才能 spawn；本轮用户要求继续推进但未显式要求子代理。 |
| reviewer | Codex |
| 结论 | Ready for disposition with findings |

## 2 Review Input Bundle

| 类别 | 文件 |
| --- | --- |
| review_object | [IR.md](./IR.md) |
| review_object | [IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md) |
| baseline_documents | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| baseline_documents | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| baseline_documents | [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) |
| baseline_documents | [../../PROJECT.md](../../PROJECT.md) |
| baseline_documents | [../../confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json](../../confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json) |

| 项 | 内容 |
| --- | --- |
| scope | 检查 V3 需求范围、两层存储边界、Redis/Gauss Mock 契约、NER 重点、用户确认闭环、验收草案和文档治理一致性。 |
| out_of_scope | 不评审 V2 before 证据关闭；不评审 V3 代码实现、功能设计、真实 Redis/Gauss 接入或真实 LLM live smoke。 |
| allowed_commands | `Get-Content` 只读读取评审输入；`rg` 查找一致性关键词；`python -m pytest`、`python -m compileall -q src scripts`、`git diff --check` 用于现有护栏验证。 |
| expected_output | 本评审记录，包含发现项、视角总结、已验证命令和处置建议。 |

## 3 Findings

### P0

无。

### P1

无。

### P2

| ID | Issue -> Current artifact behavior -> Impact -> Recommended correction |
| --- | --- |
| V3-REQ-REVIEW-001 | Issue: V3 GUI 确认 JSON 的保留规则与当前治理文档存在冲突。Current artifact behavior: V3 IR、D077 和合同测试都把 `docs/confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json` 当作当前评审输入和签署证据；但 [../../PROJECT.md](../../PROJECT.md) 仍写着临时确认 JSON 不再长期保留在 HEAD，[../../current/DECISIONS.md](../../current/DECISIONS.md) 也保留“历史确认 JSON 已合并到台账、需要细节通过 Git 历史追溯”的通用说法。Impact: 维护者可能按治理规则删除当前 V3 GUI 签署文件，导致 D077、IR 附录和合同测试失去证据来源。Recommended correction: 明确 V3 GUI 确认 JSON 是当前版本评审输入证据，可保留至 V3 需求评审/处置/闭环完成；或将 JSON 内容完全合并入台账并移除所有 HEAD 引用与测试断言。 |

### P3

| ID | Issue -> Current artifact behavior -> Impact -> Recommended correction |
| --- | --- |
| V3-REQ-REVIEW-002 | Issue: V3.1 文档更新日期未反映本轮 2026-06-25 的修订。Current artifact behavior: V3 IR、SR 分解和 current 文档仍显示最近更新/最后更新为 2026-06-24，V3.1 版本行也使用 2026-06-24；但本轮已在 2026-06-25 继续推进并修订。Impact: 审计链路会把 GUI 确认时间和文档修订时间混在一起。Recommended correction: 将本轮修订文件的最近更新/最后更新和 V3.1 版本行日期更新为 2026-06-25，保留 GUI `confirmed_at=2026-06-24T18:14:23` 不变。 |
| V3-REQ-REVIEW-003 | Issue: Redis key 来源措辞尚未完全统一。Current artifact behavior: D077、SR 分解和 Data Contract 使用 `canonical_name` + 经确认 `aliases`；但 V3 IR 5.1 仍写“来自实体标准名或经确认的实体词表”，V3 IR 范围表仍只写 key 是实体词。Impact: 后续设计可能把“经确认实体词表”解释成 aliases 以外的独立来源，弱化“不自动生成别名”的已确认约束。Recommended correction: 将 V3 IR 中 Redis key 来源统一改为 `canonical_name` + 经确认 `aliases`，并显式说明不自动生成别名。 |

## 4 视角总结

| 视角 | 结论 |
| --- | --- |
| 架构边界 | 两层存储拆分为 `EntityWordCache` 与 `StructuredEntityStore`，真实 Redis/Gauss 排除在 V3 初始范围外，边界清晰。 |
| 输入输出契约 | Redis 单值、Gauss 最小字段、NER stage 输出和 storage trace 均有设计输入；Redis key 来源需进一步统一措辞。 |
| 异常语义 | duplicate key、dangling entity ID、schema error、dependency failed、cache/entity miss 已覆盖到需求和验收草案。 |
| NER 主线 | SR-V3-A05 将 Query validation、need-linking、mention detection、type classification、normalization、storage lookup、candidate construction 和状态聚合作为最高优先级，满足用户重点。 |
| 验收与回归 | V1/V2 回归、Redis/Gauss Mock、两层集成、NER golden cases 和敏感扫描均进入验收草案。 |
| 文档治理 | 当前需要处置 V3 GUI 确认 JSON 保留规则与日期口径。 |

## 5 已验证命令

| 命令 | 结果 |
| --- | --- |
| `python -m pytest` | 通过，`80 passed`。 |
| `python -m compileall -q src scripts` | 通过。 |
| `git diff --check` | 通过；仅输出既有 LF 将被 CRLF 替换的工作区警告。 |

## 6 推荐处置动作

| Finding | 推荐动作 |
| --- | --- |
| V3-REQ-REVIEW-001 | 接受。修订治理说明和决策台账，明确当前 V3 GUI 确认 JSON 的保留期限或改为完全合并。 |
| V3-REQ-REVIEW-002 | 接受。统一更新本轮修订文档日期为 2026-06-25。 |
| V3-REQ-REVIEW-003 | 接受。修订 V3 IR 5.1 和相关范围措辞，与 D077 保持一致。 |

## 7 Disposition Readiness

无 P0/P1 阻塞。建议进入需求评审处置，处置完成后再进行闭环验证；闭环前不要进入 V3 功能设计。
