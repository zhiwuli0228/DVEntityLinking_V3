## Why

V4 只读使用 Entity Data Service，实体构建、上游运行数据和知识库数据的获取与持续更新尚未形成受控能力。V5 需要在服务启动后构建并批量发布实体，并以统一的远程请求边界和每日增量更新，保持实体数据可用、可追踪且不破坏 V4 的链接契约。

## What Changes

- 新增实体构建应用服务：服务启动后从调用方配置的运行时数据接口及知识库接口拉取数据，规范化、校验、去重并批量写入 Entity Data Service。
- 新增独立常驻 REST 请求工具：调用方仅提供 URL、请求方法、参数及安全配置引用；认证、超时、重试、响应解码、错误归一化和安全 trace 在工具内部处理。V4 Entity Data 查询适配器与 V5 构建插件共同复用该工具。
- 新增实体构建、批量更新、原子切换与失败处置契约；构建后的实体严格复用 V4 schema，不新增来源、版本、时间或快照字段。
- 新增服务启动首次同步与每日凌晨数据快照刷新；运行中不得并发执行同一同步任务，失败必须可观察且不破坏上一成功数据快照。软件版本不随每日刷新变化。
- 新增独立、可插拔的 V5 Entity Build Plugin；V4 不导入或调用插件，未来可将插件整体迁入 Entity Data Service。
- 新增独立 Query Recall Facade：对外以原始 Query 为核心入参，LLM 参与和 Top-K 等策略由可热加载配置默认控制，并允许少量显式覆盖。
- V5 新增的对外 Query Recall DTO、字段和方法一律去除 `V1` 等版本后缀；现有 V4 `*V1` 类型仅保留兼容适配职责，不向新调用面扩散。
- 新增 V5 IR/SR、追踪矩阵、测试和运行手册，明确 V4 只读链接链路与 V5 写入/更新链路的边界。

## Capabilities

### New Capabilities

- `v5-entity-construction`: 从运行时与知识库来源构建、规范化、校验和批量发布 canonical 实体。
- `v5-rest-request-boundary`: 以独立常驻工具封装 V4/V5 的远程 HTTP/IR 交互及其可靠性、安全与错误语义。
- `v5-scheduled-entity-refresh`: 服务启动同步与每日凌晨实体刷新、并发互斥、失败保留和运行证据。
- `v5-entity-build-governance`: V5 的 IR/SR、来源治理、写入追踪、回退和验收证据。
- `v5-query-recall-facade`: 面向外部调用的简化 Query 召回入口、候选 Top-K 与 LLM 策略配置热加载。

### Modified Capabilities

None; the repository has no baseline OpenSpec capability specifications.

## Impact

Affected areas include a new V5 plugin package, Entity Data Service write-side adapter, plugin configuration, optional host lifecycle integration, scheduler, tests, operational documentation, and V5 baseline artifacts. V4 module composition, public linking DTOs, Entity Data read IR, deterministic fallback, and V4.1 runtime-isolation rules remain unchanged.
