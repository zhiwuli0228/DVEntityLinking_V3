# DigitalView-SW DVEntityLinking V2 SR 分解需求分析

日期：2026-06-01

> 文档治理说明：本文是 V2 IR 阶段的 SR 分解主输出件，按版本保留。本文只做需求分解，不替代后续 SR 功能设计。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V2.0-addendum-draft | 2026-06-01 | Codex | 根据 V2 启动要求输出设计就绪 SR 分解；将数据预处理合并为大模块，将运行时接口 Mock 独立为可替换 SR。 |
| V2.1-addendum-draft | 2026-06-01 | Codex | 根据用户补充要求细化 KPI/网元实体类型拆分，并将新增类型别名规则收紧为默认空、显式标注。 |
| V2.2-addendum-draft | 2026-06-01 | Codex | 根据 V2 IR 独立评审处置，补充启动样例已确认、多 mention、`partial` 和评测语义要求。 |
| V2.3-addendum | 2026-06-01 | Codex | 根据 no-context/sealed 闭环验证结论更新状态为需求评审闭环已通过，可作为 V2 功能设计输入。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| 需求分解 | Requirement Decomposition |
| 数据预处理 | Data Preprocessing |
| 运行时 Mock | Runtime Mock |
| 多类型实体链接 | Multi-type Entity Linking |
| LLM Rerank | LLM Reranking |
| 前端演示 | Frontend Demo |

### Abstract 摘要

**中文摘要**：

本文档补充 DVEntityLinking V2 的 IR 阶段 SR 分解。用户确认数据预处理应作为大模块统一管控实体类型扩充、KPI/网元类型预置挖掘、样例规范化和校验；运行时接口 Mock 应独立成 SR，因为后续可能被真实 DV 接口整体替换。V2 KPI 类实体拆为 `kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`，网元类实体拆为 `ne_type` 和 `ne_name`；新增 KPI/网元类实体别名默认空，必须特殊标注并经确认。V2 启动样例已确认，补充 Query 全部为英文且必须支持多 mention。本文将 V2 需求拆分为 8 个设计就绪 SR，覆盖数据预处理、运行时 Mock、分层分类 NER、LLM-based 抽取/解释/rerank、多类型链接、多类型检索、Web demo 增强以及评测验收与安全边界。

**English Abstract**：

This addendum provides the V2 SR decomposition at the IR phase. Data preprocessing is treated as a unified module covering entity type expansion, KPI preset mining, sample normalization, and validation. Runtime interface mocking is separated as an independent SR because it may later be replaced by real DV interfaces as a whole. Eight design-ready SRs are defined for V2.

## 1 引言

### 1.1 目的

本文用于把 V2 需求拆分成可直接指导后续功能设计的 SR，满足本项目优化后的 DV 流程要求：IR 阶段必须完成需求分解，IR 独立评审必须从功能设计视角检查 SR 拆分是否合理。

### 1.2 范围

#### 需求范围内

| 范围项 | 说明 |
| --- | --- |
| V2 SR 分解 | 将 V2 多类型、LLM-based、运行时 Mock 和前端演示增强需求拆成设计就绪 SR。 |
| 数据预处理大模块 | 统一承接预置配置、DVKnowledge KPI/网元类型挖掘、样例规范化、显式别名标注、去重和校验。 |
| 运行时接口 Mock 独立 SR | 保持文件读取 Mock 的可替换边界，未来能整体替换为真实 DV 接口。 |
| 结构不升级约束 | 所有 SR 都必须遵守实体结构不升级约束。 |

#### 需求范围外

| 范围外项 | 说明 |
| --- | --- |
| 代码实现 | 本文不实现 runtime mock、LLM prompt、NER、linker、index 或 Web UI。 |
| 功能设计细节 | 模块类图、接口定义、异常枚举和测试设计在后续 SR 文档中展开。 |
| 后续新增样例固化 | V2 启动样例已确认；后续新增 KPI/网元/真实 DV payload 未确认前，不作为提交样例基线。 |

### 1.3 与用户要求的映射

| 用户要求 | SR 承接 |
| --- | --- |
| 实体结构暂不升级，改动必须确认 | 所有 SR 的通用约束，重点在 SR-V2-A01、A05、A06。 |
| 新增网元类型 `ne_type`，一般可预置 | SR-V2-A01、SR-V2-A05。 |
| 新增网元名称 `ne_name`，来源为运行时接口 Mock | SR-V2-A02、SR-V2-A01、SR-V2-A05。 |
| KPI 拆分为 `kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key` | SR-V2-A01、SR-V2-A02、SR-V2-A03、SR-V2-A05。 |
| `kpi_meas_type_key` 全部保留，`kpi_meas_objects` 本轮先忽略 | SR-V2-A01、SR-V2-A08。 |
| `kpi_task_name` 补充不同类型任务名 `Network quality monitoring` | SR-V2-A01、SR-V2-A08。 |
| 新增类型别名默认空，必须特殊标注 | SR-V2-A01、SR-V2-A03、SR-V2-A06、SR-V2-A08。 |
| 数据预处理统一管控 001 和 003 | SR-V2-A01。 |
| 运行时接口 Mock 独立 SR | SR-V2-A02。 |
| NER 开始考虑分层、分类 | SR-V2-A03。 |
| V2 必须支持多 mention Query，补充 Query 全部使用英文 | SR-V2-A03、SR-V2-A05、SR-V2-A08。 |
| V2 重点是 LLM-based 方法 | SR-V2-A04，并影响 A03、A05、A07、A08。 |
| 前端方案 C，但不要过度前端 | SR-V2-A07。 |

## 2 SR 总览

| SR | 标题 | 类型 | 责任模块 | 优先级 |
| --- | --- | --- | --- | --- |
| SR-V2-A01 | 数据预处理与实体目录统一管控 | 功能 SR | data preprocessing、catalog | 高 |
| SR-V2-A02 | 运行时接口 Mock | 功能 SR | runtime mock adapter | 高 |
| SR-V2-A03 | 分层分类 NER 与 mention 规范化 | 功能 SR | NER router、recognizer | 高 |
| SR-V2-A04 | LLM-based 抽取、分类、解释和 rerank | 功能 SR | LLM adapter、prompt/schema | 高 |
| SR-V2-A05 | 多类型实体链接与跨类型消歧 | 功能 SR | linker、status resolver | 高 |
| SR-V2-A06 | 多类型索引、检索与存储策略 | 技术 SR | index、retrieval、storage | 高 |
| SR-V2-A07 | Web demo 演示工作台增强 | 功能 SR | Web UI/API projection | 中 |
| SR-V2-A08 | V2 评测验收与安全边界 | 非功能 SR | evaluator、test、artifact hygiene | 高 |

## 3 需求明细 - SR 分解

### 3.1 SR-V2-A01 数据预处理与实体目录统一管控

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | data preprocessing、entity catalog、schema validator |
| 优先级 | 高 |

**#需求背景#**：

V2 新增 `ne_type`、`ne_name` 和 KPI 三类子类型后，实体数据来源不再只有单一预置样例。KPI 需要区分测量任务名称、测量对象和测量指标；网元需要区分可预置的网元类型和运行时实例化的网元名称。用户要求数据预处理作为大模块统一管控相关内容。

**#需求价值#**：

避免每类实体各自散落实现加载、清洗、显式别名标注和校验；为后续真实 DV 接口接入、KPI 数据扩展和检索索引构建提供稳定前置输入。

**#需求内容#**：

- 统一接收配置预置实体、DVKnowledge KPI/网元类型候选和运行时 Mock 输出。
- 将输入记录规范化到当前最小实体契约：`entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`。
- 支持 V2 实体类型：`alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`。
- 保持 V1 `alarm` 基线不变。
- 对 KPI/网元类型预置候选执行去重；预处理过程可保留内部来源上下文，但不得把来源上下文固化为 V2 实体提交字段。
- 对新增 KPI/网元类实体，`aliases` 默认必须为空数组；预处理不得自动根据 canonical name、大小写、缩写、路径或括号内容生成别名。
- 如确有别名，必须在样例确认清单中特殊标注，确认后才可进入 `aliases`。
- 对运行时 Mock 输出执行类型校验、必填字段校验、重复 ID/别名校验和可链接性校验。
- 预处理失败必须 fail-closed，不得输出部分损坏 catalog 进入链接链路。

**#需求范围#**：

包括预置数据、DVKnowledge 挖掘候选、运行时 Mock 输出和统一 catalog 形成。不包括真实 DV 接口实现和实体结构升级。

**#约束条件#**：

不得新增实体字段、关系或类型专属 schema 作为 V2 默认契约；如发现必须新增，需回到用户确认。类型拆分不等同于字段结构升级。

**设计输入提示**：

功能设计需定义 preprocessing pipeline、source record、normalized entity、validation error、ID 生成规则、explicit alias annotation rule、duplicate policy、confirmed/unconfirmed candidate handling 和 catalog handoff。

### 3.2 SR-V2-A02 运行时接口 Mock

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | runtime mock adapter |
| 优先级 | 高 |

**#需求背景#**：

V2 需要模拟 DV 启动时通过运行时接口获取 `ne_name` 和部分 KPI 运行时数据。用户明确运行时接口 Mock 应作为独立 SR，因为未来可能被真实 DV 接口整体替换。

**#需求价值#**：

让 demo 能体现运行时实体来源，同时保持接口适配层清晰，避免把文件读取细节耦合到实体链接核心逻辑。

**#需求内容#**：

- 使用本地文件模拟 DV 运行时接口返回。
- 至少支持 `ne_name` 网元名称/实例数据。
- 可选支持 `kpi_meas_objects` 和其他 KPI 运行时数据，和预置 KPI 数据共同进入数据预处理模块。
- Mock adapter 输出必须是结构化记录，不直接写入最终 catalog。
- 支持文件缺失、非法 JSON、类型不支持、字段缺失和重复记录等结构化错误。
- 业务逻辑只能依赖 adapter 输出契约，不依赖文件路径、JSON 内部组织或读取实现。

**#需求范围#**：

包括文件读取 Mock、结构化输出和错误语义。不包括真实 DV 接口鉴权、网络调用、分页、限流和权限处理。

**#约束条件#**：

Mock 内容和字段样例必须确认后提交；未确认真实 DV payload 不得进入 repo。

**设计输入提示**：

功能设计需定义 RuntimeEntitySource interface、file mock implementation、response object、error object、startup lifecycle、retry/degraded behavior 和 future real adapter replacement boundary。

### 3.3 SR-V2-A03 分层分类 NER 与 mention 规范化

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | NER router、type-specific recognizer、normalizer |
| 优先级 | 高 |

**#需求背景#**：

实体类型从 `alarm` 扩展到 `ne_type`、`ne_name` 和 KPI 子类型后，单一规则匹配容易产生跨类型误识别。用户要求 V2 开始考虑分层、分类 NER。

**#需求价值#**：

提高多类型实体识别准确率，降低跨类型候选混淆，并为 LLM-based 方法提供可验证的结构化接口。

**#需求内容#**：

- 第一层判断 Query 是否需要实体链接。
- 第二层判断候选实体类型，可输出单类型、多类型或不确定。
- 第三层按类型执行 mention 识别和规范化。
- 输出 mention 的 text、span、normalized_text、candidate_type、source、confidence。
- `candidate_type` 必须能区分 `ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`。
- 对新增类型不得依赖自动别名召回；默认只按 canonical_name 或明确标注别名识别。
- 对无实体需求、无法判断类型、LLM schema 错误等情况输出结构化状态。
- V2 必须支持一个 Query 中出现多个实体词；启动样例每条 Query 最多 2 个 mention，具体扩展上限和评测规则在功能设计中明确。

**#需求范围#**：

包括多类型 NER 路由、类型内 mention 识别和规范化。不包括复杂事件抽取或生产级自然语言理解平台。

**#约束条件#**：

LLM 可参与但不能成为默认自动化的唯一依赖；离线规则路径仍需可回归。

**设计输入提示**：

功能设计需定义 NER pipeline、type classifier、mention schema、multi-mention policy、query/mention status boundary、confidence semantics、fallback order 和 not_required 前置点。

### 3.4 SR-V2-A04 LLM-based 抽取、分类、解释和 rerank

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | LLM adapter、prompt/schema、fallback |
| 优先级 | 高 |

**#需求背景#**：

用户明确 V2 重点是 LLM-based 方法。V1 已支持 LLM 模式切换，但 LLM 对实体识别和链接的核心贡献仍有限。

**#需求价值#**：

验证 LLM 在多类型 Query 中的实际价值：判断是否需要链接、抽取 mention、识别实体类型、解释候选、辅助消歧和 rerank。

**#需求内容#**：

- LLM 可用于 need-linking 判断、实体类型分类、mention 抽取、候选解释和 rerank。
- LLM 输出必须是结构化 schema，并经过严格校验。
- LLM 失败、超时、鉴权错误、HTTP 异常或 schema 异常时必须结构化降级。
- 不允许把 LLM 自然语言解释直接作为实体事实。
- Web/API 只展示 LLM 状态、摘要解释和安全字段，不展示完整 prompt、完整响应或敏感配置。

**#需求范围#**：

包括 LLM prompt/schema、adapter 输出、降级状态和候选 rerank。不包括模型训练、微调或供应商 SLA。

**#约束条件#**：

默认验收不能依赖真实 LLM；真实 LLM smoke 只能作为条件补证。`config/llm.local.json` 必须 ignored。

**设计输入提示**：

功能设计需定义 prompt template、JSON schema、schema validator、LLM error mapping、fallback state machine、safe trace projection 和 offline/LLM comparison report。

### 3.5 SR-V2-A05 多类型实体链接与跨类型消歧

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | entity linker、status resolver |
| 优先级 | 高 |

**#需求背景#**：

V2 同时存在告警、网元和 KPI，同一个实体词可能在不同类型中有候选，或者一个 Query 中可能包含多个不同类型实体词。

**#需求价值#**：

让运维 Copilot 和故障 Agent 能获得可信的多类型链接结果，避免把 KPI 当成网元、把告警 ID 当成资源名或在歧义时强行选择。

**#需求内容#**：

- 支持 `alarm`、`ne_type`、`ne_name` 和 KPI 子类型的候选融合。
- 对跨类型候选输出类型、得分、match_reason 和来源。
- 保留 `linked`、`ambiguous`、`no_match`、`not_required` 等核心状态，并扩展到多类型场景。
- 支持 Query 级 `partial` 状态：同一 Query 中至少一个 mention 可链接、至少一个 mention 不匹配或待降级处理时，不得强行归为完全 `linked`。
- 保留 mention 级状态和候选，避免 Query 级聚合状态掩盖局部 no_match、ambiguous 或降级。
- 对跨类型歧义保留候选，不强制选择。
- 支持 LLM rerank 结果和离线排序结果的可解释对比。

**#需求范围#**：

包括多类型候选融合、状态判定和跨类型消歧。不包括实体结构升级、拓扑推理或故障根因判断。

**#约束条件#**：

no_match/not_required 场景不得产生误候选；多类型扩展不能破坏 V1 alarm 回归。

**设计输入提示**：

功能设计需定义 MultiTypeLinkResult、per-mention candidates、type confidence、query-level `partial` aggregation、status decision tree、ambiguity policy、V1 compatibility 和 LLM/offline rank merge。

### 3.6 SR-V2-A06 多类型索引、检索与存储策略

| 字段 | 内容 |
| --- | --- |
| 类型 | 技术 SR |
| 责任模块 | index、retrieval、storage |
| 优先级 | 高 |

**#需求背景#**：

V2 实体类型和来源增加后，检索需要同时考虑实体量级、实体类型数量、预置和运行时数据的生命周期，以及未来可能的持久化策略。

**#需求价值#**：

在不引入过多三方组件的前提下，保持检索可解释、可测试和可扩展，为后续规模化留出路径。

**#需求内容#**：

- 默认继续采用 Python 内存索引优先。
- 索引必须支持按实体类型分区或过滤。
- 支持标准名、ID、类型、轻量 token 和经确认的显式别名候选召回。
- 支持预置数据和运行时 Mock 数据的合并、刷新和错误隔离。
- 规划实体量级、类型数量增长后的持久化路线，但不把外部检索组件作为 V2 默认依赖。

**#需求范围#**：

包括多类型内存索引、类型过滤、候选召回、排序解释和存储路线规划。不包括生产级向量库、分布式索引或外部 FTS 强依赖。

**#约束条件#**：

少依赖优先；如引入新三方件必须有明确收益并经确认。

**设计输入提示**：

功能设计需定义 IndexBundle v2、type partition、refresh lifecycle、source merge policy、score components、scale assumptions 和 optional persistence decision。

### 3.7 SR-V2-A07 Web demo 演示工作台增强

| 字段 | 内容 |
| --- | --- |
| 类型 | 功能 SR |
| 责任模块 | Web UI、API projection |
| 优先级 | 中 |

**#需求背景#**：

用户反馈当前页面简陋。V2 需要前端美化，但用户也明确前端只是为了更好演示项目，不应过度投入。

**#需求价值#**：

让多类型实体、mention、候选、LLM 链路和实体目录更容易被观察和演示，提高 V2 体验可信度。

**#需求内容#**：

- 采用方案 C：运维工作台基础 + LLM 交互式高亮/解释。
- 页面第一屏应直接服务实体链接 demo，不做营销式 landing。
- 支持查看当前全部样例实体，并按实体类型和来源过滤。
- Query 区域展示 mention 高亮、类型、置信度和简要信息。
- 结果区展示候选列表、实体详情字段名称、相似实体、状态和错误/降级原因。
- LLM 区域展示安全摘要：是否启用、是否降级、参与环节和摘要解释。

**#需求范围#**：

包括 demo 页面布局、视觉层级、核心交互和结果展示。不包括完整设计系统、权限、多租户、复杂拓扑工作台或大规模前端工程。

**#约束条件#**：

不得为了视觉效果牺牲实体链接主流程；不得展示敏感配置和完整 LLM 日志。

**设计输入提示**：

功能设计需定义 page layout、component states、entity catalog modal/panel、mention highlight、candidate/detail panels、LLM trace summary 和 responsive checks。

### 3.8 SR-V2-A08 V2 评测验收与安全边界

| 字段 | 内容 |
| --- | --- |
| 类型 | 非功能 SR |
| 责任模块 | evaluator、test automation、artifact hygiene |
| 优先级 | 高 |

**#需求背景#**：

V1 已确认准确率和召回率同等重要，且必须充分覆盖无法匹配或不需要匹配场景。V2 引入多类型和 LLM 后，需要重新定义评测集和安全边界。

**#需求价值#**：

防止 V2 只展示 LLM 命中效果而忽略误匹配、降级、负例和安全风险。

**#需求内容#**：

- V2 评测集必须覆盖多类型实体、多 mention、`partial`、跨类型歧义、no_match、not_required、LLM 失败降级和 V1 回归。
- precision 和 recall 同等重要。
- 对 no_match/not_required 的 false positive 继续作为验收关键指标。
- 评测报告需要区分 offline deterministic、LLM enabled、fallback used 和 schema error。
- 启动样例不等同于最终验收全集；若跨类型歧义或 LLM 降级样例未能在本轮纳入，测试设计必须记录延期理由和残余风险。
- 敏感字段扫描继续排除本地 ignored 配置，但必须阻止 API key、token、base URL、完整 DV payload 和完整 LLM 日志进入提交。

**#需求范围#**：

包括 V2 评测口径、验收阈值草案、自动化入口和安全扫描。不包括线上 A/B、人工标注系统或生产审计。

**#约束条件#**：

默认自动化仍要可离线运行；真实 LLM live 测试不能成为唯一验收证据。

**设计输入提示**：

功能设计需定义 V2 EvaluationCase、multi-mention metrics、query-level `partial` pass/fail、mention-level precision/recall、per-type precision/recall、negative false positive、LLM comparison report、sensitive scan pattern 和 acceptance smoke。

## 4 SR 交接矩阵

| 交接对象 | 生产 SR | 消费 SR | 关键字段/内容 |
| --- | --- | --- | --- |
| RuntimeSourceRecord | SR-V2-A02 | SR-V2-A01 | source_type、entity_type、raw_id、raw_name、explicit_aliases、description、error。 |
| NormalizedEntity | SR-V2-A01 | SR-V2-A05、A06、A07、A08 | entity_id、entity_type、canonical_name、aliases、description。 |
| MentionCandidate | SR-V2-A03、A04 | SR-V2-A05、A07、A08 | text、span、normalized_text、candidate_type、confidence、source。 |
| CandidateSet | SR-V2-A06 | SR-V2-A05、A07、A08 | entity_id、entity_type、score、match_reason、rank、source。 |
| LinkResult | SR-V2-A05 | SR-V2-A07、A08 | query_status、mention_results、candidates、top_entity、error_code、result_source、llm_summary；V2 Query 级状态包含 `partial`。 |

## 5 SR 到验收映射

| SR | 验收关注 |
| --- | --- |
| SR-V2-A01 | 数据预处理能统一产出 V2 新增类型的最小契约 catalog；非法输入 fail-closed；不升级实体字段；新增类型别名默认空。 |
| SR-V2-A02 | 文件驱动 Mock 可独立运行、错误结构化、未来可替换；不泄露未确认真实 payload。 |
| SR-V2-A03 | NER 有 need-linking、类型路由和多 mention 输出；负例不进入误匹配。 |
| SR-V2-A04 | LLM 输出可校验、可降级、可解释；默认自动化不依赖真实 LLM。 |
| SR-V2-A05 | 多类型链接状态清晰；多 mention 和 `partial` 聚合语义明确；跨类型歧义保留；V1 alarm 回归不破坏。 |
| SR-V2-A06 | 多类型索引支持类型过滤、来源合并和可解释召回；少依赖。 |
| SR-V2-A07 | 页面演示清晰、美观但不过度；能查看实体目录、mention、候选、详情和 LLM 摘要。 |
| SR-V2-A08 | 评测覆盖正例、负例、无需匹配、多 mention、`partial`、跨类型和 LLM 降级；敏感扫描通过。 |

## 6 当前结论

V2 SR 分解已按用户要求调整：数据预处理统一承接原多类型 catalog、KPI 子类型挖掘和网元类型预置挖掘职责；运行时接口 Mock 独立成可替换 SR；新增 KPI/网元类实体别名默认空且必须显式标注；多 mention 和 Query 级 `partial` 状态已作为 V2 设计输入；其他能力围绕分层分类 NER、LLM-based 方法、多类型链接、检索策略、前端演示和评测安全展开。

本文已完成本轮 IR 独立评审、评审处置和 no-context/sealed 闭环验证，闭环结论为 closed with recorded residual risk，可作为 V2 功能设计输入。残余风险为跨类型歧义、LLM 降级、多 mention precision/recall 公式需在后续功能设计和测试设计中固化。

## 7 评审和闭环记录

| 日期 | 阶段 | 结论 | 状态 |
| --- | --- | --- | --- |
| 2026-06-01 | sealed 本地独立需求评审 | Ready for disposition；无 P0，发现多 mention/`partial` 语义和样例确认状态同步问题 | 处置完成 |
| 2026-06-01 | no-context/sealed 独立闭环验证 | Closed with recorded residual risk；残余风险进入后续功能设计和测试设计 | 已闭环 |

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V2-SR-DECOMPOSITION |
| 创建日期 | 2026-06-01 |
| 最近更新 | 2026-06-01 |
| 作者 | Codex |
| 状态 | 需求评审闭环已通过，可作为功能设计输入 |
| 版本 | V2.3-addendum |
