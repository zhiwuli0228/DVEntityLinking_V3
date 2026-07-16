# 当前数据契约

最后更新：2026-06-25

本文档记录当前代码和样例应遵循的核心数据结构。字段说明保持最小必要集合，避免把调试、提交状态或敏感分层字段暴露给用户默认视图。

## V1 Alarm Entity

`samples/real/entity_examples.json` 是 V1 alarm-only 实体样例基线。

根字段：

| 字段 | 含义 |
| --- | --- |
| `metadata.schema_version` | 当前为 `v1.alarm_entity.2` |
| `metadata.entity_type_scope` | 当前仅允许 `["alarm"]` |
| `metadata.entity_count` | 当前为 `9` |
| `entities` | 告警知识实体列表 |

实体字段：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `entity_id` | 是 | 项目内部实体 ID，例如 `DV-ALM-001` |
| `entity_type` | 是 | V1 固定为 `alarm` |
| `entity_name` | 是 | 标准名称，通常包含告警 ID 和英文名称 |
| `alias` | 是 | 可匹配别名，包含数字 ID、`ALM-...`、英文名等 |
| `desc` | 是 | 用于展示和检索解释的简短描述 |

V1 样例不要求 `attributes`、`relationships`、`data_layer`、`source`、`can_commit`、`sensitive_level`。后续若要固化 severity、impact、possible_causes 等 DVKnowledge 字段，必须进入新一轮实体结构决策。

## V1 Query Sample

`samples/real/query_samples.json` 是 V1 Query 样例基线。

根字段：

| 字段 | 含义 |
| --- | --- |
| `metadata.schema_version` | 当前为 `v1.alarm_query.2` |
| `metadata.query_count` | 当前为 `16` |
| `metadata.max_one_entity_mention_per_query` | V1 固定为 `true` |
| `queries` | Query 样例列表 |

Query 字段：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `id` | 是 | 样例 ID |
| `query` | 是 | 用户 Query 文本 |
| `mentions` | 是 | 0 或 1 个实体词标注 |
| `expected_entities` | 是 | 期望链接实体列表 |
| `expected_status` | 是 | `linked`、`ambiguous`、`no_match`、`not_required` |
| `negative_reason` | 条件必填 | `no_match` 或 `not_required` 的负例理由 |

Mention 字段：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `text` | 是 | Query 中的实体词文本 |
| `span` | 是 | 0-based、end-exclusive span，必须与 `query[start:end]` 一致 |
| `expected_entity_ids` | 是 | 该 mention 期望覆盖的实体 ID 集合 |

不再使用 `word2entity`、`query_id`、`query_text` 作为规范主契约。

## Link Result

运行时链接结果至少需要表达：

| 字段 | 含义 |
| --- | --- |
| `status` | `linked`、`ambiguous`、`no_match`、`not_required`、V2 Query 级 `partial` 或结构化错误/降级状态 |
| `mentions` | 识别到的 mention 简要信息 |
| `candidates` | 候选实体列表，包含实体 ID、类型、名称、得分和匹配理由 |
| `top_entity` | `linked` 时的 Top-1 实体；其他状态可为空 |
| `error_code` | invalid input、invalid mode、LLM/schema error 等结构化错误 |
| `result_source` | `offline_demo`、`llm_enabled_demo` 或 fallback 来源 |

前端默认展示运行状态、mention 简要信息、候选实体、实体详情和相似实体；完整 JSON 只作为折叠调试信息。

## LLM 配置边界

- `config/llm.example.json` 只能包含示例结构和环境变量名。
- `config/llm.local.json` 只允许本地使用，必须保持 ignored。
- Web/API 不得展示 API key、真实 base URL、完整请求、完整响应或完整日志。
- `offline_demo` 是默认回归和验收模式；真实 LLM smoke 只能作为条件补证。

## V2 Contract Direction

V2 已进入初始代码实现阶段。当前已落地 confirmed-sample startup slice，runtime mock adapter 仍作为后续扩展边界保留。当前约束如下：

| 项 | V2 方向 |
| --- | --- |
| 实体类型 | `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`。 |
| 实体字段 | 暂沿用最小字段：`entity_id`、`entity_type`、`entity_name`、`alias`、`desc`。 |
| 结构变更 | 不默认新增字段、关系或类型专属 schema；如需要必须先确认。 |
| 数据来源 | `alarm` 继续使用 V1 预置基线；`ne_type` 来自预置或 DVKnowledge 挖掘；`ne_name` 来源为运行时接口 Mock；KPI 子类型来源包含预置配置、DVKnowledge 挖掘和运行时接口 Mock。 |
| 别名规则 | V2 新增 KPI/网元类实体 `alias` 默认为空数组；任何别名必须特殊标注并经确认，不得自动生成。 |
| 数据预处理 | 统一负责预置数据、DVKnowledge KPI/网元类型候选、运行时 Mock 输出的规范化和校验。 |
| LLM 输出 | 必须经结构化 schema 校验后才能进入链接链路；自然语言解释只能作为说明，不作为事实字段。 |

### V2 Startup Samples

`samples/real/v2_entity_examples.json` 是 V2 新增实体启动样例，并通过 `metadata.base_entity_files` 合并 V1 `alarm` 样例作为 unified catalog 回归基线。

| 字段 | 当前值/规则 |
| --- | --- |
| `metadata.schema_version` | `v2.entity_examples.1` |
| `metadata.entity_type_scope` | `ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key` |
| `metadata.entity_count` | `16`，表示 V2 新增实体数量 |
| `metadata.base_entity_files` | `samples/real/entity_examples.json`，合并 9 个 V1 `alarm` 实体 |
| unified catalog count | `25`，包含 9 个 `alarm` 和 16 个 V2 新增实体 |
| `metadata.alias_default_empty` | `true` |
| `metadata.kpi_meas_objects_included` | `false` |

V2 新增实体仍只包含 `entity_id`、`entity_type`、`entity_name`、`alias`、`desc`。本轮所有新增实体 `alias` 均为空数组。

`samples/real/v2_query_samples.json` 是 V2 Query 启动样例。

| 字段 | 当前值/规则 |
| --- | --- |
| `metadata.schema_version` | `v2.query_samples.1` |
| `metadata.query_language` | `en` |
| `metadata.query_count` | `12` |
| `metadata.multi_mention_supported` | `true` |
| `metadata.max_mentions_per_query` | `2` |
| `expected_status` | Query 级允许 `linked`、`partial`、`no_match`、`not_required` |

V2 mention 必须包含 `text`、`span`、`expected_entity_ids` 和 mention-level `expected_status`。`partial` 表示同一 Query 中至少一个 mention 可链接、至少一个 mention 不匹配或待降级处理。V2 启动样例必须覆盖 alarm + 新增实体同 Query 多 mention。

## V3 Contract Direction

V3 已完成 GUI 决策确认、需求评审、评审处置、需求闭环验证、SR 功能设计评审闭环验证以及初始代码实现。当前实现记录见 [../baselines/v3/IMPLEMENTATION.md](../baselines/v3/IMPLEMENTATION.md) `V3-IMPL.1`；具体 schema、文件格式、类接口和错误枚举以 [../baselines/v3/SR.md](../baselines/v3/SR.md) `V3-SR.2-closed` 与当前实现共同约束。

| 项 | V3 方向 |
| --- | --- |
| 版本目标 | 搁置 V2 遗留视觉证据问题，启动 V3 两层存储和 NER 详细设计；Human Decision Gate 已通过 GUI 确认关闭。 |
| Redis Mock | 实体词到实体 ID 的 KV 缓存接口 Mock；key 来自 `entity_name` + 经确认 `alias`，value 是单实体 ID；不自动生成别名。 |
| 高斯 Mock | 结构化实体数据接口 Mock；至少支持按 `entity_id` 查询实体记录。 |
| 默认外部依赖 | 默认不连接真实 Redis、真实 GaussDB、真实 DV 生产接口或真实 LLM；当前实现仅加载本地 JSON Mock。 |
| 实体结构 | V3 初始继续沿用最小实体字段：`entity_id`、`entity_type`、`entity_name`、`alias`、`desc`；类型专属字段后续另行确认。 |
| NER 输出 | 需显式表达 query/mention 状态、span、normalized text、entity-word key、candidate type、Redis lookup 状态、高斯 lookup 状态、候选实体和结构化错误。 |
| NER 内部 schema | 允许内部 schema 扩展，用于 stage trace、storage lookup 和重构隔离；外部 API 与样例提交字段受控。 |
| LLM 角色 | 默认离线 deterministic 可回归；LLM 仅作为可选分类、解释或 rerank 增强。 |
| 冲突处理 | 同一实体词对应多个实体时，冲突数据加载 fail-closed，不进入链接链路；不得静默改为多值 Redis 结构。 |
| 样例策略 | 复用 V1/V2 已确认样例；当前已新增 `samples/real/v3_gauss_entities.json`、`samples/real/v3_redis_entity_words.json` 和 `samples/real/v3_ner_golden_cases.json`。 |
| 安全边界 | 不提交真实 Redis/Gauss 连接串、账号、密码、token、真实 DV payload 或完整 LLM 请求响应。 |

### V3 Redis Mock KV

| 字段 | 含义 |
| --- | --- |
| `metadata.schema_version` | 当前为 `v3.redis_entity_words.1`。 |
| `metadata.word_count` | 当前为 `11`。 |
| `metadata.key_scope` | 固定为 `entity_name` 和 `confirmed_alias`。 |
| `metadata.alias_auto_generated` | 当前必须为 `false`。 |
| `entity_words[]` | Redis Mock KV 列表。 |
| `entity_word` | Redis key 的语义字段，表示实体词，来源限于 `entity_name` 和经确认 `alias`。 |
| `normalized_key` | 运行时按 Unicode NFKC、`casefold()`、移除 whitespace 重新计算并校验。 |
| `entity_id` | Redis value 的语义字段，表示实体 ID。当前按单值处理；重复 key 冲突加载 fail-closed。 |
| `source` | 只允许 `entity_name` 或 `confirmed_alias`，不得包含真实生产路径或敏感连接信息。 |
| `normalization_version` | 当前为 `v3.entity_word_norm.1`。 |

### V3 高斯 Mock 查询

| 字段 | 含义 |
| --- | --- |
| `metadata.schema_version` | 当前为 `v3.gauss_entities.1`。 |
| `metadata.entity_count` | 当前为 `7`。 |
| `entities[]` | 高斯 Mock 结构化实体列表。 |
| `entity_id` | 查询主键。 |
| `entity_type` | 实体类型。 |
| `entity_name` | 标准名。 |
| `alias` | 经确认别名列表。 |
| `desc` | 展示和检索解释所需的简短描述。 |

### V3 NER Golden Cases

| 字段 | 含义 |
| --- | --- |
| `metadata.schema_version` | 当前为 `v3.ner_golden_cases.1`。 |
| `metadata.query_count` | 当前为 `6`。 |
| `queries[]` | V3 两层存储和 NER pipeline golden cases。 |
| `expected_status` | 覆盖 `linked`、`partial`、`no_match`、`not_required`。 |
| `mentions[]` | 期望 mention，包含 `text`、`span`、`expected_status` 和 `expected_entity_ids`。 |

### V3 NER 结果

| 字段 | 含义 |
| --- | --- |
| `query_status` | Query 级状态，需兼容 linked、partial、ambiguous、no_match、not_required 和结构化错误/降级状态。 |
| `mentions[]` | mention 级结果列表。 |
| `mentions[].text` | Query 原文中的实体词文本。 |
| `mentions[].span` | 0-based、end-exclusive span。 |
| `mentions[].normalized_text` | 供实体词缓存查询使用的归一化文本。 |
| `mentions[].entity_word_key` | Redis lookup 使用的实体词 key。 |
| `mentions[].candidate_type` | NER 判断出的候选实体类型或不确定原因。 |
| `mentions[].storage_lookup` | 可安全展示的 Redis/Gauss lookup 状态。 |
| `mentions[].candidates` | 候选实体列表。 |
