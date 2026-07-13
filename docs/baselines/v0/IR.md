# DigitalView-SW DVEntityLinking V0 需求分析文档

---

> 文档治理说明：本文是 V0 IR 主输出件，按版本保留。原过程性确认、评审和闭环文件已合并到 [../../releases/V0.md](../../releases/V0.md) 与 [../../current/DECISIONS.md](../../current/DECISIONS.md)；需要原始过程细节时通过 Git 历史追溯。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V0.1 | 2026-05-25 | Codex | 基于项目初始化信息和 GUI 确认结果形成需求分析初稿，作为独立需求评审输入候选。 |
| V0.2 | 2026-05-25 | Codex | 根据独立需求评审和 P1 处置确认，补充数据保存边界、LLM 验收模式、最小输出契约、Mock 溯源、Top-K 和样例覆盖验收底线。 |
| V0.3 | 2026-05-25 | Codex | 根据第二轮闭环验证结论更新文档状态为需求评审闭环已通过。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 实体链接 | Entity Linking |
| 实体词表 | Entity Vocabulary |
| 实体识别 | Named Entity Recognition |
| 实体消歧 | Entity Disambiguation |
| 运维 Copilot | Operations Copilot |
| 故障 Agent | Fault Agent |
| 相似度检索 | Similarity Retrieval |
| OpenAI 兼容接口 | OpenAI-compatible API |

### Abstract 摘要

**中文摘要**：

本文档定义 DVEntityLinking V0 demo 的需求范围。V0 目标是构建面向 DV 运维 Copilot 和故障 Agent 的实体链接基础能力，覆盖 Mock 实体目录构建、Query 中 NER、实体匹配与链接、实体查询、Top-K 相似度检索、简易 Web UI 和可选本地运行记录。V0 采用 L0 抽象合成 Mock 为默认数据层级，允许后续使用用户提供的脱敏样例和模拟 DV 接口返回；未确认的真实 DV 字段、接口和能力必须标记为 TBD。Qwen3.6-27B 通过 OpenAI-compatible API 作为 V0 的 LLM 主路径方向，用于 NER、实体匹配和实体消歧等难点，同时必须提供确定性或 Mock 降级路径，保证 demo 在 LLM 不可用时仍可运行。

**English Abstract**：

This document defines the V0 requirements for DVEntityLinking, a demo-oriented entity linking foundation for DV Operations Copilot and Fault Agent workflows. V0 covers mock entity catalog construction, NER over user queries, entity matching and linking, entity lookup, top-k similarity retrieval, a lightweight web UI, and local run records. The default data strategy is L0 synthetic mock data, with user-approved sanitized samples and simulated DV interface responses allowed later. Unconfirmed real DV fields, interfaces, or capabilities must remain TBD. Qwen3.6-27B via an OpenAI-compatible API is the intended LLM main path for NER, matching, and disambiguation, while deterministic or mock degradation is required so the demo remains runnable when the LLM is unavailable.

---

## List of Abbreviations 缩略语清单

| 缩略语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| DV | DigitalView-SW | 面向运营商领域的电信软件网管系统 |
| IR | Issue Requirement | 需求项 |
| SR | Sub Requirement | 子需求 |
| UC | Use Case | 用例 |
| NER | Named Entity Recognition | 命名实体识别 |
| LLM | Large Language Model | 大语言模型 |
| API | Application Programming Interface | 应用程序接口 |
| KPI | Key Performance Indicator | 关键性能指标 |
| Top-K | Top K Results | 返回排序前 K 个结果 |
| DFX | Design for X | 面向可靠性、可测试性、安全性等质量属性的设计 |

---

## 目录

<!-- 自动生成目录 -->

---

## 1 引言

### 1.1 目的

本文档用于明确 DVEntityLinking V0 demo 的需求范围、非范围、系统上下文、核心用例、输入输出契约、Mock 和 LLM 策略、异常降级行为、验收底线和后续评审输入。

预期读者：

- 需求评审者。
- 后续功能设计负责人。
- 后续代码实现和测试设计负责人。
- DV 运维 Copilot、故障 Agent 相关能力规划人员。

### 1.2 范围

#### 需求范围内

| 产品/服务 | 说明 |
| --- | --- |
| DVEntityLinking V0 demo | 面向 DV 运维 Copilot 和故障 Agent 的实体链接 demo。 |
| Mock 实体目录 | 构建可加载的实体词表、标准名、别名、类型、描述和关系。 |
| Query 实体识别 | 从用户 Query 中识别实体提及，重点覆盖 NER。 |
| 实体匹配与链接 | 将实体提及匹配到标准实体，输出候选、置信度、消歧理由和无匹配原因。 |
| 实体查询 | 支持按实体 ID、名称或类型查询实体详情。 |
| 相似度检索 | 支持 Top-K 相似实体或相关实体检索。 |
| 简易 Web UI | 提供直观测试入口，支持加载样例、输入 Query、查看链接和检索结果。 |
| LLM 主路径和降级 | 使用 Qwen3.6-27B/OpenAI-compatible API 作为 NER、匹配和消歧主路径方向，同时提供确定性或 Mock 降级。 |
| 本地运行记录 | Demo 阶段允许本地保存用户 Query、实体链接中间结果和运行结果，不提交敏感配置或不受控生产数据。 |

#### 需求范围外

| 产品/服务 | 说明 |
| --- | --- |
| 真实 DV 生产接入 | V0 不直接接入真实 DV 生产环境。 |
| 写操作闭环 | V0 不做自动修复、派单、变更、确认告警等写操作。 |
| 未确认真实 DV 字段和接口 | 未经用户确认的真实 DV 字段、接口和能力不得写成需求事实。 |
| 生产级权限和向量库运维 | V0 不覆盖企业级权限、审计、租户隔离、生产级向量库容量和运维。 |
| 完整数据治理 | V0 不建设生产级实体治理、长期实体生命周期、全量数据同步和血缘治理。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| 实体 | 具有可被查询、链接或推理引用的 DV 运维对象，例如网元、告警、KPI、拓扑关系、知识条目或案例。 |
| 实体提及 | 用户 Query 或上下文文本中出现的实体名称、别名、缩写、编号或描述性表达。 |
| 标准实体 | 实体目录中经过归一化的实体记录，具有标准实体 ID、类型和标准名。 |
| 实体链接 | 将实体提及映射到一个或多个标准实体，并给出置信度、候选和解释的过程。 |
| 消歧 | 当一个实体提及可能对应多个标准实体时，结合类型、上下文、关系或 LLM 判断选择更合适实体的过程。 |
| L0 Mock | 抽象合成 Mock 数据，明显标注为 demo 数据，不代表真实 DV 事实。 |
| L1 Mock | 用户确认可使用的脱敏样例。 |
| L2 Mock | 本地模拟 DV 接口返回。 |
| L3 接入 | 真实 DV 只读接入；V0 不默认进入。 |

---

## 2 系统总体说明

DVEntityLinking V0 作为实体理解基础能力，位于用户 Query、运维 Copilot、故障 Agent 与实体数据/知识之间。V0 不是生产级实体中心，而是可演示、可测试、可评审的实体链接 demo。

### 2.1 上下文边界

```text
用户 Query / Agent 上下文
  -> NER 与实体提及识别
  -> 候选生成
  -> 实体匹配、链接和消歧
  -> 实体查询 / Top-K 相似度检索
  -> Copilot 或故障 Agent 可消费的结构化结果
```

### 2.2 首批实体类型

GUI 确认的 V0 首批实体类型：

| 实体类型 | V0 需求说明 |
| --- | --- |
| 网络资源/网元 | 用于表示 DV 运维资源对象，真实字段 TBD。 |
| 告警/事件 | 用于表示告警码、告警名称、事件或告警实例，真实字段 TBD。 |
| KPI/性能指标 | 用于表示性能指标、计数器或异常指标，真实字段 TBD。 |
| 拓扑/关系 | 用于表示实体之间的连接、依赖、归属或相关关系，真实字段 TBD。 |
| 知识/Runbook/案例 | 用于表示运维知识、处理指引和历史案例，真实字段 TBD。 |

### 2.3 首批 Query 场景

GUI 确认的 V0 Query 场景：

- 精确名称匹配。
- 别名/缩写匹配。
- 模糊匹配。
- 多实体 Query。
- 歧义消解。
- 查无结果降级。

### 2.4 数据与依赖策略

| 类别 | V0 策略 |
| --- | --- |
| 默认样例 | L0 抽象合成 Mock。 |
| 脱敏样例 | 允许使用用户提供的脱敏样例。 |
| 模拟接口 | 允许模拟 DV 接口返回。 |
| 真实 DV 字段 | 未确认前不允许写入需求事实，必须标记 TBD。 |
| LLM | Qwen3.6-27B/OpenAI-compatible API 为主路径方向。 |
| LLM 验收模式 | V0 必须提供可配置的 LLM nominal path；自动化基线测试必须在离线 deterministic/Mock 模式下通过；存在本地 LLM 配置时可执行真实 LLM smoke。 |
| LLM 失败 | 必须提供确定性或 Mock 降级，demo 仍可运行；输出必须标记 `degraded=true`、`status=degraded` 或 `status=dependency_failed`，并给出原因。 |
| 本地保存 | Demo 阶段允许本地保存 Query、链接中间结果、运行输出和用户明确提供的真实 DV artifact；未脱敏生产 payload 仅可保存到 git ignored 本地路径，不得提交、不得写入文档、不得作为默认样例。 |

---

## 3 需求总体描述

### 3.1 用户痛点

运维 Copilot 和故障 Agent 的任务通常涉及多个实体：网元、告警、KPI、拓扑、知识和历史案例。若缺少统一的实体链接能力，系统容易出现以下问题：

- 用户自然语言中的简称、别名和模糊表达难以映射到标准对象。
- Copilot 查询和 Agent 诊断链路对同一实体的引用不一致。
- 告警、KPI、拓扑和知识之间缺少统一的实体上下文。
- 无匹配、歧义匹配和依赖失败时缺少可解释降级。
- 后续实体检索、案例召回和证据链构建缺少可复用基础能力。

### 3.2 预期价值

V0 交付后应能证明：

- DV 智能任务可以通过统一实体链接结果消费实体上下文。
- LLM 可参与 NER、实体匹配和实体消歧等难点问题。
- 在 LLM 不可用或结果不确定时，系统仍能以确定性或 Mock 方式降级。
- 简易 Web UI 可支撑用户直观测试 Query、链接结果和相似度检索。
- 需求、样例、输出契约和验收用例可进入后续独立评审。

### 3.3 V0 当前确认与 TBD

| 事项 | 结论 |
| --- | --- |
| V0 定位 | 实体链接 demo，不做真实 DV 生产接入。 |
| Demo 形态 | 轻量 Web UI。 |
| 使用方优先级 | V0 以实体链接能力闭环为主，不以某一使用方为 gating；样例至少覆盖一条 Copilot 风格 Query 和一条故障 Agent 风格 Query；Demo UI 展示顺序在功能设计阶段确定。 |
| LLM 角色 | 必选 nominal path，重点处理 NER、实体匹配、实体消歧；自动化基线测试离线 deterministic/Mock 通过；有本地配置时执行真实 LLM smoke。 |
| Mock 策略 | V0 baseline 仅依赖 L0 抽象合成 Mock；L1 脱敏样例和 L2 模拟接口是可选增强，进入验收前需用户确认；样例和输出必须标记 `data_layer`/`source`。 |
| 数据保存 | Demo 阶段不重点做脱敏工程，允许未脱敏生产 payload 本地保存；但必须保存到 ignored 路径，不得提交 git、不得写入文档、不得作为默认样例，密钥、token、cookie、完整生产 payload、敏感配置和完整 LLM 日志不得提交。 |

### 3.4 最小可测试契约

本节定义 requirement-level 最小契约，供功能设计和自动化测试使用；不限定内部算法、数据结构实现或具体 Web API 形态。

#### 3.4.1 通用枚举和范围

| 名称 | 取值/范围 | 说明 |
| --- | --- | --- |
| `data_layer` | `L0_SYNTHETIC` / `L1_SANITIZED` / `L2_SIMULATED_INTERFACE` / `L3_REAL_READONLY` / `LOCAL_REAL_ARTIFACT` | 标记样例、实体、证据或输出来源层级。V0 baseline 只要求 `L0_SYNTHETIC`。 |
| `source` | 非空字符串 | 标记数据来源，例如 `mock_catalog`、`user_sanitized_sample`、`simulated_dv_api`、`local_real_dv_ignored`。 |
| `status` | `linked` / `ambiguous` / `no_match` / `degraded` / `dependency_failed` / `invalid_input` | 链接或检索结果的归一化状态。 |
| `confidence` | 0.0 到 1.0 | 实体链接置信度；越高代表越可信。 |
| `score` | 0.0 到 1.0 | 相似度检索分数；越高代表越相似。 |

#### 3.4.2 `EntityRecord` 最小字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `entity_id` | 是 | 标准实体 ID；在当前实体目录内唯一。 |
| `entity_type` | 是 | 首批类型之一：网络资源/网元、告警/事件、KPI/性能指标、拓扑/关系、知识/Runbook/案例。 |
| `canonical_name` | 是 | 标准名。 |
| `aliases` | 是 | 别名数组，可为空数组。 |
| `description` | 否 | 描述文本。 |
| `attributes` | 否 | 扩展属性对象；真实 DV 字段未确认前只能使用 Mock 字段或标记 TBD。 |
| `relations` | 否 | 关系数组，至少可表达关联实体 ID、关系类型和来源。 |
| `data_layer` | 是 | 数据层级。 |
| `source` | 是 | 数据来源。 |

#### 3.4.3 `EntityMention` 和 `LinkCandidate` 最小字段

| 对象 | 字段 | 必填 | 说明 |
| --- | --- | --- | --- |
| `EntityMention` | `text` | 是 | Query 中的实体提及文本。 |
| `EntityMention` | `span` | 否 | 起止位置；轻量 UI 可不强制展示，但测试样例可使用。 |
| `EntityMention` | `predicted_type` | 否 | NER 预测实体类型。 |
| `EntityMention` | `source` | 是 | `llm` / `deterministic` / `mock` 等。 |
| `LinkCandidate` | `entity_id` | 是 | 候选标准实体 ID。 |
| `LinkCandidate` | `canonical_name` | 是 | 候选标准名。 |
| `LinkCandidate` | `entity_type` | 是 | 候选实体类型。 |
| `LinkCandidate` | `confidence` | 是 | 0.0 到 1.0。 |
| `LinkCandidate` | `match_reason` | 是 | 候选原因，例如标准名匹配、别名匹配、语义相似、拓扑相关。 |
| `LinkCandidate` | `evidence` | 是 | 证据数组，可包含来源、片段、关系或分数。 |

#### 3.4.4 `EntityLinkResult` 最小字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `query` | 是 | 原始 Query。 |
| `status` | 是 | `linked`、`ambiguous`、`no_match`、`degraded`、`dependency_failed` 或 `invalid_input`。 |
| `mentions` | 是 | `EntityMention` 数组；多实体 Query 必须支持多个 mention。 |
| `linked_entity` | 条件必填 | `status=linked` 时必填；其他状态可为空。 |
| `candidates` | 是 | 候选数组；按 `confidence` 降序排列；无候选时为空数组。 |
| `confidence` | 条件必填 | 有链接或候选时必填。 |
| `disambiguation_reason` | 条件必填 | `linked` 或 `ambiguous` 时必填。 |
| `no_match_reason` | 条件必填 | `status=no_match` 时必填。 |
| `degraded` | 是 | 布尔值；发生 fallback 或依赖异常时为 `true`。 |
| `error_code` | 条件必填 | `degraded`、`dependency_failed`、`invalid_input` 时必填。 |
| `data_layer` | 是 | 结果所依据的最高风险数据层级。 |
| `source` | 是 | 结果来源摘要，例如 `llm+catalog`、`deterministic+catalog`、`mock_fallback`。 |

#### 3.4.5 `RetrievalResult` 和 Top-K 语义

| 字段/规则 | 要求 |
| --- | --- |
| 默认 K | 5 |
| 最大 K | 20 |
| 排序 | 按 `score` 降序排列；分数相同按 `entity_id` 稳定排序。 |
| 空结果 | 返回 `status=no_match` 或空 `items`，并给出 `no_match_reason`。 |
| `items[]` | 每项至少包含 `entity_id`、`canonical_name`、`entity_type`、`score`、`similarity_reason`、`source`、`data_layer`。 |
| 支持语义 | 名称/别名相似、语义相似、类型相同、拓扑相邻、历史案例相似。 |

#### 3.4.6 `RunRecord` 最小字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `run_id` | 是 | 本地运行 ID。 |
| `mode` | 是 | `offline_demo` / `llm_enabled_demo` / `mock_fallback`。 |
| `query` | 是 | 用户 Query；本地保存允许，但提交前需检查。 |
| `result` | 是 | 链接或检索结果摘要。 |
| `llm_used` | 是 | 是否调用 LLM。 |
| `degraded` | 是 | 是否发生降级。 |
| `created_at` | 是 | 运行时间。 |

### 3.5 V0 验收底线

| 类别 | 最小要求 |
| --- | --- |
| L0 实体样例 | 至少 20 个实体，覆盖全部 5 类首批实体；每类至少 2 个实体。 |
| Query 样例 | 至少 12 条 Query，覆盖精确名称、别名/缩写、模糊、多实体、歧义、查无结果六类场景。 |
| 使用方覆盖 | 至少 1 条 Copilot 风格 Query 和 1 条故障 Agent 风格 Query；V0 不以某一使用方为 gating。 |
| 检索样例 | 至少 5 条 Top-K 检索样例，覆盖名称/别名、语义、类型、拓扑相邻、历史案例相似。 |
| 降级样例 | 至少覆盖 LLM 超时/不可用、返回格式异常或 schema 异常、无匹配、歧义、依赖失败。 |
| 自动化基线 | 必须在 `offline_demo` 模式下不依赖真实 DV 和真实 LLM 通过。 |
| LLM smoke | 有本地 OpenAI-compatible 配置时执行，不作为离线自动化基线前置条件。 |

---

## 4 需求明细 - 功能性与非功能性需求分解

### 4.1 IR001 DVEntityLinking V0 实体链接 demo

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户直接提出 |
| 需求编号 | IR001 |
| 标题 | DV 实体链接 demo |
| 状态 | 需求评审闭环已通过 |
| 处理人 | Codex |
| 链接 | N/A |

**原始需求描述**：

构建 DV 实体链接 demo，支撑运维 Copilot 和故障 Agent 中所有涉及实体的任务，包括但不限于实体构建、实体词表、Query 实体匹配与链接、实体查询与相似度检索；项目基于 Python 3.12 实现，涉及真实 DV 的内容需要与用户确认 Mock 方式；项目考虑使用 Qwen3.6-27B 大模型，可提供 OpenAI 格式的 API 接口。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR001 |
| 需求标题 | DVEntityLinking V0 实体链接 demo |
| 需求类型 | 功能性需求 / 非功能性需求 |
| 优先级 | 高 |
| 目标版本 | V0 |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

DV 运维 Copilot 和故障 Agent 在查询、诊断、证据组织、知识检索和历史案例复用中都需要识别和引用实体。V0 通过 demo 形式验证实体目录、NER、实体匹配与链接、实体查询和相似度检索的最小闭环。

**需求方案**：

V0 建设一个 Python 3.12 项目，提供 Mock 数据加载、实体目录、Query 实体链接、实体查询、Top-K 相似度检索和轻量 Web UI。Qwen3.6-27B/OpenAI-compatible API 作为 LLM 主路径方向参与 NER、匹配和消歧，同时系统必须具备确定性或 Mock 降级路径。

**实现细节**：

本阶段不规定内部实现算法，但要求功能设计阶段明确模块边界、输入输出 Schema、LLM adapter、Mock adapter、降级语义、Web UI API、样例数据格式和测试策略。

#### 4.1.2 配套影响分析

| 配套项 | 影响说明 |
| --- | --- |
| 运维 Copilot | 后续可消费实体链接结果增强 Query 理解和实体上下文。 |
| 故障 Agent | 后续可消费实体链接结果增强告警、KPI、拓扑、知识和案例关联。 |
| LLM 配置 | 需要 OpenAI-compatible 配置样例和本地 ignored 配置策略。 |
| Mock 数据 | 需要构造 L0 抽象合成样例，并预留 L1/L2 扩展方式。 |
| Web UI | 需要简易页面支持 Query 输入、实体链接结果展示和检索测试。 |

#### 4.1.3 需求场景

##### 4.1.3.1 UC001 加载 Mock 实体目录

###### 4.1.3.1.1 用例信息

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC001 |
| 用例标题 | 加载 Mock 实体目录 |
| 参与者 | Demo 用户、系统 |
| 前置条件 | 存在 L0 Mock 实体样例 |
| 后置条件 | 系统可查询实体目录、别名和关系 |

###### 4.1.3.1.4 业务处理流程

| 步骤 | 操作 | 系统响应 |
| --- | --- | --- |
| 1 | 用户启动 demo | 系统加载 Mock 实体目录 |
| 2 | 系统校验样例结构 | 成功时进入可查询状态；失败时展示结构错误 |
| 3 | 用户打开 Web UI | UI 展示样例加载状态和实体数量摘要 |

###### 4.1.3.1.5 数据影响列表

| 数据项 | 操作类型 | 说明 |
| --- | --- | --- |
| Mock 实体目录 | 读取 | 从本地样例读取实体、别名、类型和关系 |
| 加载状态 | 创建 | 本地运行态或输出记录，可用于 demo 查看 |

##### 4.1.3.2 UC002 Query 实体匹配与链接

###### 4.1.3.2.1 用例信息

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC002 |
| 用例标题 | Query 实体匹配与链接 |
| 参与者 | Demo 用户、系统、LLM adapter |
| 前置条件 | Mock 实体目录已加载 |
| 后置条件 | 系统返回结构化实体链接结果 |

###### 4.1.3.2.4 业务处理流程

| 步骤 | 操作 | 系统响应 |
| --- | --- | --- |
| 1 | 用户在 Web UI 输入 Query | 系统接收 Query |
| 2 | 系统进行 NER | 识别实体提及；优先使用 LLM 主路径，失败时降级 |
| 3 | 系统生成候选实体 | 使用名称、别名、类型、上下文和关系生成候选 |
| 4 | 系统执行匹配与消歧 | 返回标准实体、候选、置信度、原因和证据 |
| 5 | 系统展示结果 | UI 展示链接结果、候选列表和无匹配/歧义提示 |

###### 4.1.3.2.5 数据影响列表

| 数据项 | 操作类型 | 说明 |
| --- | --- | --- |
| Query | 创建/读取 | Demo 阶段允许本地保存 |
| 实体链接结果 | 创建/读取 | 用于 UI 展示和测试断言 |
| LLM 请求响应摘要 | 创建/读取 | 仅本地开发显式开启且不提交完整日志 |

##### 4.1.3.3 UC003 实体查询与 Top-K 相似度检索

###### 4.1.3.3.1 用例信息

| 字段 | 内容 |
| --- | --- |
| UC 编号 | UC003 |
| 用例标题 | 实体查询与 Top-K 相似度检索 |
| 参与者 | Demo 用户、系统 |
| 前置条件 | Mock 实体目录已加载，至少存在可检索实体 |
| 后置条件 | 系统返回实体详情或相似实体列表 |

###### 4.1.3.3.4 业务处理流程

| 步骤 | 操作 | 系统响应 |
| --- | --- | --- |
| 1 | 用户选择或输入实体 | 系统查询实体详情 |
| 2 | 用户发起相似度检索 | 系统按名称/别名、语义、类型、拓扑相邻和历史案例相似等语义召回 Top-K |
| 3 | 系统展示结果 | UI 展示相似实体、分数、相似原因和来源 |

###### 4.1.3.3.5 数据影响列表

| 数据项 | 操作类型 | 说明 |
| --- | --- | --- |
| 实体详情 | 读取 | 返回标准实体、类型、别名和关系 |
| 相似度检索结果 | 创建/读取 | Demo 阶段可保存本地结果 |

#### 4.1.4 DFX 需求

##### 4.1.4.1 可靠性/可用性分析

- [x] 是否涉及
- 说明：LLM 不可用、超时、返回格式异常或 Mock 数据结构错误时，demo 不应整体崩溃，应展示明确降级或错误信息。

##### 4.1.4.2 可维护性/可测试性

- [x] 是否涉及
- 说明：实体目录、Query 样例、链接结果、相似度检索和降级场景应具备可自动化测试的输入输出契约。

##### 4.1.4.3 安全/可信/合规规范/隐私保护

- [x] 是否涉及
- 说明：用户确认 demo 阶段无需重点关注脱敏工程，允许未脱敏生产 payload 本地保存；但必须保存到 git ignored 路径，不得提交、不得写入文档、不得作为默认样例。V0 baseline 不依赖真实 DV 生产接入；密钥、token、cookie、完整生产 payload、敏感配置和完整 LLM 日志不得提交。

##### 4.1.4.4 其他 DFX 需求分析

| DFX 类型 | 是否涉及 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 支持 LLM 和数据依赖失败降级。 |
| 可用性 | 是 | Web UI 应能直观测试 Query、链接、查询和检索。 |
| 可维护性 | 是 | 样例、配置、adapter 和输出契约应清晰分离。 |
| 可测试性 | 是 | 至少覆盖加载样例、链接、查询、Top-K 检索和降级。 |
| 安全性 | 是 | 未脱敏生产 payload 仅允许本地 ignored 保存；不提交敏感配置、完整生产 payload和完整 LLM 日志。 |

#### 4.1.5 配套影响列表

| 配套系统/模块 | 影响描述 | 工作量 |
| --- | --- | --- |
| `src/dv_entity_linking/` | 新增实体目录、链接、检索、LLM adapter 和 Web 服务模块。 | 待设计评估 |
| `samples/mock/` | 新增 L0 Mock 实体目录和 Query 样例。 | 待设计评估 |
| `config/` | 新增 LLM 示例配置和本地 ignored 配置说明。 | 待设计评估 |
| `tests/` | 新增契约测试和实现级测试。 | 待设计评估 |
| Web UI | 新增简易测试页面。 | 待设计评估 |

#### 4.1.6 需求分解列表

##### 4.1.6.1 SR001 Mock 实体目录与实体词表

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR001 |
| 标题 | Mock 实体目录与实体词表 |
| 类型 | 功能 SR |
| 责任模块 | Entity Catalog |

**#需求背景#**：

实体链接需要标准实体集合作为链接目标。

**#需求价值#**：

为 Query 实体匹配、查询和相似度检索提供统一实体基础。

**#需求内容#**：

- 支持加载 L0 Mock 实体目录。
- 实体至少包含标准实体 ID、实体类型、标准名、别名、描述、来源、数据层级和关系。
- 首批实体类型覆盖网络资源/网元、告警/事件、KPI/性能指标、拓扑/关系、知识/Runbook/案例。
- Mock 数据必须明确标注为 demo 数据，实体和样例必须包含 `data_layer` 与 `source`。
- V0 baseline 仅要求 L0 抽象合成 Mock；L1/L2 作为可选增强，进入验收前必须有用户确认记录。

**#需求范围#**：

V0 使用本地文件或本地内存加载即可，不要求生产级实体同步。

**#约束条件#**：

真实 DV 字段未确认前必须标记 TBD；L2 模拟接口不得被描述为真实 DV 能力代表。

##### 4.1.6.2 SR002 Query NER 与实体提及识别

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR002 |
| 标题 | Query NER 与实体提及识别 |
| 类型 | 功能 SR |
| 责任模块 | Entity Extraction |

**#需求背景#**：

用户 Query 中的实体可能以标准名、别名、缩写、模糊描述或多实体组合出现。

**#需求价值#**：

让运维 Copilot 和故障 Agent 能够从自然语言中提取可链接实体。

**#需求内容#**：

- 支持精确名称、别名/缩写、模糊、多实体、歧义和查无结果场景。
- LLM 主路径应重点用于 NER 难点。
- LLM 不可用时必须有确定性或 Mock 降级，并在输出中标记降级状态和原因。

**#需求范围#**：

V0 关注 Query 级实体提及识别，不要求处理长文档级实体抽取。

**#约束条件#**：

NER 输出必须能被后续链接模块测试和复现，至少满足 `EntityMention` 最小字段要求。

##### 4.1.6.3 SR003 实体匹配、链接与消歧

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR003 |
| 标题 | 实体匹配、链接与消歧 |
| 类型 | 功能 SR |
| 责任模块 | Entity Linking |

**#需求背景#**：

一个实体提及可能对应多个候选实体，也可能没有候选。

**#需求价值#**：

提供可解释的标准实体链接结果，支撑下游任务稳定消费。

**#需求内容#**：

- 输出满足 `EntityLinkResult` 最小契约，包括标准实体 ID、实体类型、标准名、候选列表、置信度、消歧理由、来源/证据、无匹配原因、状态、降级标记和数据层级。
- 支持歧义消解和查无结果降级。
- LLM 主路径应参与匹配和消歧难点，失败时降级。

**#需求范围#**：

V0 以 demo 级别候选生成和消歧为目标，不要求生产级准确率。

**#约束条件#**：

链接结果必须可被自动化测试断言；候选必须按置信度降序排列，置信度范围为 0.0 到 1.0。

##### 4.1.6.4 SR004 实体查询与 Top-K 相似度检索

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR004 |
| 标题 | 实体查询与 Top-K 相似度检索 |
| 类型 | 功能 SR |
| 责任模块 | Retrieval |

**#需求背景#**：

实体链接结果需要进一步查询详情和召回相似实体，才能支撑 Copilot 和 Agent 的上下文扩展。

**#需求价值#**：

提供实体详情、相似实体和相关实体召回能力。

**#需求内容#**：

- 支持按实体 ID、名称或类型查询实体。
- 支持 Top-K 检索，默认 K=5，最大 K=20。
- 相似度语义覆盖名称/别名相似、语义相似、类型相同、拓扑相邻和历史案例相似。
- 返回分数、相似原因、来源和数据层级；分数范围为 0.0 到 1.0，按分数降序排列。

**#需求范围#**：

V0 不要求接入生产级向量库；可使用本地检索、轻量 embedding mock 或其他设计阶段确认的方式。

**#约束条件#**：

检索结果必须能解释排序原因；空结果必须给出无匹配原因。

##### 4.1.6.5 SR005 轻量 Web UI

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR005 |
| 标题 | 轻量 Web UI |
| 类型 | 功能 SR |
| 责任模块 | Web UI |

**#需求背景#**：

用户确认 V0 demo 形态为轻量 Web UI，支持直观测试。

**#需求价值#**：

降低演示和验收成本，便于观察 Query、候选、置信度、消歧理由和检索结果。

**#需求内容#**：

- 展示 Mock 数据加载状态。
- 支持输入 Query 并展示实体链接结果。
- 支持选择实体进行详情查询和 Top-K 相似度检索。
- 支持展示无匹配、歧义和依赖失败降级信息。

**#需求范围#**：

V0 只要求简易 UI，不要求生产级视觉设计、鉴权和多用户协作。

**#约束条件#**：

UI 不应隐藏错误和降级原因。

##### 4.1.6.6 SR006 LLM Adapter 与降级路径

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR006 |
| 标题 | LLM Adapter 与降级路径 |
| 类型 | 技术 SR |
| 责任模块 | LLM |

**#需求背景#**：

用户确认 Qwen3.6-27B 在 V0 中为必选主路径，OpenAI-compatible API 信息参考之前项目。

**#需求价值#**：

让 NER、实体匹配和实体消歧能够利用 LLM，同时避免外部依赖阻断 demo。

**#需求内容#**：

- 支持 OpenAI-compatible API 配置，配置项至少包括 base URL、模型名、API key 来源、超时和启用开关。
- 支持本地 ignored 配置，不提交 API key。
- 支持 mock adapter 或 deterministic fallback。
- LLM 请求响应完整日志仅允许本地开发显式开启且不提交。
- LLM 不可用或超时时，demo 仍可运行并展示降级信息。
- V0 必须实现可配置的 `llm_enabled_demo` nominal path；自动化基线测试必须在 `offline_demo` 模式下通过；有本地配置时可执行真实 LLM smoke。

**#需求范围#**：

V0 不要求支持所有 OpenAI API 特性；是否支持 tool calling、streaming 等在设计阶段确认，不作为 V0 baseline 验收前置条件。

**#约束条件#**：

配置示例不得包含真实凭据；LLM fallback 必须输出 `degraded=true`、状态和原因。

##### 4.1.6.7 SR007 本地运行记录与自动化验收

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR007 |
| 标题 | 本地运行记录与自动化验收 |
| 类型 | 技术 SR |
| 责任模块 | Evaluation / Tests |

**#需求背景#**：

V0 demo 需要能被评审和回放，不能只靠人工观察。

**#需求价值#**：

支撑需求评审、实现评审和测试设计闭环。

**#需求内容#**：

- 自动化测试至少覆盖加载 Mock 实体目录、Query 实体链接、候选和置信度、实体查询、Top-K 检索、无匹配/歧义/依赖失败降级。
- 自动化测试必须覆盖 3.5 中定义的 V0 验收底线。
- Demo 阶段允许本地保存 Query、链接中间结果、运行输出和用户明确提供的真实 DV artifact。
- 未脱敏生产 payload 仅允许保存到 git ignored 路径，不得提交、不得写入文档、不得作为默认样例。
- 输出文件不应包含密钥、token、cookie、完整生产 payload、完整 LLM 日志或敏感配置。

**#需求范围#**：

V0 不要求生产级评测平台。

**#约束条件#**：

测试必须能在没有真实 DV 接入、没有真实 LLM 接入的 `offline_demo` 模式下运行。

---

## 5 配套影响列表

| 序号 | 配套系统/模块 | 影响描述 | 责任方 | 工作量 |
| --- | --- | --- | --- | --- |
| 1 | Python 包 `dv_entity_linking` | 新增实体目录、抽取、链接、检索、LLM 和 Web 边界。 | 后续设计/实现 | 待评估 |
| 2 | Mock 样例 | 新增 L0 实体目录、Query 样例和期望结果。 | 后续设计/实现 | 待评估 |
| 3 | Web UI | 新增简易 UI 支持直观测试。 | 后续设计/实现 | 待评估 |
| 4 | LLM 配置 | 新增 OpenAI-compatible 示例配置和本地 ignored 配置。 | 后续设计/实现 | 待评估 |
| 5 | 自动化测试 | 新增需求契约和实现级测试。 | 后续测试设计 | 待评估 |
| 6 | 本地真实 DV artifact ignored 路径 | 新增或使用 git ignored 路径保存用户明确提供的本地真实 DV artifact，不进入提交和默认样例。 | 后续设计/实现 | 待评估 |

---

## 6 系统用例列表

| 序号 | UC 编号 | 用例名称 | 所属 IR | 优先级 |
| --- | --- | --- | --- | --- |
| 1 | UC001 | 加载 Mock 实体目录 | IR001 | 高 |
| 2 | UC002 | Query 实体匹配与链接 | IR001 | 高 |
| 3 | UC003 | 实体查询与 Top-K 相似度检索 | IR001 | 高 |

---

## 附录

### 附录 A 参考资料

- 项目总览：[../../PROJECT.md](../../PROJECT.md)
- DV 背景与实体链接上下文：[../../DV_CONTEXT.md](../../DV_CONTEXT.md)
- V0 关闭记录：[../../releases/V0.md](../../releases/V0.md)
- 当前决策台账：[../../current/DECISIONS.md](../../current/DECISIONS.md)
- V0 需求评审记录：[IR-DVEntityLinking-requirements-review-record.md](./IR-DVEntityLinking-requirements-review-record.md)
- V0 需求评审处置结论：见 [../../releases/V0.md](../../releases/V0.md)。
- DV IR 模板：`D:\workspace\analysis_and_design\templates\IR-templates.md`

### 附录 B 需求评审输入包建议

后续独立需求评审建议读取以下输入：

| 类型 | 文档 |
| --- | --- |
| 需求分析文档 | `docs/baselines/v0/IR.md` |
| 项目总览 | `docs/PROJECT.md` |
| DV 背景 | `docs/DV_CONTEXT.md` |
| 用户确认 | `docs/current/DECISIONS.md` |
| V0 决策 | `docs/releases/V0.md` |

评审重点建议：

- V0 范围和非范围是否足以支撑后续功能设计。
- LLM nominal path、offline_demo 和真实 LLM smoke 的边界是否清楚。
- Demo 阶段真实 DV artifact 和未脱敏 production payload 的本地保存策略是否清楚。
- 首批使用方不作为 V0 gating 是否可接受。
- 输出契约和验收底线是否可测试。

### 附录 C 文档信息和评审记录

| 字段 | 内容 |
| --- | --- |
| 文档名称 | DigitalView-SW DVEntityLinking V0 需求分析文档 |
| 当前版本 | V0.3 |
| 当前状态 | 需求评审闭环已通过，结论为 closed with recorded residual risk，可作为功能设计输入 |
| 最近用户确认 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| 评审记录 | [IR-DVEntityLinking-requirements-review-record.md](./IR-DVEntityLinking-requirements-review-record.md) |
| 处置记录 | [IR-DVEntityLinking-requirements-review-disposition.md](./IR-DVEntityLinking-requirements-review-disposition.md) |
