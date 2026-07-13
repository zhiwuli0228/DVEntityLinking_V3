# DigitalView-SW DVEntityLinking V2 前端视觉风格补救需求分析文档

---

> 文档治理说明：本文是用户在 V2 前端补救候选阶段指出“前端风格似乎并没有太大改动，是否真的参考了其他原型”后重新进入 DV 流程的需求分析输出。本文只覆盖 V2 前端视觉风格和原型吸收补救，不替代已闭环的 V2 数据、链接、评测和前端功能补救基线。本文已完成独立需求评审、评审处置和独立闭环验证，可作为 V2 前端视觉风格补救功能设计输入；进入代码实现、验收候选或版本关闭仍需后续 DV 门禁。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V2-FE-VIS.0-draft | 2026-06-02 | Codex | 根据用户确认，新增 V2 前端视觉风格补救需求草稿，补齐原型吸收矩阵、当前差距、验收底线和评审输入包。 |
| V2-FE-VIS.1-draft | 2026-06-02 | Codex | 接受 no-context 独立需求评审 2 个 P1、2 个 P2、1 个 P3，补齐 D003 安全边界、visual traceability schema、before/after 可比场景、首屏边界和参考源 capture metadata。 |
| V2-FE-VIS.2-closed | 2026-06-02 | Codex | 记录独立需求评审闭环验证通过，FE-VIS-REQ-001 至 FE-VIS-REQ-005 均 Closed with recorded residual risk，可进入功能设计。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 前端视觉补救 | Frontend Visual Remediation |
| 原型吸收矩阵 | Prototype Absorption Matrix |
| 运维观测工作台 | Observability Workbench |
| 视觉验收门禁 | Visual Acceptance Gate |
| 反静默降级 | No Silent Downgrade |

### Abstract 摘要

**中文摘要**：

本文档定义 DVEntityLinking V2 前端视觉风格补救需求。上一轮前端补救已补齐多 mention、候选联动、LLM 安全解释、安全投影和浏览器证据，但用户复核指出页面视觉仍接近基础表单和白卡片分区，未明显体现对 SigNoz、OpenGenerativeUI 和 Tambo 等参考原型的风格吸收。本文将“参考原型”从抽象描述转化为可验收的视觉原则、官方参考依据、页面结构、交互表达、before/after 截图证据和人工确认门禁。本轮不改变 V2 实体 schema、链接算法、样例数据或单一 Web 启动脚本。

**English Abstract**：

This document defines the V2 frontend visual remediation requirements for DVEntityLinking. The previous frontend remediation implemented multi-mention interaction, candidate-detail linkage, safe LLM explanations, safe projection, and browser evidence. However, user review found that the visual style still looked like a basic form with white card sections and did not visibly absorb the referenced prototypes such as SigNoz, OpenGenerativeUI, and Tambo. This document converts prototype references into testable visual principles, official reference signals, layout requirements, interaction cues, before/after screenshot evidence, and a manual acceptance gate. It does not change the V2 entity schema, linking algorithms, sample data, or the single web startup script.

---

## List of Abbreviations 缩略语清单

| 缩略语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| IR | Issue Requirement | 需求项 |
| SR | Sub Requirement | 子需求 |
| UI | User Interface | 用户界面 |
| DV | DigitalView-SW | 电信软件网管系统 |
| LLM | Large Language Model | 大语言模型 |
| AC | Acceptance Criteria | 验收项 |

---

## 1 引言

### 1.1 目的

本文用于把 V2 前端视觉风格缺口重新纳入 DV 流程，从需求阶段明确：

- 上一轮前端补救为何不能作为最终验收候选。
- 参考原型需要被吸收成哪些可观察、可评审、可验收的视觉和交互原则。
- 哪些内容仍然不进入本轮，避免把 demo 变成生产级前端工程。
- 后续设计、实现、测试和验收必须如何证明“风格确实改了”。

预期读者：

- V2 前端视觉补救需求评审者。
- V2 前端视觉补救功能设计负责人。
- V2 前端实现、测试设计和验收复核人员。

### 1.2 范围

#### 需求范围内

| 产品/服务 | 说明 |
| --- | --- |
| 当前 Web demo 首页 | 仍使用 `scripts/run_web_demo.py` 启动；在当前 Flask Web demo 内重构视觉层级、首屏结构、密度、状态表达和交互提示。 |
| 原型吸收矩阵 | 明确 SigNoz、OpenGenerativeUI、Tambo 中可吸收和不可吸收的原则，并追踪到 SR、实现、测试和验收。 |
| 运维观测工作台视觉 | 页面应呈现更明显的工作台气质：状态带、指标概览、结果流、详情联动、类型筛选和解释区域应形成清晰的操作面板，而不是普通表单堆叠。 |
| AI/LLM 交互表达 | LLM 安全解释应更像交互式组件区，展示上下文、阶段、候选关联和降级状态，不只是普通文本列表。 |
| 截图和人工验收门禁 | 除自动化布局断言外，必须提供当前旧页面和改造后页面的 before/after 桌面、窄屏截图，并在验收前记录用户对视觉风格是否接受的明确结论。 |
| 安全内容边界 | 视觉补救只能使用已确认 V2 样例或明确 synthetic/mock UI copy；任何新增真实感 DV 字段、接口、实体、样例、指标或 Mock 边界必须回到 D003 用户确认。 |

#### 需求范围外

| 产品/服务 | 说明 |
| --- | --- |
| 生产级前端产品化 | 不建设权限、多租户、完整设计系统、图表编辑器、复杂拓扑或商业化 observability 平台。 |
| 强制框架迁移 | 不强制迁移 React/Next.js；若功能设计认为 Flask 内嵌页面无法满足视觉基线，必须单独回到用户确认。 |
| 数据和算法改动 | 不改变实体 schema、V2 样例、链接算法、评测口径或 LLM fallback 状态机。 |
| 复制外部产品 | 不照抄参考产品 UI，不引入其商标、图标、专有布局或完整产品能力，只吸收适合本 demo 的信息组织和交互原则。 |
| 未确认真实感内容 | 不为追求观感新增未经确认的真实 DV 指标名、接口名、字段名、拓扑标签、生产对象名、运行时 Mock 边界或真实样例。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| 视觉风格补救 | 针对上一轮前端补救中“功能存在但风格未明显变化”的问题，重新定义、设计、实现和验收前端视觉层级。 |
| 原型吸收矩阵 | 将参考原型中的可吸收原则映射到本项目 SR、实现、测试和验收证据的矩阵。 |
| 运维观测工作台 | 面向运维分析场景的密集但清晰的操作界面，突出状态、指标、对象列表、详情联动、异常解释和筛选。 |
| 人工视觉验收门禁 | 自动化不能充分判断审美和风格变化时，必须由用户基于截图或浏览器实际页面确认是否接受。 |

---

## 2 系统总体说明

当前 V2 Web demo 已有多 mention、候选联动、catalog filter、LLM 安全解释、安全投影和浏览器级证据。但用户复核后指出：页面观感仍是浅灰背景、白色卡片、普通表单、蓝色按钮和 section 列表，视觉上没有明显拉开与旧轻量 UI 的差距。

本轮补救的系统边界如下：

```text
run_web_demo.py
  -> Flask page
  -> existing safe APIs
  -> visual workbench shell
  -> prototype absorption evidence
  -> browser screenshots
  -> user visual acceptance decision
```

核心原则：

| 原则 | 说明 |
| --- | --- |
| 先需求后实现 | 本文闭环前不得直接修改前端实现。 |
| 视觉可验收 | “参考了原型”必须有矩阵、截图、评审项和用户确认，不能只写在附录。 |
| Demo 适配 | 只吸收信息组织、密度、状态表达和交互提示，不复制完整产品。 |
| 单入口保留 | Web demo 仍只维护 `scripts/run_web_demo.py`。 |
| 不牺牲功能 | 视觉改造不得破坏 V2 多 mention、partial、负例、安全投影和离线验收能力。 |
| D003 安全边界 | 不得为了模拟 observability 工作台而新增未经确认的真实感 DV 字段、接口、实体、指标、拓扑标签、样例或 Mock 策略。 |

---

## 3 需求总体描述

### 3.1 背景和问题

上一轮 V2 前端补救正确解决了“API projection 替代前端交互”的问题，但没有解决“视觉风格是否真正参考原型”的问题。具体表现：

- 文档提到 SigNoz、OpenGenerativeUI 和 Tambo，但没有把参考内容转成可验收的视觉设计规则。
- 功能设计偏重 `data-testid`、响应式和 safe projection，缺少视觉风格目标和截图级验收项。
- 实现仍以基础白卡片、表单和普通 section 为主，缺少明显的工作台外壳、状态带、信息密度分区和交互式 AI 面板。
- 自动化验收检查 section 可见、无溢出、多 mention 和安全投影，但无法阻止“功能有了、风格没变”的再次发生。

### 3.2 预期价值

- 用户打开页面即可感知这是 V2 运维实体链接工作台，而不是旧版轻量表单。
- 多 mention、候选、实体详情、catalog 和 LLM 解释在视觉上形成一个可扫读、可联动的操作面。
- 参考原型从“引用链接”变成“可追踪的设计原则和验收证据”。
- 后续评审不能再用 API 字段、DOM marker 或无溢出截图替代视觉风格验收。

### 3.3 原型吸收矩阵

| 参考 | 官方参考信号 | 可吸收原则 | 本项目必须转化为 | 不吸收内容 |
| --- | --- | --- | --- | --- |
| SigNoz | 官方 README 将 SigNoz 定位为 logs、metrics、traces 的单一 observability application，并强调 p99 latency、error rate、Apdex、operations per second 等 out-of-box charts，以及 logs quick filters、query builder、trace breakdown、metrics dashboards。 | 运维观测页面的信息密度、顶部状态概览、指标/日志/trace 类似的多维对象组织、列表和详情联动。 | 深色或中性工作台外壳；首屏状态带；实体类型和 query 结果指标块；结果流与详情区联动；异常/partial 状态醒目；至少一个类似 query builder / filter rail 的控制区。 | 不建设完整 observability 平台、告警规则、仪表盘编辑器或真实 telemetry 图表。 |
| OpenGenerativeUI | 官方 README 强调 generative UI 不只是文本响应，而是 fully interactive visual components，并列出 charts、diagrams、interactive widgets、responsive sizing、progressive reveal 等模式。 | AI 输出不只是文本，应能驱动和解释 UI 组件；用户看到的是结构化组件和上下文，而非长段响应。 | LLM 安全解释区以“阶段、上下文、候选、原因、降级”的组件方式展示；点击 mention/candidate 后解释区视觉焦点同步变化；解释区需有明确 loading/empty/fallback 状态表达。 | 不引入 CopilotKit、Deep Agents、iframe sandbox 或流式生成 UI 架构。 |
| Tambo | 官方 README 将 Tambo 描述为 React generative UI toolkit，核心是注册组件 schema，由 agent 选择组件并流式传入 props，包含 generative components 和 interactable components。 | AI 与应用组件绑定，组件 schema、状态和用户选择应清晰。 | mention、candidate、entity detail、LLM explanation 之间建立可见 selection state；组件状态必须可被测试和人工观察；功能设计需写出主要 UI component state schema。 | 不迁移到 React SDK，不要求 AI 运行时动态生成页面组件。 |

参考源 capture metadata：

| 参考 | Capture date | 规范性 |
| --- | --- | --- |
| SigNoz | 2026-06-02 | 本矩阵中的吸收原则为本项目规范要求；live external page 仅为背景参考。 |
| OpenGenerativeUI | 2026-06-02 | 本矩阵中的吸收原则为本项目规范要求；live external page 仅为背景参考。 |
| Tambo | 2026-06-02 | 本矩阵中的吸收原则为本项目规范要求；live external page 仅为背景参考。 |

### 3.4 视觉差异验收策略

本轮不得只证明“页面可用”。功能设计、实现和验收必须证明“页面观感发生了可见变化”：

| 项 | 要求 |
| --- | --- |
| Before evidence | 保留上一轮页面桌面和窄屏截图作为旧基线，至少包括 `outputs/logs/v2_frontend_desktop_1366x768.png` 和 `outputs/logs/v2_frontend_narrow_390x844.png` 或等价刷新截图。 |
| After evidence | 改造后重新生成相同 viewport 截图，并在视觉补救 traceability artifact 中记录截图路径、生成时间和对应 commit/worktree 状态。 |
| Canonical scenario | before/after 必须使用相同 canonical scenario：同一 sample query `Check ALM-51020 and CPU Usage.`、默认 `offline_demo`、桌面 `1366x768` 和窄屏 `390x844`、browser zoom/device scale 不变、debug collapsed、第二个 mention `CPU Usage` 和候选 `DV-KPI-MTK-001` 为选中态。若功能设计需要替换场景，必须说明理由并保持 before/after 一致。 |
| Manual gate | 验收候选前必须记录用户视觉接受结论；自动化通过不能替代该结论。 |
| Regression guard | 自动化需至少检查工作台外壳、状态带、query/filter 控制区、selection state、LLM explanation component state、debug collapsed 和无横向溢出。 |
| Forbidden weak proof | 不得只用 `data-testid` 存在、API 字段存在、DOM section 可见或卡片文字可读证明视觉风格补救完成。 |

Visual traceability artifact 最小 schema：

| 字段 | 类型 | 要求 |
| --- | --- | --- |
| `schema_version` | string | 必须固定版本，例如 `v2.frontend_visual_traceability.1`。 |
| `scenario` | object | 必须记录 query、mode、viewport、browser zoom/device scale、selected mention/candidate、debug collapsed。 |
| `items[]` | array | 每个 prototype principle 和每个 AC 至少一个 item。 |
| `items[].prototype_ref` | string | `SigNoz`、`OpenGenerativeUI`、`Tambo` 或 `project_visual_ac`。 |
| `items[].absorbed_principle` | string | 原型吸收或项目视觉 AC 的具体原则。 |
| `items[].target_ui_regions` | array | 受影响 UI 区域，例如 shell、status band、query controls、result stream、detail panel、LLM explanation。 |
| `items[].before_screenshot` | string | before 截图路径。 |
| `items[].after_screenshot` | string | after 截图路径。 |
| `items[].same_viewport_and_query` | boolean | before/after 是否使用 canonical scenario。 |
| `items[].automated_visual_semantic_checks` | array | 自动化检查列表及 pass/fail。 |
| `items[].manual_user_acceptance_status` | string | `accepted`、`rejected`、`pending`、`not_applicable`。 |
| `items[].downgrade_classification` | string | `none`、`weak_marker_only`、`api_only`、`no_visual_delta`、`needs_user_decision`。 |
| `items[].reviewer_result` | string | `pass`、`fail`、`needs_user_decision`。 |
| `summary.blocking_count` | number | 任一 P0/P1 visual AC 未 pass、出现 `weak_marker_only` / `api_only` / `no_visual_delta`、或用户视觉接受为 `pending/rejected` 时必须大于 0。 |

阻塞规则：任何 P0/P1 visual AC 没有 `reviewer_result=pass`，或缺少用户 `manual_user_acceptance_status=accepted`，或存在 `downgrade_classification` 为 `weak_marker_only` / `api_only` / `no_visual_delta` / `needs_user_decision`，均不得进入验收关闭。

### 3.5 当前页面差距记录

| 差距 | 证据 | 影响 |
| --- | --- | --- |
| 视觉风格仍接近基础表单 | 当前页面 CSS 以 `--bg: #f4f6f8`、白色 `section/details`、普通蓝色 button 为主。 | 用户难以感知“参考原型后的前端改造”。 |
| 首屏缺少工作台外壳 | 标题、运行状态、LLM 配置、Query 以纵向 section 堆叠为主。 | 不像运维观测工作台，信息密度和层级不足。 |
| LLM 解释仍像文本列表 | safe explanation 主要是普通卡片文本。 | 没有体现交互式 AI UI 的组件化表达。 |
| 自动化验收不能覆盖视觉风格 | 当前 browser evidence 覆盖可见性、点击、无溢出和安全边界。 | 仍可能“自动化通过但用户视觉不认可”。 |

---

## 4 需求明细

### 4.1 IR-V2-FE-VIS-001 V2 前端视觉风格原型吸收补救

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户复核和确认 |
| 需求编号 | IR-V2-FE-VIS-001 |
| 标题 | V2 前端视觉风格原型吸收补救 |
| 状态 | 需求评审闭环已通过，可作为功能设计输入 |
| 处理人 | Codex |

**原始需求描述**：

- 用户指出：前端风格似乎并没有太大的改动，质疑是否真的参考了其他原型。
- Codex 回溯后确认：上一轮补救主要完成信息架构、交互和安全投影，未形成可验收的视觉风格原型吸收要求。
- 用户确认：按 V2 前端视觉风格补救重新进入 DV 流程。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR-V2-FE-VIS-001 |
| 需求标题 | V2 前端视觉风格原型吸收补救 |
| 需求类型 | 可用性需求 + 可测试性需求 + 前端功能展示需求 |
| 优先级 | 高，V2 验收关闭前阻塞 |
| 目标版本 | V2 visual remediation |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

DVEntityLinking V2 需要通过 Web demo 向用户展示多类型实体、多 mention、partial、候选详情和 LLM-based 解释能力。若页面仍像基础表单，即使功能存在，也不能体现 V2 前端改造价值。

**需求方案**：

- 新增原型吸收矩阵并纳入用户确认需求追踪。
- 将页面视觉目标从“区域存在”提升为“运维观测工作台观感明确”。
- 将 LLM 安全解释从普通文本列表提升为可联动的组件区。
- 将截图和人工视觉验收门禁纳入验收候选前反向核查。

**实现细节**：

本文不规定具体 CSS 或 DOM 结构。功能设计阶段必须给出页面布局草案、色彩层级、组件区边界、状态表达、响应式策略和可测试证据。代码实现前必须完成独立需求评审、处置和闭环验证。

#### 4.1.2 配套影响分析

| 配套项 | 影响说明 |
| --- | --- |
| `docs/baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md` | 后续新增视觉补救功能设计，承接本文 SR 和 AC。 |
| `src/dv_entity_linking/web.py` | 后续可能重构 HTML/CSS/JS 视觉外壳和组件区，但本 IR 阶段不改。 |
| `tests/test_web.py` | 后续补充视觉语义、状态带、selection state 和安全解释组件断言。 |
| `scripts/run_v2_acceptance_smoke.py` | 后续补充 visual traceability、截图 freshness 和人工验收状态字段。 |
| `docs/current/TEST_ACCEPTANCE.md` | 当前 V2 重新标记为视觉补救需求阶段，验收候选不得关闭。 |
| `docs/releases/V2.md` | 记录补救后候选被用户复核打回，进入视觉风格补救流程。 |

#### 4.1.3 需求场景

##### 4.1.3.1 UC-V2-FE-VIS-001 打开工作台并感知运维观测风格

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-VIS-001 |
| 用例标题 | 打开 V2 Web demo 并感知工作台视觉变化 |
| 参与者 | Demo 用户、验收者 |
| 前置条件 | `python scripts\run_web_demo.py --mode offline_demo --port 5015` 已启动 |
| 后置条件 | 首屏呈现明确的工作台外壳、状态概览、Query 操作区、结果概览和 catalog/LLM 概览，不再像普通表单页面。 |

##### 4.1.3.2 UC-V2-FE-VIS-002 通过多 mention 结果观察联动关系

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-VIS-002 |
| 用例标题 | 观察 mention、candidate、entity detail 和 LLM explanation 联动 |
| 参与者 | Demo 用户 |
| 前置条件 | 英文多 mention Query 已运行 |
| 后置条件 | 当前选中的 mention/candidate 在视觉上有明确焦点；详情和 LLM 解释区同步展示关联上下文。 |

##### 4.1.3.3 UC-V2-FE-VIS-003 复核桌面和窄屏截图

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-VIS-003 |
| 用例标题 | 通过截图复核视觉补救 |
| 参与者 | 验收者、用户 |
| 前置条件 | 浏览器证据已生成桌面和窄屏截图 |
| 后置条件 | 截图记录视觉风格变化、无关键重叠、无横向溢出，并包含用户视觉验收结论。 |

#### 4.1.4 DFX 需求

| DFX 类型 | 是否涉及 | 说明 |
| --- | --- | --- |
| 可用性 | 是 | 页面必须显著提升可扫读性和工作台感。 |
| 可测试性 | 是 | 视觉原则需转成可检查的 DOM/CSS/截图/人工验收证据。 |
| 可维护性 | 是 | 仍保持轻量 Flask demo 可维护，避免无边界堆叠 CSS。 |
| 安全性 | 是 | 视觉补救不得暴露真实 secret/API key、base URL、raw prompt、raw response 或完整日志。 |
| 真实 DV 内容保护 | 是 | 视觉补救不得新增未经确认的真实感 DV 字段、接口、实体、指标、拓扑标签、样例或 Mock 边界；只能使用已确认样例或明确 synthetic/mock copy。 |
| 可靠性 | 是 | 视觉改造不得破坏已有 API、离线 demo、多 mention 和负例语义。 |

#### 4.1.5 需求分解列表

##### 4.1.5.1 SR-V2-FE-VIS-A01 原型吸收矩阵和视觉设计原则

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-VIS-A01 |
| 标题 | 原型吸收矩阵和视觉设计原则 |
| 类型 | 非功能 SR |
| 责任模块 | Requirements、Web UI |

**需求内容**：功能设计必须把 SigNoz、OpenGenerativeUI 和 Tambo 的可吸收点转化为本项目视觉原则、组件区、状态 schema 和验收项，不得只保留引用链接。设计文档必须逐项说明每个参考信号如何被吸收、被舍弃或被替换。

##### 4.1.5.2 SR-V2-FE-VIS-A02 运维工作台首屏视觉外壳

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-VIS-A02 |
| 标题 | 运维工作台首屏视觉外壳 |
| 类型 | 功能 SR |
| 责任模块 | Web UI |

**需求内容**：桌面首屏必须形成明确的工作台外壳，包含状态带、Query 操作区、结果概览、实体类型概览和 LLM 概览。视觉层级应区别于旧版白卡片表单堆叠，并通过 before/after 截图对比证明变化。

##### 4.1.5.3 SR-V2-FE-VIS-A03 结果流、详情和筛选联动视觉

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-VIS-A03 |
| 标题 | 结果流、详情和筛选联动视觉 |
| 类型 | 功能 SR |
| 责任模块 | Web UI |

**需求内容**：mention、candidate、entity detail、catalog filter 和 similar entities 的选中状态、关联关系和状态差异必须可见，支持用户快速扫读 linked、partial、no_match 和 not_required。

##### 4.1.5.4 SR-V2-FE-VIS-A04 LLM 交互式解释组件化表达

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-VIS-A04 |
| 标题 | LLM 交互式解释组件化表达 |
| 类型 | 功能 SR |
| 责任模块 | Web UI/API projection |

**需求内容**：LLM 安全解释必须以组件化区域展示阶段、上下文、候选、原因、fallback/degraded 状态和安全边界；点击 mention/candidate 后视觉焦点同步变化。

##### 4.1.5.5 SR-V2-FE-VIS-A05 视觉验收证据和人工确认门禁

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-VIS-A05 |
| 标题 | 视觉验收证据和人工确认门禁 |
| 类型 | 非功能 SR |
| 责任模块 | Tests、Acceptance、Documentation |

**需求内容**：后续 smoke 必须输出视觉补救 traceability、before/after 桌面/窄屏截图 freshness、关键视觉语义检查和用户视觉验收结论字段。未得到用户明确视觉验收确认前，V2 不得 accepted/closed。

##### 4.1.5.6 SR-V2-FE-VIS-A06 真实 DV 内容和 Mock 边界保护

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-VIS-A06 |
| 标题 | 真实 DV 内容和 Mock 边界保护 |
| 类型 | 非功能 SR |
| 责任模块 | Web UI、samples、documentation |

**需求内容**：视觉补救只能使用已确认 V2 样例、已有脱敏字段或明确标记为 synthetic/mock 的 UI copy。不得为了增强 observability 观感新增未经确认的真实感 DV metric label、topology label、interface name、field name、entity detail、sample payload、mock strategy 或 capability boundary。若功能设计认为必须新增，必须先回到 D003 用户确认。

---

## 5 用户确认需求追踪矩阵

| 决策来源 | 用户确认项 | IR | SR | 实现 | 测试 | 验收 |
| --- | --- | --- | --- | --- | --- | --- |
| D024 | V2 前端采用运维工作台式演示 + LLM 交互式高亮/解释 | IR-V2-FE-VIS-001 | SR-V2-FE-VIS-A01、A02、A04 | 后续功能设计后填入 | 后续测试设计后填入 | AC-V2-FE-VIS-001、004、006 |
| D042 | 不得静默降级用户确认需求 | IR-V2-FE-VIS-001 | SR-V2-FE-VIS-A05 | 后续功能设计后填入 | 后续测试设计后填入 | AC-V2-FE-VIS-007 |
| D058 | 用户确认上一轮候选视觉风格不足，重新进入视觉风格补救 DV 流程 | IR-V2-FE-VIS-001 | SR-V2-FE-VIS-A01 至 A05 | 未开始 | 未开始 | AC-V2-FE-VIS-001 至 008 |
| D041 | Web demo 只维护 `scripts\run_web_demo.py` 一个入口 | IR-V2-FE-VIS-001 | SR-V2-FE-VIS-A02、A05 | 后续保持 | 后续测试设计后填入 | AC-V2-FE-VIS-006 |
| D003 | 真实 DV 内容和敏感配置不得未经确认进入提交 | IR-V2-FE-VIS-001 | SR-V2-FE-VIS-A04、A05、A06 | 后续保持 | 后续测试设计后填入 | AC-V2-FE-VIS-005、009 |

状态说明：本文为需求草稿，所有实现、测试和验收列均不得标记为完成。

---

## 6 验收底线草案

| ID | 验收项 | 阻塞级别 |
| --- | --- | --- |
| AC-V2-FE-VIS-001 | 功能设计必须包含原型吸收矩阵，逐项说明 SigNoz、OpenGenerativeUI、Tambo 的可吸收点如何落到页面结构、组件和验收证据。 | P0 |
| AC-V2-FE-VIS-002 | 桌面 `1366x768` 第一 viewport 必须呈现 cohesive workbench shell，且至少包含 grouped control zone、results zone 和 detail/explanation zone；不得由多个孤立 full-width stacked panels 组成。功能设计必须提供 annotated desktop 和 narrow layout sketch 标出视觉层级。 | P0 |
| AC-V2-FE-VIS-003 | mention/candidate/entity detail/catalog/LLM explanation 的选中状态和联动关系必须可见，用户无需展开 debug JSON 即可理解当前上下文。 | P0 |
| AC-V2-FE-VIS-004 | LLM 安全解释必须组件化展示阶段、上下文、候选、原因和 fallback/degraded 状态，体现交互式 AI UI 思路，而不是普通文本列表。 | P1 |
| AC-V2-FE-VIS-005 | 视觉补救不得展示真实 secret/API key、token、真实 base URL、raw prompt、raw response 或完整 LLM 日志。 | P0 |
| AC-V2-FE-VIS-006 | Web demo 仍只维护 `scripts\run_web_demo.py`；不新增版本专用启动脚本。 | P0 |
| AC-V2-FE-VIS-007 | 验收候选前必须提供桌面和窄屏截图、visual traceability artifact、自动化布局/语义检查和用户视觉验收确认；缺少用户确认时不得 accepted/closed。 | P0 |
| AC-V2-FE-VIS-008 | 验收证据必须包含 before/after 对比，明确说明改造后不再是普通白卡片表单堆叠；不得只以 `data-testid`、API 字段、section 可见、无溢出或文字可读作为视觉风格完成证明。 | P0 |
| AC-V2-FE-VIS-009 | 视觉补救只能使用已确认 V2 样例或明确 synthetic/mock UI copy；任何新增真实感 DV 字段、接口、实体、样例、metric label、topology label 或 Mock 边界必须先回到 D003 用户确认。 | P0 |

---

## 7 风险和待确认事项

| 风险/问题 | 当前处理 | 是否阻塞需求评审 |
| --- | --- | --- |
| 视觉风格主观性 | 通过原型吸收矩阵、截图和用户确认门禁降低主观漂移。 | 否 |
| Flask 内嵌页面复杂度上升 | 功能设计阶段需限制 CSS/JS 复杂度；若必须引入前端框架需用户确认。 | 否 |
| 自动化无法完全判断审美 | 自动化只做结构、语义和布局证据；最终视觉接受必须由用户确认。 | 否 |
| 参考源可能变化 | 只吸收稳定的高层原则，不依赖外部页面像素级一致。 | 否 |
| 真实感示例诱惑 | 禁止为了增强风格引入未经确认的真实 DV 内容；使用已确认样例或 synthetic/mock copy。 | 否 |

---

## 8 当前结论

V2 前端视觉风格补救已根据用户确认重新进入需求分析阶段。独立需求评审已完成，2 个 P1、2 个 P2、1 个 P3 已接受并完成处置修订；独立闭环验证结论为 closed with recorded residual risk，FE-VIS-REQ-001 至 FE-VIS-REQ-005 均 Closed。本文可作为 V2 前端视觉风格补救功能设计输入；进入代码实现、验收候选或版本关闭仍需后续 DV 门禁。

## 附录 A 参考资料

| 编号 | 资料名称 | 来源 |
| --- | --- | --- |
| A1 | V2 原需求分析 | [IR.md](./IR.md) |
| A2 | V2 前端功能补救需求 | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| A3 | V2 前端功能补救设计 | [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md) |
| A4 | V2 release / acceptance record | [../../releases/V2.md](../../releases/V2.md) |
| A5 | 当前决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| A6 | SigNoz | [https://github.com/SigNoz/signoz](https://github.com/SigNoz/signoz)，captured on 2026-06-02 |
| A7 | OpenGenerativeUI | [https://github.com/CopilotKit/OpenGenerativeUI](https://github.com/CopilotKit/OpenGenerativeUI)，captured on 2026-06-02 |
| A8 | Tambo | [https://github.com/tambo-ai/tambo](https://github.com/tambo-ai/tambo)，captured on 2026-06-02 |
| A9 | 当前旧版桌面截图 | `outputs/logs/v2_frontend_desktop_1366x768.png` |
| A10 | 当前旧版窄屏截图 | `outputs/logs/v2_frontend_narrow_390x844.png` |

## 附录 B 需求评审输入包

请独立需求评审者只读复核以下输入：

- [IR-FRONTEND-VISUAL-REMEDIATION.md](./IR-FRONTEND-VISUAL-REMEDIATION.md)
- [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md)
- [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md)
- [../../releases/V2.md](../../releases/V2.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- `src/dv_entity_linking/web.py`
- `outputs/logs/v2_frontend_desktop_1366x768.png`
- `outputs/logs/v2_frontend_narrow_390x844.png`

评审输出要求：

- 列出 P0/P1/P2/P3 findings。
- 特别检查原型吸收矩阵是否足够指导功能设计。
- 特别检查验收底线是否能阻止“功能通过但风格没变”。
- 特别检查是否错误要求生产级前端或复制外部产品。
- 给出是否 ready for disposition 的结论。

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V2-FE-Visual-Remediation |
| 创建日期 | 2026-06-02 |
| 作者 | Codex |
| 状态 | 需求评审闭环已通过，可作为功能设计输入 |
| 版本 | V2-FE-VIS.2-closed |

## 评审记录

| 评审日期 | 评审人 | 评审意见 | 状态 |
| --- | --- | --- | --- |
| 2026-06-02 | no-context 独立需求评审 Nash | Ready for disposition；无 P0，2 个 P1，2 个 P2，1 个 P3，要求补齐 D003 安全边界、visual traceability schema、before/after 可比场景、首屏边界和参考源 capture metadata。 | 处置完成，待独立闭环验证 |
| 2026-06-02 | no-context sealed closure verification Raman | FE-VIS-REQ-001 至 FE-VIS-REQ-005 均 Closed；结论为 closed with recorded residual risk；允许进入功能设计。 | 闭环通过 |
