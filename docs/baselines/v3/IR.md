# DigitalView-SW DVEntityLinking V3 需求分析文档

---

> 文档治理说明：本文是 V3 IR 主输出件草稿，按版本保留。V3 已由用户确认启动，V2 遗留视觉 before 证据问题搁置，不作为 V3 启动阻塞。本文只做需求分析和需求分解，不代表功能设计、代码实现、评审结论或验收关闭。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V3.0-draft | 2026-06-24 | Codex | 根据用户确认启动 V3，明确两层存储、Redis 接口 Mock、高斯数据库接口 Mock 和 NER 详细设计/必要重构为 V3 重点。 |
| V3.1-draft | 2026-06-25 | Codex | 根据 V3 GUI 决策确认记录关闭 Human Decision Gate，固化 Redis 单值冲突 fail-closed、Redis key 范围、高斯最小字段、NER 内部 schema、LLM 角色和样例策略，并根据需求评审处置统一日期、治理和 Redis key 来源措辞。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 两层存储 | Two-layer Storage |
| Redis 缓存 Mock | Redis Cache Mock |
| 高斯数据库 Mock | GaussDB Mock |
| 实体词索引 | Entity-word Index |
| 结构化实体存储 | Structured Entity Store |
| NER 重构 | NER Refactoring |
| 分层 NER | Layered NER |
| 实体链接 | Entity Linking |

### Abstract 摘要

**中文摘要**：

本文档定义 DVEntityLinking V3 的需求分析草稿。V3 搁置 V2 视觉验收遗留问题，进入新版本需求阶段。V3 重点包括两层存储和 NER 详细设计：实体词到实体 ID 的 KV 对通过 Redis 缓存接口 Mock 提供，结构化实体数据通过高斯数据库接口 Mock 提供并支持按实体 ID 查询；NER 是 V3 重中之重，需要重新梳理 Query 到 mention、类型、候选、实体 ID 的完整链路，必要时允许重构现有抽取、链接、catalog 和存储边界。V3 默认仍采用本地可控 Mock，不接真实 Redis、高斯数据库或真实 DV 生产接口。

**English Abstract**：

This document defines the V3 requirement analysis draft for DVEntityLinking. V3 defers the remaining V2 visual acceptance issue and starts a new version. The main V3 focus areas are two-layer storage and a detailed NER design. Entity-word to entity-id KV pairs are provided through a Redis interface mock, while structured entity data is provided through a GaussDB interface mock with entity-id lookup. NER is the primary focus and may require refactoring existing extraction, linking, catalog, and storage boundaries. V3 remains locally controllable and does not connect to real Redis, GaussDB, or production DV interfaces by default.

---

## List of Abbreviations 缩略语清单

| 缩略语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| DV | DigitalView-SW | 面向运营商领域的电信软件网管系统 |
| IR | Issue Requirement | 需求项 |
| SR | Sub Requirement | 子需求 |
| UC | Use Case | 用例 |
| NER | Named Entity Recognition | 命名实体识别 |
| KV | Key-Value | 键值对 |
| DB | Database | 数据库 |
| LLM | Large Language Model | 大语言模型 |

---

## 1 引言

### 1.1 目的

本文用于明确 DVEntityLinking V3 的需求范围、非范围、两层存储边界、Redis/Gauss 接口 Mock 约束、NER 详细设计目标和后续评审门控。

预期读者：

| 角色 | 关注点 |
| --- | --- |
| 需求评审者 | V3 范围、非范围、用户确认项和设计输入是否清晰。 |
| 功能设计负责人 | 存储接口、NER pipeline、模块边界和重构策略。 |
| 代码实现负责人 | 后续可替换接口、现有代码迁移风险和测试入口。 |
| 测试设计负责人 | Redis/Gauss Mock、NER 准确性、降级和兼容性验收。 |

### 1.2 范围

#### 需求范围内

| 产品/服务 | 说明 |
| --- | --- |
| V3 版本启动 | 用户明确要求搁置 V2 遗留问题，进入 V3。 |
| 两层存储 | 实体词到实体 ID 的 KV 对走 Redis 缓存接口 Mock；结构化实体数据走高斯数据库接口 Mock。 |
| Redis 接口 Mock | key 是实体词，来源为 `canonical_name` + 经确认 `aliases`，不自动生成别名；value 是单实体 ID；用于 NER 和链接链路的快速实体词命中。 |
| 高斯数据库接口 Mock | 存储结构化实体数据，至少支持按实体 ID 查询。 |
| 存储抽象和可替换边界 | 业务逻辑依赖接口契约，不依赖 Mock 文件、内存结构或具体实现细节。 |
| NER 详细设计 | 作为 V3 重点，细化 Query 预处理、need-linking、mention 识别、类型分类、实体词规范化、候选生成、错误和降级。 |
| 必要重构 | 若现有 `EntityExtractor`、`EntityLinker`、`CatalogRepository` 或 Web/API projection 难以承载 V3 NER 和存储边界，允许在设计闭环后重构。 |
| V1/V2 回归兼容 | V3 不能破坏已关闭的 V1 能力；V2 已落地的多类型样例可作为 V3 回归输入。 |

#### 需求范围外

| 产品/服务 | 说明 |
| --- | --- |
| V2 视觉遗留收口 | V2 `AC-V2-FE-VIS-008` before 同场景截图或替代口径搁置，不作为 V3 前置条件。 |
| 真实 Redis 接入 | V3 当前只要求 Redis 接口 Mock，不连接真实 Redis 服务。 |
| 真实高斯数据库接入 | V3 当前只要求高斯数据库接口 Mock，不连接真实 GaussDB 服务。 |
| 真实 DV 生产接口和生产数据 | 未经确认的真实 DV 字段、payload、接口、凭据和日志不得进入仓库。 |
| 真实 DV 写操作 | 不做自动修复、派单、告警确认、变更或生产写操作。 |
| 代码实现立即启动 | V3 代码实现必须等待 IR 评审、处置、闭环，以及后续 SR 功能设计评审闭环。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| 实体词 | Query 或实体目录中可用于查找实体的词面表达。V3 Redis key 使用实体词。 |
| Redis 缓存 Mock | 模拟 Redis KV 能力的本地接口实现，提供实体词到实体 ID 的查询。 |
| 高斯数据库 Mock | 模拟 GaussDB 结构化存储的本地接口实现，提供按实体 ID 查询实体记录。 |
| 两层存储 | 第一层为实体词 KV 缓存，第二层为结构化实体数据存储。 |
| NER pipeline | 从 Query 输入到 mention、类型、候选和实体 ID 的识别流程。 |
| fail-closed | 数据、接口、schema 或依赖异常时不输出伪实体、不误链接，返回结构化错误或 no_match/降级状态。 |

---

## 2 系统总体说明

V3 的核心变化是把当前主要由 catalog 内存结构承担的实体词索引和实体详情存储，拆成两层可替换接口：

```text
Entity samples / confirmed data
  -> preprocessing and validation
  -> GaussDB mock structured entity store
  -> Redis mock entity-word cache

Query
  -> NER pipeline
  -> entity-word normalization
  -> Redis mock lookup: entity_word -> entity_id
  -> GaussDB mock lookup: entity_id -> structured entity
  -> candidate scoring / linking / explanation
  -> API and Web projection
```

V3 不要求立刻引入真实外部服务。Redis 和高斯均以接口 Mock 形式进入系统，设计必须保证未来能替换为真实 Redis/GaussDB 适配器。当前代码中的 `CatalogRepository`、`EntityExtractor`、`EntityLinker` 和 `EntityLinkingService` 可作为迁移基础，但 V3 NER 和存储边界允许重新划分。

---

## 3 需求总体描述

### 3.1 用户痛点

| 痛点 | V3 影响 |
| --- | --- |
| 现有 catalog 同时承担实体目录、词面索引和详情查询职责 | 难以表达真实系统中缓存和结构化数据库分层。 |
| V2 运行时 Mock 仍偏 confirmed-sample startup slice | V3 需要更像真实运行架构，但仍保持本地可控。 |
| NER 当前以 deterministic literal spans 和 LLM schema fallback 为主 | 多类型、多 mention、实体词缓存、结构化详情查询接入后，需要更明确的 NER pipeline 和边界。 |
| 词面命中、类型分类、候选生成和链接聚合耦合 | V3 必须让 NER 详细设计成为后续重构依据。 |

### 3.2 预期价值

- 用 Redis Mock 表达实体词快速查找能力，用 GaussDB Mock 表达结构化实体详情查询能力。
- 为未来真实 Redis/GaussDB 接入预留接口边界，避免 demo 代码和存储实现强耦合。
- 通过 NER 详细设计明确分层步骤、输入输出、错误语义和可测试目标。
- 支持必要重构，让实体识别、存储查询和实体链接职责更清晰。
- 保留 V1/V2 自动化回归，避免 V3 架构改造破坏已关闭能力。

---

## 4 需求明细 - 功能性与非功能性需求分解

### 4.1 IR-V3-001 两层存储和 NER 重构增强

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户直接提出 |
| 需求编号 | IR-V3-001 |
| 标题 | V3 两层存储和 NER 详细设计 |
| 状态 | 需求评审处置闭环已通过，可进入功能设计 |
| 处理人 | Codex |

**原始需求描述**：

用户要求搁置 V2 遗留问题，进入 V3。V3 重点考虑两件事：

1. 两层存储，KV 对走 Redis 缓存，key 是实体词，value 是实体 ID，Redis 接口 Mock；结构化数据存高斯数据库，高斯接口 Mock，支持按实体 ID 查询。
2. NER 部分详细设计，是本项目重中之重，必要时重构。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR-V3-001 |
| 需求标题 | DVEntityLinking V3 两层存储和 NER 重构增强 |
| 需求类型 | 功能性需求 + 技术架构需求 |
| 优先级 | 高 |
| 目标版本 | V3 |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

DVEntityLinking 已经具备 V1 alarm-only 和 V2 多类型、多 mention、Web demo、LLM fallback 等基础能力。V3 开始从 demo 样例能力转向更接近真实实体链接服务的架构：实体词命中通过缓存，实体详情通过结构化数据库，NER 作为 Query 到实体 ID 的核心智能层。

**需求方案**：

- 定义 `EntityWordCache` 抽象，V3 默认实现为 Redis 接口 Mock，提供实体词到实体 ID 查询。
- 定义 `StructuredEntityStore` 抽象，V3 默认实现为高斯数据库接口 Mock，提供按实体 ID 查询实体结构化数据。
- 定义 V3 NER pipeline，从 Query 清洗、need-linking、mention detection、type classification、entity-word normalization 到 storage-backed candidate lookup。
- 保留离线 deterministic 回归路径，LLM 可作为分类、抽取、解释或 rerank 辅助，但不能成为默认自动化唯一依赖。
- 必要时重构现有模块，使 `CatalogRepository` 不再是唯一数据读取入口，`EntityExtractor` 和 `EntityLinker` 的职责重新划分。

**实现细节**：

本文不定义代码级实现。V3 IR 独立评审、处置和闭环已完成；代码实现仍需等待 V3 SR 功能设计独立评审、处置和闭环。

#### 4.1.2 需求场景

##### 4.1.2.1 UC-V3-001 通过 Redis Mock 按实体词查询实体 ID

| 字段 | 内容 |
| --- | --- |
| 参与者 | NER pipeline、Redis Mock |
| 前置条件 | 实体词 KV 缓存已从确认样例或预处理结果构建 |
| 后置条件 | 输入实体词返回实体 ID，未命中返回结构化 miss，不产生伪实体 |

##### 4.1.2.2 UC-V3-002 通过高斯 Mock 按实体 ID 查询结构化实体

| 字段 | 内容 |
| --- | --- |
| 参与者 | Linker、GaussDB Mock |
| 前置条件 | 结构化实体数据已加载到高斯 Mock |
| 后置条件 | 输入实体 ID 返回实体记录；缺失、重复或 schema 错误 fail-closed |

##### 4.1.2.3 UC-V3-003 NER 从 Query 识别实体词并完成存储查询

| 字段 | 内容 |
| --- | --- |
| 参与者 | Web/API 用户、NER pipeline、存储接口 |
| 前置条件 | 用户输入 Query；两层存储 Mock 可用 |
| 后置条件 | 输出 mention、实体词、实体 ID、实体详情、候选和 Query/mention 级状态 |

##### 4.1.2.4 UC-V3-004 存储或 NER 异常时结构化降级

| 字段 | 内容 |
| --- | --- |
| 参与者 | Service、NER pipeline、storage adapters |
| 前置条件 | Redis Mock 或高斯 Mock 出现缺失、schema 错误或查询异常 |
| 后置条件 | API/Web 输出结构化错误或降级状态，不误链接、不泄露敏感信息 |

#### 4.1.3 DFX 需求

| DFX 类型 | 是否涉及 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | Redis/Gauss Mock 不可用、未命中或数据不一致时必须结构化降级。 |
| 可用性 | 是 | Web/API 需能展示 V3 存储来源、NER 阶段和错误状态。 |
| 可维护性 | 是 | 存储接口和 NER pipeline 必须模块边界清晰，支持必要重构。 |
| 可测试性 | 是 | Redis/Gauss Mock、NER 分层结果、cache miss、entity not found、V1/V2 回归必须可自动化测试。 |
| 安全性 | 是 | 不接真实 Redis/Gauss 凭据，不提交真实 DV payload、真实连接串或完整 LLM 请求响应。 |

#### 4.1.4 需求分解列表

| SR | 标题 | 类型 | 责任模块 | 优先级 |
| --- | --- | --- | --- | --- |
| SR-V3-A01 | V3 存储契约和数据模型 | 技术 SR | storage contract、models | 高 |
| SR-V3-A02 | Redis 实体词缓存接口 Mock | 功能 SR | redis mock adapter、entity-word index | 高 |
| SR-V3-A03 | 高斯结构化实体存储接口 Mock | 功能 SR | gauss mock adapter、entity store | 高 |
| SR-V3-A04 | 两层存储集成和一致性策略 | 技术 SR | service orchestration、preprocessing | 高 |
| SR-V3-A05 | NER pipeline 详细设计和重构策略 | 功能 SR | NER router、recognizer、normalizer、linker boundary | 最高 |
| SR-V3-A06 | V3 评测、回归和安全边界 | 非功能 SR | evaluator、tests、artifact hygiene | 高 |

详细 SR 分解见 [IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md)。

---

## 5 输入输出契约草案

### 5.1 Redis Mock KV 契约

| 字段 | 要求 |
| --- | --- |
| key | 实体词，来源为 `canonical_name` + 经确认 `aliases`；不自动生成别名。功能设计需定义大小写、空白、标点、中文/英文归一化规则。 |
| value | 实体 ID。用户确认保持单实体 ID；若同一实体词映射多个实体，冲突数据加载 fail-closed，不进入链接链路。 |
| miss | 返回结构化 miss，不得制造候选。 |
| error | Mock 文件缺失、非法格式、重复 key、重复/不存在 entity ID 必须结构化报错。 |
| sensitive boundary | 不包含真实 Redis host、port、password、token 或连接串。 |

### 5.2 高斯 Mock 实体查询契约

| 字段 | 要求 |
| --- | --- |
| lookup key | `entity_id` |
| result | 至少包含当前最小实体字段：`entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`。 |
| optional fields | V3 初始不纳入类型专属结构化字段；后续扩展需另行确认。 |
| miss | entity ID 不存在时返回结构化 miss。 |
| error | schema 错误、重复 ID、字段缺失、数据层未确认必须 fail-closed。 |
| sensitive boundary | 不包含真实 GaussDB host、port、user、password、JDBC/ODBC 连接串或生产 payload。 |

### 5.3 NER 输出契约草案

| 字段 | 要求 |
| --- | --- |
| query_status | `linked`、`partial`、`ambiguous`、`no_match`、`not_required`、`dependency_failed`、`invalid_input` 等。 |
| mentions[] | 每个 mention 至少包含 `text`、`span`、`normalized_text`、`entity_word_key`、`candidate_type`、`source`、`confidence`。 |
| storage_lookup | 每个 mention 需记录 Redis lookup 状态和可安全展示的 Gauss lookup 状态。 |
| candidates[] | 候选实体 ID、类型、名称、得分、来源和理由。 |
| errors[] | 结构化错误，不展示真实连接信息或敏感内容。 |

---

## 6 验收草案

| 类别 | 最小要求草案 |
| --- | --- |
| V3 启动状态 | V2 遗留视觉 before 证据搁置，不阻塞 V3；V3 从需求分析开始。 |
| Redis Mock | 可加载实体词到实体 ID 的 KV 数据；支持命中、miss、重复 key、非法 value、引用不存在 ID 的 fail-closed 测试。 |
| 高斯 Mock | 可加载结构化实体数据；支持按实体 ID 查询；支持 miss、重复 ID、字段缺失和 schema 错误测试。 |
| 两层集成 | NER 命中的实体词先查 Redis Mock，再用实体 ID 查高斯 Mock；任一层失败不得误链接。 |
| NER 重点 | 形成详细 NER 设计，覆盖 need-linking、mention detection、type classification、normalization、storage lookup、candidate ranking 和降级。 |
| 必要重构 | 若设计确认现有模块边界不足，允许重构，但必须保持 V1/V2 回归绿色。 |
| 回归 | `python -m pytest`、V1 evaluation/smoke、V2 evaluation/smoke 保持可运行。 |
| 安全 | 不提交真实 Redis/Gauss 连接信息、真实 DV payload、真实 API key、完整 LLM 请求响应。 |

---

## 7 Human Decision Gate 确认结果

| ID | 确认事项 | 确认结论 | 状态 |
| --- | --- | --- | --- |
| V3-HD-001 | Redis value 是否严格单实体 ID，遇到同一实体词对应多个实体时如何处理 | 保持 value 为单实体 ID；冲突数据加载 fail-closed，不进入链接链路。 | Confirmed |
| V3-HD-002 | Redis key 的实体词范围 | 使用 `canonical_name` + 经确认 `aliases`；不自动生成别名。 | Confirmed |
| V3-HD-003 | 高斯 Mock 结构化实体字段是否继续沿用最小字段 | 沿用最小字段 `entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`；类型专属字段后续另行确认。 | Confirmed |
| V3-HD-004 | NER 是否允许引入新的内部中间 schema | 允许内部 schema 扩展；外部 API 和样例提交字段受控。 | Confirmed |
| V3-HD-005 | LLM 在 V3 NER 中的角色 | 默认离线 deterministic 可回归；LLM 作为可选分类、解释和 rerank 增强。 | Confirmed |
| V3-HD-006 | V3 样例数据是否复用 V2 样例并新增 storage mock artifacts | 复用 V1/V2 样例，新增 Redis/Gauss Mock artifacts 和 NER golden cases；新增样例必须脱敏并遵守 D003。 | Confirmed |

---

## 8 当前结论

V3 已启动需求分析。用户已确认：搁置 V2 遗留问题，进入 V3；V3 重点是两层存储和 NER 详细设计；Redis 缓存接口 Mock 负责实体词到实体 ID 的 KV 查询；高斯数据库接口 Mock 负责结构化实体数据并支持按实体 ID 查询；NER 是本项目重中之重，必要时可重构。

V3 Human Decision Gate 已通过 GUI 确认记录关闭，确认文件为 `docs/confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json`。V3 需求评审、处置和闭环验证已完成，当前已进入 SR 功能设计草稿阶段；代码实现前仍需完成 SR 功能设计独立评审、处置和闭环验证。

## 附录 A 参考资料

| 编号 | 资料名称 | 来源 |
| --- | --- | --- |
| A1 | 当前项目总览 | [../../PROJECT.md](../../PROJECT.md) |
| A2 | 当前决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| A3 | 当前数据契约 | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| A4 | V2 验收记录 | [../../releases/V2.md](../../releases/V2.md) |
| A5 | V2 IR | [../v2/IR.md](../v2/IR.md) |
| A6 | V2 SR | [../v2/SR.md](../v2/SR.md) |

## 附录 B 相关文件

| 编号 | 文件名称 | 版本/状态 |
| --- | --- | --- |
| B1 | [IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md) | V3 IR 阶段 SR 分解，已补齐用户决策 |
| B2 | `samples/real/entity_examples.json` | V1 alarm 基线样例，V3 回归输入 |
| B3 | `samples/real/v2_entity_examples.json` | V2 多类型实体样例，V3 可复用输入 |
| B4 | `samples/real/v2_query_samples.json` | V2 多 mention Query 样例，V3 可复用输入 |
| B5 | `docs/confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json` | V3 GUI 决策确认记录 |

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V3 |
| 创建日期 | 2026-06-24 |
| 最近更新 | 2026-06-25 |
| 作者 | Codex |
| 状态 | 需求评审处置闭环已通过，可进入功能设计 |
| 版本 | V3.1-draft |

## 评审记录

| 评审日期 | 评审方式 | 评审结论 | 状态 |
| --- | --- | --- | --- |
| 2026-06-25 | 主代理只读需求评审 | Ready for disposition with findings，见 [REQUIREMENT-REVIEW.md](./REQUIREMENT-REVIEW.md) | 已处置 |
| 2026-06-25 | 需求评审处置 | Accepted all findings，见 [REQUIREMENT-REVIEW-DISPOSITION.md](./REQUIREMENT-REVIEW-DISPOSITION.md) | 已闭环验证 |
| 2026-06-25 | 需求闭环验证 | Closed with recorded residual risk，见 [REQUIREMENT-CLOSURE-VERIFICATION.md](./REQUIREMENT-CLOSURE-VERIFICATION.md) | Closed |
