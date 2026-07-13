# DigitalView-SW DVEntityLinking V2 前端改造补救需求分析文档

---

> 文档治理说明：本文是 V2 blocked 后针对前端改造阻塞项重新进入 DV 流程的需求分析输出。本文只覆盖 V2 前端改造补救范围，不替代已闭环的 [IR.md](./IR.md) 和 [SR.md](./SR.md)。本文已完成需求评审处置和独立闭环验证，可作为 V2 前端补救功能设计输入。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V2-FE.0-draft | 2026-06-01 | Codex | 根据用户追责和重新走 DV 流程要求，形成 V2 前端改造补救需求分析草稿。 |
| V2-FE.1-draft | 2026-06-01 | Codex | 接受 no-context 独立需求评审 4 个 P1 和 3 个 P2，补齐追踪矩阵、浏览器级验收证据、多 mention 字段、LLM 交互式安全解释和安全边界澄清。 |
| V2-FE.2-closed | 2026-06-02 | Codex | 记录独立闭环验证通过，4 个 P1 和 3 个 P2 均 Closed，可进入 V2 前端补救功能设计。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 前端改造 | Frontend Remediation |
| 演示工作台 | Demo Workbench |
| 多 Mention 可视化 | Multi-mention Visualization |
| LLM 交互式安全解释 | LLM Interactive Safe Explanation |
| 用户确认需求追踪 | User-confirmed Requirement Traceability |
| 静默降级禁止 | No Silent Downgrade |

### Abstract 摘要

**中文摘要**：

本文档定义 DVEntityLinking V2 前端改造补救需求。V2 原验收候选已撤回，原因是已确认的重要前端改造要求未落实，并被后续实现、测试和验收静默降级为 Web/API projection。本文重新从需求分析阶段定义 V2 前端补救范围、非范围、用户确认需求追踪矩阵、用例、SR 分解、验收底线和评审输入包。本文不新增实体 schema、不改变 V2 已验证的数据/链接/评测语义，不要求引入生产级前端工程。

**English Abstract**：

This document defines the V2 frontend remediation requirements for DVEntityLinking. The previous V2 acceptance candidate was withdrawn because an important user-confirmed frontend enhancement was not implemented and was silently downgraded to a Web/API projection. This document restarts the DV process at requirement analysis for the frontend remediation scope, including traceability, use cases, SR decomposition, acceptance floor, and review inputs. It does not change the V2 entity schema, linking semantics, or evaluation semantics, and it does not mandate a production-grade frontend stack.

---

## List of Abbreviations 缩略语清单

| 缩略语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| IR | Issue Requirement | 需求项 |
| SR | Sub Requirement | 子需求 |
| UC | Use Case | 用例 |
| DV | DigitalView-SW | 电信软件网管系统 |
| LLM | Large Language Model | 大语言模型 |
| UI | User Interface | 用户界面 |
| API | Application Programming Interface | 应用程序接口 |

---

## 1 引言

### 1.1 目的

本文用于把 V2 前端改造阻塞项重新纳入 DV 流程，从需求分析阶段明确：

- V2 前端改造当前必须补齐什么。
- 哪些内容不进入本次补救范围。
- 用户确认的重要需求如何追踪到 IR、SR、实现、测试和验收。
- 哪些验收项必须阻塞 V2 重新进入 acceptance candidate。

预期读者：

- V2 前端补救需求评审者。
- V2 前端补救功能设计负责人。
- V2 前端实现和测试设计负责人。
- V2 验收复核人员。

### 1.2 范围

#### 需求范围内

| 产品/服务 | 说明 |
| --- | --- |
| 当前 Web demo 首页 | 保持 `scripts/run_web_demo.py` 作为唯一启动入口，改造当前 Flask Web demo 的页面结构、信息层级和交互体验。 |
| V2 多类型实体展示 | 展示 V2 unified catalog 的实体类型、数量、实体目录、类型过滤、实体详情和相似实体。 |
| 多 mention 结果展示 | 在 Query 视图中展示 mention 文本、类型、状态、span/位置、候选和 linked entity。 |
| `partial`、`no_match`、`not_required` 展示 | 页面必须让用户直观看到 Query 级状态和 mention 级局部状态，不得只给一个模糊 summary。 |
| LLM 交互式安全解释 | 展示 LLM 是否启用、是否参与、是否 fallback、阶段级错误和安全摘要；用户点击 mention、候选或 LLM 状态时，页面必须展示相关的脱敏解释和阶段摘要；不得展示真实 secret/API key、真实 base URL、完整 prompt、完整响应或完整日志。 |
| Demo 验收证据 | 补充可执行验证，包括页面结构断言、API 断言、真实浏览器或等价浏览器级渲染断言、桌面/窄屏截图或布局证据，以及用户确认需求追踪矩阵。 |
| 参考内容吸收 | 参考 SigNoz 的运维观测工作台信息密度，以及 OpenGenerativeUI/Tambo 的交互式 AI UI 思路，但只转化为本项目 demo 需要的展示和交互要求。 |

#### 需求范围外

| 产品/服务 | 说明 |
| --- | --- |
| 生产级前端产品化 | 不建设权限、多租户、国际化管理、完整设计系统、复杂拓扑工作台或商业化运维平台。 |
| 强制前端框架迁移 | 本需求不强制从 Flask 内嵌页面迁移到 React/Next.js；若设计阶段认为必须迁移，需单独回到用户确认。 |
| 实体 schema 改动 | 不新增实体字段、关系或类型专属 schema；如必须新增，回到需求确认。 |
| 链接算法重写 | 不重写 V2 已验证的 catalog、extractor、linker、evaluator 主流程。 |
| 真实 DV 接口直连 | 不接入真实 DV 生产接口。 |
| 默认真实 LLM 验收 | 默认验收仍不依赖真实 LLM；真实 LLM 只作为条件补证。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| 前端补救 | 针对 V2 已确认但未落实的前端演示工作台要求进行需求、设计、实现、测试和评审补齐。 |
| 演示工作台 | 面向 demo 和评审的操作台式页面，第一屏直接呈现运行状态、Query、mention、候选、实体目录和 LLM 交互式安全解释概览。 |
| 多 mention 可视化 | 同一 Query 中多个实体提及的文本、状态、类型、候选和链接结果可分别观察。 |
| LLM 交互式安全解释 | 在不暴露敏感配置、完整 prompt、完整响应或完整日志的前提下，把 LLM 参与环节、状态、错误码、阶段摘要和与 mention/candidate 关联的脱敏解释作为可点击查看的信息。 |
| 静默降级 | 未经用户确认，将已确认需求实现为更弱能力、较弱测试或较弱验收项。 |

---

## 2 系统总体说明

DVEntityLinking 当前是 Python 3.12 + Flask 单进程 demo。V2 数据、链接、评测和 smoke 已有默认离线验证，但前端仍停留在普通表单和 section 列表，不能充分展示 V2 的多类型、多 mention、`partial` 和 LLM 降级语义。

本次补救不改变后端主能力，只要求 Web demo 以更清晰的工作台方式消费现有 API 和 safe projection：

```text
run_web_demo.py
  -> Flask page
  -> /api/status
  -> /api/link
  -> /api/entities
  -> /api/retrieve
  -> safe Web projection
  -> demo workbench UI
```

设计原则：

| 原则 | 说明 |
| --- | --- |
| 单一入口 | Web 启动脚本只维护 `scripts/run_web_demo.py`。 |
| Demo 优先 | 第一屏就是可操作体验，不做 landing page。 |
| 信息可扫读 | 状态、Query、mention、候选、详情和 catalog 分区清晰，适合反复演示。 |
| 安全投影 | 前端只展示 safe fields。 |
| 不静默降级 | 若设计或实现无法满足本文验收项，必须记录为需用户确认，不能直接进入验收候选。 |

---

## 3 需求总体描述

### 3.1 背景和问题

V2 原 IR/SR 已确认前端采用“运维工作台式演示 + LLM 交互式高亮/解释”。后续实现阶段主要完成了数据和 API 能力，但 Web 页面只做到基础 section 渲染；测试也只检查 section 存在和 API projection，未覆盖已确认的重要前端改造要求。因此 V2 原验收候选已撤回。

### 3.2 预期价值

- 让用户打开 Web demo 后能直接理解 V2 当前实体目录、运行模式、LLM 状态和链接能力。
- 让多 mention Query 的局部成功、局部失败、候选和解释可见。
- 让 `partial`、`no_match`、`not_required` 不被隐藏在调试 JSON 中。
- 让后续验收不再把“API 有字段”误判为“前端改造完成”。

### 3.3 参考内容吸收方式

参考内容只作为需求启发，不直接引入外部产品的技术栈或完整产品能力：

| 参考 | 可吸收点 | 不吸收点 |
| --- | --- | --- |
| SigNoz | 运维观测类页面的信息密度、状态概览、列表/详情联动、日志/指标/trace 类似的多维结果组织。 | 不建设完整 observability 平台、告警系统、仪表盘编辑器。 |
| OpenGenerativeUI | AI 结果可以以交互式组件呈现，而不只是文本；适合把 LLM 安全解释和结果可视化。 | 不要求引入 CopilotKit、LangChain Deep Agents 或 iframe sandbox 架构。 |
| Tambo | AI 可以选择或驱动既有 UI 组件，组件 schema 和状态管理应明确。 | 不要求迁移到 React SDK 或流式生成 UI。 |

---

## 4 需求明细

### 4.1 IR-V2-FE-001 V2 前端演示工作台补救

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户追责和重新流程指令 |
| 需求编号 | IR-V2-FE-001 |
| 标题 | V2 前端演示工作台补救 |
| 状态 | 需求评审闭环已通过，可作为功能设计输入 |
| 处理人 | Codex |

**原始需求描述**：

- 用户指出：V2 版本很重要的一个事情是参考调研内容，对前端进行改造，但没有执行。
- 用户要求严格回溯评审为何通过，并追责。
- 用户随后要求：重新把 V2 版本前端改造需求重新走 DV 流程。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR-V2-FE-001 |
| 需求标题 | V2 前端演示工作台补救 |
| 需求类型 | 功能性需求 + 可用性/可测试性需求 |
| 优先级 | 高，V2 重新进入验收前阻塞 |
| 目标版本 | V2 remediation |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

V2 已完成多类型实体、英文多 mention、`partial`、V2 evaluation 和 acceptance smoke 的初始实现，但前端改造要求未按用户确认落地。该问题影响 V2 demo 可理解性和验收可信度。

**需求方案**：

- 保持单 Web 启动入口。
- 将当前 Web 页面改造成 V2 演示工作台。
- 将 Query、mention、候选、实体详情、catalog、LLM 交互式安全解释和调试 JSON 明确分层。
- 将前端补救要求纳入用户确认需求追踪矩阵。
- 将测试从 API/DOM section 存在扩展到可验证的页面行为和验收项。

**实现细节**：

本文不定义具体代码结构。功能设计阶段需决定是否继续 Flask 内嵌 HTML/CSS/JS，或在用户确认后引入更重前端结构。

#### 4.1.2 配套影响分析

| 配套项 | 影响说明 |
| --- | --- |
| `src/dv_entity_linking/web.py` | 预计需要重构页面模板、CSS、前端 JS 和 safe projection 渲染。 |
| `tests/test_web.py` | 需要补充页面结构、交互和安全展示断言。 |
| `scripts/run_v2_acceptance_smoke.py` | 需要补充前端工作台关键 marker 和示例渲染检查。 |
| `docs/current/TEST_ACCEPTANCE.md` | 需要补充 V2 前端补救验收项。 |
| `docs/releases/V2.md` | 需保持 blocked，直到补救闭环完成。 |

#### 4.1.3 需求场景

##### 4.1.3.1 UC-V2-FE-001 打开当前 V2 Web demo

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-001 |
| 用例标题 | 打开当前 V2 Web demo 并理解运行状态 |
| 参与者 | Demo 用户、验收者 |
| 前置条件 | `python scripts\run_web_demo.py --mode offline_demo --port 5015` 已启动 |
| 后置条件 | 页面第一屏展示运行模式、catalog loaded、entity_count、type_counts、LLM 状态和当前样例 Query |

##### 4.1.3.2 UC-V2-FE-002 运行英文多 mention Query

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-002 |
| 用例标题 | 链接英文多 mention Query |
| 参与者 | Demo 用户 |
| 前置条件 | V2 catalog 和 query samples 可用 |
| 后置条件 | 页面展示 Query 级 status、每个 mention 的 text/type/status、linked entity、候选和解释 |

##### 4.1.3.3 UC-V2-FE-003 观察 partial / no_match / not_required

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-003 |
| 用例标题 | 观察异常和负例语义 |
| 参与者 | Demo 用户、验收者 |
| 前置条件 | 输入覆盖 `partial`、`no_match`、`not_required` 的 Query |
| 后置条件 | 页面能直观看到局部成功/失败、无候选和无需链接，不需要展开调试 JSON 才理解 |

##### 4.1.3.4 UC-V2-FE-004 查看实体目录和实体详情

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-004 |
| 用例标题 | 按类型浏览 V2 catalog |
| 参与者 | Demo 用户 |
| 前置条件 | V2 unified catalog 已加载 |
| 后置条件 | 用户可按 entity_type 查看实体目录、选择实体、查看详情和相似实体 |

##### 4.1.3.5 UC-V2-FE-005 查看 LLM 交互式安全解释

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC-V2-FE-005 |
| 用例标题 | 点击查看 LLM 参与、解释和降级状态 |
| 参与者 | Demo 用户、验收者 |
| 前置条件 | offline 或 llm_enabled 模式 |
| 后置条件 | 页面展示 LLM enabled/used/fallback/degraded/stage error；点击 mention、候选或 LLM 状态时展示关联的脱敏解释和阶段摘要；不展示敏感配置、完整 prompt、完整响应或完整日志 |

#### 4.1.4 DFX 需求

| DFX 类型 | 是否涉及 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 页面只消费 safe projection，不参与业务判定；API 异常必须显示为可理解错误。 |
| 可用性 | 是 | 第一屏能支持演示；结果分层清楚；状态和候选易扫读。 |
| 可维护性 | 是 | 页面结构、样式和渲染逻辑应可被测试定位，避免所有内容堆进不可维护字符串。 |
| 可测试性 | 是 | 至少覆盖页面结构、关键交互、示例 Query 渲染、安全字段缺失和 smoke evidence。 |
| 安全性 | 是 | 真实 secret/API key、token、真实 base URL、raw prompt、raw response、完整 LLM 日志不得展示或入库；字段名、password input 类型、环境变量名和脱敏配置状态可以用于安全配置说明。 |

#### 4.1.5 需求分解列表

##### 4.1.5.1 SR-V2-FE-A01 工作台信息架构

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-A01 |
| 标题 | V2 Web demo 工作台信息架构 |
| 类型 | 功能 SR |
| 责任模块 | Web UI |

**需求内容**：页面第一屏必须以工作台方式组织 Runtime status、Query panel、Result summary、Mention strip、Candidate/Entity detail、Catalog panel 和 LLM interactive safe explanation overview。

##### 4.1.5.2 SR-V2-FE-A02 Query 与多 mention 可视化

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-A02 |
| 标题 | Query 输入和多 mention 可视化 |
| 类型 | 功能 SR |
| 责任模块 | Web UI/API projection |

**需求内容**：支持样例 Query 选择或快速填充；运行后展示每个 mention 的文本、类型、状态、span、linked entity 和候选入口。`partial` 必须保留 mention 级局部解释。

##### 4.1.5.3 SR-V2-FE-A03 候选、实体详情和相似实体联动

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-A03 |
| 标题 | 候选实体与详情联动 |
| 类型 | 功能 SR |
| 责任模块 | Web UI/API projection |

**需求内容**：候选列表应显示 entity_id、entity_type、canonical_name、score/rank 或 match_reason；选择候选或 linked entity 后展示实体详情和相似实体。

##### 4.1.5.4 SR-V2-FE-A04 Catalog、运行状态和 LLM 交互式安全解释

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-A04 |
| 标题 | Catalog、运行状态和 LLM 交互式安全解释 |
| 类型 | 功能 SR |
| 责任模块 | Web UI/API projection |

**需求内容**：展示 catalog loaded、entity_count、type_counts、当前 mode、LLM enabled/used/fallback/degraded、stage_statuses 和 safe_summary；点击 mention、candidate 或 LLM status 时展示关联的脱敏解释、参与阶段和降级原因；不得展示真实 secret/API key、真实 base URL、raw prompt、raw response 或完整 LLM 日志。

##### 4.1.5.5 SR-V2-FE-A05 页面可用性、响应式和安全边界

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-A05 |
| 标题 | 页面可用性、响应式和安全边界 |
| 类型 | 非功能 SR |
| 责任模块 | Web UI、tests |

**需求内容**：桌面和窄屏布局不得出现关键文字重叠；调试 JSON 默认折叠；页面不使用营销 landing；真实 secret/API key、真实 base URL、token、raw prompt、raw response 和完整 LLM 日志不得出现在 HTML、API safe projection 或 smoke 日志中。字段名、password input 类型、环境变量名和 redacted/empty 配置状态可出现，用于说明安全配置边界。

##### 4.1.5.6 SR-V2-FE-A06 验收追踪和测试补强

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V2-FE-A06 |
| 标题 | 验收追踪和测试补强 |
| 类型 | 非功能 SR |
| 责任模块 | tests、acceptance smoke、documentation |

**需求内容**：建立用户确认需求追踪矩阵；补充页面结构、关键交互、安全展示、浏览器级 smoke evidence 和截图/布局证据；验收候选前必须从用户确认项反向核查。评审输入包必须包含用户决策来源、当前差异文件清单、测试映射、每项是否存在降级的状态，以及无法满足项的用户确认记录。

---

## 5 用户确认需求追踪矩阵

| 决策来源 | 用户确认项 | IR | SR | 实现 | 测试 | 验收 |
| --- | --- | --- | --- | --- | --- | --- |
| D024 | V2 前端采用运维工作台式演示，不做过度产品化 | IR-V2-FE-001 | SR-V2-FE-A01、A05 | 后续功能设计和实现阶段填入 | 后续测试设计阶段填入 | AC-V2-FE-001、AC-V2-FE-007 |
| D024、D043 | V2 前端展示 Query、mention、高亮/可视化、候选、实体详情和 LLM 交互式解释 | IR-V2-FE-001 | SR-V2-FE-A02、A03、A04 | 后续功能设计和实现阶段填入 | 后续测试设计阶段填入 | AC-V2-FE-002、AC-V2-FE-003、AC-V2-FE-005、AC-V2-FE-006 |
| D028、D043 | V2 必须支持多 mention Query，且前端必须可观察 | IR-V2-FE-001 | SR-V2-FE-A02、A03 | 后续功能设计和实现阶段填入 | 后续测试设计阶段填入 | AC-V2-FE-002、AC-V2-FE-003 |
| D042、D043 | 不得把前端改造静默降级为 Web/API projection | IR-V2-FE-001 | SR-V2-FE-A06 | 后续功能设计和实现阶段填入 | 后续测试设计阶段填入 | AC-V2-FE-008、AC-V2-FE-009 |
| D041 | Web demo 只维护 `run_web_demo.py` 一个入口 | IR-V2-FE-001 | SR-V2-FE-A01、A06 | 已有基础，后续需保持 | 后续测试设计阶段补强 | AC-V2-FE-001、AC-V2-FE-008 |
| D003、D042 | 敏感配置和完整 LLM 请求响应不得展示或提交 | IR-V2-FE-001 | SR-V2-FE-A04、A05 | 后续功能设计和实现阶段填入 | 后续测试设计阶段填入 | AC-V2-FE-006、AC-V2-FE-008 |

状态说明：本 IR 阶段只允许 `IR` 和计划性 `SR` 关闭；实现、测试、验收必须在后续阶段填入具体文件、用例和证据。

---

## 6 验收底线草案

| ID | 验收项 | 阻塞级别 |
| --- | --- | --- |
| AC-V2-FE-001 | `run_web_demo.py` 默认打开 V2 工作台页面；桌面 `1366x768` 第一屏可见运行状态、Query 输入、结果摘要、catalog 概览和 LLM overview；窄屏 `390x844` 通过正常纵向滚动可访问相同关键区块。 | P0 |
| AC-V2-FE-002 | 英文多 mention Query 运行后，页面逐 mention 展示 `text`、`entity_type` 或 `predicted_type`、`status`、`span`、`linked_entity`，并展示该 mention 的候选或 no-candidate reason，不只依赖调试 JSON。 | P0 |
| AC-V2-FE-003 | `partial` Query 能直观看到哪个 mention linked、哪个 mention no_match/degraded；各 mention 的原因、候选归属和降级状态可区分。 | P0 |
| AC-V2-FE-004 | `no_match` 和 `not_required` 不展示伪候选或伪 linked entity。 | P0 |
| AC-V2-FE-005 | Catalog panel 可按类型观察 V2 entity_count/type_counts，并能查看实体详情。 | P1 |
| AC-V2-FE-006 | LLM 交互式安全解释展示 enabled/used/fallback/degraded/stage error；点击 mention、候选或 LLM 状态时展示关联的脱敏解释和阶段摘要；不展示真实 secret/API key、真实 base URL、raw prompt、raw response 或完整 LLM 日志。 | P1 |
| AC-V2-FE-007 | 桌面 `1366x768` 和窄屏 `390x844` 视图无关键文本重叠；调试 JSON 默认折叠；页面首屏不是 landing page。 | P1 |
| AC-V2-FE-008 | 自动化测试或 smoke 证据必须包含真实浏览器或等价浏览器级断言，覆盖桌面/窄屏 viewport、Query submit、candidate/entity detail linkage、catalog type filter、debug collapsed、截图/布局证据和单 Web 入口；纯 marker 或 API projection 检查只能作为补充证据。 | P1 |
| AC-V2-FE-009 | 验收候选前反向核查表完成，所有用户确认项均映射到实现、测试和验收证据。 | P0 |

---

## 7 风险和待确认事项

| 风险/问题 | 当前处理 | 是否阻塞需求评审 |
| --- | --- | --- |
| 是否引入前端框架 | 当前不强制引入；功能设计可评估，若必须引入需用户确认。 | 否 |
| LLM 交互式解释深度 | 本轮最低要求为点击 mention、候选或 LLM 状态后展示关联的脱敏解释和阶段摘要；不要求实时流式生成 UI。 | 否 |
| 高亮的具体实现方式 | 可为 span chip、文本标注、mention strip 或等价视觉表达，但必须能连接 mention、candidate/entity detail 和 LLM 安全解释。 | 否 |
| LLM 配置 UI 安全边界 | 字段名、password input、环境变量名和 redacted/empty 配置状态可以展示；真实 secret/API key、真实 base URL、raw prompt、raw response 和完整日志禁止展示。 | 否 |
| 视觉精细程度 | 要求专业可演示、信息层级清晰；不要求完整设计系统。 | 否 |

---

## 8 当前结论

V2 前端改造补救已重新进入 DV 流程并完成需求评审处置和独立闭环验证。本文可作为 V2 前端补救功能设计输入，但不得直接进入实现或验收。下一步必须进行功能设计、独立设计评审、设计评审处置和设计闭环验证。

## 附录 A 参考资料

| 编号 | 资料名称 | 来源 |
| --- | --- | --- |
| A1 | V2 原需求分析 | [IR.md](./IR.md) |
| A2 | V2 原功能设计 | [SR.md](./SR.md) |
| A3 | V2 验收候选撤回记录 | [../../releases/V2.md](../../releases/V2.md) |
| A4 | 当前 DV 流程 | [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md) |
| A5 | 当前决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| A6 | SigNoz | [https://github.com/SigNoz/signoz](https://github.com/SigNoz/signoz) |
| A7 | OpenGenerativeUI | [https://github.com/CopilotKit/OpenGenerativeUI](https://github.com/CopilotKit/OpenGenerativeUI) |
| A8 | Tambo | [https://github.com/tambo-ai/tambo](https://github.com/tambo-ai/tambo) |
| A9 | 前端补救需求评审处置 | [FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| A10 | 前端补救需求评审闭环验证 | [FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |

## 附录 B 需求评审输入包

请独立需求评审者只读复核以下输入：

- [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md)
- [IR.md](./IR.md)
- [SR.md](./SR.md)
- [../../releases/V2.md](../../releases/V2.md)
- [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- `src/dv_entity_linking/web.py`
- `tests/test_web.py`
- `scripts/run_v2_acceptance_smoke.py`

评审输出要求：

- 列出 P0/P1/P2/P3 findings。
- 特别检查用户确认需求追踪矩阵是否完整。
- 特别检查是否仍存在静默降级风险。
- 给出是否 ready for disposition 的结论。

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V2-FE-Remediation |
| 创建日期 | 2026-06-01 |
| 作者 | Codex |
| 状态 | 需求评审闭环已通过，可作为功能设计输入 |
| 版本 | V2-FE.2-closed |

## 评审记录

| 评审日期 | 评审人 | 评审意见 | 状态 |
| --- | --- | --- | --- |
| 2026-06-01 | no-context 独立需求评审 Harvey | Ready for disposition；无 P0，4 个 P1，3 个 P2，要求补齐追踪矩阵、浏览器级验收证据、LLM 交互式解释、多 mention 字段、安全边界、反降级输入包和 viewport 定义。 | 处置完成 |
| 2026-06-02 | independent subagent Erdos | 4 个 P1 和 3 个 P2 均 Closed；文档卫生 Passed；可进入功能设计。 | 闭环通过 |
