# DigitalView-SW DVEntityLinking V3 SR 分解需求分析

日期：2026-06-25

> 文档治理说明：本文是 V3 IR 阶段的 SR 分解主输出件，按版本保留。本文只做需求分解，不替代后续 SR 功能设计。V3 IR 独立评审、处置和闭环验证已完成；代码实现和验收必须等待 V3 SR 功能设计独立评审、处置和闭环验证。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V3.0-addendum-draft | 2026-06-24 | Codex | 根据 V3 启动要求，将两层存储、Redis Mock、高斯 Mock、NER 详细设计和必要重构拆分为设计就绪 SR。 |
| V3.1-addendum-draft | 2026-06-25 | Codex | 根据 V3 GUI 决策确认记录关闭 Human Decision Gate，固化 Redis 冲突、key 范围、高斯字段、NER schema、LLM 角色和样例策略，并根据需求评审处置统一日期和治理口径。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 需求分解 | Requirement Decomposition |
| Redis Mock | Redis Mock |
| 高斯 Mock | GaussDB Mock |
| 两层存储 | Two-layer Storage |
| NER Pipeline | NER Pipeline |
| 存储一致性 | Storage Consistency |
| 回归验收 | Regression Acceptance |

### Abstract 摘要

**中文摘要**：

本文档补充 DVEntityLinking V3 的 IR 阶段 SR 分解。V3 由用户明确启动，V2 视觉验收遗留问题搁置。V3 需求拆分为 6 个 SR：存储契约和数据模型、Redis 实体词缓存接口 Mock、高斯结构化实体存储接口 Mock、两层存储集成和一致性策略、NER pipeline 详细设计和重构策略、V3 评测回归和安全边界。其中 NER pipeline 是最高优先级 SR，后续功能设计需围绕 NER 的分层、分类、mention 规范化、存储查询、候选生成和降级语义展开。

**English Abstract**：

This addendum provides the V3 SR decomposition at the IR phase. V3 defers the remaining V2 visual acceptance issue and focuses on two-layer storage and detailed NER design. Six SRs are defined, covering storage contracts, Redis mock, GaussDB mock, storage integration and consistency, NER pipeline design and refactoring strategy, and V3 testing, regression, and safety boundaries. The NER pipeline is the highest-priority SR.

## 1 引言

### 1.1 目的

本文用于把 V3 需求拆分成可直接指导后续功能设计的 SR，满足项目流程要求：IR 阶段必须完成需求分解，IR 独立评审必须从功能设计视角检查 SR 拆分是否合理。

### 1.2 范围

#### 需求范围内

| 范围项 | 说明 |
| --- | --- |
| V3 SR 分解 | 将 V3 两层存储、Redis/Gauss Mock、NER 详细设计和必要重构拆成设计就绪 SR。 |
| 存储接口边界 | 明确实体词缓存与结构化实体存储的接口职责和可替换边界。 |
| NER 主线 | 明确 NER 是 V3 最高优先级，后续允许重构现有抽取、链接和 catalog 边界。 |
| 回归和安全 | 保持 V1/V2 回归，并阻止真实 Redis/Gauss/DV 敏感信息进入提交。 |

#### 需求范围外

| 范围外项 | 说明 |
| --- | --- |
| 代码实现 | 本文不实现 Redis Mock、高斯 Mock、NER pipeline 或重构。 |
| 功能设计细节 | 类图、接口签名、错误枚举、数据文件格式和测试矩阵在后续 SR 文档中展开。 |
| 真实外部服务 | 本文不要求连接真实 Redis、高斯数据库或 DV 生产接口。 |
| V2 遗留视觉问题 | V2 `AC-V2-FE-VIS-008` 搁置，不纳入 V3 SR。 |

### 1.3 与用户要求的映射

| 用户要求 | SR 承接 |
| --- | --- |
| 搁置 V2 遗留问题，进入 V3 | 全部 SR 的版本状态前置约束；SR-V3-A06 负责文档和回归状态记录。 |
| KV 对走 Redis 缓存 | SR-V3-A01、SR-V3-A02、SR-V3-A04。 |
| Redis key 是实体词，value 是实体 ID | SR-V3-A01、SR-V3-A02；保持 value 单实体 ID，冲突数据加载 fail-closed。 |
| Redis 接口 Mock | SR-V3-A02。 |
| 结构化数据存高斯数据库 | SR-V3-A01、SR-V3-A03。 |
| 高斯接口 Mock，支持按实体 ID 查询 | SR-V3-A03。 |
| NER 部分详细设计，是项目重中之重 | SR-V3-A05，最高优先级。 |
| 必要时重构 | SR-V3-A05 负责重构边界，SR-V3-A06 负责回归和验收护栏。 |

## 2 SR 总览

| SR | 标题 | 类型 | 责任模块 | 优先级 |
| --- | --- | --- | --- | --- |
| SR-V3-A01 | V3 存储契约和数据模型 | 技术 SR | storage contract、models | 高 |
| SR-V3-A02 | Redis 实体词缓存接口 Mock | 功能 SR | redis mock adapter、entity-word index | 高 |
| SR-V3-A03 | 高斯结构化实体存储接口 Mock | 功能 SR | gauss mock adapter、entity store | 高 |
| SR-V3-A04 | 两层存储集成和一致性策略 | 技术 SR | service orchestration、preprocessing | 高 |
| SR-V3-A05 | NER pipeline 详细设计和重构策略 | 功能 SR | NER router、recognizer、normalizer、linker boundary | 最高 |
| SR-V3-A06 | V3 评测、回归和安全边界 | 非功能 SR | evaluator、tests、artifact hygiene | 高 |

## 3 需求明细 - SR 分解

### 3.1 SR-V3-A01 V3 存储契约和数据模型

| 字段 | 内容 |
| --- | --- |
| 类型 | 技术 SR |
| 责任模块 | storage contract、models、schema validator |
| 优先级 | 高 |

**#需求背景#**：

V3 要把实体词索引和结构化实体详情拆成两层存储。现有 catalog 同时承担加载、索引和查询职责，无法清晰表达 Redis 缓存和高斯数据库的职责分离。

**#需求价值#**：

为 Redis Mock、高斯 Mock、NER pipeline 和后续真实适配器提供统一数据契约，降低后续重构和替换成本。

**#需求内容#**：

- 定义 V3 存储角色：`EntityWordCache` 和 `StructuredEntityStore`。
- 定义实体词 KV 记录：`entity_word`、`entity_id`、`entity_type` 可选、`source` 可选、`normalization_version` 可选。
- 定义结构化实体记录，初始建议沿用当前最小实体字段：`entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`。
- 定义实体词归一化要求：大小写、空白、标点、括号、中文/英文混合和原文 span 保留策略需要在功能设计中明确。
- 定义错误和 miss 契约：duplicate key、duplicate entity_id、dangling entity_id、invalid schema、unconfirmed data layer、cache miss、entity miss。
- 定义安全边界：任何真实 Redis/Gauss/DV 连接信息、凭据或生产 payload 不进入提交。

**#需求范围#**：

包括接口级数据契约、Mock 输入输出字段、错误语义和后续适配器边界。不包括具体代码实现和真实外部服务接入。

**#约束条件#**：

用户已确认 Redis value 保持单实体 ID。若同一实体词映射多个实体，冲突数据加载必须 fail-closed，不能进入链接链路，也不能静默升级为多值结构。

**设计输入提示**：

功能设计需定义 `EntityWordRecord`、`StructuredEntityRecord`、`StorageLookupResult`、`StorageError`、normalization policy、single-value conflict policy 和 schema version。

### 3.2 SR-V3-A02 Redis 实体词缓存接口 Mock

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | redis mock adapter、entity-word index |
| 优先级 | 高 |

**#需求背景#**：

V3 要求实体词到实体 ID 的 KV 对走 Redis 缓存，且当前阶段使用 Redis 接口 Mock。

**#需求价值#**：

让 NER 和链接链路通过缓存快速把实体词转换为实体 ID，同时保留未来接入真实 Redis 的接口位置。

**#需求内容#**：

- 提供 Redis-like lookup 接口：输入实体词 key，返回实体 ID 或 miss/error。
- V3 Mock 可使用本地 JSON/内存结构实现，但业务层不得依赖具体文件结构。
- 加载时校验 key 为空、value 为空、重复 key、value 引用不存在实体 ID 等异常。
- 支持可观测的 lookup 状态：hit、miss、invalid_key、dependency_failed、schema_error。
- 支持 NER 调用时按 normalized entity word 查询。
- Redis key 范围限定为 `canonical_name` + 经确认 `aliases`；不允许自动生成未经确认的 alias key。

**#需求范围#**：

包括 Redis 接口 Mock、KV 加载校验和 lookup 结果。不包括真实 Redis 网络调用、连接池、认证、TTL 和集群。

**#约束条件#**：

key 是实体词，value 是实体 ID 是 V3 当前硬约束；冲突数据加载 fail-closed。Mock 不得包含真实 Redis host、port、password 或连接串。

**设计输入提示**：

功能设计需定义 `RedisEntityWordCache` interface、mock artifact schema、normalization handoff、error mapping、cache miss semantics 和 conflict behavior。

### 3.3 SR-V3-A03 高斯结构化实体存储接口 Mock

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | gauss mock adapter、entity store |
| 优先级 | 高 |

**#需求背景#**：

V3 要求结构化实体数据存高斯数据库，高斯接口 Mock 支持按实体 ID 查询。

**#需求价值#**：

将实体详情查询从实体词缓存中分离出来，让链接结果能够以实体 ID 为稳定主键查询结构化实体信息。

**#需求内容#**：

- 提供 Gauss-like lookup 接口：输入 entity ID，返回结构化实体记录或 miss/error。
- V3 Mock 可使用本地 JSON/内存结构实现，但接口应模拟数据库查询边界。
- 支持按实体 ID 查询，这是当前最小必需能力。
- 加载时校验 duplicate entity_id、字段缺失、entity_type 不支持、schema_version 不支持。
- 查询返回不得暴露真实数据库连接信息或敏感字段。
- 保留未来扩展按类型、按实体词、批量查询或关系查询的空间，但不纳入 V3 最小范围。

**#需求范围#**：

包括高斯接口 Mock、实体记录加载、按 ID 查询和错误语义。不包括真实 GaussDB 连接、SQL 调优、事务、分页、权限和生产部署。

**#约束条件#**：

V3 初始不新增类型专属字段；若高斯结构化数据后续需要扩展字段，需单独确认并进入新一轮设计。

**设计输入提示**：

功能设计需定义 `GaussEntityStore` interface、mock schema、entity-id lookup result、error mapping、future real adapter boundary 和 safe projection。

### 3.4 SR-V3-A04 两层存储集成和一致性策略

| 字段 | 内容 |
| --- | --- |
| 类型 | 技术 SR |
| 责任模块 | service orchestration、preprocessing、storage repository |
| 优先级 | 高 |

**#需求背景#**：

Redis Mock 和高斯 Mock 分别承担实体词索引和实体详情查询。系统需要保证两层数据可一起加载、校验、查询和降级。

**#需求价值#**：

避免 cache 命中但 DB 缺失、DB 有实体但 cache 无 key、重复 key 指向错误实体等问题进入链接链路。

**#需求内容#**：

- 定义 startup lifecycle：加载高斯 Mock 实体，再加载 Redis Mock KV，并执行跨层一致性校验。
- Redis value 引用的 entity ID 必须能在高斯 Mock 查询到。
- 高斯实体的 `canonical_name` 和经确认 `aliases` 可进入 Redis key；不得自动生成别名 key。
- 定义 cache miss、entity miss、schema error、dependency failed 对 Query 级和 mention 级状态的影响。
- 支持 V1/V2 样例迁移到两层存储 Mock，以便保持回归。
- 支持 storage lookup trace 的安全展示，不暴露本地路径、真实连接串或敏感 payload。

**#需求范围#**：

包括两层加载顺序、一致性检查、错误隔离、service handoff 和安全 trace。不包括真实数据库迁移和线上数据同步。

**#约束条件#**：

任何一层异常不得回退为伪实体链接。存储层异常和 no_match 必须可区分。

**设计输入提示**：

功能设计需定义 `StorageBackedCatalog` 或等价 adapter、startup check report、cross-layer validation、lookup trace、degraded result source 和 V1/V2 compatibility plan。

### 3.5 SR-V3-A05 NER pipeline 详细设计和重构策略

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | NER router、mention detector、type classifier、normalizer、linker boundary |
| 优先级 | 最高 |

**#需求背景#**：

用户明确 NER 是 V3 的重中之重，必要时重构。V2 的 NER 已支持多 mention 和 LLM fallback，但核心仍偏轻量规则和 catalog 搜索。V3 两层存储接入后，NER 必须成为 Query 到实体词、实体 ID 和候选实体的清晰 pipeline。

**#需求价值#**：

提高实体识别链路的可解释性、可测试性和可扩展性，降低多类型、多 mention、cache miss、LLM 降级和跨类型歧义下的误链接风险。

**#需求内容#**：

- 定义 NER pipeline 阶段：
  - Query validation and normalization。
  - need-linking 判断。
  - mention detection。
  - mention span 校验和原文保留。
  - entity type classification。
  - entity-word normalization。
  - Redis entity-word cache lookup。
  - Gauss entity lookup。
  - candidate construction。
  - linking status aggregation。
- 对每个阶段定义输入、输出、错误、降级和可观测 trace。
- 支持单 Query 多 mention；Query 级 `partial` 不得掩盖 mention 级失败。
- 明确 deterministic NER 和 LLM-assisted NER 的关系：默认离线 deterministic 路径必须可回归，LLM 仅作为可选分类、解释或 rerank 增强。
- 明确候选类型分类和 storage lookup 的先后关系：类型分类可帮助过滤 Redis key 或候选，但不得导致已确认实体词被静默丢弃。
- 定义 not_required 和 no_match 的前置判断，避免无实体意图 Query 进入 Redis/Gauss lookup。
- 定义 ambiguity 处理：单值 Redis 约束下，若实体词冲突或候选歧义，必须返回结构化冲突或 ambiguous，不强行链接。
- 允许 NER 内部 schema 扩展，用于 stage trace、storage lookup 和重构隔离；外部 API 与样例提交字段必须受控。
- 给出现有模块重构策略：`EntityExtractor`、`EntityLinker`、`CatalogRepository`、`EntityLinkingService` 的职责是否拆分和迁移。

**#需求范围#**：

包括 NER pipeline、阶段契约、状态语义、LLM 辅助、重构边界和输出 schema。不包括模型训练、生产 NLP 平台或大规模标注系统。

**#约束条件#**：

NER 重构不得破坏 V1 alarm 回归、V2 多 mention 回归和默认离线验收。功能设计未闭环前不得开始代码重构。

**设计输入提示**：

功能设计需定义 `NerPipeline`、`NerStageResult`、`MentionDetectionResult`、`TypeClassificationResult`、`EntityWordLookupResult`、`StorageBackedCandidate`、status decision tree、fallback state machine、trace schema 和 migration plan。

### 3.6 SR-V3-A06 V3 评测、回归和安全边界

| 字段 | 内容 |
| --- | --- |
| 类型 | 非功能 SR |
| 责任模块 | evaluator、test automation、artifact hygiene |
| 优先级 | 高 |

**#需求背景#**：

V3 架构改造风险高。两层存储和 NER 重构可能破坏 V1/V2 已验证能力，必须在需求阶段就定义回归和安全护栏。

**#需求价值#**：

确保 V3 改造可验证、可回退、可解释，不把存储 Mock 或 NER 重构变成不可控的大改。

**#需求内容#**：

- 保留 V1/V2 evaluation 和 acceptance smoke 作为回归底线。
- 样例策略复用 V1/V2 已确认样例，并新增 Redis/Gauss Mock artifacts 和 NER golden cases；新增样例必须脱敏并遵守 D003。
- 新增 Redis Mock 单元/契约测试：hit、miss、duplicate key、dangling entity ID、invalid schema。
- 新增高斯 Mock 单元/契约测试：entity lookup、miss、duplicate ID、missing fields、invalid schema。
- 新增两层集成测试：cache hit + DB hit、cache hit + DB miss、cache miss、storage dependency failed。
- 新增 NER pipeline 测试：need-linking、mention detection、span、type classification、entity-word normalization、多 mention、partial、ambiguous/no_match/not_required。
- 新增敏感扫描：禁止真实 Redis/Gauss 连接串、password、token、真实 DV payload、完整 LLM 请求响应进入提交。
- 生成 V3 review input bundle，包含用户决策台账、GUI 确认记录、IR/SR、当前实现文件列表、测试映射和已关闭 Human Decision Gate 摘要。

**#需求范围#**：

包括测试策略、验收草案、回归命令、安全扫描和评审输入。不包括实现评审、测试评审或闭环验证结论。

**#约束条件#**：

默认自动化必须离线可执行；真实 Redis/Gauss/LLM 不得成为默认验收依赖。

**设计输入提示**：

功能设计和测试设计需定义 V3 test matrix、storage contract fixtures、NER golden cases、regression commands、sensitive patterns 和 acceptance smoke summary schema。

## 4 SR 交接矩阵

| 交接对象 | 生产 SR | 消费 SR | 关键字段/内容 |
| --- | --- | --- | --- |
| StructuredEntityRecord | SR-V3-A01、A03 | SR-V3-A04、A05、A06 | entity_id、entity_type、canonical_name、aliases、description、schema_version。 |
| EntityWordRecord | SR-V3-A01、A02 | SR-V3-A04、A05、A06 | entity_word、normalized_key、entity_id、source、normalization_version。 |
| StorageLookupResult | SR-V3-A02、A03、A04 | SR-V3-A05、A06 | status、entity_id、entity_record、error_code、safe_trace。 |
| NerStageResult | SR-V3-A05 | SR-V3-A06、Web/API 后续设计 | stage、status、input_summary、output_summary、error_code、degraded。 |
| LinkResult | SR-V3-A05 | SR-V3-A06、Web/API 后续设计 | query_status、mention_results、candidates、storage_trace、result_source。 |

## 5 SR 到验收映射

| SR | 验收关注 |
| --- | --- |
| SR-V3-A01 | 存储契约清晰，单值 Redis 约束、结构化实体字段、错误语义和安全边界明确。 |
| SR-V3-A02 | Redis Mock 可加载 KV、按实体词查询实体 ID，并覆盖 hit/miss/error/重复/悬挂引用。 |
| SR-V3-A03 | 高斯 Mock 可按实体 ID 查询结构化实体，并覆盖 miss/error/重复/字段缺失。 |
| SR-V3-A04 | 两层数据启动、一致性校验和降级语义明确；V1/V2 样例可迁移或兼容。 |
| SR-V3-A05 | NER 详细设计覆盖完整 pipeline、阶段契约、LLM/离线关系、多 mention、歧义和重构边界。 |
| SR-V3-A06 | 自动化覆盖 Redis/Gauss Mock、NER pipeline、两层集成、V1/V2 回归和敏感信息扫描。 |

## 6 Human Decision Gate 确认结果

| 决策项 | 影响 SR | 确认结论 | 状态 |
| --- | --- | --- | --- |
| Redis 单 key 是否允许多实体冲突升级 | A01、A02、A05、A06 | 保持 value 为单实体 ID；冲突数据加载 fail-closed，不进入链接链路。 | Confirmed |
| Redis key 范围是否包含 aliases | A01、A02、A04、A05 | 使用 `canonical_name` + 经确认 `aliases`；不自动生成别名。 | Confirmed |
| 高斯结构化实体字段是否扩展 | A01、A03、A06 | V3 初始沿用最小字段；类型专属字段后续单独确认。 | Confirmed |
| NER 内部 schema 可扩展边界 | A05、A06 | 允许内部 schema 扩展；外部 API 和样例提交字段受控。 | Confirmed |
| LLM 在 V3 NER 中的默认角色 | A05、A06 | 默认离线 deterministic 可回归；LLM 作为可选分类、解释和 rerank 增强。 | Confirmed |
| V3 样例数据策略 | A02、A03、A04、A06 | 复用 V1/V2 样例，新增 Redis/Gauss Mock artifacts 和 NER golden cases；新增样例遵守 D003。 | Confirmed |

## 7 当前结论

V3 SR 分解已按用户要求形成：两层存储拆为存储契约、Redis Mock、高斯 Mock 和集成一致性四个设计输入；NER 作为最高优先级 SR，需要详细设计并允许必要重构；评测和安全 SR 负责守住 V1/V2 回归、Mock 契约测试和敏感边界。

V3 Human Decision Gate 已通过 GUI 确认记录关闭，确认文件为 `docs/confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json`。V3 需求评审、处置和闭环验证已完成，当前已进入 SR 功能设计草稿阶段；代码实现前仍需完成 SR 功能设计独立评审、处置和闭环验证。

## 8 评审和闭环记录

| 日期 | 阶段 | 结论 | 状态 |
| --- | --- | --- | --- |
| 2026-06-25 | 独立需求评审 | Ready for disposition with findings，见 [REQUIREMENT-REVIEW.md](./REQUIREMENT-REVIEW.md) | 已处置 |
| 2026-06-25 | 需求评审处置 | 接受全部 P2/P3 发现并完成修订，见 [REQUIREMENT-REVIEW-DISPOSITION.md](./REQUIREMENT-REVIEW-DISPOSITION.md) | 已闭环验证 |
| 2026-06-25 | 需求闭环验证 | Closed with recorded residual risk，见 [REQUIREMENT-CLOSURE-VERIFICATION.md](./REQUIREMENT-CLOSURE-VERIFICATION.md) | Closed |

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V3-SR-DECOMPOSITION |
| 创建日期 | 2026-06-24 |
| 最近更新 | 2026-06-25 |
| 作者 | Codex |
| 状态 | 需求评审处置闭环已通过，可进入功能设计 |
| 版本 | V3.1-addendum-draft |
