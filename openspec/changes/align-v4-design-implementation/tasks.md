## 1. 设计与契约收敛

- [x] 1.1 将 V4 IR、SR 与 module README 中全部生产调用术语统一为“Entity Data IR URL + 平台 Client”，仅在本地契约测试说明中保留 REST。
- [x] 1.2 统一 IR 请求信封：将 `expected_data_version` 明确为 read-operation `payload` 字段，并让 IR/SR、README、IR client 和契约 mock 使用同一 schema。
- [x] 1.3 修正 IR 中 S5 rerank 的失败规则：无论 `allow_fallback` 值为何，超时、非法 schema/ID 或低置信均保留确定性 Top-K 与 `ambiguous`。
- [x] 1.4 在 IR/SR 增加设计—组件—测试映射表，逐项列出能力矩阵的 owner、测试文件和完成状态；缺少任一映射即阻断 V4 验收。

## 2. Entity Data 生命周期与生产装配

- [x] 2.1 扩展 `EntityDataClient` 与 `InternalRouteClient` 的健康检查契约，定义安全的健康响应、错误映射和 data/contract version 语义。
- [x] 2.2 为 `IrEntityDataClient` 实现健康检查；直连 REST adapter 仅补充本地契约测试所需实现，不成为生产装配选项。
- [x] 2.3 使 `ModuleConfig.startup_failure_policy` 生效并校验合法枚举值；`FAIL_FAST` 健康失败时拒绝创建 module，`DEGRADED` 健康失败时允许创建但保留结构化依赖失败语义。
- [x] 2.4 增加工厂黑盒测试：缺 IR URL、缺平台 Client、FAIL_FAST 健康失败、DEGRADED 健康失败、健康成功；每例断言绝不加载 V3 Mock/Redis/Gauss JSON 或直连 HTTP client。

## 3. V1–V3 能力矩阵的领域组件迁入

- [x] 3.1 提取 `LinkingIntentPolicy`，迁移并覆盖 V1/V3 的 not-required、负例与“不调用远端”的 golden cases，替换硬编码 `needs_linking` 规则。
- [x] 3.2 提取 `KnownMentionRecognizer` 与 `UnknownMentionRecognizer`，保留归一化 span 恢复、边界/上下文确认、重复位置和数据库空命中的 unknown/no-match 语义。
- [x] 3.3 提取 `EntityTypeResolver`，统一 request type hint、confirmed word type 与合法 S3 类型线索的收敛、冲突和未知处理，并补充跨类型场景测试。
- [x] 3.4 提取 `CandidateResolver`，实现可解释的候选去重、来源/priority/边界/上下文/类型/有效置信度排序，以及唯一、Top-K、no-match 决策；禁止生成新 ID。
- [x] 3.5 提取 `MentionSelector`，保持最长非重叠、同起点与 priority 的确定性规则，并针对已知/未知/抽取 mention 混合重叠建立独立测试。
- [x] 3.6 提取 `ResultAggregator` 与 `SafeTraceBuilder`，统一 mention 状态、Query 的 linked/partial/ambiguous/no_match/not_required/dependency_failed 聚合及安全 trace 字段。
- [x] 3.7 让 `EntityLinkingModule` 只负责默认组件组装和用例编排；增加组件替换测试，证明公开 V1 DTO 不因内部替换而改变。

## 4. LLM 与异步语义

- [x] 4.1 保持 S3/S5 仅为旧版抽取和歧义候选 rerank 两个 hook；更新单元和黑盒测试，证明不新增实体 ID、alias 或新的 LLM 阶段。
- [x] 4.2 增加 S5 的 strict-mode 回归：`allow_fallback=false` 下 timeout、非法 schema、非法 ID、低置信都必须返回确定性 `ambiguous` Top-K。
- [x] 4.3 将 `link_async` 改为不阻塞调用方事件循环的实现，并新增并发 event-loop 测试验证其响应语义与 `link` 相同。

## 5. 验收与回归门禁

- [x] 5.1 为每个第 2–4 节任务增加独立的负向测试；测试不得依赖 production trace 或私有函数作为唯一 oracle。
- [x] 5.2 扩展 V4 IR 端到端 contract mock，覆盖健康、版本 pinning、服务错误、类型冲突、候选排序、S3/S5 回退和 async 调用。
- [x] 5.3 运行并记录 V1、V2、V3 全量 golden/evaluation、V4 黑盒流程测试、全量 pytest 与静态设计一致性扫描；任何失败阻断验收。
- [x] 5.4 审核 V4 默认运行依赖和公开工厂，确认 Redis、缓存词表、本地持久实体快照、V3 Mock、Gauss/Redis JSON 与 Flask 均未进入核心 module 的默认运行链。
