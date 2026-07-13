# DigitalView-SW DVEntityLinking V1 SR 分解补充需求分析

日期：2026-05-31

> 文档治理说明：本文是 V1 IR 阶段的 SR 分解主输出件，按版本保留。原过程性评审、处置和闭环文件已合并到 [../../releases/V1.md](../../releases/V1.md)；需要原始过程细节时通过 Git 历史追溯。

## 文档控制

### 版本记录

| 版本 | 日期 | 作者 | 变更描述 |
| --- | --- | --- | --- |
| V1.5-addendum-draft | 2026-05-31 | Codex | 基于优化 DV 流程补充 V1 可设计 SR 分解，修正旧 SR 粒度不足问题。 |
| V1.6-addendum-draft | 2026-05-31 | Codex | 根据独立需求评审补充 fallback 输入、Query fail-closed 校验、API 参数异常、评测公式和 SR 交接表。 |
| V1.7-addendum-draft | 2026-06-01 | Codex | 根据用户 V1 验收反馈，将启动样例契约更新为 v2 最小字段，移除样例级提交状态和数据分层字段。 |

### Keywords 关键词

| 中文 | English |
| --- | --- |
| SR 分解 | Sub Requirement Decomposition |
| 告警实体 | Alarm Entity |
| 候选召回 | Candidate Retrieval |
| 实体链接 | Entity Linking |
| 评测器 | Evaluator |
| 安全边界 | Security Boundary |

### Abstract 摘要

**中文摘要**：

本文档是 DVEntityLinking V1 需求分析的 SR 分解补充文档。V1 原需求文档已经在旧流程下完成需求评审闭环，但按优化后的 DV 流程，IR 阶段必须输出可直接指导功能设计的 SR 分解。本 addendum 保留原 V1 范围、样例、验收和用户决策不变，将旧 SR 中偏需求活动或过宽的内容重新拆分为 8 个可设计 SR，覆盖 Web/API LLM 模式、`alarm` 实体 schema、Query 样例 schema、mention 识别、实体链接、内存索引、评测器以及安全配置日志边界。

**English Abstract**：

This addendum supplements the DVEntityLinking V1 requirement analysis with a design-ready SR decomposition. The previous V1 requirement baseline was closed under the earlier process, while the optimized DV process requires the IR phase to provide SRs that can directly guide function design. This addendum keeps the V1 scope, samples, acceptance criteria, and user decisions unchanged, and decomposes the previous broad/activity-oriented SRs into eight design-ready SRs covering Web/API LLM mode handling, alarm entity schema, query sample schema, mention recognition, entity linking, in-memory indexing, evaluation, and security/configuration/logging boundaries.

## 1 引言

### 1.1 目的

本文档用于关闭 [IR-DVEntityLinking-v1-sr-decomposition-reassessment.md](./IR-DVEntityLinking-v1-sr-decomposition-reassessment.md) 中发现的 SR 分解门禁问题，为 V1 功能设计提供稳定、可评审、可追踪的 SR 输入。

预期读者：

- V1 需求独立评审者。
- V1 需求评审处置和闭环验证负责人。
- V1 功能设计负责人。
- V1 测试设计负责人。

### 1.2 范围

#### 需求范围内

| 范围项 | 说明 |
| --- | --- |
| SR 重新分解 | 将 V1 需求拆成可直接指导功能设计的 SR。 |
| V1 `alarm` only 基线 | 仅覆盖 `alarm` 告警知识/事实实体，不扩展其他实体类型。 |
| 启动样例契约 | 承接 `samples/real/entity_examples.json` 和 `samples/real/query_samples.json` 的 v2 最小字段 schema、span 和 expected entity 规则。 |
| 检索与链接语义 | 明确 mention 识别、候选召回、排序解释、歧义、no_match、not_required 和评测口径。 |
| LLM 模式和安全边界 | 明确 Web/API mode、fallback、结构化状态、敏感配置和日志禁止项。 |

#### 需求范围外

| 范围外项 | 说明 |
| --- | --- |
| 运行时代码实现 | 本文不实现 loader、matcher、index、evaluator 或 Web UI。 |
| V2+ 实体类型 | 其他实体类型的数据结构、关系和样例补充不属于 V1 当前 SR。 |
| 真实 DV 接口接入 | 告警类 V1 不接运行时实例化 DV 接口；接口拉取机制留到后续实体类型或迭代。 |
| 生产级检索基础设施 | 不引入三方检索组件、生产级向量库或 SQLite FTS5 必需实现。 |
| 本地私密内容治理 | 真实 API 配置和完整请求响应只允许 ignored 路径本地保存，不进入本文基线。 |

### 1.3 术语定义

| 术语 | 定义 |
| --- | --- |
| 设计就绪 SR | 范围、输入、输出、异常、验收和设计输入提示足够明确，可直接作为功能设计章节或模块边界输入的 SR。 |
| `alarm` 实体 | V1 唯一目标实体类型，表示告警知识/事实类实体，不表示运行时告警事件实例。 |
| mention | Query 中待识别和链接的实体词片段，V1 每条 Query 最多 1 个 mention。 |
| `no_match` | Query 中出现实体形态，但不应链接到任何已知实体。 |
| `not_required` | Query 没有实体链接需求，应在候选召回前绕过实体链接。 |

## 2 系统总体说明

本 addendum 不改变 V1 的系统边界。V1 仍基于 Python 3.12、Flask Web/API、OpenAI-compatible LLM adapter、默认 `offline_demo` 和本地安全配置边界。

优化后的 V1 需求到设计流如下：

```text
V1 requirement baseline
  -> SR decomposition addendum
  -> independent requirement review focused on SR design-readiness
  -> disposition and closure verification
  -> V1 function design
```

V1 运行时能力在需求层被拆为以下责任块：

```text
Web/API mode boundary
  -> sample loaders and validators
  -> mention recognition and normalization
  -> candidate retrieval and ranking
  -> entity linking status decision
  -> evaluator and reports
  -> security/config/log redaction boundary
```

## 3 需求总体描述

### 3.1 补充背景

用户已确认 DV 流程优化：IR 阶段必须完成可指导功能设计的 SR 需求分解；IR 独立评审必须站在功能设计视角检查 SR 拆分是否合理。V1 原需求文档中的 SR-V1-002、SR-V1-003 偏需求活动，SR-V1-004 过宽，SR-V1-005 与检索规划重叠，因此不能直接进入功能设计。

### 3.2 补充目标

- 保留 V1 旧需求闭环的范围、样例和验收结论。
- 将旧 SR 重新拆为设计就绪 SR，减少功能设计阶段重新拆需求的空间。
- 明确每个 SR 的责任模块、输入输出、异常语义、验收要点和设计输入提示。
- 将 SR 分解合理性纳入下一轮独立需求评审范围。

### 3.3 与旧 SR 的映射

| 旧 SR | 处理方式 | 新 SR |
| --- | --- | --- |
| SR-V1-001 Web demo LLM 模式切换与配置 | 保留并细化为 Web/API 状态 SR | SR-V1-A01 |
| SR-V1-002 真实 Query 样例接收与标注 | 从流程活动改写为 Query dataset schema/loader/validator SR | SR-V1-A03、SR-V1-A07 |
| SR-V1-003 实体数据结构审视 | 从分析活动改写为 `alarm` schema/catalog/loader SR | SR-V1-A02 |
| SR-V1-004 检索算法规划与设计 | 拆分为 mention、linking、retrieval、evaluation | SR-V1-A04、SR-V1-A05、SR-V1-A06、SR-V1-A07 |
| SR-V1-005 实体来源、运行时存储与索引 | 拆分到 catalog loader、内存索引和安全配置边界 | SR-V1-A02、SR-V1-A06、SR-V1-A08 |

## 4 需求明细 - SR 分解补充

### 4.1 IR-V1-001 DVEntityLinking V1 增强 SR Addendum

#### 4.1.1 IR 描述

##### 4.1.1.1 IR 原始需求

| 字段 | 内容 |
| --- | --- |
| 需求来源 | 用户流程优化确认和 V1 SR 分解复审 |
| 需求编号 | IR-V1-001-ADDENDUM |
| 标题 | V1 可设计 SR 分解补充 |
| 状态 | 草稿，待独立需求评审 |
| 处理人 | Codex |

**原始需求描述**：

IR 阶段要完成对需求的分解，能够指导后续的设计并为每个 SR 提供输入；需求分解是否合理，要作为 IR 独立评审阶段的重要关注内容，特别要站在功能设计的角度分析是否拆分合理。

##### 4.1.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| IR 编号 | IR-V1-001-ADDENDUM |
| 需求标题 | DVEntityLinking V1 SR 分解补充 |
| 需求类型 | 功能性需求 + 非功能性需求 |
| 优先级 | 高 |
| 目标版本 | V1 |

##### 4.1.1.3 IR 扩展信息

**业务背景**：

V1 已有 `alarm` only 样例、LLM 模式、安全边界、检索和评测验收要求。为了按优化后的 DV 流程进入功能设计，需要将这些要求拆成更小、更稳定的 SR，确保设计阶段可以围绕模块边界、接口、异常和测试映射展开，而不是重新解释需求主题。

**需求方案**：

采用 8 个补充 SR 作为 V1 功能设计输入。每个 SR 包含责任模块、输入、输出、异常语义、验收要点和设计输入提示。原 V1 IR 的范围、非范围、样例和验收仍然有效；本 addendum 只补充分解粒度。

**实现细节**：

本文不定义代码级实现。所有实现方案必须在本 addendum 完成独立需求评审、评审处置和闭环验证后，在功能设计阶段展开。

#### 4.1.2 需求分解列表

##### 4.1.2.1 SR-V1-A01 Web/API LLM 模式切换与状态输出

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A01 |
| 标题 | Web/API LLM 模式切换与状态输出 |
| 类型 | 功能 SR |
| 责任模块 | Web/API、LLM adapter boundary |
| 优先级 | 高 |

**#需求背景#**：

V1 需要让用户在 Web demo 和 API 请求中选择 `offline_demo` 或 `llm_enabled_demo`，并能观察真实 LLM 是否启用、是否降级和失败原因。

**#需求价值#**：

为运维 Copilot 和故障 Agent 的实体链接 demo 提供可验证的 LLM nominal path，同时保证默认离线回归稳定、失败可解释、安全信息不泄露。

**#需求内容#**：

- Web demo 必须提供 mode selector，支持 `offline_demo` 和 `llm_enabled_demo`。
- Web/API 必须接收或继承 `mode` 参数；缺省时使用启动配置默认 mode，V1 默认值为 `offline_demo`。
- Web/API 必须接收或继承 `allow_fallback` 参数；缺省时使用启动配置默认值，V1 默认值为 `true`，显式传入 `false` 时不得自动降级。
- API 必须返回 `requested_mode`、`effective_mode`、`llm_enabled`、`degraded`、`fallback_allowed`、`fallback_used`、`error_code`、`provider`、`model_alias` 和 `result_source`。
- 启动配置必须保留默认 mode，默认值为 `offline_demo`。
- `llm_enabled_demo` 在本地配置缺失、鉴权失败、超时、HTTP 异常或响应 schema 异常时，必须返回结构化状态。
- 当 `allow_fallback=false` 且 LLM 失败时，不得返回离线结果伪装成功。
- `mode` 不在允许枚举内时必须返回 `invalid_mode`，`allow_fallback` 不是 boolean 时必须返回 `invalid_allow_fallback`，两者都不得进入实体链接。
- catalog 或 Query dataset validation 失败时，Web/API 必须投影为结构化错误状态，`result_source=none`，不得输出 linked/ambiguous/no_match/not_required 伪结果。

**#需求范围#**：

包括 Web/API 模式选择、状态输出和降级语义。不包括真实 LLM 服务质量保障或供应商侧问题处理。

**#约束条件#**：

不得展示 API key、base URL 原文、Authorization header、完整请求、完整响应或原始 LLM 日志。自动化默认不依赖真实 LLM。

**设计输入提示**：

功能设计需定义 API request/response schema、UI 控件状态、`allow_fallback` 默认值和承载方式、LLM adapter 错误映射、fallback 决策点、invalid parameter error contract、本地数据验证错误投影和默认配置加载顺序。

##### 4.1.2.2 SR-V1-A02 `alarm` 实体 schema 与预置 catalog 加载

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A02 |
| 标题 | `alarm` 实体 schema 与预置 catalog 加载 |
| 类型 | 功能 SR |
| 责任模块 | entity catalog loader、schema validator |
| 优先级 | 高 |

**#需求背景#**：

V1 只覆盖 `alarm` 告警知识/事实实体。用户已确认 9 个可提交告警实体样例，采用内部 `entity_id`、`canonical_name`、`aliases` 和 `description` 的最小字段契约；不再要求样例级 `data_layer`、`can_commit`、`sensitive_level` 等非核心字段。

**#需求价值#**：

为实体链接提供稳定实体目录，避免将未确认的 DVKnowledge 扩展字段或运行时告警实例混入 V1 baseline。

**#需求内容#**：

- 默认实体 catalog 路径为 `samples/real/entity_examples.json`。
- 文件 metadata 必须包含 `schema_version=v1.alarm_entity.2`、`entity_type_scope=["alarm"]` 和 `entity_count`。
- 每个实体必须包含 `entity_id`、`entity_type=alarm`、`canonical_name`、`aliases` 和 `description`。
- loader 必须校验 JSON 结构、schema version、非空实体集、重复 `entity_id`、重复高置信告警号/数字别名、非 `alarm` 类型和实体字段完整性。
- 加载失败时不得静默部分加载，不得进入正常链接路径。

**#需求范围#**：

包括预置配置文件加载和 schema 校验。不包括通过 DV 运行时接口拉取告警实例实体。

**#约束条件#**：

DVKnowledge 中 severity、impact、possible_causes 等字段当前只作为参考上下文，不进入 V1 实体 schema 必填或可选字段基线。

**设计输入提示**：

功能设计需定义 entity dataclass/schema、loader error object、重复 alias 策略、catalog lifecycle 和 degraded/error 状态对 Web/API 的传递方式。

##### 4.1.2.3 SR-V1-A03 Query 样例 schema、评测数据集加载与校验

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A03 |
| 标题 | Query 样例 schema、评测数据集加载与校验 |
| 类型 | 功能 SR |
| 责任模块 | query dataset loader、annotation validator |
| 优先级 | 高 |

**#需求背景#**：

V1 启动 Query 样例已扩展为 16 条，每条最多 1 个实体词，覆盖 linked、ambiguous、no_match 和 not_required。Query 样例是 V1 验收和评测器输入，不只是需求分析附件，并且只保留实体链接评测需要的最小字段。

**#需求价值#**：

将真实 Query 转为可复现评测资产，确保功能设计和测试开发可围绕同一 schema、span 和 expected entity 语义工作。

**#需求内容#**：

- 默认 Query 样例路径为 `samples/real/query_samples.json`。
- 文件 metadata 必须包含 `schema_version=v1.alarm_query.2`、`query_count` 和 `max_one_entity_mention_per_query=true`。
- 每条 Query 必须包含 `id`、`query`、`mentions`、`expected_entities` 和 `expected_status`。
- 有 mention 时，`span` 必须为 0-based end-exclusive，且 `query[start:end] == mention.text`。
- `expected_entities` 引用的 `entity_id` 必须存在于实体 catalog。
- `expected_status` 为 `no_match` 或 `not_required` 时必须包含 `negative_reason`。
- validator 必须拒绝缺失文件、非法 JSON、metadata schema 不匹配、`query_count` 与实际数量不一致、重复 `id`、缺失必填字段、`expected_status` 不在枚举内、`mentions` 超过 1 个、span 越界或与文本不一致、expected entity 引用不存在、negative query 缺少 `negative_reason`、`not_required` 带有 mention 或 expected entity、`linked` 不等于 1 个 expected entity、`ambiguous` 少于 2 个 expected entity 等异常。
- Query dataset validation 失败时必须产生结构化 validation error，不能部分加载，不能作为 evaluator pass/fail 证据。

**#需求范围#**：

包括样例加载、schema 校验、span 校验、expected entity 引用校验和评测输入对象形成。不包括生产原始 payload 处理平台。

**#约束条件#**：

`word2entity`、`query_id`、`query_text` 不作为 V1 canonical 字段。not_required 样例允许 `mentions=[]` 和 `expected_entities=[]`。`source_scene`、`difficulty`、`expected_intent` 不进入 V1 最小样例契约。

**设计输入提示**：

功能设计需定义 QuerySample、MentionAnnotation、ExpectedEntity、ValidationError、fail-closed loader 行为，以及 loader 与 evaluator 的数据交接结构。

##### 4.1.2.4 SR-V1-A04 alarm mention 识别边界与规范化

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A04 |
| 标题 | alarm mention 识别边界与规范化 |
| 类型 | 功能 SR |
| 责任模块 | mention recognizer、normalizer |
| 优先级 | 高 |

**#需求背景#**：

V1 每条 Query 最多 1 个实体词，但实体词可能以告警 ID、数字 ID、告警名称或 ID+名称同时出现。短 ID 和数字别名存在子串误匹配风险。

**#需求价值#**：

提高实体链接入口质量，避免把不需要匹配的 Query 或子串噪声送入候选召回，兼顾准确率和召回率。

**#需求内容#**：

- mention 识别必须支持告警号格式、数字别名、canonical name、英文名称片段和 ID+名称组合。
- V1 每条 Query 最多输出 1 个 mention；如识别到多个候选 mention，必须按设计规则选择或返回结构化限制状态，不能隐式多实体处理。
- not_required 场景应在候选召回前绕过实体链接。
- mention normalizer 必须保留原始 text、span、normalized_text 和识别来源。
- 短 ID 或数字别名必须按完整 token/边界匹配，不得使用裸 substring 作为高置信匹配。

**#需求范围#**：

包括 V1 `alarm` mention 的离线识别和 LLM 辅助识别边界。不包括多实体 Query 链接、不包括跨句复杂事件抽取。

**#约束条件#**：

LLM 输出只能作为辅助路径；默认离线路径必须可独立完成回归。LLM 返回非法 schema 时必须进入结构化降级或错误。

**设计输入提示**：

功能设计需定义 mention priority、token boundary 规则、normalization 函数、not_required 判定前置点、LLM mention schema 和 fallback 行为。

##### 4.1.2.5 SR-V1-A05 alarm 实体链接与状态判定

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A05 |
| 标题 | alarm 实体链接与状态判定 |
| 类型 | 功能 SR |
| 责任模块 | entity linker、status resolver |
| 优先级 | 高 |

**#需求背景#**：

一个实体词可能对应一个实体、多个实体或没有任何实体。V1 需要明确 linked、ambiguous、no_match 和 not_required 的状态语义，避免为了召回而制造误匹配。

**#需求价值#**：

为 Copilot 和故障 Agent 提供可信的实体链接结果：能链接时给出 Top-1，歧义时保留候选，不应匹配时明确不返回实体。

**#需求内容#**：

- 输出状态必须至少包含 `linked`、`ambiguous`、`no_match` 和 `not_required`。
- `linked` 表示 Top-1 唯一且高置信命中。
- `ambiguous` 表示同一 mention 命中多个合理实体，必须返回去重候选，不强制选一个。
- `no_match` 表示出现实体形态但不应命中任何已知实体。
- `not_required` 表示 Query 无实体链接需求，应不进入候选召回或返回空候选。
- linked 和 ambiguous 结果必须带 `entity_id`、`entity_type`、`canonical_name`、match_reason、score 或排序解释。

**#需求范围#**：

包括 V1 `alarm` 实体链接状态判定和结果结构。不包括跨类型实体消歧、不包括运行时事件实例链接。

**#约束条件#**：

no_match/not_required 不允许产生实体候选；短 ID 子串不得导致 linked；ambiguous 不得伪装成 linked。

**设计输入提示**：

功能设计需定义 LinkResult schema、候选阈值、状态决策树、ambiguous candidate cap、排序解释和错误/降级状态与链接状态的关系。

##### 4.1.2.6 SR-V1-A06 内存索引、候选召回与排序解释

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A06 |
| 标题 | 内存索引、候选召回与排序解释 |
| 类型 | 技术 SR |
| 责任模块 | in-memory index、candidate retriever、ranker |
| 优先级 | 高 |

**#需求背景#**：

用户已确认 V1 优先使用 Python 内存索引，不引入三方检索组件；SQLite FTS5 仅作为后续可选路线。V1 需要兼顾长告警 ID、数字别名、名称匹配、歧义候选和短 ID 子串保护。

**#需求价值#**：

在少依赖、可解释、可测试的基础上支撑 V1 检索和链接，避免过早引入复杂基础设施。

**#需求内容#**：

- 运行时应构建告警号精确索引、数字别名精确索引、规范化名称/别名索引和轻量 token 倒排索引。
- 候选召回应支持 exact ID、numeric alias、canonical name、alias token 和英文名称片段。
- 排序必须可解释，至少能区分 exact、alias、name/token、fuzzy 或 LLM-assisted reason。
- Top-K 默认 K=5，返回前必须按 `entity_id` 去重。
- 索引构建失败或 catalog 无效时必须返回结构化错误，不得误链接。

**#需求范围#**：

包括 V1 单进程内存索引和候选召回排序。不包括持久化索引、分布式索引、向量库、embedding 服务或生产级同步。

**#约束条件#**：

禁止将裸 substring 作为高置信匹配；`51` 不应命中 `ALM-151` 或 `ALM-51020`。索引数据不得包含未确认敏感字段。

**设计输入提示**：

功能设计需定义 IndexBundle、index build lifecycle、normalization/tokenization、candidate score components、tie-breaker 和 debug explanation 字段。

##### 4.1.2.7 SR-V1-A07 V1 评测器与验收指标

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A07 |
| 标题 | V1 评测器与验收指标 |
| 类型 | 功能 SR |
| 责任模块 | evaluator、report generator |
| 优先级 | 高 |

**#需求背景#**：

用户明确要求验收测试充分覆盖无法匹配或不需要匹配场景，准确率和召回率同样重要。V1 样例包含 linked、ambiguous、no_match 和 not_required。

**#需求价值#**：

将主观 demo 表现转成可执行、可回归的验收指标，避免只看命中正例而忽略误匹配。

**#需求内容#**：

- evaluator 必须加载 V1 Query 样例并执行实体链接评测。
- linked 样例要求 Top-1 `entity_id` 命中唯一期望实体。
- ambiguous 样例要求 Top-5 去重候选覆盖全部 `expected_entities`，状态保持 `ambiguous`。
- no_match 和 not_required 样例要求候选为空，任何候选都计为 false positive。
- precision 以 Query 级误链接计算，公式为 `TP / (TP + FP)`；当 `TP + FP = 0` 时记为 1.0 并在报告中标注 `no_positive_predictions`。
- recall 以 Query 级期望命中计算，公式为 `TP / (TP + FN)`；当 `TP + FN = 0` 时记为 1.0 并在报告中标注 `no_expected_positive_cases`。
- linked pass 计为 `TP=1`；linked 无候选或 Top-1 未命中计为 `FN=1`，若返回了错误实体候选则同时计为 `FP=1`。
- ambiguous pass 计为 `TP=1`；Top-5 未覆盖全部 expected entity 或状态不是 `ambiguous` 计为 `FN=1`；若候选包含不在 expected entity 集合中的实体则同时计为 `FP=1`。
- no_match 和 not_required pass 计为 `TN=1`；任何实体候选都计为 `FP=1`。
- V1 启动样例集验收门槛为：所有样例 pass、negative false positive 数为 0、precision=1.0、recall=1.0；任何未达标项均阻塞 V1 验收，除非形成经评审接受的残余风险记录。
- 评测报告必须输出总量、各状态数量、TP/FP/FN/TN、pass/fail、precision、recall、失败样例明细、失败原因和安全脱敏说明。

**#需求范围#**：

包括 V1 样例驱动评测和报告。不包括大规模 benchmark、人工标注平台或线上 A/B 评测。

**#约束条件#**：

默认自动化评测不能依赖真实 LLM；真实 LLM smoke 可以作为补充证据，但不得替代 offline deterministic 回归。

**设计输入提示**：

功能设计需定义 EvaluationCase、EvaluationResult、MetricSummary、TP/FP/FN/TN 计数、failure reason enum、report path、pass/fail derivation 和测试自动化入口。

##### 4.1.2.8 SR-V1-A08 安全、配置和日志边界

| 字段 | 内容 |
| --- | --- |
| SR 编号 | SR-V1-A08 |
| 标题 | 安全、配置和日志边界 |
| 类型 | 非功能 SR |
| 责任模块 | config loader、logging/redaction、artifact hygiene |
| 优先级 | 高 |

**#需求背景#**：

用户在 `config/llm.local.json` 配置了真实 API 以便本地测试。项目必须允许本地真实 LLM smoke，同时避免密钥、真实 base URL 和完整请求响应进入 git 或文档。

**#需求价值#**：

保护真实 DV 内容和本地凭据，使 demo 能在本地验证真实路径，但提交物保持安全、可共享、可评审。

**#需求内容#**：

- `config/llm.local.json` 必须保持 git ignored。
- `config/llm.example.json` 不得包含真实 key，仅允许环境变量名，如 `DVEL_LLM_API_KEY`。
- Web/API 输出不得展示 API key、base URL 原文、Authorization header、完整请求或完整响应。
- 文档、评测报告和 run record 必须过滤敏感字段：`api_key`、`token`、`cookie`、`authorization`、`password`、`secret`、`payload`、`raw_request`、`raw_response`、`llm_full_log`。
- `samples/real` 放用户确认可提交的 V1 启动样例；样例契约不再要求提交状态和数据分层字段。

**#需求范围#**：

包括配置文件边界、日志/报告脱敏、样例提交边界和敏感信息扫描要求。不包括企业级权限系统或生产审计平台。

**#约束条件#**：

任何真实 API key、token、cookie、完整生产 payload、完整 LLM 请求响应日志和敏感配置均不得提交。真实 LLM smoke 报告只能记录脱敏摘要。

**设计输入提示**：

功能设计需定义 config precedence、redaction function、safe status projection、ignored path policy、run artifact layout 和 sensitive scan gate。

## 5 补充输入输出契约

### 5.1 SR 到功能设计输入矩阵

| SR | 功能设计必须产出 |
| --- | --- |
| SR-V1-A01 | API request/response schema、Web 控件状态、`mode`/`allow_fallback` 默认值、LLM fallback 状态机、invalid parameter 处理、错误码映射。 |
| SR-V1-A02 | AlarmEntity schema、catalog loader、schema validator、loader error 语义。 |
| SR-V1-A03 | QuerySample schema、annotation validator、span 校验、expected entity 引用校验、fail-closed validation error。 |
| SR-V1-A04 | Mention recognizer、normalizer、token boundary、LLM/offline mention schema。 |
| SR-V1-A05 | LinkResult schema、状态决策树、ambiguous/no_match/not_required 行为。 |
| SR-V1-A06 | In-memory IndexBundle、候选召回、排序解释、短 ID 子串保护。 |
| SR-V1-A07 | Evaluator、TP/FP/FN/TN metric 计算、报告结构、失败样例输出、启动集验收门槛。 |
| SR-V1-A08 | 配置加载、脱敏日志、ignored path、安全扫描和 run artifact 边界。 |

### 5.2 Runtime Handoff 契约

| 交接对象 | 生产 SR | 消费 SR | 关键字段 | 异常传递点 |
| --- | --- | --- | --- | --- |
| Mention | SR-V1-A04 | SR-V1-A06、SR-V1-A05 | `text`、`span`、`normalized_text`、`source`、`confidence` | not_required 前置绕过；多 mention 限制状态；LLM schema error。 |
| CandidateSet | SR-V1-A06 | SR-V1-A05、SR-V1-A07 | `entity_id`、`entity_type`、`score`、`match_reason`、`rank`、`dedup_key` | catalog/index validation error；短 ID 子串保护；Top-K 去重。 |
| LinkResult | SR-V1-A05 | SR-V1-A07、Web/API | `status`、`candidates`、`top_entity`、`error_code`、`result_source`、`explanation` | ambiguous 保留候选；no_match/not_required 空候选；validation/LLM error 不伪装为链接状态。 |

### 5.3 V1 评测计数契约

| expected_status | pass 条件 | fail 计数规则 |
| --- | --- | --- |
| `linked` | 返回 `linked`，Top-1 `entity_id` 等于唯一期望实体。 | 无候选或 Top-1 未命中计 `FN=1`；返回错误实体候选时另计 `FP=1`。 |
| `ambiguous` | 返回 `ambiguous`，Top-5 去重候选覆盖全部 expected entities。 | 未覆盖全部 expected entities 或状态不是 `ambiguous` 计 `FN=1`；候选包含非 expected entity 时另计 `FP=1`。 |
| `no_match` | 返回空候选，不链接任何实体。 | 任何实体候选计 `FP=1`。 |
| `not_required` | 候选召回前绕过或返回空候选。 | 任何实体候选计 `FP=1`。 |

V1 启动样例集的验收聚合公式：

```text
precision = TP / (TP + FP)
recall = TP / (TP + FN)
```

当分母为 0 时，指标记为 1.0 并在报告中注明原因。V1 启动样例集验收阈值为所有样例 pass、negative false positive 数为 0、precision=1.0、recall=1.0。

### 5.4 SR 到验收映射

| SR | 验收关注 |
| --- | --- |
| SR-V1-A01 | Web/API 可切换模式；LLM 失败有结构化状态；离线模式不调用 LLM；invalid mode/allow_fallback 不进入链接。 |
| SR-V1-A02 | 9 个 `alarm` 实体加载并校验；非法 schema、重复 ID/alias、非 alarm 类型失败。 |
| SR-V1-A03 | 16 条 Query 加载并校验；span 与文本一致；expected entity 引用存在；异常数据集 fail-closed。 |
| SR-V1-A04 | ID、数字别名、名称、ID+名称可识别；not_required 绕过；短 ID 不裸 substring。 |
| SR-V1-A05 | linked、ambiguous、no_match、not_required 状态符合样例期望。 |
| SR-V1-A06 | Top-K 去重、排序解释、完整 token 匹配和短 ID 子串保护可测试。 |
| SR-V1-A07 | precision 和 recall 均输出且公式明确；启动集所有样例 pass；no_match/not_required 零误报作为验收门槛。 |
| SR-V1-A08 | 本地真实配置不入库；敏感字段不进入文档、报告和 Web/API 输出。 |

## 6 风险和待确认事项

| 风险/问题 | 状态 | 影响 |
| --- | --- | --- |
| SR 分解是否足够支撑功能设计 | 处置修订中 | 独立评审发现 1 个 P1 和若干 P2/P3，当前已在 V1.7-addendum-draft 中补强，并纳入 V1 样例最小字段反馈。 |
| 8 个 SR 是否过细或边界仍重叠 | 待独立评审 | 影响功能设计章节边界和测试映射。 |
| V1 不覆盖多实体 Query | 已确认范围边界 | 后续 V2+ 需要重新扩展 mention/linking/evaluator SR。 |
| 告警扩展字段暂不进入 schema | 已确认最小字段策略 | 后续如使用 severity、impact、possible_causes 需新决策。 |

## 7 当前结论

本 addendum 将 V1 需求拆分为 8 个设计就绪 SR，覆盖 Web/API LLM 模式、`alarm` catalog、Query dataset、mention、linking、retrieval、evaluator 和安全配置日志边界。独立需求评审已完成，发现 1 个 P1、4 个 P2 和 1 个 P3；V1.7-addendum-draft 已补充 fallback 输入、Query fail-closed 校验、API 参数异常、评测公式、SR 交接表和 V1 样例最小字段契约。

在本 addendum 完成评审处置和闭环验证前，V1 仍不得进入功能设计。

## 附录 A 参考资料

| 编号 | 资料名称 | 来源 |
| --- | --- | --- |
| A1 | V1 需求分析 | [IR-DVEntityLinking-v1-requirements-analysis.md](./IR-DVEntityLinking-v1-requirements-analysis.md) |
| A2 | V1 SR 分解重新审视记录 | [IR-DVEntityLinking-v1-sr-decomposition-reassessment.md](./IR-DVEntityLinking-v1-sr-decomposition-reassessment.md) |
| A3 | DV IR 阶段 SR 需求分解规则 | [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md) |
| A4 | 当前用户决策台账 | [../../current/DECISIONS.md](../../current/DECISIONS.md) |
| A5 | 当前数据契约 | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |

## 附录 B 相关文件

| 编号 | 文件名称 | 版本/状态 |
| --- | --- | --- |
| B1 | `samples/real/entity_examples.json` | `v1.alarm_entity.2`，最小字段可提交样例 |
| B2 | `samples/real/query_samples.json` | `v1.alarm_query.2`，最小字段可提交样例 |
| B3 | [IR-DVEntityLinking-v1-sr-decomposition-addendum-review-input.md](./IR-DVEntityLinking-v1-sr-decomposition-addendum-review-input.md) | 独立需求评审输入包 |
| B4 | [IR-DVEntityLinking-v1-sr-decomposition-addendum-review-record.md](./IR-DVEntityLinking-v1-sr-decomposition-addendum-review-record.md) | 独立需求评审记录 |

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | IR-DVEntityLinking-V1-SR-ADDENDUM |
| 创建日期 | 2026-05-31 |
| 最近更新 | 2026-06-01 |
| 作者 | Codex |
| 状态 | 需求评审闭环已通过，功能设计可承接 |
| 版本 | V1.7-addendum-draft |

## 评审记录

| 评审日期 | 评审方式 | 评审结论 | 状态 |
| --- | --- | --- | --- |
| 2026-05-31 | 两个 no-context/sealed 独立只读评审 | Ready for disposition；无 P0，1 个 P1、4 个 P2、1 个 P3 | 处置中 |
| 2026-05-31 | no-context/sealed 独立闭环验证 | Closed with recorded residual documentation hygiene follow-up | 已闭环 |
