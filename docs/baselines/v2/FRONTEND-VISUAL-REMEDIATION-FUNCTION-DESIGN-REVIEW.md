# DVEntityLinking V2 前端视觉风格补救功能设计独立评审记录

---

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Review type | Function design review |
| Review object | [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) |
| Review date | 2026-06-02 |
| Reviewer | Lovelace，no-context 独立评审 |
| Review mode | Read-only, no-context |
| 结论 | Ready for disposition；无 P0，3 个 P1，3 个 P2 |

## Review 输入

| 输入 | 结果 |
| --- | --- |
| [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md) | 已读取并按 AC、接口、证据、D003 核对 |
| [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md) | 已核对 AC-V2-FE-VIS-001 至 009 |
| [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md) | 已核对需求评审发现 |
| [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) | 已核对处置输入 |
| [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) | 已核对需求闭环结论 |
| [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md)、[SR.md](./SR.md) | 已核对既有 Flask/API/单入口约束 |
| [../../current/DECISIONS.md](../../current/DECISIONS.md)、[../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md)、[../../releases/V2.md](../../releases/V2.md) | 已核对 D003、D041、D058-D061 和当前 blocked 状态 |
| `src/dv_entity_linking/web.py`、`scripts/run_web_demo.py`、`scripts/run_v2_acceptance_smoke.py` | 已核对接口、路径和旧 evidence 产物 |
| `tests/test_web.py`、`tests/test_contract_artifacts.py` | 已核对现有 schema、test id 和 evidence 断言 |
| `outputs/logs/v2_frontend_desktop_1366x768.png`、`outputs/logs/v2_frontend_narrow_390x844.png` | 文件存在且非空 |

## Findings

### P0

None.

### P1

#### FE-VIS-SR-001 `/api/link` 前端依赖字段与既有 Flask safe projection 不一致

Issue -> `/api/link` 前端依赖字段与既有 Flask safe projection 不一致。

Current artifact behavior -> SR 在接口表中要求 `mentions[].status`、`mentions[].linked_entity`、`mentions[].candidates[]`、`mentions[].no_candidate_reason`，但现有实现和测试使用 `mention_results[]` 承载 status、candidates、linked entity 和 LLM linkage。

Impact -> 实现者按 SR 接线会找错字段，mention/candidate/entity/LLM selection linkage 可能不可实现或需要未记录 adapter。

Recommended correction -> 将接口设计改为既有 `mention_results[].mention.text/span/predicted_type`、`mention_results[].status`、`mention_results[].linked_entity`、`mention_results[].candidates[]`；若 UI 内部仍叫 `mentions[]`，必须定义 API-to-UI adapter schema。

#### FE-VIS-SR-002 visual traceability artifact schema 无法可靠执行阻塞规则

Issue -> visual traceability artifact schema 无法可靠执行“任一 P0/P1 visual AC 未 pass 即阻塞”。

Current artifact behavior -> schema 要求每个 AC 至少一个 item，但 item 字段没有 `ac_id/ac_ids`、`priority/blocking_level` 或 `evidence_type`；同时 item 级 `manual_user_acceptance_status` 允许 `not_applicable`，但阻塞规则又要求缺少 `accepted` 必须阻塞。

Impact -> 自动化无法确定哪个 item 对应 AC-V2-FE-VIS-001 至 009，也无法稳定计算 P0/P1 `blocking_count`；用户视觉门禁可能被误阻塞或误放行。

Recommended correction -> 增加 `items[].ac_ids`、`items[].priority`、`summary.ac_statuses`、`summary.blocking_ac_ids`；将用户接受结论提升为 top-level `manual_user_acceptance_status`，并明确 item 级 `not_applicable` 不可替代全局 accepted。

#### FE-VIS-SR-003 D003 未确认真实感 DV 内容边界尚未进入可审计 schema

Issue -> D003 “未确认真实感 DV 内容”边界尚未进入可审计 schema。

Current artifact behavior -> SR 有内容来源分类和扫描要求，但 visual semantic checks 只列出 `no_forbidden_sensitive_content`，偏向 secret、raw prompt、raw response，未要求记录新增 UI copy、metric/topology/interface label 的来源分类。

Impact -> 实现可能新增看似真实的 observability label、metric、topology、interface 或 mock boundary，并通过敏感词扫描。

Recommended correction -> 在 artifact 中增加 `d003_content_inventory[]`，记录 `text_or_label`、`classification`、`source_reference`、`decision_id`、`needs_d003_confirmation`；新增 check `no_unconfirmed_real_dv_content`。

### P2

#### FE-VIS-SR-004 新旧 traceability artifact 路径和生成方存在混淆风险

Issue -> 新旧 traceability artifact 路径和生成方存在混淆风险。

Current artifact behavior -> 新 SR 指定 `v2_frontend_visual_traceability_check.*`，但现有 smoke 仍写 `v2_frontend_traceability_check.*`，现有 contract test 也只断言旧路径文本。

Impact -> 后续实现/测试可能继续生成上一轮 artifact，误认为满足视觉补救证据。

Recommended correction -> 明确由 `scripts/run_v2_acceptance_smoke.py` 生成新 visual artifact，或指定新的 browser evidence generator；同时标注旧 `v2_frontend_traceability_check.*` 仅为上一轮历史证据。

#### FE-VIS-SR-005 窄屏无文本重叠/裁剪风险未转成明确检查项

Issue -> 窄屏“无文本重叠/裁剪风险”未转成明确检查项。

Current artifact behavior -> SR 要求 `390x844` 无横向 overflow 和稳定顺序，但 VisualSemanticCheck 只有 `no_horizontal_overflow_narrow`。

Impact -> 长 entity id、canonical name、chip 文本可能在控件内裁剪或重叠，但 body 无横向 overflow 时仍通过。

Recommended correction -> 增加 CSS 设计约束和检查项，例如 `min-width:0`、`overflow-wrap:anywhere`、按钮/卡片稳定尺寸，以及 browser bounding-box check `no_text_overlap_or_clipping_narrow`。

#### FE-VIS-SR-006 `/api/entities` 错误码设计与现有接口不一致

Issue -> `/api/entities` 错误码设计与现有接口不一致。

Current artifact behavior -> SR 声明 `invalid_entity_type`、`invalid_entity_id`、`not_found`，现有 `/api/entities/<id>` 404 返回 `status=no_match` 与 `no_match_reason`，没有结构化 error code。

Impact -> 局部 safe error UI 与测试期望可能分叉。

Recommended correction -> 要么把 SR 改为沿用现有 `no_match/no_match_reason`，要么明确本轮允许补充 safe error code 且不改变核心语义。

### P3

None.

## Perspective summaries

| 视角 | 结论 |
| --- | --- |
| Module layering | 保持 Flask single-entry、`web.py` 内嵌 HTML/CSS/JS、`run_web_demo.py` 单入口的方向合理；不需要 React/Next.js 迁移。 |
| Interfaces/schemas/enums | UI region/state schema 基本到位，但 `/api/link` mention schema、traceability AC identity、D003 content inventory 需要补齐。 |
| Runtime flow/state transitions | query -> mention -> candidate -> entity detail -> LLM explanation 的状态转移设计可实现；offline/fallback/degraded/empty 也有设计，但需和真实 `mention_results[]` 字段对齐。 |
| File paths/persistence/config/secrets | 单入口和 V2 sample defaults 一致；secret/raw LLM 边界有覆盖；visual evidence 新旧路径需消歧。 |
| Test mapping to requirements | AC-V2-FE-VIS-001 至 009 均有 TS/TC 映射，但 AC blocking 的 artifact schema 不足，窄屏 text-overlap 与 D003 unconfirmed-content 缺少可执行证据字段。 |

## Verified commands/results

| 命令 | 结果 |
| --- | --- |
| `Get-Content` | 读取目标 SR、基线片段、`web.py`、`run_web_demo.py`、`run_v2_acceptance_smoke.py` 和测试文件。 |
| `rg` | 核对 AC、D003、traceability、test ids、API 字段和 evidence 路径。 |
| `git diff -- docs/baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md` | 无输出，目标文件无当前未提交 diff。 |
| `Get-ChildItem` | 确认 desktop/narrow before screenshots 存在且非空。 |

评审未运行会写 outputs 的测试，未修改文件。

## Disposition readiness

Ready for disposition。该设计不应进入实现或闭环，直到 P1 findings 完成处置并复核；P2 可随处置记录为非阻塞残余风险或同步修订。
