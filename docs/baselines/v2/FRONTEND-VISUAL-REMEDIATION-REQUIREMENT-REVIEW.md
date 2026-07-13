# DVEntityLinking V2 前端视觉风格补救需求独立评审记录

日期：2026-06-02

## 基本信息

| 项 | 内容 |
| --- | --- |
| 评审类型 | requirement review |
| 评审对象 | DVEntityLinking V2 frontend visual style remediation requirement draft |
| 评审模式 | no-context independent read-only review |
| 评审者 | Nash |
| 结论 | Ready for disposition；无 P0，2 个 P1，2 个 P2，1 个 P3 |

## 评审输入

| 类型 | 文件 |
| --- | --- |
| 需求草稿 | [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md) |
| 前端功能补救需求 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| 前端功能补救设计 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| V2 release record | [../../releases/V2.md](../../releases/V2.md) |
| 决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| 当前 Web 实现 | `src/dv_entity_linking/web.py` |
| 旧版桌面截图 | `outputs/logs/v2_frontend_desktop_1366x768.png` |
| 旧版窄屏截图 | `outputs/logs/v2_frontend_narrow_390x844.png` |

## Findings

### P0

无。

### P1

| ID | Finding | 问题 | 影响 | 建议 |
| --- | --- | --- | --- | --- |
| FE-VIS-REQ-001 | D003 safety traceability is too narrow | D003 不只覆盖 secret redaction，还覆盖真实 DV 实体、字段、接口、数据样例、能力边界和 Mock 策略确认；当前草稿只把 D003 映射到 secret/API key/token/base URL/raw prompt/raw response/full logs。 | 后续视觉补救可能为了更像 observability 页面而引入真实感 metric label、topology label、sample detail、interface name 或 mock 边界，仍可能通过当前 AC。 | 增加 SR/AC：视觉补救只能使用已确认 V2 样例或明确 synthetic/mock UI copy；任何新增真实感 DV 字段、接口、实体、样例、指标或 Mock 边界必须回到 D003 用户确认。 |
| FE-VIS-REQ-002 | Visual traceability artifact schema is not defined | 草稿要求 visual traceability artifact，但未定义最小字段、状态、阻塞规则或 downgrade 分类。 | 可能再次出现叙述型证据或 marker 型证据声称视觉变化，却没有逐原型、逐 AC 的 pass/fail 责任。 | 定义最小 schema：`prototype_ref`、`absorbed_principle`、`target_ui_regions`、`before_screenshot`、`after_screenshot`、`same_viewport_and_query`、`automated_visual_semantic_checks`、`manual_user_acceptance_status`、`downgrade_classification`、`reviewer_result` 等；任何 P0/P1 visual AC 未 pass 或无用户视觉接受均阻塞 closure。 |

### P2

| ID | Finding | 问题 | 影响 | 建议 |
| --- | --- | --- | --- | --- |
| FE-VIS-REQ-003 | Before/after screenshot comparability is underspecified | 草稿要求 before/after 桌面和窄屏截图，但没有要求同 query、mode、viewport、browser zoom、theme 和 interaction state。 | 视觉差异可能由不同场景或 UI 状态造成，而非真正风格补救。 | 要求 canonical scenario：同一 sample query、默认 `offline_demo`、同一 selected mention/candidate、同一 viewport、browser zoom/device scale、debug collapsed。 |
| FE-VIS-REQ-004 | “Near first screen” remains open to weak interpretation | AC-V2-FE-VIS-002 中“同屏或近首屏”没有边界。 | 设计仍可保留大段 full-width 纵向白卡片并声称近首屏满足。 | 明确桌面第一 viewport 必须展示 cohesive shell 和 grouped control/results/detail zones，不超过孤立 full-width stacked panels；功能设计需给出 annotated desktop/narrow layout sketch。 |

### P3

| ID | Finding | 问题 | 影响 | 建议 |
| --- | --- | --- | --- | --- |
| FE-VIS-REQ-005 | Prototype source snapshots are not frozen | 草稿总结官方 README 信号，但未记录 capture date/source snapshot。 | 未来评审可能不知道参考源状态。 | 增加 “reference captured on 2026-06-02”，并声明矩阵文本是规范要求，live external pages 仅为参考。 |

## 正向观察

- 需求草稿相对上一轮已有实质提升。
- 已把 prototype references 转成矩阵。
- 已禁止 weak proof。
- 已要求 before/after screenshot、单一 `run_web_demo.py`、不做生产级前端和用户视觉验收。
- 两张旧版截图支持当前问题判断：功能可用但视觉仍是浅灰背景、白色 panel、普通控件和 section 堆叠。

## 评审结论

Ready for disposition。无 P0；P1 必须在需求闭环和功能设计入口前完成处置。
