# DVEntityLinking V2 前端视觉风格补救功能设计评审处置记录

---

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 处置对象 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| 被评审文档 | [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) |
| 处置日期 | 2026-06-02 |
| 处置人 | Codex |
| 处置状态 | 功能设计评审处置完成，待独立闭环验证 |
| 总体结论 | 接受全部 3 个 P1 和 3 个 P2；已修订 SR 至 `V2-FE-VIS-SR.1-draft`；未修改前端实现代码。 |

## 输入评审结论

| Priority | Findings | 处置结论 |
| --- | --- | --- |
| P0 | 0 | 无 |
| P1 | 3 | 全部 Accepted，本轮修订 SR |
| P2 | 3 | 全部 Accepted，本轮同步修订 SR |
| P3 | 0 | 无 |

## 逐项处置

| Finding | 级别 | 处置 | 原因 | 修订内容 | 残余风险 |
| --- | --- | --- | --- | --- | --- |
| FE-VIS-SR-001 `/api/link` 前端依赖字段与既有 Flask safe projection 不一致 | P1 | Accepted | 设计必须对齐现有 `/api/link` 的 `mention_results[]`，否则实现会接错字段。 | 在 SR 中补充 API-to-UI adapter schema；明确 UI `VisualWorkbenchState.mentions[]` 由 `mention_results[]` 生成；接口表改为 `mention_results[].mention.text/span/predicted_type`、`mention_results[].status`、`linked_entity`、`candidates[]`、`no_candidate_reason`。 | 无阻塞残余风险；闭环验证需检查 SR 不再要求新增并行顶层 `mentions[]` API。 |
| FE-VIS-SR-002 visual traceability artifact schema 无法可靠执行阻塞规则 | P1 | Accepted | P0/P1 visual AC 必须能自动汇总阻塞，item 无 AC id/priority 会导致误放行。 | 在 SR 的 `VisualTraceabilityArtifact` schema 中增加 `manual_user_acceptance_status` 顶层字段、`items[].ac_ids`、`items[].priority`、`items[].evidence_type`、`summary.ac_statuses`、`summary.blocking_ac_ids`；明确 item 级 `not_applicable` 不可替代全局 accepted。 | 用户视觉判断仍有主观性，但已由顶层人工接受门禁管理。 |
| FE-VIS-SR-003 D003 未确认真实感 DV 内容边界尚未进入可审计 schema | P1 | Accepted | 仅扫描 secret/raw prompt 不足以防止新增真实感 metric/topology/interface label。 | 在 artifact schema 中增加 `d003_content_inventory[]`；定义 `text_or_label`、`classification`、`source_reference`、`decision_id`、`needs_d003_confirmation`；新增 `no_unconfirmed_real_dv_content` 检查。 | 无阻塞残余风险；实现阶段仍需实际生成 inventory。 |
| FE-VIS-SR-004 新旧 traceability artifact 路径和生成方存在混淆风险 | P2 | Accepted | 上一轮旧 artifact 不能替代本轮视觉补救 evidence。 | 在总体设计和 file artifact 章节明确旧 `v2_frontend_traceability_check.*` 仅为前端功能补救历史证据；本轮视觉补救必须生成 `v2_frontend_visual_traceability_check.*`，生成方为后续扩展的 `scripts/run_v2_acceptance_smoke.py` 或测试设计确认的 browser evidence generator。 | 生成脚本尚未实现，作为后续实现/测试阶段工作，不阻塞当前设计处置闭环。 |
| FE-VIS-SR-005 窄屏无文本重叠/裁剪风险未转成明确检查项 | P2 | Accepted | 无 body overflow 不能证明长 ID、chip、按钮文本可读。 | 在窄屏布局和视觉 tokens 中补充 `min-width: 0`、`overflow-wrap: anywhere`、稳定控件尺寸要求；新增 `no_text_overlap_or_clipping_narrow` 检查；更新测试场景和用例名称。 | 浏览器 bounding-box 实现细节留到测试设计/实现阶段，不阻塞当前设计处置闭环。 |
| FE-VIS-SR-006 `/api/entities` 错误码设计与现有接口不一致 | P2 | Accepted | 设计需避免与现有 `/api/entities/<id>` 404 `status=no_match` / `no_match_reason` 语义分叉。 | 接口章节改为沿用现有 safe error 语义：unknown entity detail 返回 HTTP 404，payload 使用 `status=no_match` 与 `no_match_reason`；后续补充 `error_code` 仅可作为 safe projection 增量，不改变 no_match 语义。 | 无阻塞残余风险。 |

## 修订文件

| 文件 | 修订 |
| --- | --- |
| [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) | 更新为 `V2-FE-VIS-SR.1-draft`；补齐 6 个 finding 对应设计修订；状态改为“功能设计评审处置完成，待独立闭环验证”。 |
| [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) | 新增独立功能设计评审记录。 |
| [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md) | 新增本处置记录。 |

## 验证命令

| 命令 | 结果 |
| --- | --- |
| `python -m pytest -p no:cacheprovider tests\test_contract_artifacts.py` | 通过，`5 passed` |
| `python -m pytest -p no:cacheprovider` | 通过，`75 passed` |
| `git diff --check` | 通过，无 whitespace error；仅有 LF/CRLF 工作区提示 |

## 后续闭环验证输入包

请独立闭环验证者只读复核：

- [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md)
- [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md)
- [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)
- [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)
- [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md)
- [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md)
- [../../releases/V2.md](../../releases/V2.md)
- `src/dv_entity_linking/web.py`
- `scripts/run_v2_acceptance_smoke.py`
- `tests/test_contract_artifacts.py`

闭环验证重点：

- FE-VIS-SR-001 至 FE-VIS-SR-006 是否均被 SR 修订覆盖。
- P1 是否全部关闭，P2 是否同步修订或有清晰非阻塞残余风险。
- SR 是否仍保持“待独立闭环验证”，未越权进入实现或验收候选。
- 文档导航、项目状态和契约测试是否已登记新 review/disposition artifact。
