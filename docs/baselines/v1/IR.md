# DigitalView-SW DVEntityLinking V1 需求分析文档

---

> 文档治理说明：本文是 V1 IR 主输出件，按版本保留。原过程性确认、评审和闭环文件已合并到 [../../releases/V1.md](../../releases/V1.md) 与 [../../current/DECISIONS.md](../../current/DECISIONS.md)；需要原始过程细节时通过 Git 历史追溯。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V1.0-draft | 2026-05-26 | Codex | 基于用户 V1 关键需求点形成需求分析初稿；真实 Query 和实体样例待用户提供，暂不进入独立评审。 |
| V1.1-draft | 2026-05-31 | Codex | 接收并规范化 V1 可提交启动样例；确认新增 `alarm` 告警知识实体类型和 Query 标注结构。 |
| V1.2-draft | 2026-05-31 | Codex | 确认 V1 仅覆盖 `alarm` 实体类型，扩展启动样例，并明确内存索引优先的检索/存储策略。 |
| V1.3-draft | 2026-05-31 | Codex | 确认 Web demo LLM 切换形态、配置展示边界和检索验收指标；样例扩展为 16 条 Query，补充 no_match/not_required 精度约束。 |
| V1.4-draft | 2026-05-31 | Codex | 根据 V1 独立需求评审处置补充 Query canonical schema、LLM 输出状态、评测计算、预置 loader 和文档追踪信息。 |
| V1.5-draft | 2026-06-01 | Codex | 根据用户验收反馈，将 V1 样例和 Web 默认展示收敛为核心实体链接字段，移除 `data_layer`、`can_commit`、`sensitive_level` 等非核心样例字段。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| LLM 模式切换 | LLM Mode Switching |
| 真实 Query 样例 | Real Query Samples |
| 实体数据结构 | Entity Data Structure |
| 告警知识实体 | Alarm Knowledge Entity |
| 检索算法 | Retrieval Algorithm |
| 混合检索 | Hybrid Retrieval |
| 可提交样例 | Commit-ready Samples |

### Abstract 摘要

**中文摘要**：

本文档定义 DVEntityLinking V1 的需求分析草稿。V1 在 V0 已关闭的基础上，重点增强 Web demo 的 LLM 模式切换与配置能力，引入真实 Query 样例接收和评测流程，围绕 `alarm` 告警知识实体审视实体数据结构，并对检索算法进行重点规划和设计。当前已接收一组用户确认可提交的启动样例：9 个告警知识实体和 16 条 Query 标注；样例覆盖 linked、ambiguous、no_match 和 not_required。用户已确认准确率和召回率同等重要，并进一步确认 V1 页面与样例默认只突出核心实体链接信息，完整 JSON 仅作为折叠调试信息保留。

**English Abstract**：

This document is the V1 requirement analysis draft for DVEntityLinking. Based on the closed V0 baseline, V1 focuses on Web demo LLM mode switching and configuration, real query sample intake and evaluation preparation, alarm knowledge entity structure review, and retrieval algorithm planning/design. One commit-ready startup sample set has been received, covering 9 alarm knowledge entities and 16 queries across linked, ambiguous, no_match, and not_required cases. The user has confirmed that precision and recall are equally important, and V1 now exposes only core entity-linking information by default while keeping full JSON in collapsed debug details.

---

## List of Abbreviations 缩略语清单

| 缩略语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| DV | DigitalView-SW | 面向运营商领域的电信软件网管系统 |
| IR | Issue Requirement | 需求项 |
| SR | Sub Requirement | 子需求 |
| UC | Use Case | 用例 |
| LLM | Large Language Model | 大语言模型 |
| NER | Named Entity Recognition | 命名实体识别 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 |
| Top-K | Top K Results | 返回排序前 K 个结果 |
| MRR | Mean Reciprocal Rank | 平均倒数排名 |

---

## 1 引言

### 1.1 目的

本文档用于明确 DVEntityLinking V1 的需求范围、非范围、样例输入策略、LLM 模式切换、实体结构审视、检索算法规划和后续评审门控。

预期读者：

- V1 需求评审者。
- V1 功能设计负责人。
- V1 代码实现和测试设计负责人。
- 真实 Query 和实体样例提供者。

### 1.2 范围

#### 需求范围内

| 产品/服务 | 说明 |
| --- | --- |
| Web demo LLM 模式切换 | 支持在 Web demo 中选择和观察 `offline_demo` 与 `llm_enabled_demo`。 |
| LLM 配置可观察性 | 支持查看 LLM 是否启用、当前运行模式、降级和错误原因；敏感配置不得展示。 |
| 真实 Query 样例接收 | 建立真实 Query 样例的本地保存、标注和评测集形成流程。 |
| 实体数据结构审视 | 按实体类型分析用户提供样例，审视字段、关系、生命周期、来源和证据。 |
| 检索算法规划 | 明确 V1 检索候选召回、排序、解释、评测指标和降级策略。 |

#### 需求范围外

| 产品/服务 | 说明 |
| --- | --- |
| 真实 DV 生产写操作 | V1 不做自动修复、派单、变更或告警确认。 |
| 未确认真实字段固化 | 样例未到位或未确认前，不把真实 DV 字段写成正式基线。 |
| 生产级向量库运维 | V1 可规划或本地验证算法，不默认上线生产级向量库。 |
| 完整实体治理平台 | V1 不建设全量实体生命周期治理和权限审计平台。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| LLM 模式切换 | 在 Web/API/启动参数中选择离线 deterministic 模式或真实 LLM 辅助模式。 |
| 真实 Query 样例 | 用户提供的实际使用 Query；V1 当前样例按可提交内容处理。 |
| 告警知识实体 | DV 告警知识/事实类实体，V1 唯一目标类型为 `alarm`，不同于 V0 的告警事件实例语义。 |
| FTS | Full-Text Search，全文检索。SQLite FTS5 可作为后续可选持久化能力，但 V1 不作为必需依赖。 |
| 实体结构审视 | 基于用户按类型提供的样例分析实体字段、关系、来源和类型差异。 |
| 混合检索 | 结合关键词、别名、类型、拓扑关系、语义 embedding、LLM rerank 等信号的检索方案。 |

---

## 2 系统总体说明

V1 继续沿用 V0 的 Python 3.12、Flask Web/API、L0 Mock、OpenAI-compatible LLM adapter 和本地安全边界。V1 不推翻 V0 基线，而是在已关闭 V0 上增加更接近真实使用的输入和算法设计。V1 实体类型范围限定为 `alarm`，其他实体类型留到后续迭代。

V1 将 `D:\workspace\DVKnowledge\memory\dv` 作为 DV context 补充来源。当前只将该目录登记为参考上下文；除用户确认的启动样例外，不把 `alarm_index` 的 severity、impact、possible_causes 等更多字段固化进实体基线。

```text
Web demo / API
  -> mode selection and LLM config status
  -> Query sample intake and entity extraction
  -> entity linking and entity structure validation
  -> retrieval candidate generation
  -> hybrid ranking / explanation / evaluation
```

---

## 3 需求总体描述

### 3.1 用户痛点

- 当前 Web demo 默认离线模式，真实 LLM 只通过 smoke 验证，用户无法在页面上直接切换和观察 LLM 模式。
- V0 使用 L0 Mock，尚未基于真实 Query 样例验证实体识别和链接难点。
- 现有实体结构是 V0 最小结构，需要结合真实实体类型样例重新审视字段、关系和证据。
- Top-K 检索仍是 deterministic score，需要进入系统性算法规划和设计。

### 3.2 预期价值

- 用户能在 Web demo 中直观看到离线模式和 LLM 模式的差异。
- 真实 Query 和实体样例能够转化为可控、可提交、可评测的 V1 样例资产。
- 实体结构更贴近真实 DV 场景，同时默认只暴露实体链接核心字段。
- 检索算法有明确候选召回、排序、解释和评测指标，为后续实现降低不确定性。

### 3.3 V1 样例策略

| 样例 | 当前状态 | 要求 |
| --- | --- | --- |
| 真实 Query 样例 | 已提供 16 条可提交启动样例 | 规范为 `id/query + mentions + expected_entities`；有 mention 时 span 必填，采用 0-based end-exclusive。 |
| 实体类型样例 | 已提供 9 个可提交 `alarm` 启动样例 | `alarm` 为 V1 新增目标类型；当前只固化最小字段，不固化 DVKnowledge 扩展字段。 |
| 检索评测样例 | 待基于 Query/实体样例形成 | 需要正例、难负例、相关性理由和 Top-K 期望。 |

当前样例集已扩展为：

| 样例类别 | 数量 | 覆盖点 |
| --- | --- | --- |
| 告警实体 | 9 | 通信、证书、资源阈值、长 ID 告警、license 类告警。 |
| Query | 16 | 每条最多 1 个实体词；覆盖 ID+名称、歧义候选、短 ID 子串保护、no_match 和 not_required。 |

---

## 4 需求明细 - 功能性与非功能性需求分解

### 4.1 IR001 DVEntityLinking V1 增强

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户直接提出 |
| 需求编号 | IR-V1-001 |
| 标题 | V1 LLM 模式、真实样例、实体结构和检索算法增强 |
| 状态 | 需求分析草稿，需求评审处置修订中 |
| 处理人 | Codex |

**原始需求描述**：

进入 V1 迭代，关键需求包括：Web demo 支持切换和配置 LLM 模式；真实 Query 样例稍后提供；实体数据结构重点审视，用户会按类型给样例；检索算法重点规划和设计。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR-V1-001 |
| 需求标题 | DVEntityLinking V1 增强 |
| 需求类型 | 功能性需求 + 非功能性需求 |
| 优先级 | 高 |
| 目标版本 | V1 |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

V0 已完成实体链接 demo 的闭环和用户验收。V1 需要围绕真实使用链路增强 demo 的可操作性、样例真实性、实体结构合理性和检索算法能力。

**需求方案**：

- 以 Web demo LLM 模式切换作为可见入口。
- 以真实 Query 和实体样例作为 V1 需求/设计输入；当前启动样例支撑 `alarm` 类型、每条最多 1 个实体词、歧义候选、短 ID 子串保护、no_match 和 not_required 需求确认，不直接触发 runtime 代码实现。
- 以检索算法设计作为 V1 重点设计工作，优先定义无三方依赖的 Python 内存索引路线，再进入代码实现。

**实现细节**：

本阶段不直接定义实现细节。实现前必须完成 V1 需求评审、处置、闭环验证和功能设计闭环。

#### 4.1.2 需求场景

##### 4.1.2.1 UC-V1-001 Web demo 切换 LLM 模式

| 字段 | 内容 |
| --- | --- |
| 参与者 | Demo 用户 |
| 前置条件 | 本地 Web demo 可启动；可选存在 `config/llm.local.json` |
| 后置条件 | 用户能选择离线或 LLM 模式，并看到模式状态和结果 |

| 步骤 | 操作 | 系统响应 |
| --- | --- | --- |
| 1 | 用户打开 Web demo | 页面展示当前模式、LLM 是否可用和安全提示 |
| 2 | 用户选择 `offline_demo` | Query 使用 deterministic/Mock 路径 |
| 3 | 用户选择 `llm_enabled_demo` | Query 使用 LLM nominal path；失败时显示 degraded/error_code |

##### 4.1.2.2 UC-V1-002 提供真实 Query 样例

| 字段 | 内容 |
| --- | --- |
| 参与者 | 用户、需求分析者 |
| 前置条件 | 用户提供 Query 样例 |
| 后置条件 | 样例被分类、标注实体词 span 和 expected entity，并形成需求约束；当前启动样例已按最小字段契约记录 |

##### 4.1.2.3 UC-V1-003 按实体类型审视实体结构

| 字段 | 内容 |
| --- | --- |
| 参与者 | 用户、需求分析者 |
| 前置条件 | 用户按类型提供实体样例 |
| 后置条件 | 形成每类实体字段候选、必选/可选判断、关系建模约束和待确认事项；当前已确认 `alarm` 告警知识实体的最小字段策略 |

##### 4.1.2.4 UC-V1-004 规划检索算法

| 字段 | 内容 |
| --- | --- |
| 参与者 | 需求分析者、设计负责人 |
| 前置条件 | 至少有 V0 样例；真实样例到位后可修订 |
| 后置条件 | 明确候选召回、排序、解释、评测和降级策略 |

#### 4.1.3 DFX 需求

| DFX 类型 | 是否涉及 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | LLM 不可用时必须可降级到离线模式。 |
| 可用性 | 是 | Web demo 的模式切换和配置状态应直观可见。 |
| 可维护性 | 是 | 样例、实体结构和算法配置需可演进。 |
| 可测试性 | 是 | 默认自动化不能依赖真实 LLM 或本地私密配置。 |
| 安全性 | 是 | 本地真实配置、API key、base URL 和完整请求响应不得提交或写入文档。 |

#### 4.1.4 需求分解列表

##### 4.1.4.1 SR-V1-001 Web demo LLM 模式切换与配置

| 字段 | 内容 |
| --- | --- |
| 优先级 | 高 |
| 需求描述 | Web demo 支持选择 `offline_demo` 和 `llm_enabled_demo`，并展示当前模式、LLM 可用性、降级状态和错误码。 |
| 验收草案 | 页面或 API 可切换模式；离线模式不调用 LLM；LLM 模式在本地配置存在时可调用，失败时结构化降级。 |
| 约束 | 页面提供 mode selector，API 支持 mode 参数，启动配置保留默认模式；默认保持 `offline_demo`。页面可展示 mode、LLM enabled/degraded/error、provider 和 model alias；不得展示 API key、base URL 原文、完整请求响应或敏感日志。输出状态契约见 5.2。 |

##### 4.1.4.2 SR-V1-002 真实 Query 样例接收与标注

| 字段 | 内容 |
| --- | --- |
| 优先级 | 高 |
| 需求描述 | 建立真实 Query 样例接收、分类、期望实体标注和评测集形成规则。 |
| 验收草案 | 样例可按场景分类，包含 span、expected entity 和 expected status；当前启动样例 16 条 Query 可作为 V1 评测基线输入。 |
| 约束 | V1 每条 Query 最多 1 个实体词；必须覆盖正例、歧义例、无法匹配例和无需匹配例。 |

##### 4.1.4.3 SR-V1-003 实体数据结构审视

| 字段 | 内容 |
| --- | --- |
| 优先级 | 高 |
| 需求描述 | 基于用户按类型提供的实体样例，审视实体 ID、标准名、别名、属性、关系、状态、来源和证据字段。 |
| 验收草案 | 形成 `alarm` 实体结构分析和字段建议；V1 不覆盖其他实体类型。 |
| 约束 | runtime 枚举/loader 支持须等需求评审闭环后进入设计实现；其他实体类型留到后续迭代。 |

##### 4.1.4.4 SR-V1-004 检索算法规划与设计

| 字段 | 内容 |
| --- | --- |
| 优先级 | 高 |
| 需求描述 | 规划候选召回、排序打分、别名/名称匹配、歧义候选、短 ID 子串保护、解释和评测指标。 |
| 验收草案 | 形成检索算法设计基线，至少包含 Python 内存索引、完整 token 匹配、轻量 token 倒排、歧义候选返回、no_match/not_required 零误报约束和可选持久化路线。 |
| 约束 | 准确率和召回率同等重要；embedding/向量库/LLM rerank 不作为 V1 必需依赖。 |

##### 4.1.4.5 SR-V1-005 实体来源、运行时存储与索引

| 字段 | 内容 |
| --- | --- |
| 优先级 | 高 |
| 需求描述 | V1 `alarm` 告警知识实体通过配置文件预置，项目启动时加载；DV 运行时实例化实体通过接口获取的机制留到后续实体类型。 |
| 验收草案 | V1 需求基线明确配置预置和运行时接口来源边界；运行时检索优先使用 Python 内存索引，不引入三方检索组件。 |
| 约束 | 后续生产规模、持久化保留策略、DV 接口契约和多类型实体同步机制不属于 V1 必须实现范围。 |

## 5 输入输出契约草案

### 5.1 Web LLM 模式输入

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `query` | string | 用户 Query。 |
| `mode` | enum | `offline_demo` 或 `llm_enabled_demo`。 |
| `allow_fallback` | boolean | LLM 失败是否允许降级。 |

### 5.2 Web LLM 模式输出状态

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `requested_mode` | enum | 用户或 API 请求的模式：`offline_demo` 或 `llm_enabled_demo`。 |
| `effective_mode` | enum | 实际执行模式。LLM 失败且允许 fallback 时可降级为 `offline_demo`。 |
| `llm_enabled` | boolean | 当前请求是否尝试使用 LLM nominal path。 |
| `degraded` | boolean | 是否发生降级、错误或能力不可用。 |
| `fallback_allowed` | boolean | 本次请求是否允许 fallback。 |
| `fallback_used` | boolean | 是否实际使用 fallback。 |
| `error_code` | string/null | 结构化错误码；正常时为空。候选值包括 `llm_config_missing`、`llm_auth_error`、`llm_timeout`、`llm_http_error`、`llm_invalid_response`、`llm_schema_error`。 |
| `provider` | string/null | 可展示的 provider 摘要，不包含 base URL 原文或鉴权信息。 |
| `model_alias` | string/null | 可展示的模型别名或脱敏模型名。 |
| `result_source` | enum | `offline_index`、`llm`、`fallback_offline` 或 `none`。 |

`llm_enabled_demo + allow_fallback=false` 时，如果 LLM 配置缺失、鉴权失败、超时、HTTP 异常或返回 schema 异常，系统不得返回离线实体链接结果伪装成功；应返回结构化错误状态，`fallback_used=false`，`result_source=none`，并在 Web demo 中展示可理解的错误/降级原因。所有输出均不得包含 API key、base URL 原文、完整请求响应或敏感日志。

### 5.3 V1 样例文件级元数据

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `schema_version` | string | V1 启动样例必须声明 schema version。实体样例为 `v1.alarm_entity.2`，Query 样例为 `v1.alarm_query.2`。 |
| `entity_type_scope` | array | 实体样例固定为 `["alarm"]`。 |
| `entity_count` | integer | 实体样例必须等于 `entities` 实际数量。 |
| `query_count` | integer | Query 样例必须等于 `queries` 实际数量。 |
| `max_one_entity_mention_per_query` | boolean | Query 样例固定为 `true`。 |

V1 不再把 `data_layer`、`source`、`can_commit`、`sensitive_level` 作为样例契约字段。它们在早期设计中用于提交边界和溯源，但用户已确认本项目样例内容均可提交，继续暴露这些字段会干扰实体链接主线。

### 5.4 V1 启动样例契约

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `queries[].id` | string | V1 canonical Query ID 字段；不使用 `query_id`。 |
| `queries[].query` | string | V1 canonical Query 文本字段；不使用 `query_text`。 |
| `entities[].entity_type` | enum | V1 启动样例允许 `alarm`，表示告警知识/事实类实体。 |
| `entities[].canonical_name` | string | 统一标准名字段，不再使用 `entity_name` 作为主字段。 |
| `queries[].mentions` | array | 每条 Query 最多 1 个 mention；not_required 样例允许为空数组。 |
| `queries[].mentions[].span` | array[int, int] | 有 mention 时必填，0-based end-exclusive。 |
| `queries[].expected_entities[]` | array | Query 的最终实体链接期望；V1 仅要求 `entity_id`。 |
| `queries[].expected_status` | enum | `linked`、`ambiguous`、`no_match` 或 `not_required`。 |
| `queries[].negative_reason` | string | `expected_status` 为 `no_match` 或 `not_required` 时必填。 |

### 5.5 V1 检索和存储契约草案

| 项 | 要求 |
| --- | --- |
| 实体来源 | `alarm` 知识实体通过配置文件预置并在项目启动时加载。 |
| 运行时存储 | V1 demo 优先使用 Python 内存索引。 |
| 基础索引 | 告警号精确索引、数字别名精确索引、规范化名称/别名索引、轻量 token 倒排索引。 |
| 短 ID 保护 | 禁止裸 substring 高置信匹配；`51` 不应命中 `ALM-151` 或 `ALM-51020`。 |
| 歧义处理 | 一个实体词命中多个实体时返回 `ambiguous` 候选，不强制选择。 |
| 负例处理 | `no_match` 表示出现实体形态但不应命中；`not_required` 表示 Query 无实体链接需求，二者都不应产生实体误匹配。 |
| 可选后续 | SQLite FTS5 可作为后续本地持久化方案；V1 不新增三方检索组件。 |

#### 5.5.1 预置数据加载和校验契约

| 项 | 要求 |
| --- | --- |
| 默认实体样例路径 | `samples/real/entity_examples.json`。 |
| 默认 Query 评测路径 | `samples/real/query_samples.json`，仅作为 V1 评测和演示输入，不代表全量生产 Query。 |
| schema version | 实体样例使用 `v1.alarm_entity.2`，Query 样例使用 `v1.alarm_query.2`。 |
| 启动校验 | 缺失文件、非法 JSON、重复 `entity_id`、重复高置信告警号别名、非 `alarm` 类型、span 与文本不一致、expected entity 引用不存在均应产生结构化验证错误。 |
| 失败语义 | V1 demo 不应静默加载部分损坏的预置样例；无法加载预置实体时应进入 degraded/error 状态并阻止误链接。 |

### 5.6 V1 评测计算契约

| 项 | 要求 |
| --- | --- |
| Top-K | V1 默认 `K=5`；评测前按 `entity_id` 去重，只保留同一实体第一次出现的位置。 |
| linked pass/fail | `expected_status=linked` 时，Top-1 `entity_id` 必须等于唯一期望实体。 |
| ambiguous pass/fail | `expected_status=ambiguous` 时，Top-5 去重候选必须覆盖全部 `expected_entities`，返回状态必须保留为 `ambiguous`。 |
| no_match pass/fail | `expected_status=no_match` 时，候选实体列表必须为空；任何实体候选均计为 false positive。 |
| not_required pass/fail | `expected_status=not_required` 时，应在实体链接前绕过候选召回；任何实体候选均计为 false positive。 |
| precision | 以 Query 级误链接计算；no_match/not_required 的任何候选、linked Top-1 错误均计入 false positive。 |
| recall | 以 Query 级期望命中计算；linked Top-1 命中和 ambiguous recall@5 覆盖全部期望实体计为召回成功。 |

## 6 V1 验收草案

| 类别 | 最小要求草案 |
| --- | --- |
| Web LLM 模式 | 能在 Web/API 层选择离线或 LLM 模式，并显示模式、降级和错误信息。 |
| 安全边界 | 不提交真实配置、API key、base URL 和完整请求响应。 |
| Query 样例 | 16 条 Query 已完成分类、span 标注和 expected entity 标注；每条最多 1 个实体词，覆盖 linked、ambiguous、no_match 和 not_required。 |
| 实体结构 | 9 个 `alarm` 告警知识实体已确认最小字段策略；V1 不覆盖其他实体类型。 |
| 检索算法 | 输出算法设计基线，包含内存索引、完整 token 匹配、歧义返回和短 ID 子串保护。 |
| 检索评测 | 准确率和召回率同等重要；linked 样例要求 Top-1 命中，ambiguous 样例要求 recall@5 覆盖全部期望候选，no_match/not_required 样例要求零误报。 |
| 自动化 | 默认回归仍必须不依赖真实 LLM 和本地私密配置。 |

## 7 风险和待确认事项

| 风险/问题 | 状态 | 影响 |
| --- | --- | --- |
| 真实 Query 样例覆盖边界 | 已部分缓解 | 当前已有 16 条启动样例，但 V1 明确不覆盖多实体 Query。 |
| 实体类型覆盖边界 | 已确认 | V1 只覆盖 `alarm`；其他实体类型留到后续迭代。 |
| LLM Web 配置可见性 | 已确认 | 只展示 mode、LLM 状态、provider 和 model alias；不展示敏感配置。 |
| 检索评测指标 | 已确认 | 准确率和召回率同等重要；负例和无需匹配样例必须纳入验收。 |

## 8 当前结论

V1 需求分析、独立需求评审、评审处置和独立闭环验证已完成。当前样例结构确认结论是：V1 只覆盖 `alarm` 告警知识实体类型，实体 ID 保留内部 ID，告警字段采用最小字段策略，样例集包含 9 个实体和 16 条 Query；Query 标注采用 `id/query + mentions + expected_entities`，每条最多 1 个实体词，有 mention 时 span 必填；检索和运行时存储采用 Python 内存索引优先，不引入三方检索组件，SQLite FTS5 仅作为后续可选方案。V1 需求评审闭环验证结论为 closed with recorded residual risk；下一步可进入 V1 功能设计，功能设计需承接 HTTP/UI/evaluator 残余风险。

## 附录 A 参考资料

| 编号 | 资料名称 | 来源 |
| --- | --- | --- |
| A1 | V1 关闭记录 | [../../releases/V1.md](../../releases/V1.md) |
| A2 | 当前用户决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| A3 | 当前数据契约 | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| A4 | V1 需求评审记录 | [IR-DVEntityLinking-v1-requirements-review-record.md](./IR-DVEntityLinking-v1-requirements-review-record.md) |
| A5 | DV 背景和真实内容规则 | [../../DV_CONTEXT.md](../../DV_CONTEXT.md) |

## 附录 B 相关文件

| 编号 | 文件名称 | 版本/状态 |
| --- | --- | --- |
| B1 | `samples/real/entity_examples.json` | `v1.alarm_entity.2`，最小字段可提交样例 |
| B2 | `samples/real/query_samples.json` | `v1.alarm_query.2`，最小字段可提交样例 |
| B3 | [IR-DVEntityLinking-v1-requirements-review-input.md](./IR-DVEntityLinking-v1-requirements-review-input.md) | V1 需求评审输入包 |
| B4 | [IR-DVEntityLinking-v1-requirements-review-record.md](./IR-DVEntityLinking-v1-requirements-review-record.md) | V1 需求评审记录 |

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V1 |
| 创建日期 | 2026-05-26 |
| 最近更新 | 2026-06-01 |
| 作者 | Codex |
| 状态 | V1 验收反馈处置修订中 |
| 版本 | V1.5-draft |

## 评审记录

| 评审日期 | 评审方式 | 评审结论 | 状态 |
| --- | --- | --- | --- |
| 2026-05-31 | 两个 no-context/sealed subagent 独立只读评审 | Ready with findings；无 P0，有 P1/P2/P3 | 处置中 |
