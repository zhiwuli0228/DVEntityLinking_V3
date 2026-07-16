# DVEntityLinking V5 需求分析文档

最后更新：2026-07-16  
状态：设计基线，待评审后进入实现  
上游基线：[V4 IR](../v4/IR.md)、[V4.1 IR](../v4.1/IR.md)

## 1. 定位

V5 在不改变 V4 只读实体链接公开契约的前提下，新增一个独立、可插拔的实体构建能力。宿主服务可选择在启动后调用该能力，从调用方声明的运行时数据接口和知识库接口获取数据、构建 V4 schema 实体并批量更新 Entity Data Service；随后在每日凌晨更新数据。

V5 是实体数据的**构建与发布侧**，不是让实体链接 module 直连数据库，也不是恢复 V1–V3 的本地 JSON、Redis 或 Gauss Mock 运行时依赖。

## 2. 目标与范围

| ID | 目标 | 可验收结果 |
| --- | --- | --- |
| IR-V5-001 | 实体构建 | 将运行时数据和知识库数据映射为符合 V4 schema 的标准实体。 |
| IR-V5-002 | 批量更新 | 仅将完整校验通过的实体集合原子更新到 Entity Data Service。 |
| IR-V5-003 | 共享远程交互隔离 | V4 Entity Data 读适配器与 V5 构建插件均仅通过独立常驻 REST 请求工具声明请求；不得感知底层 HTTP client。 |
| IR-V5-004 | 定时更新 | 服务启动后执行首次同步，并在显式时区的每日凌晨执行刷新；单进程不允许重叠运行。 |
| IR-V5-005 | 失败安全 | 拉取、构建、校验或快照切换失败时保留上一成功数据快照，不得清空或部分替换。 |
| IR-V5-006 | 兼容与去版本化 | 链接状态、Entity Data 只读 IR 和运行时隔离规则保持不变；V5 对外 DTO 不带 `V1` 等版本后缀。 |
| IR-V5-007 | 可审计 | 每次构建、发布、跳过和失败都有安全摘要，且不记录凭据、完整 URL 或完整上游 payload。 |
| IR-V5-008 | 原子与可迁移 | 实体构建、远程请求、发布与调度各自独立；构建能力可整体迁移至 Entity Data Service，而不修改 V4。 |
| IR-V5-009 | 简化查询召回 | 对外提供仅以原始 `query` 为核心入参的 mention/实体召回门面；LLM、Top-K 等策略由可热加载配置控制。 |

### 范围内

- 运行时数据与知识库数据的来源 adapter、V4 schema 映射、校验、合并和冲突拒绝。
- 独立常驻 REST 请求工具的请求执行、认证注入、超时、有限重试、响应解码和安全错误投影；V4 Entity Data 查询适配器复用该工具。
- Entity Data Service 的批量更新/原子切换端口，以及上一成功数据保留。
- 服务启动同步、每日凌晨定时刷新、状态观测与单进程互斥。
- V5 IR/SR、来源清单、测试、运行手册与追踪证据。
- 作为独立插件的实体构建门面与可选宿主生命周期接入。
- 独立的 Query Recall Facade、运行配置文件及其安全热加载。

### 范围外

- V4 链接 module 直连数据库、执行 SQL，或承担实体写入逻辑。
- 将实体构建器、调度器或 REST 工具嵌入 V4 linking pipeline，或使 V4 反向调用这些新增能力。
- 自动生成未经确认的 alias、以自由文本覆盖 V4 标准字段，或放宽实体词单值/冲突 fail-closed 规则。
- 猜测正式来源 URL、凭据、认证方式、分页协议或 Entity Data Service 写接口。
- 未经部署方案确认的分布式锁、多副本调度协调及自动反向迁移。
- 要求调用方构造 V4 兼容层 DTO、管理 LLM adapter 或传递全部运行参数。

## 3. 业务与数据约束

1. 构建后的每个实体严格使用 V4 已有 schema；V5 不新增 `canonical`、来源、版本、时间或快照等实体字段。
2. `entity_id`、`entity_type`、`entity_name` 为必填，alias 仍必须是确认来源提供的值。
3. 合并必须确定性：按稳定实体标识和已配置来源优先级处理；关键字段冲突、必填字段缺失或 active normalized entity word 冲突时整批拒绝更新。
4. V5 只在完整构建和验证成功后请求原子更新当前实体数据；失败后 Entity Data Service 中最近成功数据继续对 V4 提供读取。

### 3.1 软件版本与数据快照分离

V5.x 软件版本只在代码、公开契约、V4 schema、构建规则或来源优先级发生经评审的变更时演进。启动同步和每日刷新只是数据更新，不得被命名、记录或宣传为新的软件版本，也不得向实体新增版本或快照字段。

每个候选快照必须先完成完整校验与对账，再以原子方式切换为 `current`；回退仅切回上一成功数据快照。快照保留、过期和清理由 Entity Data Service 的数据治理策略管理，不能由单次刷新任务隐式删除。

## 4. REST 请求边界

| 调用方提供 | REST 工具内部负责 | 禁止项 |
| --- | --- | --- |
| URL、方法、query params、JSON body、认证配置引用、超时/重试策略标识、可选 idempotency key | 底层 client、认证注入、请求执行、超时、有限重试、响应解码、错误分类与安全 trace | 业务 adapter 直接导入 HTTP client、日志中输出 token/Authorization/完整 payload |

仅共享 `RestRequestTool` 可以访问底层 HTTP client 或平台 IR client。V4 的 `IrEntityDataClient`、`RestEntityDataClient`，以及 V5 的来源/发布 adapter 都仅接收其结构化成功值或结构化错误；它们各自只保留 Entity Data 或来源协议的 payload 映射和 schema 校验。

## 4.1 V4 查询场景优化

V4 的 `MATCH_WORDS`、`BATCH_GET_ENTITIES`、`HEALTH` 及既有写入管理调用继续保持原有公开 Entity Data 契约，但不再自行处理 `urllib`、平台 client、超时或 transport 异常。它们改由共享 REST 工具执行：

| V4 当前适配器 | 优化后职责 | 共享工具职责 |
| --- | --- | --- |
| `IrEntityDataClient` | 组装 Entity Data operation envelope，校验业务响应。 | 调用平台 IR transport、处理超时/鉴权/传输错误。 |
| `RestEntityDataClient` | 组装本地契约测试请求，校验业务响应。 | 调用 HTTP transport、编码/解码、处理超时/HTTP/传输错误。 |

该优化不改变 V4 module 的公开 DTO、状态语义、IR URL 或 `platform_client` 装配参数；`platform_client` 仅作为共享 REST 工具可注入的 transport 实现。共享工具不属于 V5 Entity Build Plugin，因此 V4 依赖共享工具不构成对 V5 的依赖。

## 4.2 对外 Query Recall Facade

V5 提供独立的 `QueryRecallFacade` 作为宿主对外召回 mention 与相关实体的默认入口：

```python
result = query_recall.recall(query="查询 ALM-51020 的关联实体")
```

除原始 `query` 外，调用方可选传入经批准的少量覆盖项（例如 `use_llm`、`top_k`）；未传入时，门面从当前有效配置读取策略。门面返回无版本后缀的 `QueryRecallResult`，其中包含稳定的状态、mentions、candidates、top entity、错误与降级信息；不得暴露或要求调用方传递 V4 兼容层 DTO、`agent_context`、`extraction_mode`、`allow_fallback`、HTTP 配置或 LLM adapter。

V4 现有 `LinkRequestV1` / `LinkResponseV1` 仅在过渡兼容适配层保留。V5 不得新增任何带版本后缀的对外 DTO、字段或方法；实现阶段应以无版本后缀的内部稳定模型完成映射，并登记旧类型的弃用路径。

配置文件至少包含 `recall.use_llm`、`recall.top_k`、LLM 失败回退策略及允许的实体类型范围。配置热加载必须先完整解析和校验，再原子替换当前有效配置；新配置仅影响后续请求，解析/校验失败时继续使用最近一次有效配置，并记录安全诊断。配置文件中的密钥、URL 或认证引用仍由共享 REST 工具的安全配置边界管理，不得在查询结果中暴露。

## 5. 生命周期与调度

| 阶段 | 行为 | 验收要求 |
| --- | --- | --- |
| 服务启动 | 根据配置执行一次首次 refresh，可选择 blocking 或 background 模式。 | 暴露 `pending/running/succeeded/failed/skipped` 状态。 |
| 每日刷新 | 按显式时区计算每日 `00:00`；默认 `Asia/Shanghai`，可覆盖。 | 构建候选数据快照；空闲时只执行一次。 |
| 重叠触发 | 上一轮仍执行时收到触发。 | 不并发发布，记录 `refresh_skipped_in_progress`。 |
| 刷新失败 | 拉取、校验或快照切换失败。 | 保留上一成功数据快照，生成安全摘要。 |

多实例部署的调度 leader 由宿主部署层明确保证；在未引入分布式锁前，V5 只承诺单进程互斥。

### 5.1 一次任务与定时任务

每个实体来源以 `EntityBuildTask(name, source, mode)` 注册，`mode` 只能为 `once` 或 `daily`，但所有 source 都必须返回同一份 V4 schema 实体列表。一次任务由 `run_once()` 显式执行一次并缓存成功结果；定时任务由 `run_daily()` 执行，新增来源只需注册新的 `daily` task。

定时任务不得仅用自身的局部返回覆盖全部实体数据。runner 必须把已成功的一次任务结果与本轮全部定时任务结果合并、校验后再原子发布；任一被执行来源失败时，不更新缓存和当前实体数据。

`DailyRefreshScheduler` 不私自创建后台线程；宿主的生命周期定时器按分钟调用 `run_if_due(now)`，其仅在本地时区每日 `00:00` 触发一次 `run_daily()`，同日重复触发返回跳过状态。这让宿主可替换为框架 scheduler、平台 cron 或未来的数据库服务调度，而无需改动构建逻辑。

## 5.1 原子插件边界

V5 实体构建必须以独立插件/包提供，其公开门面只暴露构建、刷新和运行状态能力。V4 只能继续通过既有 Entity Data 只读 IR 获取实体数据，不得导入、实例化或触发 V5 构建类。

宿主负责选择是否装配该插件、何时调用启动刷新，以及在未来将整套构建插件迁入承载数据库的 Entity Data Service。迁移时仅替换宿主装配与发布端口实现；V4 公开 DTO、链接 pipeline 和只读 IR 不得改动。

## 6. 验收矩阵

| 验收 ID | 验收项 | 最小证据 |
| --- | --- | --- |
| AC-V5-001 | 两类来源可构建 canonical entity | fixture adapter 与映射/来源单测。 |
| AC-V5-002 | 冲突/缺失 fail-closed | 构建校验和零发布断言。 |
| AC-V5-003 | REST 工具是唯一远程访问路径 | 静态依赖检查和 transport 行为测试。 |
| AC-V5-004 | 批量更新可安全重试和原子切换 | publisher contract/integration test。 |
| AC-V5-005 | 启动与每日数据更新正确 | fake clock/scheduler、互斥、对账和上一成功数据保留测试。 |
| AC-V5-006 | V4/V4.1 不回退且 V5 门面去版本化 | 旧调用兼容、无版本 V5 DTO 合约、状态兼容、V4 不导入 V5 插件的隔离回归。 |
| AC-V5-008 | 构建能力可独立装配和迁移 | 独立 package/import 测试、端口替换测试。 |
| AC-V5-009 | 对外查询入参简化且策略可动态生效 | facade 合约、配置热加载、LLM/Top-K 覆盖优先级及 V4 兼容回归。 |
| AC-V5-007 | 运行证据安全 | trace/report 无凭据、完整 URL、完整上游 payload 的测试。 |

## 7. 待确认输入

- 正式运行时数据和知识库接口的 owner、认证、分页/游标、版本字段和 SLA。
- Entity Data Service 的候选快照写入、原子切换、快照查询、保留策略和快照回退接口。
- 宿主实例拓扑，以及首次同步应阻塞 readiness 还是后台执行。
