# DVEntityLinking V2 前端视觉风格补救功能设计说明书

---

> 文档治理说明：本文承接已闭环的 [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)，只覆盖 V2 前端视觉风格和原型吸收补救的功能设计。本文不修改 V2 实体 schema、链接算法、样例数据、LLM 能力边界或 Web demo 单一启动入口。本文已完成独立功能设计评审、处置修订和独立闭环验证，可作为 V2 前端视觉风格补救代码实现输入；进入验收候选或 accepted/closed 仍需后续实现、测试、评审、视觉证据和用户验收门禁。

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 特性名称 | V2 frontend visual remediation workbench |
| 版本号 | V2-FE-VIS-SR.2-closed |
| 编写日期 | 2026-06-02 |
| 编写人 | Codex |
| 审核人 | no-context 独立功能设计评审 Lovelace |
| 状态 | 功能设计评审闭环已通过，可作为代码实现输入 |

## 版本历史

| 版本号 | 修改日期 | 修改人 | 修改描述 |
| --- | --- | --- | --- |
| V2-FE-VIS-SR.0-draft | 2026-06-02 | Codex | 基于已闭环的 V2 前端视觉风格补救 IR 形成 SR 设计草稿，补齐工作台布局、原型吸收、状态 schema、traceability artifact、D003 安全边界和设计级测试映射。 |
| V2-FE-VIS-SR.1-draft | 2026-06-02 | Codex | 接受独立功能设计评审 3 个 P1、3 个 P2，补齐 `mention_results[]` API-to-UI adapter、traceability AC 阻塞字段、D003 content inventory、新旧 artifact 路径边界、窄屏文本重叠检查和 `/api/entities` 错误语义。 |
| V2-FE-VIS-SR.2-closed | 2026-06-02 | Codex | 记录独立功能设计评审闭环验证通过，FE-VIS-SR-001 至 FE-VIS-SR-006 均 Closed with recorded residual risk，可作为代码实现输入。 |

---

# 1 概述

## 1.1 目的

本文将 V2 前端视觉风格补救需求转换为可实现、可评审、可测试的功能设计，重点解决上一轮补救中“功能存在但视觉风格仍像基础白卡片表单”的问题。

本文的设计目标：

- 把 SigNoz、OpenGenerativeUI、Tambo 的参考原则转化为本项目页面区域、组件状态和验收证据。
- 约束桌面首屏必须形成 cohesive workbench shell，而不是孤立 full-width stacked panels。
- 将 LLM 安全解释设计成可联动的结构化组件区。
- 固化 before/after canonical scenario、visual traceability artifact schema 和阻塞规则。
- 明确不进入本轮的生产级前端、框架迁移、真实 DV 内容扩展和算法改动。

预期读者：

- V2 前端视觉风格补救功能设计评审者。
- 后续代码实现负责人。
- 后续测试设计、测试开发、实现评审、验收复核人员。

## 1.2 范围

| 范围 | 设计结论 |
| --- | --- |
| Web demo 入口 | 继续只维护 `scripts/run_web_demo.py`；当前版本默认加载 V2 样例。 |
| Web UI 实现边界 | 仍在 `src/dv_entity_linking/web.py` 的轻量 Flask 页面、CSS 和原生 JS 内完成；本设计不要求 React/Next.js 迁移。 |
| 页面形态 | 首屏重构为运维观测工作台，包括 shell/status band、query/filter command zone、result stream、detail/explanation zone、catalog filter zone。 |
| 原型吸收 | 原型只作为信息组织、状态表达和组件化交互原则来源，不复制外部产品 UI、商标、图标或完整能力。 |
| 交互状态 | 保留并强化多 mention、candidate、entity detail、catalog filter、LLM explanation 的可见 selection state。 |
| 视觉证据 | 后续实现/测试必须输出 before/after 桌面和窄屏截图、visual traceability artifact、自动化视觉语义检查和用户视觉接受结论。 |
| 安全内容边界 | 只能使用已确认 V2 样例或明确 synthetic/mock UI copy；任何新增真实感 DV 字段、接口、实体、指标、拓扑标签、样例或 Mock 边界必须回到 D003 用户确认。 |

范围外：

- 不建设生产级 observability 平台、仪表盘编辑器、告警规则、权限、多租户或复杂拓扑。
- 不引入新的前端构建链，除非后续设计评审判定 Flask 内嵌页面无法满足基线并回到用户确认。
- 不改变实体 schema、链接算法、V2 样例、评测口径、LLM fallback 状态机或 API 核心语义。
- 不展示真实 secret/API key/token、真实 base URL、raw prompt、raw response、完整 LLM 日志或完整生产 payload。

## 1.3 缩略语和术语

| 缩略语/术语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| Visual Workbench | Visual Workbench | 本轮视觉补救后的 V2 运维实体链接工作台 |
| Status Band | Status Band | 首屏顶部状态带，汇总 mode、entity count、type counts、LLM 状态和 query 状态 |
| Result Stream | Result Stream | 多 mention 结果流，展示 mention/candidate/status 的可扫读列表 |
| Detail Zone | Detail and Explanation Zone | 实体详情、相似实体和 LLM 安全解释的联动区域 |
| Visual Traceability | Visual Traceability Artifact | 原型吸收、视觉 AC、截图、自动化检查和人工确认的追踪证据 |
| Downgrade Classification | Downgrade Classification | 标记证据是否降级为 marker/API-only/no visual delta 等不可接受状态 |

## 1.4 参考文献

| 文档名称 | 文档编号 | 版本 | 来源 |
| --- | --- | --- | --- |
| V2 前端视觉风格补救需求分析 | IR-DVEntityLinking-V2-FE-Visual-Remediation | V2-FE-VIS.2-closed | [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md) |
| V2 前端视觉风格补救需求评审 | FE-VIS-REQ-REVIEW | 2026-06-02 | [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md) |
| V2 前端视觉风格补救需求评审处置 | FE-VIS-REQ-DISPOSITION | 2026-06-02 | [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| V2 前端视觉风格补救需求闭环验证 | FE-VIS-REQ-CLOSURE | 2026-06-02 | [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |
| V2 前端视觉风格补救功能设计评审 | FE-VIS-SR-REVIEW | 2026-06-02 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| V2 前端视觉风格补救功能设计评审处置 | FE-VIS-SR-DISPOSITION | 2026-06-02 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md) |
| V2 前端视觉风格补救功能设计闭环验证 | FE-VIS-SR-CLOSURE | 2026-06-02 | [FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| V2 前端功能补救设计 | SR-DVEntityLinking-V2-FE-Remediation | V2-FE-SR.2-closed | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| V2 主功能设计 | SR-DVEntityLinking-V2 | V2.2 | [SR.md](./SR.md) |
| 当前决策台账 | DECISIONS | 2026-06-02 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| SigNoz 参考 | External reference | captured 2026-06-02 | https://github.com/SigNoz/signoz |
| OpenGenerativeUI 参考 | External reference | captured 2026-06-02 | https://github.com/CopilotKit/OpenGenerativeUI |
| Tambo 参考 | External reference | captured 2026-06-02 | https://github.com/tambo-ai/tambo |

---

# 2 需求实现设计

## 2.1 总体设计方案概述

### 2.1.1 设计定位

本轮采用“视觉工作台壳层 + 现有安全投影 + 浏览器证据”的方案。后端 API 和核心链接能力保持不变；前端在现有 Flask 页面内重构视觉层级、状态表达和联动组件。

```text
scripts/run_web_demo.py
  -> src/dv_entity_linking/web.py:create_app(...)
  -> GET /
      renders visual workbench shell, CSS, native JS
  -> existing safe APIs
      /api/status
      /api/link
      /api/entities
      /api/entities/<entity_id>
      /api/retrieve
  -> browser evidence and visual traceability artifacts
      outputs/logs/v2_frontend_visual_traceability_check.json
      outputs/logs/v2_frontend_visual_traceability_check.md
      before/after desktop and narrow screenshots
```

Artifact 边界：`outputs/logs/v2_frontend_traceability_check.json` 和 `.md` 是上一轮前端功能补救的历史反向核查证据；本轮视觉风格补救必须由后续扩展的 `scripts/run_v2_acceptance_smoke.py` 或测试设计确认的 browser evidence generator 生成 `outputs/logs/v2_frontend_visual_traceability_check.json` 和 `.md`，不得用旧 artifact 替代。

核心约束：

| 约束 | 设计说明 |
| --- | --- |
| 不做框架迁移 | 继续使用 Flask-rendered HTML、CSS 和原生 JS；如后续必须拆分静态文件，应限定在 Web UI 边界内并在设计评审中说明。 |
| 不改变后端语义 | 允许复用或补充 safe projection 字段，但不得改变 linking、retrieval、evaluation 的核心状态语义。 |
| 不引入真实感未确认内容 | 页面 copy、指标、标签、拓扑名和 Mock 边界必须来自已确认 V2 样例或明确标为 synthetic/mock。 |
| 不以 marker 替代视觉 | `data-testid` 用于定位测试，不作为视觉风格完成证明。 |
| 用户视觉确认必需 | 自动化通过后仍必须记录用户视觉接受结论，缺失则阻塞验收关闭。 |

### 2.1.2 页面区域架构

本轮页面拆为 6 个稳定区域，每个区域具有视觉职责、交互职责和测试职责。

| 区域 | `data-testid` | 视觉职责 | 交互职责 |
| --- | --- | --- | --- |
| Workbench shell | `visual-workbench-shell` | 提供非白卡片堆叠的整体工作台外壳、背景、网格和密度基线。 | 承载所有子区域和全局视觉状态。 |
| Status band | `status-band` | 首屏状态带，聚合 mode、catalog、entity_count、type_counts、LLM status、latest query status。 | 点击 LLM status 时切换 explanation 到 global context。 |
| Query command zone | `query-command-zone` | 类 query builder / filter rail 的输入和控制区域。 | 输入英文 query、选择 sample/mode、触发 link、切换 entity type filter。 |
| Result stream | `result-stream` | 多 mention 结果流，展示 mention/candidate/status/partial/no_match。 | 点击 mention/candidate 更新 selection state。 |
| Detail and explanation zone | `entity-detail-zone`、`llm-explanation-component` | 展示 selected entity、similar entities、LLM 阶段/上下文/候选/原因。 | 随 mention/candidate/entity selection 同步更新。 |
| Catalog filter zone | `catalog-filter-zone` | 展示 type counts 和实体目录，形成可扫读的 catalog 面板。 | 类型过滤、实体选择、详情联动。 |

### 2.1.3 桌面布局草案

Desktop canonical viewport 为 `1366x768`。第一 viewport 必须出现 cohesive workbench shell，不能由多个 full-width white sections 纵向堆叠组成。

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Status band: offline_demo | 25 entities | type counts | LLM not used | run │
├───────────────────────────┬───────────────────────────┬────────────────────┤
│ Query command zone        │ Result stream              │ Detail/explanation │
│ - sample/query input      │ - query summary            │ - selected entity  │
│ - mode/fallback controls  │ - mention cards            │ - LLM component    │
│ - type filter rail        │ - candidate stack          │ - similar entities │
├───────────────────────────┴───────────────────────────┬────────────────────┤
│ Catalog filter zone: type counts + entity list          │ Debug collapsed    │
└─────────────────────────────────────────────────────────┴────────────────────┘
```

桌面视觉要求：

- Status band 必须贴近顶部，成为第一眼可见的信息密度锚点。
- Query/filter、result stream、detail/explanation 必须在同一首屏网格中形成横向或 2+1 工作台关系。
- 白色卡片可以作为局部内容容器，但不得成为整个页面唯一视觉语言；shell、status band、分隔线、状态色、密度和面板层级必须形成明显差异。
- 首屏至少可见 selected mention/candidate 的联动关系，用户无需展开 debug JSON。
- Debug 区域默认 collapsed，不能抢占首屏主视觉。

### 2.1.4 窄屏布局草案

Narrow canonical viewport 为 `390x844`。窄屏允许纵向滚动，但必须保持上下文连续、无横向溢出、无关键文本重叠。

```text
┌──────────────────────────────┐
│ Compact status band           │
├──────────────────────────────┤
│ Query command zone            │
├──────────────────────────────┤
│ Result summary + mention list │
├──────────────────────────────┤
│ Selected candidate/detail     │
├──────────────────────────────┤
│ LLM explanation component     │
├──────────────────────────────┤
│ Catalog filter/list           │
├──────────────────────────────┤
│ Debug collapsed               │
└──────────────────────────────┘
```

窄屏视觉要求：

- 不得出现 body 或关键区域横向 overflow。
- 状态、query、result、detail、LLM explanation、catalog 的顺序必须稳定，避免用户在提交后丢失当前上下文。
- 按钮、状态 chip 和候选卡文字必须换行或截断得当，不得溢出容器。
- 所有 grid/flex 子项必须设置可收缩边界，例如 `min-width: 0`；长 entity id、canonical name、chip 文本和按钮文字必须使用 `overflow-wrap: anywhere`、可读截断或稳定尺寸，防止 body 无 overflow 但文本在容器内裁剪或重叠。
- 后续浏览器证据必须包含 `no_text_overlap_or_clipping_narrow` bounding-box/scrollWidth 类检查；单独通过 `no_horizontal_overflow_narrow` 不足以证明窄屏可验收。
- 字体不得按 viewport width 缩放；通过布局和文本换行解决窄屏适配。

### 2.1.5 参考原型吸收设计

| 参考 | 吸收原则 | 设计落点 | 不吸收边界 |
| --- | --- | --- | --- |
| SigNoz | 运维观测页面的信息密度、状态概览、query/filter rail、列表详情联动。 | `status-band`、`query-command-zone`、`result-stream`、`catalog-filter-zone`、桌面 3 区工作台网格。 | 不做真实 telemetry、charts editor、告警规则、traces/logs 平台。 |
| OpenGenerativeUI | AI 输出是结构化交互组件，不只是文本响应。 | `llm-explanation-component` 展示 stage chips、context、candidate reason、fallback/degraded/empty/loading state。 | 不引入 CopilotKit、agent runtime、iframe sandbox 或流式生成 UI 架构。 |
| Tambo | 组件 schema、props/state 和用户选择应清晰可观察。 | `VisualWorkbenchState`、selection state、component state schema、traceability item state。 | 不迁移 React SDK，不要求 AI 动态生成页面组件。 |

设计评审检查点：

- 每个参考原则必须至少映射到一个 UI 区域、一个 state 字段和一个设计级测试场景。
- 如果实现后某原则只能由 `data-testid` 或 API 字段证明，必须标记 `downgrade_classification=weak_marker_only` 或 `api_only` 并阻塞验收。
- 如因 Flask 实现边界导致无法吸收某参考原则，必须在设计评审处置阶段显式回到用户确认。

### 2.1.6 视觉设计 tokens 和约束

本设计不固定像素级 CSS，但给出实现必须遵守的视觉约束。

| 维度 | 约束 |
| --- | --- |
| Shell | 页面必须有统一 workbench shell；背景、边界、状态带和主网格应能与普通白卡片表单明显区分。 |
| 信息密度 | 首屏展示运行状态、query 控制、结果摘要、至少一个 mention/candidate 上下文和 LLM/catalog 概览。 |
| 状态色 | linked、partial、no_match、not_required、ambiguous、degraded/fallback 必须有可区分的 chip 或状态标识。 |
| 选中态 | selected mention、candidate、entity、LLM context 必须可见，不依赖 debug JSON。 |
| 组件半径 | 卡片或面板圆角保持 8px 或更小，避免偏营销风格。 |
| 文本 | 不使用 viewport-width 字号缩放；按钮、chip、entity id、canonical name 和卡片长文本必须换行、可读截断或使用更紧凑结构；窄屏需检查无重叠和无不可读裁剪。 |
| 图形资产 | 本轮不需要引入外部图片；UI 以真实 DVEntityLinking 数据状态和组件组织承担视觉变化。 |
| 调试区 | Debug JSON 默认 collapsed；可用于复核但不得成为主证据。 |

## 2.2 需求分解

### IR-V2-FE-VIS-001 V2 前端视觉风格原型吸收补救

#### 2.2.1.1 IR 原始描述

用户指出上一轮 V2 前端补救后页面视觉风格仍无明显变化，质疑是否真的参考了 SigNoz、OpenGenerativeUI、Tambo 等原型。需求闭环后要求重新按 DV 流程进入功能设计，保证后续实现能够证明“页面风格确实发生可见变化”，并且不能以 API projection、DOM marker 或 section 可见性替代视觉验收。

#### 2.2.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| 需求优先级 | 高，V2 验收关闭前阻塞 |
| 需求类型 | 可用性需求 + 可测试性需求 + 前端功能展示需求 |
| 涉及模块 | `src/dv_entity_linking/web.py`、`scripts/run_web_demo.py`、`tests/test_web.py`、`scripts/run_v2_acceptance_smoke.py`、文档/验收证据 |

#### 2.2.1.3 IR 与 SR 的分解关系

| IR 编号 | SR 编号 | 分解说明 |
| --- | --- | --- |
| IR-V2-FE-VIS-001 | SR-V2-FE-VIS-D01 | 原型吸收矩阵和视觉设计原则落地 |
| IR-V2-FE-VIS-001 | SR-V2-FE-VIS-D02 | Workbench shell、桌面首屏和窄屏布局 |
| IR-V2-FE-VIS-001 | SR-V2-FE-VIS-D03 | 多 mention、候选、详情和 catalog 联动视觉 |
| IR-V2-FE-VIS-001 | SR-V2-FE-VIS-D04 | LLM 交互式安全解释组件 |
| IR-V2-FE-VIS-001 | SR-V2-FE-VIS-D05 | Visual traceability artifact、截图和人工确认门禁 |
| IR-V2-FE-VIS-001 | SR-V2-FE-VIS-D06 | D003 真实 DV 内容和 Mock 边界保护 |

### SR-V2-FE-VIS-D01 原型吸收矩阵和视觉设计原则落地

#### 2.2.2.1 SR 描述

功能设计和后续实现必须把 SigNoz、OpenGenerativeUI、Tambo 的参考原则落到可观察 UI 区域、component state 和验收证据。参考原型不作为 live dependency；2026-06-02 capture 的原则已经在 IR 中转化为本项目规范。

#### 2.2.2.2 SR 实现思路

在设计、实现和 traceability artifact 中建立三层映射：

| 层级 | 内容 |
| --- | --- |
| Prototype principle | SigNoz/OpenGenerativeUI/Tambo 或 project visual AC 的具体原则。 |
| UI region/component | `status-band`、`query-command-zone`、`result-stream`、`entity-detail-zone`、`llm-explanation-component`、`catalog-filter-zone`。 |
| Evidence | before/after screenshot、automated visual semantic check、manual user acceptance。 |

最小映射要求：

| 参考 | UI 区域 | State 字段 | 测试场景 |
| --- | --- | --- | --- |
| SigNoz | `status-band`、`query-command-zone`、`result-stream`、`catalog-filter-zone` | `runtimeSummary`、`activeTypeFilter`、`queryStatus` | TS-V2-FE-VIS-001、002、003 |
| OpenGenerativeUI | `llm-explanation-component` | `activeExplanationContext`、`llmComponentState` | TS-V2-FE-VIS-005、006 |
| Tambo | selection linkage across result/detail/explanation | `activeMentionIndex`、`activeCandidateId`、`activeEntityId` | TS-V2-FE-VIS-004、005 |

#### 2.2.2.3 功能实现刷新

后续实现应在页面初始化时定义 `VisualWorkbenchState` 并通过用户操作更新组件状态。后续 evidence 生成脚本必须读取 DOM/状态语义和截图路径，填充 visual traceability artifact。

#### 2.2.2.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 原型原则固化在本地文档和测试，不依赖 live external page。 |
| 可用性 | 是 | 页面风格变化有明确视觉区域和交互状态承载。 |
| 安全性 | 是 | 不复制外部商标/图标/专有 UI，也不新增真实 DV 内容。 |
| 可维护性 | 是 | 原型原则映射到有限区域，避免无限扩展成产品级前端。 |

#### 2.2.2.5 架构元素影响列表

| 架构元素 | 影响说明 | 修改类型 |
| --- | --- | --- |
| `docs/baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md` | 定义原型吸收设计和评审输入 | 新增 |
| `src/dv_entity_linking/web.py` | 后续实现页面区域和 state，当前设计阶段不改 | 后续修改 |
| `scripts/run_v2_acceptance_smoke.py` | 后续生成 visual traceability artifact | 后续修改 |

### SR-V2-FE-VIS-D02 Workbench shell、桌面首屏和窄屏布局

#### 2.2.3.1 SR 描述

Web 首页必须直接呈现 V2 visual workbench。桌面 `1366x768` 首屏必须包含 cohesive workbench shell、grouped control zone、results zone、detail/explanation zone，不得退化为多个孤立 full-width stacked panels。窄屏 `390x844` 必须无横向溢出、无关键重叠，并保持 query -> result -> detail -> explanation -> catalog 的上下文顺序。

#### 2.2.3.2 SR 实现思路

桌面布局采用 CSS grid 或等价 flex/grid 方案：

| Region | Desktop 设计 | Narrow 设计 |
| --- | --- | --- |
| Status band | 横跨顶部，紧凑展示 runtime/type/LLM/query 状态 | 紧凑 chip 组，可换行 |
| Query command zone | 左侧或上左控制区，包含 query、sample、mode、entity type filter | 位于 status 之后，单列 |
| Result stream | 中央主区域，展示 mention cards 和 candidate stack | 位于 query 后，优先展示 summary 和 mentions |
| Detail/explanation | 右侧联动区域，展示 selected entity 和 LLM component | 位于 result 后，拆成 detail 与 explanation 两段 |
| Catalog filter | 桌面底部或侧栏，展示 type counts/entity list | 位于 explanation 后，单列可滚动 |
| Debug | 次要区域，默认 collapsed | 页面末尾，默认 collapsed |

页面必须提供以下稳定 test ids：

| `data-testid` | 要求 |
| --- | --- |
| `visual-workbench-shell` | 页面根工作台容器 |
| `status-band` | 顶部状态带 |
| `query-command-zone` | Query 和过滤控制区 |
| `result-stream` | 结果流 |
| `mention-result-card` | 单个 mention card |
| `entity-detail-zone` | 详情区 |
| `llm-explanation-component` | LLM 解释组件 |
| `catalog-filter-zone` | catalog/filter 区 |
| `debug-panel` | 默认折叠 debug 区 |

#### 2.2.3.3 功能实现刷新

加载流程：

1. Browser 打开 `/`。
2. JS 调用 `/api/status` 和 `/api/entities`。
3. 渲染 status band、query command zone、catalog counts 和默认空状态。
4. 用户提交 canonical query `Check ALM-51020 and CPU Usage.`。
5. JS 调用 `/api/link`，更新 result stream、selection state、detail/explanation。
6. 默认 debug panel 仍为 collapsed。

布局异常语义：

| 异常 | UI 行为 |
| --- | --- |
| `/api/status` 失败 | Status band 展示 safe error chip；query 区可保持禁用或错误提示。 |
| `/api/entities` 失败 | Catalog 区展示 safe error empty state；不伪造 type counts。 |
| `/api/link` 失败 | Result stream 展示 safe error banner；保留或清空旧结果必须有明确状态，不混淆新旧 query。 |
| 窄屏内容过长 | 允许换行和垂直滚动；不得横向 overflow。 |

#### 2.2.3.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | API 失败时展示局部 safe error，不破坏页面整体。 |
| 可用性 | 是 | 桌面首屏形成工作台，窄屏保持清晰顺序。 |
| 安全性 | 是 | 错误信息不得包含 raw payload、secret 或真实 base URL。 |
| 可维护性 | 是 | 只定义有限区域和 test ids，不把 CSS 像素固定成僵硬实现。 |

### SR-V2-FE-VIS-D03 多 mention、候选、详情和 catalog 联动视觉

#### 2.2.4.1 SR 描述

页面必须在视觉上表现 mention、candidate、entity detail、catalog filter 和 similar entities 的关联关系。用户无需展开 debug JSON，即可理解当前 query、当前选中 mention、当前候选、当前 entity detail 和 partial/no_match/not_required/degraded 状态。

#### 2.2.4.2 SR 实现思路

`VisualWorkbenchState` 最低字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `scenario` | object | 当前 query、mode、viewport、selected mention/candidate、debug collapsed 等 canonical 场景信息 |
| `runtimeSummary` | object | mode、entity_count、type_counts、LLM enabled/used/fallback/degraded |
| `queryText` | string | 当前 query |
| `queryStatus` | enum | `idle`、`loading`、`linked`、`partial`、`ambiguous`、`no_match`、`not_required`、`dependency_failed`、`error` |
| `mentions[]` | array | UI normalized mention safe projection；由 `/api/link` 的 `mention_results[]` adapter 得到，不是新增 API 顶层字段 |
| `activeMentionIndex` | number/null | 当前选中 mention |
| `activeCandidateId` | string/null | 当前选中 candidate；无候选时为 null |
| `activeEntityId` | string/null | 当前 detail entity |
| `activeTypeFilter` | string/null | 当前 catalog entity type filter |
| `activeExplanationContext` | enum | `global`、`mention`、`candidate`、`empty` |
| `visualState` | enum | `initial`、`ready`、`loading`、`result_loaded`、`partial_result`、`empty`、`degraded`、`error` |
| `debugCollapsed` | boolean | debug 是否默认折叠 |

Mention card 最低展示字段：

| 字段 | 展示要求 |
| --- | --- |
| `text` | mention 文本，突出当前 span 语义 |
| `span` | 可紧凑展示 `[start,end]` |
| `entity_type` / `predicted_type` | 类型 chip |
| `status` | 状态 chip |
| `linked_entity` | linked 时展示 entity id/name/type |
| `candidates[]` | 有候选时展示 rank/score/reason |
| `no_candidate_reason` | no_match/not_required/degraded 时展示原因 |

API-to-UI adapter schema：

| UI normalized 字段 | 现有 `/api/link` safe projection 来源 | 说明 |
| --- | --- | --- |
| `mentions[].text` | `mention_results[].mention.text` | mention 文本 |
| `mentions[].span` | `mention_results[].mention.span` | mention span |
| `mentions[].entity_type` / `mentions[].predicted_type` | `mention_results[].mention.entity_type` 或 `mention_results[].mention.predicted_type` | 若只有 `predicted_type`，UI type chip 使用该值 |
| `mentions[].status` | `mention_results[].status` | mention 级 linked/ambiguous/no_match/degraded 等状态 |
| `mentions[].linked_entity` | `mention_results[].linked_entity` | linked entity safe summary |
| `mentions[].candidates[]` | `mention_results[].candidates[]` | candidate safe summaries |
| `mentions[].no_candidate_reason` | `mention_results[].no_candidate_reason` 或 `mention_results[].no_match_reason` | no_match/not_required/degraded 原因 |
| `mentions[].disambiguation_reason` | `mention_results[].disambiguation_reason` | ambiguous 或 candidate reason 展示 |
| `mentions[].llm_context_key` | `mention_results[]` index + candidate/entity id | LLM explanation context resolution 的稳定关联键 |

设计约束：后续实现不得要求 `/api/link` 新增顶层 `mentions[]` 来满足本设计；若需要为了 UI 简化在 JS 内构造 `state.mentions[]`，必须保留 `mention_results[]` 到 UI state 的显式 adapter，并由测试覆盖。

Selection state 规则：

- 点击 mention 后，`activeMentionIndex` 更新，result stream 中该 mention 高亮，candidate stack 和 LLM explanation 同步。
- 点击 candidate 后，`activeCandidateId` 和 `activeEntityId` 更新，detail zone 和 LLM explanation 同步。
- 点击 catalog entity 后，`activeEntityId` 更新，但不得伪造其来源于当前 mention；UI 需标明来自 catalog selection。
- `partial` 必须同时展示成功和失败 mention，不得只显示 query-level partial。

#### 2.2.4.3 功能实现刷新

交互流程：

```text
submit query
  -> render query summary
  -> render mention cards
  -> default active mention: first linked mention if present, otherwise first mention
  -> render candidates for active mention
  -> render entity detail for active candidate/entity
  -> resolve LLM explanation context
```

状态语义：

| 状态 | UI 行为 |
| --- | --- |
| `linked` | mention card 和 summary 使用 linked 状态，detail zone 指向 linked entity。 |
| `partial` | query summary 标记 partial，mention cards 分别展示 linked/no_match/ambiguous/degraded。 |
| `ambiguous` | 展示多个候选，不自动声称唯一 linked。 |
| `no_match` | 展示 no-candidate reason，不展示伪候选或伪 detail。 |
| `not_required` | 展示无需链接状态，不创建伪 mention/candidate。 |
| `dependency_failed` | 展示 stage/error chip，不伪造链接结果。 |

#### 2.2.4.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 选择状态集中维护，避免 detail/explanation 与 result stream 脱节。 |
| 可用性 | 是 | 多 mention 和 partial 状态无需 debug 即可扫读。 |
| 安全性 | 是 | 所有字段来自 safe projection，不新增未确认实体或属性。 |
| 可维护性 | 是 | 使用明确 state 字段和 test ids，便于后续自动化。 |

### SR-V2-FE-VIS-D04 LLM 交互式安全解释组件

#### 2.2.5.1 SR 描述

LLM 安全解释必须以组件化区域展示阶段、上下文、候选、原因、fallback/degraded/loading/empty 状态，而不是普通文本列表。点击 mention、candidate 或 LLM status 后，该区域必须根据 selection state 同步切换。

#### 2.2.5.2 SR 实现思路

`LLMExplanationComponentState` 最低字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `enabled` | boolean | 当前模式是否允许 LLM |
| `used` | boolean | 本次是否使用 LLM |
| `fallbackUsed` | boolean | 是否 fallback |
| `degraded` | boolean | 是否降级 |
| `contextType` | enum | `global`、`mention`、`candidate`、`empty` |
| `mentionIndex` | number/null | 当前解释关联 mention |
| `candidateId` | string/null | 当前解释关联 candidate |
| `entityId` | string/null | 当前解释关联 entity |
| `stageChips[]` | array | `need_linking`、`classify_type`、`extract_mention`、`retrieve_candidates`、`rerank`、`explain`、`fallback` 等阶段状态 |
| `safeSummary` | string | 脱敏解释摘要 |
| `fallbackReason` | string/null | fallback/degraded 原因 |
| `redactionNote` | string | 脱敏说明 |
| `emptyReason` | string/null | 当前对象无 LLM explanation 时的空状态说明 |

组件视觉分区：

| 子区 | 要求 |
| --- | --- |
| Context header | 展示当前解释关联 global/mention/candidate，包含 selected mention/candidate/entity 简短摘要。 |
| Stage chips | 用 chip 或紧凑行展示各阶段状态；fallback/degraded/failed 必须醒目。 |
| Reason panel | 展示 safe summary、match reason 或 no explanation empty state。 |
| Redaction footer | 展示 redaction note；不得展示 raw prompt/raw response。 |

#### 2.2.5.3 功能实现刷新

点击解析规则：

| 触发 | 解析 |
| --- | --- |
| 点击 LLM status | `contextType=global`，展示 global explanation 和 stage overview。 |
| 点击 mention | 优先匹配 `contextType=mention` 且 `mentionIndex` 相同的 explanation；无则展示 mention-level empty state 和 stage overview。 |
| 点击 candidate | 优先匹配 `contextType=candidate` 且 `mentionIndex`、`candidateId/entityId` 相同的 explanation；无则展示 candidate match reason 和 empty state。 |
| offline_demo | 展示 LLM disabled/not used 状态和 deterministic summary，不留空白。 |

安全规则：

- 允许展示字段名、环境变量名、redacted/empty 配置状态。
- 禁止展示真实 secret/API key/token、真实 base URL、raw prompt、raw response、完整 LLM 日志。
- 错误码必须结构化且脱敏，例如 `llm_auth_error`、`llm_timeout`、`llm_schema_error`。

#### 2.2.5.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | LLM 失败只影响解释组件，不伪造链接结果。 |
| 可用性 | 是 | 用户能看到 AI explanation 与当前选择对象的关系。 |
| 安全性 | 是 | 只展示 safe summary、stage status 和 redaction note。 |
| 可维护性 | 是 | 组件状态独立于业务事实字段，便于测试。 |

### SR-V2-FE-VIS-D05 Visual traceability artifact、截图和人工确认门禁

#### 2.2.6.1 SR 描述

后续实现和验收候选前必须生成 visual traceability artifact，并提供 before/after 桌面和窄屏截图。任一 P0/P1 visual AC 缺少 pass、出现弱证明降级、缺少用户视觉接受结论，均阻塞验收关闭。

#### 2.2.6.2 SR 实现思路

输出路径：

| Artifact | 路径 |
| --- | --- |
| JSON | `outputs/logs/v2_frontend_visual_traceability_check.json` |
| Markdown | `outputs/logs/v2_frontend_visual_traceability_check.md` |
| Before desktop | `outputs/logs/v2_frontend_desktop_1366x768.png` 或等价刷新路径 |
| Before narrow | `outputs/logs/v2_frontend_narrow_390x844.png` 或等价刷新路径 |
| After desktop | `outputs/logs/v2_frontend_visual_after_desktop_1366x768.png` 或测试设计确认的等价路径 |
| After narrow | `outputs/logs/v2_frontend_visual_after_narrow_390x844.png` 或测试设计确认的等价路径 |

Canonical scenario：

| 字段 | 值 |
| --- | --- |
| `query` | `Check ALM-51020 and CPU Usage.` |
| `mode` | `offline_demo` |
| `desktop_viewport` | `1366x768` |
| `narrow_viewport` | `390x844` |
| `browser_zoom_device_scale` | same before/after |
| `debug_collapsed` | `true` |
| `selected_mention` | `CPU Usage` |
| `selected_candidate` | `DV-KPI-MTK-001` |

`VisualTraceabilityArtifact` 最小 schema：

| 字段 | 类型 | 要求 |
| --- | --- | --- |
| `schema_version` | string | 固定为 `v2.frontend_visual_traceability.1`。 |
| `scenario` | object | 记录 query、mode、viewport、zoom/device scale、selected mention/candidate、debug collapsed。 |
| `manual_user_acceptance_status` | string | 顶层用户视觉接受结论：`accepted`、`rejected`、`pending`；验收关闭前必须为 `accepted`。 |
| `manual_user_acceptance_evidence` | object | 用户确认来源、日期、截图或浏览器 URL 摘要；不得记录敏感 raw log。 |
| `d003_content_inventory[]` | array | 新增 UI copy、metric/topology/interface label、mock boundary 文案的来源分类清单。 |
| `items[]` | array | 每个 prototype principle 和每个 AC 至少一个 item。 |
| `items[].ac_ids` | array | 该 item 覆盖的 `AC-V2-FE-VIS-*`；prototype-only item 可为空但不得替代 AC item。 |
| `items[].priority` | string | `P0`、`P1`、`P2`、`P3`；AC item 必须继承 IR 中阻塞级别。 |
| `items[].evidence_type` | string | `prototype_absorption`、`visual_ac`、`before_after`、`d003_content_boundary`、`manual_gate`。 |
| `items[].prototype_ref` | string | `SigNoz`、`OpenGenerativeUI`、`Tambo` 或 `project_visual_ac`。 |
| `items[].absorbed_principle` | string | 原型吸收或项目视觉 AC 的具体原则。 |
| `items[].target_ui_regions` | array | shell、status band、query controls、result stream、detail panel、LLM explanation 等。 |
| `items[].before_screenshot` | string | before 截图路径。 |
| `items[].after_screenshot` | string | after 截图路径。 |
| `items[].same_viewport_and_query` | boolean | before/after 是否使用 canonical scenario。 |
| `items[].automated_visual_semantic_checks` | array | 自动化检查列表及 pass/fail。 |
| `items[].manual_user_acceptance_status` | string | `accepted`、`rejected`、`pending`、`not_applicable`；item 级 `not_applicable` 仅表示该 item 不需要单独人工判断，不可替代顶层 accepted。 |
| `items[].downgrade_classification` | string | `none`、`weak_marker_only`、`api_only`、`no_visual_delta`、`needs_user_decision`。 |
| `items[].reviewer_result` | string | `pass`、`fail`、`needs_user_decision`。 |
| `summary.ac_statuses` | object | 每个 AC 的 pass/fail/needs_user_decision 汇总。 |
| `summary.blocking_ac_ids` | array | 被阻塞的 P0/P1 AC id 列表。 |
| `summary.blocking_count` | number | 任何阻塞规则命中时必须大于 0。 |

`d003_content_inventory[]` 条目 schema：

| 字段 | 类型 | 要求 |
| --- | --- | --- |
| `text_or_label` | string | 新增 UI copy、metric/topology/interface label、mock boundary 文案或其稳定摘要。 |
| `classification` | string | `project_safe`、`synthetic_ui`、`existing_confirmed_sample`、`needs_d003_confirmation`。 |
| `source_reference` | string | 样例文件、决策 ID、SR section 或 synthetic/mock 说明。 |
| `decision_id` | string/null | 涉及真实 DV 内容时必须指向 `D003` 或后续用户确认决策。 |
| `needs_d003_confirmation` | boolean | 为 true 时必须阻塞实现或验收候选。 |

阻塞规则：

- 任一 P0/P1 visual AC 没有 `reviewer_result=pass`，阻塞。
- 顶层 `manual_user_acceptance_status` 缺少 `accepted`，阻塞；item 级 `not_applicable` 不可替代全局用户视觉接受结论。
- 出现 `weak_marker_only`、`api_only`、`no_visual_delta`、`needs_user_decision`，阻塞。
- `summary.blocking_ac_ids` 非空或 `summary.blocking_count > 0`，阻塞。
- 任一 `d003_content_inventory[].needs_d003_confirmation=true`，阻塞。
- before/after 未使用相同 canonical scenario，阻塞，除非用户确认并记录替代场景。

#### 2.2.6.3 功能实现刷新

后续 smoke 或浏览器证据脚本应执行：

1. 启动 `scripts/run_web_demo.py --mode offline_demo --port <port>`。
2. 打开桌面和窄屏 viewport。
3. 提交 canonical query。
4. 选择第二个 mention `CPU Usage` 和候选 `DV-KPI-MTK-001`。
5. 确认 debug collapsed。
6. 截取 after screenshots。
7. 对 UI 区域和视觉语义执行自动化检查。
8. 扫描并记录 `d003_content_inventory[]`。
9. 生成 visual traceability JSON/Markdown。
10. 在验收阶段追加顶层用户视觉接受状态。

自动化视觉语义检查最低项：

| Check ID | 语义 |
| --- | --- |
| `shell_visible_not_plain_stack` | `visual-workbench-shell` 可见，且页面不是孤立 full-width stacked panel 结构。 |
| `status_band_density_visible` | status band 展示 mode、entity_count/type_counts、LLM/query 状态。 |
| `grouped_zones_first_viewport` | desktop 首屏同时包含 query/control、result、detail/explanation。 |
| `multi_mention_selection_visible` | 第二个 mention `CPU Usage` 的选中态可见。 |
| `candidate_detail_linkage_visible` | `DV-KPI-MTK-001` candidate/detail 联动可见。 |
| `llm_component_state_visible` | LLM 组件展示 context、stage chips、safe summary 或 empty/fallback state。 |
| `debug_collapsed` | Debug 默认折叠。 |
| `no_horizontal_overflow_narrow` | `390x844` 无 body 横向 overflow。 |
| `no_text_overlap_or_clipping_narrow` | `390x844` 下长 entity id、canonical name、状态 chip、按钮文字无关键重叠或不可读裁剪。 |
| `no_forbidden_sensitive_content` | HTML/API/evidence 不包含真实 secret/raw prompt/raw response。 |
| `no_unconfirmed_real_dv_content` | `d003_content_inventory[]` 中无 `needs_d003_confirmation=true`，且新增文案均可追溯到已确认样例、项目事实或 synthetic/mock copy。 |

#### 2.2.6.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | artifact schema 和阻塞规则可由测试自动判断。 |
| 可用性 | 是 | 最终仍保留用户视觉接受门禁，承认审美判断不能完全自动化。 |
| 安全性 | 是 | evidence 只记录路径和脱敏摘要，不提交 `outputs/**`。 |
| 可维护性 | 是 | visual AC 与 prototype principles 均进入同一个 artifact。 |

### SR-V2-FE-VIS-D06 D003 真实 DV 内容和 Mock 边界保护

#### 2.2.7.1 SR 描述

视觉补救不得为了增强“observability 感”而新增未经确认的真实感 DV 字段、接口、实体、指标、拓扑标签、样例 payload、Mock 策略或能力边界。可使用已确认 V2 样例和明确标为 synthetic/mock 的 UI copy。

#### 2.2.7.2 SR 实现思路

内容来源规则：

| 内容类型 | 允许 | 禁止 |
| --- | --- | --- |
| Entity/sample | 已确认 `samples/real/v2_entity_examples.json`、`samples/real/v2_query_samples.json` | 新增真实感 entity id、metric name、NE name、topology label |
| UI copy | 明确 synthetic/mock 的通用状态词，如 demo mode、offline、redacted | 暗示真实接口已接入、真实 telemetry 已采集、真实生产拓扑已存在 |
| API/status | 现有 safe projection 和脱敏字段 | raw prompt/raw response、真实 base URL、token、host、完整 payload |
| Mock boundary | 已确认文件驱动 Mock 和 offline demo | 未确认 runtime source lifecycle、真实接口路径、生产能力承诺 |

实现阶段若需要新增 copy，应按如下分类：

- `project_safe`: 项目已有确认事实，例如 `offline_demo`、entity_count、type_counts。
- `synthetic_ui`: 明确演示性文案，不像真实 DV 生产字段。
- `existing_confirmed_sample`: 来自已确认 V2 样例的 entity id、canonical name、query 或 type label。
- `needs_d003_confirmation`: 新真实感 DV 内容或能力边界，必须停止并回到用户确认。

`d003_content_inventory[]` 必须覆盖后续实现新增的所有工作台文案、metric/topology/interface label 和 mock boundary copy。仅复用现有 HTML 静态按钮词如 `Link`、`Debug`、`Catalog` 可按 `project_safe` 合并记录；任何看似真实 DV 生产对象、接口路径、metric label、topology label 或 runtime source lifecycle 的新增文本都必须单独列项。

#### 2.2.7.3 功能实现刷新

后续测试应扫描：

- HTML 页面。
- `/api/status`、`/api/link`、`/api/entities`、`/api/entities/<id>`、`/api/retrieve` safe projection。
- visual traceability artifact。
- smoke 日志摘要。

扫描重点：

- 不出现 `api_key` 真值、token-like value、Authorization bearer、真实 base URL、raw prompt、raw response。
- 不出现未经确认的新真实感 metric/topology/interface/sample labels。
- 若出现新增 UI copy，应能归类为 `project_safe` 或 `synthetic_ui`。
- `d003_content_inventory[]` 中不得出现 `needs_d003_confirmation=true`；如出现，状态必须标记为阻塞且不得进入实现评审闭环或验收候选。

#### 2.2.7.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 内容来源分类减少“看起来像真实能力”的误导。 |
| 可用性 | 是 | 仍可使用已确认样例形成真实 demo 上下文。 |
| 安全性 | 是 | D003 边界直接进入设计和测试。 |
| 可维护性 | 是 | 新增真实感内容有明确停止点。 |

---

# 3 接口设计

## 3.1 接口概述

本设计不新增外部 API。后续实现复用现有 Flask 接口和 safe projection。

| 接口 | 变更 |
| --- | --- |
| `GET /` | 修改页面 shell、CSS、原生 JS 和 test ids。 |
| `GET /api/status` | 保持现有接口；页面从中读取 runtime/catalog/LLM safe status。 |
| `POST /api/link` | 保持现有接口；页面从中读取 multi mention、candidate、stage 和 safe explanation projection。 |
| `GET /api/entities` | 保持现有接口；用于 catalog filter zone。 |
| `GET /api/entities/<entity_id>` | 保持现有接口；用于 entity detail zone。 |
| `POST /api/retrieve` 或当前实现等价方法 | 保持现有接口；用于 similar entities。 |

说明：本轮不新增 `/api/catalog`，避免与上一轮已明确的 `/api/entities` catalog endpoint 分叉。

## 3.2 ER 接口设计

### 3.2.1 GET /

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-VIS-001 |
| 接口路径 | `/` |
| 请求方法 | GET |
| 请求参数 | 无 |
| 返回参数 | HTML/CSS/JS，包含 visual workbench shell 和稳定 `data-testid` |
| 错误码 | Flask 默认错误；页面内部 API 错误由 safe error banner 展示 |

最低页面结构：

| `data-testid` | 必须 |
| --- | --- |
| `visual-workbench-shell` | 是 |
| `status-band` | 是 |
| `query-command-zone` | 是 |
| `result-stream` | 是 |
| `entity-detail-zone` | 是 |
| `llm-explanation-component` | 是 |
| `catalog-filter-zone` | 是 |
| `debug-panel` | 是，默认 collapsed |

### 3.2.2 POST /api/link

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-VIS-002 |
| 接口路径 | `/api/link` |
| 请求方法 | POST |
| 请求参数 | `query`、`mode`、`allow_fallback` |
| 返回参数 | Query result safe projection |
| 错误码 | 沿用现有 `invalid_input`、`invalid_mode`、`llm_timeout`、`llm_http_error`、`llm_auth_error`、`llm_schema_error`、`dependency_failed` 等 |

前端最低依赖字段：

| 字段路径 | 用途 |
| --- | --- |
| `status` | query summary 和 status chip |
| `mention_results[].mention.text` | mention card |
| `mention_results[].mention.span` | mention card |
| `mention_results[].mention.entity_type` / `mention_results[].mention.predicted_type` | type chip |
| `mention_results[].status` | mention status chip |
| `mention_results[].linked_entity` | linked detail |
| `mention_results[].candidates[]` | candidate stack |
| `mention_results[].no_candidate_reason` / `mention_results[].no_match_reason` | no_match/not_required/degraded 展示 |
| `mention_results[].disambiguation_reason` | ambiguous/candidate reason 展示 |
| `stage_statuses[]` | LLM stage chips |
| `llm_explanations[]` 或等价 safe explanation 字段 | LLM component context resolution |

UI 内部可继续使用 `VisualWorkbenchState.mentions[]`，但该数组必须由 `mention_results[]` adapter 构造，且测试需覆盖 adapter 字段来源。不得为了满足视觉设计新增与 `mention_results[]` 并行的第二套 `/api/link` 顶层 mention schema。

### 3.2.3 GET /api/entities 和 GET /api/entities/<entity_id>

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-VIS-003 |
| 接口路径 | `/api/entities`、`/api/entities/<entity_id>` |
| 请求方法 | GET |
| 请求参数 | 可选 `entity_type` 或 path `entity_id` |
| 返回参数 | catalog list、type counts、entity detail safe projection |
| 错误语义 | 沿用现有 safe 语义：unknown entity detail 返回 HTTP 404，payload 使用 `status=no_match` 与 `no_match_reason`；后续如补充 `error_code` 仅可作为 safe projection 增量，不得改变现有 no_match 语义 |

### 3.2.4 Visual traceability artifact

该 artifact 是文件输出，不是 Web API。

| 项目 | 内容 |
| --- | --- |
| 接口 ID | FILE-V2-FE-VIS-001 |
| JSON 路径 | `outputs/logs/v2_frontend_visual_traceability_check.json` |
| Markdown 路径 | `outputs/logs/v2_frontend_visual_traceability_check.md` |
| 生成方 | 后续 smoke/browser evidence 脚本 |
| 入库规则 | `outputs/**` 不入库；文档只记录脱敏摘要和命令结果 |

## 3.3 IR 接口设计

### 3.3.1 VisualWorkbenchState

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `scenario` | object | 是 | 当前 canonical scenario 或运行场景 |
| `runtimeSummary` | object | 是 | mode/entity_count/type_counts/LLM 状态 |
| `queryText` | string | 是 | 当前 query |
| `queryStatus` | enum | 是 | `idle`、`loading`、`linked`、`partial`、`ambiguous`、`no_match`、`not_required`、`dependency_failed`、`error` |
| `mentions` | array | 是 | UI normalized mention safe projections；由 `/api/link` 的 `mention_results[]` adapter 生成 |
| `activeMentionIndex` | number/null | 是 | 当前 mention |
| `activeCandidateId` | string/null | 是 | 当前 candidate |
| `activeEntityId` | string/null | 是 | 当前 entity detail |
| `activeTypeFilter` | string/null | 是 | catalog filter |
| `activeExplanationContext` | enum | 是 | `global`、`mention`、`candidate`、`empty` |
| `llmComponentState` | object | 是 | LLM 解释组件状态 |
| `visualState` | enum | 是 | 页面视觉状态 |
| `debugCollapsed` | boolean | 是 | debug 默认折叠 |
| `errors` | array | 是 | safe error objects |

### 3.3.2 LinkResultVisualAdapter

`LinkResultVisualAdapter` 是 JS/UI 侧的规范化约束，不要求后端新增类。它把现有 `/api/link` safe projection 转换为 `VisualWorkbenchState.mentions[]`。

| Adapter 输出 | 来源字段 | 必填规则 |
| --- | --- | --- |
| `mentions[].text` | `mention_results[].mention.text` | 是 |
| `mentions[].span` | `mention_results[].mention.span` | 是 |
| `mentions[].predicted_type` | `mention_results[].mention.predicted_type` 或 `mention_results[].mention.entity_type` | 至少一个 |
| `mentions[].status` | `mention_results[].status` | 是 |
| `mentions[].linked_entity` | `mention_results[].linked_entity` | linked 时必填，否则 null |
| `mentions[].candidates[]` | `mention_results[].candidates[]` | 有候选时使用 safe summaries |
| `mentions[].no_candidate_reason` | `mention_results[].no_candidate_reason` 或 `mention_results[].no_match_reason` | 无候选且非 not_required 时必填 |
| `mentions[].selection_key` | `mention_results[]` index | 是，作为 `activeMentionIndex` 对应键 |
| `mentions[].candidate_keys[]` | candidate `entity_id` 或 stable candidate id | 有候选时必填 |

### 3.3.3 VisualSemanticCheck

| 枚举值 | 说明 |
| --- | --- |
| `shell_visible_not_plain_stack` | 工作台 shell 可见且非普通 full-width stacked panels。 |
| `status_band_density_visible` | status band 展示 mode/entity/type/LLM/query 状态。 |
| `grouped_zones_first_viewport` | desktop 首屏包含 grouped control/result/detail zones。 |
| `multi_mention_selection_visible` | selected mention 可见。 |
| `candidate_detail_linkage_visible` | candidate/detail 联动可见。 |
| `llm_component_state_visible` | LLM explanation 组件状态可见。 |
| `debug_collapsed` | debug 默认折叠。 |
| `no_horizontal_overflow_narrow` | 窄屏无横向 overflow。 |
| `no_text_overlap_or_clipping_narrow` | 窄屏无关键文本重叠或不可读裁剪。 |
| `no_forbidden_sensitive_content` | 无禁用敏感内容。 |
| `no_unconfirmed_real_dv_content` | 无未确认真实感 DV 内容。 |

### 3.3.4 DowngradeClassification

| 枚举值 | 是否阻塞 | 说明 |
| --- | --- | --- |
| `none` | 否 | 无降级。 |
| `weak_marker_only` | 是 | 只有 marker/testid，无真实视觉证据。 |
| `api_only` | 是 | 只有 API 字段，无页面视觉变化。 |
| `no_visual_delta` | 是 | before/after 看不出变化。 |
| `needs_user_decision` | 是 | 需要用户确认但尚未确认。 |

---

# 4 数据库设计

本次前端视觉补救不新增数据库、表结构、索引或数据迁移。

| 项 | 结论 |
| --- | --- |
| 表结构设计 | 不涉及 |
| 索引设计 | 不涉及 |
| 数据迁移 | 不涉及 |

---

# 5 部署设计

## 5.1 部署架构

仍为本地单进程 demo：

```text
Python 3.12
  -> scripts/run_web_demo.py
  -> Flask app
  -> in-memory catalog/linking service
  -> browser at localhost
```

## 5.2 配置项

| 配置项 | 默认值 | 说明 | 是否可热更新 |
| --- | --- | --- | --- |
| `--catalog` | `samples/real/v2_entity_examples.json` | 当前默认 V2 entity catalog | 否 |
| `--samples` | `samples/real/v2_query_samples.json` | 当前默认 V2 query samples | 否 |
| `--mode` | `offline_demo` | 默认不依赖真实 LLM | 页面可选 |
| `--port` | 调用方指定或默认 | 本地 Web demo 端口 | 否 |
| LLM 本地配置 | ignored/local only | 不得回显真实值 | 进程内 |

## 5.3 依赖组件

| 组件名称 | 版本要求 | 用途 |
| --- | --- | --- |
| Flask | 项目现有依赖 | Web/API demo |
| pytest | 项目现有依赖 | 自动化测试 |
| Browser automation / in-app browser / CDP equivalent | 测试设计阶段确认 | 浏览器级截图和视觉语义 evidence |

---

# 6 测试设计

## 6.1 测试场景

| 场景编号 | 场景名称 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- | --- |
| TS-V2-FE-VIS-001 | Prototype absorption matrix | SR/实现/evidence 已形成 | 检查 SigNoz/OpenGenerativeUI/Tambo 映射 | 每个参考原则映射到 UI 区域、state 和 evidence |
| TS-V2-FE-VIS-002 | Desktop cohesive workbench shell | Web demo 启动 | `1366x768` 打开 canonical scenario | 首屏包含 shell、status band、query/control、result、detail/explanation，非 full-width stacked panels |
| TS-V2-FE-VIS-003 | Narrow responsive visual flow | Web demo 启动 | `390x844` 打开 canonical scenario 并滚动 | 无横向 overflow；无关键文本重叠或不可读裁剪；query/result/detail/explanation/catalog 顺序稳定 |
| TS-V2-FE-VIS-004 | Multi mention selection linkage | canonical query 已提交 | 选择 `CPU Usage` mention 和 `DV-KPI-MTK-001` candidate | selected mention/candidate/entity detail 视觉联动可见 |
| TS-V2-FE-VIS-005 | LLM component context states | canonical query 已提交 | 点击 LLM status、mention、candidate | LLM 组件展示 context、stage chips、safe summary/empty/fallback/degraded |
| TS-V2-FE-VIS-006 | D003 content boundary | 实现/evidence 已形成 | 扫描 HTML、API、artifact、logs，并校验 `d003_content_inventory[]` | 无禁用敏感值；无 `needs_d003_confirmation=true`；无未经确认真实感 DV 内容 |
| TS-V2-FE-VIS-007 | Visual traceability schema and blocking | smoke/evidence 已生成 | 校验 JSON/Markdown schema 和阻塞规则 | P0/P1 visual AC 全 pass；无弱证明降级；用户接受状态符合门禁 |
| TS-V2-FE-VIS-008 | Before/after comparability | before/after screenshots 已生成 | 比较 canonical scenario metadata | query、viewport、zoom/device scale、selected mention/candidate 一致 |
| TS-V2-FE-VIS-009 | Single web entry preserved | 仓库脚本 | 检查 demo 启动脚本和文档 | 只维护 `scripts/run_web_demo.py`；无版本专用 web demo 脚本 |

## 6.2 测试用例

| 用例编号 | 用例名称 | 所属场景 | 优先级 | 设计者 |
| --- | --- | --- | --- | --- |
| TC-V2-FE-VIS-001 | Prototype principle to UI/state/evidence mapping | TS-V2-FE-VIS-001 | P0 | Codex |
| TC-V2-FE-VIS-002 | Desktop first viewport visual shell check | TS-V2-FE-VIS-002 | P0 | Codex |
| TC-V2-FE-VIS-003 | Narrow viewport overflow, clipping, and flow check | TS-V2-FE-VIS-003 | P1 | Codex |
| TC-V2-FE-VIS-004 | CPU Usage mention to DV-KPI-MTK-001 linkage | TS-V2-FE-VIS-004 | P0 | Codex |
| TC-V2-FE-VIS-005 | LLM explanation component global/mention/candidate states | TS-V2-FE-VIS-005 | P1 | Codex |
| TC-V2-FE-VIS-006 | D003 forbidden content inventory and mock boundary scan | TS-V2-FE-VIS-006 | P0 | Codex |
| TC-V2-FE-VIS-007 | Visual traceability artifact schema and blocker check | TS-V2-FE-VIS-007 | P0 | Codex |
| TC-V2-FE-VIS-008 | Before/after canonical screenshot metadata check | TS-V2-FE-VIS-008 | P0 | Codex |
| TC-V2-FE-VIS-009 | Single `run_web_demo.py` entry regression | TS-V2-FE-VIS-009 | P0 | Codex |

## 6.3 验收标准

| IR AC | 设计测试映射 |
| --- | --- |
| AC-V2-FE-VIS-001 | TS-V2-FE-VIS-001、TC-V2-FE-VIS-001 |
| AC-V2-FE-VIS-002 | TS-V2-FE-VIS-002、TS-V2-FE-VIS-003、TC-V2-FE-VIS-002、TC-V2-FE-VIS-003 |
| AC-V2-FE-VIS-003 | TS-V2-FE-VIS-004、TC-V2-FE-VIS-004 |
| AC-V2-FE-VIS-004 | TS-V2-FE-VIS-005、TC-V2-FE-VIS-005 |
| AC-V2-FE-VIS-005 | TS-V2-FE-VIS-006、TC-V2-FE-VIS-006 |
| AC-V2-FE-VIS-006 | TS-V2-FE-VIS-009、TC-V2-FE-VIS-009 |
| AC-V2-FE-VIS-007 | TS-V2-FE-VIS-007、TC-V2-FE-VIS-007 |
| AC-V2-FE-VIS-008 | TS-V2-FE-VIS-002、TS-V2-FE-VIS-003、TS-V2-FE-VIS-008、TC-V2-FE-VIS-002、TC-V2-FE-VIS-003、TC-V2-FE-VIS-008 |
| AC-V2-FE-VIS-009 | TS-V2-FE-VIS-006、TC-V2-FE-VIS-006 |

验收候选前最低门禁：

- 功能设计评审、处置和闭环验证已通过。
- 实现评审、处置和闭环验证已通过。
- 测试设计/开发、测试评审、处置和闭环验证已通过。
- Visual traceability artifact 中所有 P0/P1 visual AC 为 pass。
- 用户视觉接受结论为 accepted。
- 无 `weak_marker_only`、`api_only`、`no_visual_delta` 或 `needs_user_decision`。

---

# 7 风险分析

| 风险编号 | 风险描述 | 风险等级 | 影响 | 应对措施 | 负责人 |
| --- | --- | --- | --- | --- | --- |
| R-V2-FE-VIS-001 | 视觉判断具有主观性 | 高 | 自动化通过但用户仍不认可 | 保留 before/after canonical screenshots、visual traceability artifact 和用户视觉接受门禁。 | 设计/验收负责人 |
| R-V2-FE-VIS-002 | 实现再次退化为 DOM marker/API-only | 高 | 重复上一轮流程问题 | `downgrade_classification` 将 marker/API-only/no visual delta 设为阻塞。 | 评审/测试负责人 |
| R-V2-FE-VIS-003 | Flask 内嵌页面复杂度上升 | 中 | `web.py` 可维护性下降 | 限定区域和 state；如必须拆静态文件，仍限定在 Web UI 边界并经设计评审。 | 实现负责人 |
| R-V2-FE-VIS-004 | 为提升观感新增未确认真实感 DV 内容 | 高 | 违反 D003 和安全边界 | 内容来源分类和扫描；`needs_d003_confirmation` 必须停止。 | 实现/评审负责人 |
| R-V2-FE-VIS-005 | 浏览器自动化环境不稳定 | 中 | 截图和布局 evidence 生成失败 | 使用 in-app browser、CDP 或等价浏览器级 renderer；不得降级为纯 API。 | 测试负责人 |
| R-V2-FE-VIS-006 | 参考原型 live page 后续变化 | 低 | 评审引用不稳定 | 使用 2026-06-02 已固化的吸收原则作为规范，不依赖 live page。 | 文档负责人 |

---

# 附录 A 评审记录

| 评审日期 | 评审人 | 评审意见 | 处理状态 |
| --- | --- | --- | --- |
| 2026-06-02 | no-context 独立功能设计评审 Lovelace | Ready for disposition；无 P0，3 个 P1、3 个 P2，要求补齐 `mention_results[]` adapter、traceability AC 阻塞字段、D003 content inventory、新旧 artifact 路径边界、窄屏文本重叠检查和 `/api/entities` 错误语义。 | 处置完成 |
| 2026-06-02 | 独立只读闭环验证 Einstein | FE-VIS-SR-001 至 FE-VIS-SR-006 均 Closed with recorded residual risk；功能设计评审闭环通过，可作为代码实现输入。 | 闭环通过 |

# 附录 B 功能设计评审输入包

请独立功能设计评审者只读复核以下输入：

- [SR-FRONTEND-VISUAL-REMEDIATION.md](./SR-FRONTEND-VISUAL-REMEDIATION.md)
- [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)
- [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md)
- [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md)
- [FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md)
- [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md)
- [SR.md](./SR.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md)
- [../../releases/V2.md](../../releases/V2.md)
- `src/dv_entity_linking/web.py`
- `scripts/run_web_demo.py`
- `tests/test_web.py`
- `scripts/run_v2_acceptance_smoke.py`
- `outputs/logs/v2_frontend_desktop_1366x768.png`
- `outputs/logs/v2_frontend_narrow_390x844.png`

评审重点：

- 是否完整覆盖 AC-V2-FE-VIS-001 至 AC-V2-FE-VIS-009。
- 是否真正把 SigNoz、OpenGenerativeUI、Tambo 转化为 UI 区域、state 和 evidence，而不是停留在引用链接。
- 桌面 `1366x768` 首屏设计是否足以阻止 full-width white-card stacked panels。
- 窄屏 `390x844` 设计是否可实现且不会横向溢出或关键文本重叠。
- LLM explanation 是否具备组件状态、selection linkage、fallback/degraded/empty/loading 表达。
- Visual traceability artifact schema 和阻塞规则是否足以阻止 marker/API-only/no visual delta。
- D003 真实 DV 内容和 Mock 边界是否覆盖视觉补救中的真实感内容风险。

# 附录 C 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | SR-DVEntityLinking-V2-FE-Visual-Remediation |
| 创建日期 | 2026-06-02 |
| 作者 | Codex |
| 状态 | 功能设计评审闭环已通过，可作为代码实现输入 |
| 版本 | V2-FE-VIS-SR.2-closed |
