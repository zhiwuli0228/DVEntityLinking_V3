# V5 接口 Mock 方案

`samples/mock/v5_interface_responses.json` 固定模拟运行时与知识库接口的 JSON 返回。测试通过可注入 `RestRequestTool` transport 返回该 fixture；不会访问真实 URL、凭据或数据库。

覆盖场景：两来源成功合并、运行时数据刷新、知识库 `desc/attributes/relationships` 保留、来源 schema 失败、必填字段缺失、跨实体归一词冲突、HTTP 503、发布失败、幂等重复刷新和旧数据保留。`InMemoryEntityPublisher` 仅在完整构建通过后原子替换当前 fixture 数据。

任务 mock 还覆盖：一次 `bootstrap` 任务只调用一次并缓存成功实体；可持续新增的 `daily` 任务与该缓存合并发布；午夜触发一次、同日重复触发跳过、非午夜不执行。所有任务无论类型均返回相同的 V4 schema 实体列表。

分页 mock 使用统一响应包：`items`、`has_more`、可选 `next_cursor`。覆盖首/末页、cursor 续页、缺失 cursor 的 fail-closed 保护；`page_size` 与有限重试次数从接口清单配置读取。

接口级隔离：配置清单中的每个 endpoint 作为独立任务。某一接口失败时继续调用后续接口；成功接口更新本轮数据，失败接口保留最近成功缓存。只要存在可用数据，整体结果为 `partial`，并不阻断后续接口查询。
