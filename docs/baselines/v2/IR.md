# DigitalView-SW DVEntityLinking V2 需求分析文档

---

> 文档治理说明：本文是 V2 IR 主输出件，按版本保留。V2 当前处于需求分析启动阶段；本文不代表功能设计、代码实现或验收关闭结论。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V2.0-draft | 2026-06-01 | Codex | 根据用户确认启动 V2，明确多类型实体、数据预处理、运行时接口 Mock、LLM-based 方法和前端演示增强需求。 |
| V2.1-draft | 2026-06-01 | Codex | 根据用户补充要求，将 KPI 拆分为三类子类型，将网元拆分为 `ne_type` 和 `ne_name`，并收紧别名规则为默认空且必须显式标注。 |
| V2.2-draft | 2026-06-01 | Codex | 根据用户确认固化 V2 启动样例，保留 KPI/网元候选，补充 `Network quality monitoring`，确认 V2 必须支持英文多 mention Query。 |
| V2.3-draft | 2026-06-01 | Codex | 根据 V2 IR 独立评审处置，同步样例已确认状态，并补充多 mention、`partial` 和评测语义要求。 |
| V2.4 | 2026-06-01 | Codex | 根据 no-context/sealed 闭环验证结论更新状态为需求评审闭环已通过，可作为 V2 功能设计输入。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 多类型实体 | Multi-type Entities |
| 数据预处理 | Data Preprocessing |
| 运行时接口 Mock | Runtime Interface Mock |
| 分层分类 NER | Layered and Classified NER |
| LLM 实体链接 | LLM-based Entity Linking |
| 网元类型 | Network Element Type |
| 网元名称 | Network Element Name |
| KPI 测量任务 | KPI Measurement Task |
| KPI 测量对象 | KPI Measurement Object |
| KPI 测量指标 | KPI Measurement Type Key |
| 演示工作台 | Demo Workbench |

### Abstract 摘要

**中文摘要**：

本文档定义 DVEntityLinking V2 的需求分析草稿。V2 在 V1 alarm-only 验收关闭的基础上，启动多实体类型、运行时接口 Mock、KPI 数据挖掘、分层分类 NER、LLM-based 实体识别/链接和前端演示增强。用户已明确：实体结构字段暂不升级，任何字段/关系/schema 改动必须先确认；V2 网元相关实体拆分为可预置的 `ne_type` 和运行时实例化的 `ne_name`；KPI 类实体拆分为 `kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`，其中 `kpi_meas_objects` 本轮先忽略；新增 KPI/网元类实体的 `aliases` 默认必须为空，别名只能特殊标注并经确认，不得由预处理自动生成；V2 启动样例已确认并落入 `samples/real/v2_entity_examples.json` 和 `samples/real/v2_query_samples.json`；V2 必须支持多 mention Query，补充 Query 全部使用英文；运行时接口 Mock 作为独立 SR，因为后续可能被真实 DV 接口整体替换；前端采用方案 C，即运维工作台基础 + LLM 交互式高亮/解释，但不得过度前端化。

**English Abstract**：

This document defines the V2 requirement analysis draft for DVEntityLinking. Based on the accepted V1 alarm-only baseline, V2 starts multi-type entity support, runtime interface mocking, KPI data mining, layered/classified NER, LLM-based entity recognition/linking, and a demo-focused frontend enhancement. The entity fields must not be upgraded without explicit user confirmation. V2 separates network-element entities into `ne_type` and `ne_name`, and separates KPI entities into `kpi_task_name`, `kpi_meas_objects`, and `kpi_meas_type_key`. Aliases for new KPI/NE classes default to empty and must be explicitly confirmed instead of generated automatically. V2 startup queries are English and must support multiple mentions.

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
| KPI | Key Performance Indicator | 关键性能指标 |
| Mock | Mock Interface/Data | 模拟接口或模拟数据 |

---

## 1 引言

### 1.1 目的

本文档用于明确 DVEntityLinking V2 的需求范围、非范围、实体类型扩展、数据来源、LLM-based 方法、前端演示增强和后续评审门控。

预期读者：

- V2 需求评审者。
- V2 功能设计负责人。
- V2 代码实现和测试设计负责人。
- DVKnowledge 样例挖掘和运行时 Mock 数据提供者。

### 1.2 范围

#### 需求范围内

| 产品/服务 | 说明 |
| --- | --- |
| V2 实体类型扩展 | 在 V1 `alarm` 基础上新增 `ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`。 |
| 数据预处理 | 统一管控预置数据、DVKnowledge 挖掘、样例规范化、显式别名标注、去重和校验；不得自动生成别名。 |
| 运行时接口 Mock | 通过文件读取模拟 DV 运行时接口，支撑 `ne_name` 和可能的 KPI 运行时数据。 |
| KPI 数据挖掘 | 从 `D:\workspace\DVKnowledge\memory\dv` 挖掘预置或预定义测量任务名称、测量对象和测量指标，具体内容必须再确认。 |
| 网元类型挖掘 | 从 DVKnowledge 挖掘可预置 `ne_type`，例如 `cbs.billing.adapterapp`、`onlinecharging_docker`。 |
| 分层分类 NER | 随实体类型增加，先做类型路由/分类，再做类型内 mention 识别和归一化。 |
| LLM-based 方法 | V2 重点验证 LLM 在意图判断、实体类型分类、mention 抽取、候选解释和 rerank 中的作用。 |
| 前端演示增强 | 采用方案 C：运维工作台式布局 + LLM 交互式高亮/解释，用于更好演示项目能力。 |

#### 需求范围外

| 产品/服务 | 说明 |
| --- | --- |
| 实体结构升级 | V2 启动阶段不升级实体结构；如需新增字段、关系或类型专属 schema，必须先经用户确认。 |
| 真实 DV 接口接入 | V2 先做文件驱动 Mock，不直接调用真实 DV 生产接口。 |
| 真实 DV 写操作 | 不做自动修复、派单、告警确认、变更或生产写操作。 |
| 生产级前端产品化 | 前端只服务演示和调试，不建设完整商业化运维平台。 |
| 三方检索基础设施强依赖 | 默认继续少依赖策略；是否引入外部检索组件需另行确认。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| 数据预处理 | 将预置配置、DVKnowledge 挖掘结果和运行时 Mock 数据统一转换为项目实体目录可消费结构的过程。 |
| 运行时接口 Mock | 用本地文件模拟 DV 运行时接口返回，保留未来整体替换为真实接口的边界。 |
| `ne_type` | 网元类型类实体，一般可预置，可从 DVKnowledge 挖掘；用户示例包括 `cbs.billing.adapterapp`、`onlinecharging_docker`。 |
| `ne_name` | 网元名称/实例类实体，来源为运行时接口 Mock；用户示例包括 `CBS_1_cbpmdb_b2fc41cbb389(FI01)`、`container(access-12345)`、`CloudHost-VM-1-1-927344`。 |
| `kpi_task_name` | KPI 测量任务名称，例如 `DCC error code num V6`、`Kafka Monitor`。 |
| `kpi_meas_objects` | KPI 测量对象，往往是实例化实体；本轮启动样例先忽略。 |
| `kpi_meas_type_key` | KPI 测量指标，例如 `CPU Usage`。 |
| 显式别名标注 | V2 新增 KPI/网元类实体的 `aliases` 默认都为空；任何别名都必须特殊标注并经确认。 |
| 分层分类 NER | 先判断 Query 是否需要链接、候选实体类型和实体词类别，再进入对应类型的识别与链接。 |
| 方案 C | 前端参考 SigNoz 风格的运维工作台，并引入 LLM 交互式高亮/解释能力；只作为 demo 增强方向。 |

---

## 2 系统总体说明

V2 从 V1 的 `alarm` only demo 进入多类型实体链接 demo，但仍坚持本地可控、少依赖、可评测和可替换原则。实体结构沿用当前最小实体契约：`entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`。本轮新增的是类型拆分，不新增实体字段；任何新增字段、关系、类型专属属性或 schema 版本升级都必须先确认。对新增 KPI/网元类实体，`aliases` 字段必须存在但默认为空数组，预处理不得自动构造别名。

V2 运行链路：

```text
Preset config and DVKnowledge references
  -> data preprocessing
  -> unified entity catalog

Runtime mock files
  -> runtime interface mock
  -> data preprocessing
  -> unified entity catalog

Query
  -> need-linking classifier
  -> entity-type routing
  -> type-specific mention extraction
  -> candidate retrieval
  -> LLM-assisted explanation/rerank
  -> link result and demo presentation
```

V2 的数据来源被拆为两类：

| 来源 | V2 用途 | 约束 |
| --- | --- | --- |
| 配置文件预置 | 固化知识和较稳定实体，包含 V1 `alarm`、经确认的 `ne_type`、`kpi_task_name` 和 `kpi_meas_type_key`。 | 可提交内容必须经确认；结构不升级；别名默认空。 |
| 运行时接口 Mock | 模拟 DV 启动时拉取 `ne_name`、可选 `kpi_meas_objects` 和部分 KPI 运行时数据。 | Mock 独立成 SR；后续可被真实 DV 接口整体替换。 |

---

## 3 需求总体描述

### 3.1 用户痛点

- V1 只覆盖 `alarm`，不能展示实体类型增加后的分类识别、跨类型候选和数据来源差异。
- 实体来源需要区分稳定知识预置和 DV 运行时实例化数据，现有 demo 尚未体现启动时拉取和加工流程。
- KPI 类型不能笼统建模，需要区分测量任务名称、测量对象和测量指标；网元也需要区分可预置的网元类型和运行时实例化的网元名称。
- LLM 目前主要是模式切换和补充路径，V2 需要把 LLM-based 方法作为能力重点验证。
- 当前 Web 页面偏简陋，不利于展示多类型实体、mention、候选、解释和 LLM 链路。

### 3.2 预期价值

- 支撑 `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key` 的统一链接 demo；`kpi_meas_objects` 可在挖掘不到时暂缓。
- 建立可替换的运行时接口 Mock 边界，为未来真实 DV 只读接口接入降低改造成本。
- 通过数据预处理模块统一管理预置、挖掘、Mock 输入和校验，避免每类实体各自散落实现。
- 让 LLM 在多类型 NER、候选解释和消歧中产生可观察价值，同时保留离线 fallback。
- 前端以更清晰的运维工作台方式展示 Query、mention、候选、实体详情、来源和 LLM 摘要。

### 3.3 V2 启动样例策略

| 样例方向 | 当前状态 | V2 要求 |
| --- | --- | --- |
| `alarm` | V1 已有 9 个实体和 16 条 Query | 保持 V1 基线，不升级结构。 |
| `ne_type` | 启动样例已确认；后续可继续从 DVKnowledge 增补候选 | 一般可预置；首批候选包含 `cbs.billing.adapterapp`、`onlinecharging_docker`；别名默认空。 |
| `ne_name` | 启动样例已确认；本轮通过文件 Mock/样例模拟运行时实例 | 来源为运行时接口 Mock；首批候选包含用户确认的 3 个实例；别名默认空。 |
| `kpi_task_name` | 启动样例已确认；后续可继续从 DVKnowledge 增补候选 | 表示测量任务名称，首批包含 `DCC error code num V6`、`Kafka Monitor` 和 `Network quality monitoring` 等；别名默认空。 |
| `kpi_meas_objects` | 本轮忽略 | 表示测量对象，往往是实例化实体；V2 启动样例先不纳入。 |
| `kpi_meas_type_key` | 启动样例已确认，用户要求全部保留 | 表示测量指标，例如 `CPU Usage`；别名默认空。 |
| Query | V1 覆盖 alarm-only | V2 应补充跨类型、负例、无需匹配、歧义和 LLM 辅助识别样例。 |

当前已确认 V2 启动样例：

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `samples/real/v2_entity_examples.json` | 16 个新增实体样例，覆盖 5 个 `kpi_task_name`、6 个 `kpi_meas_type_key`、2 个 `ne_type`、3 个 `ne_name`；`kpi_meas_objects` 本轮忽略。 | 已确认，可提交。 |
| `samples/real/v2_query_samples.json` | 11 条英文 Query，覆盖多 mention linked、partial、no_match 和 not_required；每条最多 2 个 mention。 | 已确认，可提交。 |

---

## 4 需求明细 - 功能性与非功能性需求分解

### 4.1 IR-V2-001 DVEntityLinking V2 多类型 LLM-based 实体链接增强

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户直接提出 |
| 需求编号 | IR-V2-001 |
| 标题 | V2 多类型实体、运行时 Mock、LLM-based 方法和前端演示增强 |
| 状态 | 需求评审闭环已通过 |
| 处理人 | Codex |

**原始需求描述**：

用户确认 V2 阶段原则上同意项目建议，并补充要求：实体结构暂时不需要升级，如涉及改动必须确认；KPI 类型需要区分 `kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`；补充可预置的网元类型 `ne_type`；网元名称/实例作为 `ne_name`；运行时接口用读取文件的 Mock 模拟；实体类型增加后 NER 要考虑分层、分类；V2 重点是 LLM-based 方法；前端采用方案 C，但不要过度前端化；需求拆分中数据预处理统一管控相关内容，运行时接口 Mock 作为独立 SR；新增 KPI/网元类实体的别名必须特殊标注且默认空，不能乱给。用户进一步确认：`kpi_meas_type_key` 全部保留，`kpi_meas_objects` 本轮先忽略，`ne_type` 和 `ne_name` 全部保留，V2 必须支持多 mention Query，补充 Query 全部换成英文；`kpi_task_name` 在原候选基础上增加一个不同类型任务名 `Network quality monitoring`。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR-V2-001 |
| 需求标题 | DVEntityLinking V2 多类型 LLM-based 实体链接增强 |
| 需求类型 | 功能性需求 + 非功能性需求 |
| 优先级 | 高 |
| 目标版本 | V2 |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

V1 已关闭 alarm-only 实体链接 demo。V2 需要开始面对真实 DV 场景中更常见的多实体类型来源：稳定知识预置、运行时实例化数据和 KPI 性能对象，并验证 LLM-based 方法在多类型识别和链接中的价值。

**需求方案**：

- 以数据预处理作为统一入口，承接预置配置、DVKnowledge 挖掘、运行时 Mock 输出和实体目录校验。
- 以运行时接口 Mock 独立 SR 模拟 DV 启动时拉取实体数据，便于未来替换为真实接口。
- 以分层分类 NER 处理多类型实体识别，避免把所有实体词交给单一匹配器。
- 以 LLM-based 方法验证 mention 抽取、类型判断、候选解释和 rerank。
- 以方案 C 改造 Web demo 展示，但目标仍是演示实体链接能力，而不是建设完整前端平台。

**实现细节**：

本文不定义代码级实现。实现前必须完成 V2 IR 独立评审、评审处置、闭环验证以及后续 SR 功能设计闭环。

#### 4.1.2 需求场景

##### 4.1.2.1 UC-V2-001 启动时构建多类型实体目录

| 字段 | 内容 |
| --- | --- |
| 参与者 | Demo 启动者、数据预处理模块 |
| 前置条件 | 预置配置存在；运行时 Mock 文件存在或可降级 |
| 后置条件 | 形成包含 `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key` 以及可选 `kpi_meas_objects` 的统一实体目录或结构化错误 |

##### 4.1.2.2 UC-V2-002 通过 Mock 接口模拟 DV 运行时实体拉取

| 字段 | 内容 |
| --- | --- |
| 参与者 | Runtime mock、数据预处理模块 |
| 前置条件 | 本地 Mock 文件提供网元实例或 KPI 运行时数据 |
| 后置条件 | Mock 输出可被预处理模块消费；接口边界可未来替换 |

##### 4.1.2.3 UC-V2-003 使用 LLM 进行分层分类 NER

| 字段 | 内容 |
| --- | --- |
| 参与者 | Web/API 用户、LLM adapter、NER 模块 |
| 前置条件 | 用户输入 Query；可选存在本地 LLM 配置 |
| 后置条件 | 输出是否需要实体链接、候选实体类型、mention、置信度和降级状态 |

##### 4.1.2.4 UC-V2-004 在 Web demo 中展示多类型链接结果

| 字段 | 内容 |
| --- | --- |
| 参与者 | Demo 用户 |
| 前置条件 | Web demo 已启动；实体目录可用 |
| 后置条件 | 用户能查看 Query 高亮、mention 摘要、候选、实体详情、来源和 LLM 摘要 |

#### 4.1.3 DFX 需求

| DFX 类型 | 是否涉及 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 运行时 Mock 或 LLM 不可用时必须结构化降级，不得误链接。 |
| 可用性 | 是 | 前端需要更清晰地展示多类型实体和 LLM 链路，但不做过度产品化。 |
| 可维护性 | 是 | 数据预处理、运行时 Mock 和 LLM 方法需模块边界清晰，便于后续替换。 |
| 可测试性 | 是 | 默认自动化仍需可离线运行；LLM live 测试作为条件补证。 |
| 安全性 | 是 | 真实 LLM 配置、真实 DV payload、完整请求响应日志不得提交。 |

#### 4.1.4 需求分解列表

| SR | 标题 | 类型 | 责任模块 | 说明 |
| --- | --- | --- | --- | --- |
| SR-V2-A01 | 数据预处理与实体目录统一管控 | 功能 SR | data preprocessing、catalog | 统一管理预置数据、DVKnowledge KPI/网元类型挖掘、样例规范化、显式别名标注、去重和校验。 |
| SR-V2-A02 | 运行时接口 Mock | 功能 SR | runtime mock adapter | 文件驱动模拟 DV 运行时接口，支撑 `ne_name` 和可选 KPI 运行时数据，未来可整体替换。 |
| SR-V2-A03 | 分层分类 NER 与 mention 规范化 | 功能 SR | NER router、type-specific recognizer | 判断是否需要链接、候选实体类型、mention 和类型内规范化。 |
| SR-V2-A04 | LLM-based 抽取、分类、解释和 rerank | 功能 SR | LLM adapter、prompt/schema、fallback | V2 重点能力；要求 schema 校验、错误降级和离线 fallback。 |
| SR-V2-A05 | 多类型实体链接与跨类型消歧 | 功能 SR | entity linker、status resolver | 支持 `alarm`、`ne_type`、`ne_name` 和 KPI 子类型的候选融合、歧义保留和状态判定。 |
| SR-V2-A06 | 多类型索引、检索与存储策略 | 技术 SR | index、retrieval、storage | 保持少依赖，优先内存索引，规划规模、类型数量和后续持久化路线。 |
| SR-V2-A07 | Web demo 演示工作台增强 | 功能 SR | Web UI/API projection | 采用方案 C，突出 Query、mention、候选、实体详情、LLM 摘要和样例目录。 |
| SR-V2-A08 | V2 评测验收与安全边界 | 非功能 SR | evaluator、test、artifact hygiene | 覆盖多类型、负例、召回、准确率、LLM 对比和敏感信息边界。 |

详细 SR 分解见 [IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md)。

---

## 5 输入输出契约草案

### 5.1 V2 实体类型范围

| 实体类型 | 来源 | V2 处理策略 |
| --- | --- | --- |
| `alarm` | V1 预置样例 | 继续使用 V1 基线，不升级结构。 |
| `ne_type` | 预置配置 + DVKnowledge 挖掘 | 表示网元类型，可预置；候选需确认后进入 catalog。 |
| `ne_name` | 运行时接口 Mock | 表示网元名称/实例，从文件读取模拟运行时接口，预处理后进入统一 catalog。 |
| `kpi_task_name` | 预置配置 + DVKnowledge 挖掘 | 表示测量任务名称；候选需确认后进入 catalog。 |
| `kpi_meas_objects` | 运行时接口 Mock 或后续挖掘 | 表示测量对象，往往是实例化实体；本轮启动样例先忽略，后续纳入需再确认样例和验收口径。 |
| `kpi_meas_type_key` | 预置配置 + DVKnowledge 挖掘 | 表示测量指标；候选需确认后进入 catalog。 |

V2 启动阶段沿用实体最小字段：`entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`。如功能设计发现必须新增字段、关系或类型专属属性，应回到需求确认。新增 KPI/网元类实体的 `aliases` 默认必须为空；任何别名必须通过样例确认清单特殊标注，不得自动从名称拆词、缩写或路径中生成。

### 5.2 V2 Query 和 Mention

| 项 | 要求 |
| --- | --- |
| Query 类型 | 覆盖 `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key`，并保留 no_match 和 not_required；`kpi_meas_objects` 可后续补充。 |
| mention 数量 | V2 必须支持多 mention；启动样例每条 Query 最多 2 个 mention，功能设计需明确扩展上限、输出结构和评测口径。 |
| Query 级状态 | V2 启动样例允许 `linked`、`partial`、`no_match`、`not_required`；`partial` 表示同一 Query 中至少一个 mention 可链接、至少一个 mention 不匹配或待降级处理。 |
| mention 级状态 | mention 结果需保留各自 `linked`、`no_match`、`ambiguous` 或降级/错误语义，避免 Query 级状态掩盖局部失败。 |
| 类型路由 | NER 输出必须包含候选实体类型或无法判断原因。 |
| LLM 输出 | 必须经 schema 校验后才能进入链接链路；非法输出必须降级或返回结构化错误。 |

### 5.3 运行时接口 Mock

| 项 | 要求 |
| --- | --- |
| 输入 | 本地文件，内容按实体类型分组。 |
| 输出 | 面向数据预处理模块的结构化记录。 |
| 错误 | 文件缺失、非法 JSON、字段缺失、类型不支持、重复记录等必须结构化返回。 |
| 替换性 | 业务逻辑不得依赖文件读取细节；后续真实 DV 接口应能替换 Mock adapter。 |

### 5.4 LLM 配置和输出边界

- 默认自动化仍不依赖真实 LLM。
- `llm_enabled_demo` 可以使用本地 `config/llm.local.json`，但敏感配置不得提交。
- Web/API 可展示模型别名、是否启用、是否降级和摘要解释，不展示 API key、base URL 原文、完整请求或完整响应。
- LLM 输出必须可追踪到结构化字段，不得把自然语言解释直接当作实体链接事实。

---

## 6 V2 验收草案

| 类别 | 最小要求草案 |
| --- | --- |
| 实体范围 | 支持 `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key`；`kpi_meas_objects` 可暂缓；实体字段结构不升级。 |
| 数据预处理 | 能统一处理预置配置、DVKnowledge 挖掘候选和运行时 Mock 输出，并产生校验结果。 |
| 运行时 Mock | 文件驱动 Mock 可模拟 `ne_name` 和可选 KPI 运行时数据；错误可结构化暴露。 |
| 别名规则 | 新增 KPI/网元类实体 `aliases` 默认空；别名必须特殊标注并经确认，不得自动生成。 |
| 分层分类 NER | 能判断是否需要链接、候选实体类型和 mention；错误或不确定时可降级。 |
| LLM-based 方法 | LLM 可参与抽取、分类、解释和 rerank；离线 fallback 和 schema 校验可用。 |
| 链接结果 | 多类型候选、歧义、`partial`、no_match、not_required 语义清晰；Query 级状态不得掩盖 mention 级局部失败，不因召回制造误匹配。 |
| 多 mention 验收 | 启动样例中的多 mention Query 必须可自动评测；`partial` pass/fail、mention-level precision/recall 和 negative false positive 需在功能设计/测试设计中固化。 |
| 跨类型歧义 | V2 最终评测需覆盖跨类型歧义，或在测试设计中记录延期理由和残余风险；启动样例不等同于最终验收全集。 |
| 前端演示 | 页面能展示当前样例实体、mention 简要信息、候选/详情、LLM 状态和多类型来源。 |
| 评测指标 | precision 和 recall 同等重要；必须充分覆盖无法匹配和不需要匹配场景。 |
| 安全边界 | 不提交真实 API key、token、base URL、完整 DV payload 或完整 LLM 日志。 |

---

## 7 风险和后续确认事项

| 风险/问题 | 状态 | 影响 |
| --- | --- | --- |
| KPI 候选内容 | 启动样例已确认；后续增补待确认 | 当前 5 个 `kpi_task_name` 和 6 个 `kpi_meas_type_key` 可作为 V2 启动样例；后续从 DVKnowledge 增补候选仍需用户确认。 |
| 网元类型和网元名称内容 | 启动样例已确认；后续增补待确认 | 当前 2 个 `ne_type` 和 3 个 `ne_name` 可作为 V2 启动样例；后续 Mock 内容或真实 DV payload 不得隐式固化。 |
| 多 mention 评测口径 | 已确认需求，待功能/测试设计固化 | V2 必须支持多 mention；`partial`、mention-level pass/fail、precision/recall 公式需在 SR 和评测器设计中定义。 |
| 跨类型歧义样例 | 待测试设计补齐或显式延期 | 启动 Query 覆盖 linked、partial、no_match、not_required；最终 V2 验收还需覆盖跨类型歧义或记录非阻塞延期。 |
| LLM 质量阈值 | 待设计 | 需要区分默认离线验收和条件 LLM live 补证。 |
| 前端增强边界 | 已确认方向 | 采用方案 C，但只服务演示，不做过度前端产品化。 |

---

## 8 当前结论

V2 已启动需求分析。当前已确认的硬约束是：实体字段结构暂不升级；V2 使用 `ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key` 作为新增类型拆分；新增 KPI/网元类实体别名默认空且必须特殊标注；数据预处理统一管控预置、DVKnowledge 挖掘和样例规范化；运行时接口 Mock 独立成 SR；NER 采用分层分类思路；V2 重点验证 LLM-based 方法；前端采用方案 C 进行演示增强但避免过度投入。

V2 启动样例已经确认；本轮 IR 独立评审、处置和 no-context/sealed 闭环验证已完成，闭环结论为 closed with recorded residual risk。本文可作为 V2 功能设计输入。残余风险为跨类型歧义、LLM 降级、多 mention precision/recall 公式需在后续功能设计和测试设计中固化。

## 附录 A 参考资料

| 编号 | 资料名称 | 来源 |
| --- | --- | --- |
| A1 | 当前项目总览 | [../../PROJECT.md](../../PROJECT.md) |
| A2 | 当前决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| A3 | 当前数据契约 | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| A4 | DV 背景上下文 | [../../DV_CONTEXT.md](../../DV_CONTEXT.md) |
| A5 | V1 关闭记录 | [../../releases/V1.md](../../releases/V1.md) |
| A6 | DVKnowledge context 目录 | `D:\workspace\DVKnowledge\memory\dv` |
| A7 | SigNoz 前端参考 | [https://github.com/SigNoz/signoz](https://github.com/SigNoz/signoz) |
| A8 | OpenGenerativeUI 前端参考 | [https://github.com/CopilotKit/OpenGenerativeUI](https://github.com/CopilotKit/OpenGenerativeUI) |
| A9 | Tambo 前端参考 | [https://github.com/tambo-ai/tambo](https://github.com/tambo-ai/tambo) |

## 附录 B 相关文件

| 编号 | 文件名称 | 版本/状态 |
| --- | --- | --- |
| B1 | `samples/real/entity_examples.json` | V1 `alarm` 基线样例，V2 继续复用 |
| B2 | `samples/real/query_samples.json` | V1 Query 基线样例，V2 继续作为回归输入 |
| B3 | [IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md) | V2 IR 阶段 SR 分解草稿 |
| B4 | `samples/real/v2_entity_examples.json` | V2 新增实体启动样例，已确认 |
| B5 | `samples/real/v2_query_samples.json` | V2 英文多 mention Query 启动样例，已确认 |

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V2 |
| 创建日期 | 2026-06-01 |
| 最近更新 | 2026-06-01 |
| 作者 | Codex |
| 状态 | 需求评审闭环已通过，可作为功能设计输入 |
| 版本 | V2.4 |

## 评审记录

| 评审日期 | 评审方式 | 评审结论 | 状态 |
| --- | --- | --- | --- |
| 2026-06-01 | sealed 本地独立需求评审 | Ready for disposition；无 P0，发现多 mention/`partial` 语义和样例确认状态同步问题 | 处置完成 |
| 2026-06-01 | no-context/sealed 独立闭环验证 | Closed with recorded residual risk；跨类型歧义、LLM 降级和多 mention 指标公式进入后续设计 | 已闭环 |
