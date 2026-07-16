## Why

V4 的验收已接近完成，但当前代码仓仍同时承载 V1–V3 的历史实现、Mock 与运行资产。若直接在该状态上继续迭代，会使生产依赖边界、迁移责任和回归结论难以判定，也会阻碍 V4 后续独立演进。

## What Changes

- 建立 V4.1 独立运行边界，使默认 module、公开工厂和生产 adapter 不再依赖历史运行实现、V3 Mock 或本地历史数据资产。
- 冻结并自动校验 V4 的公开 module 契约、状态语义和安全错误语义，新增内容仅允许向后兼容地追加。
- 增加实体数据与配置的可验证迁移工具：支持 dry-run、投影/关系校验、幂等重跑和安全的结构化报告。
- 增加历史行为对照、禁止依赖检查、迁移验证与运行故障测试，形成从 V4 到 V4.1 的可追溯验收证据。
- 建立 V4.1 的历史资产弃用登记和实施追踪文档。

本变更不新增实体链接业务能力，也不改变 V4 的 Entity Data IR、canonical entity schema、候选确认、状态聚合或 LLM 回退语义。

## Capabilities

### New Capabilities

- `v41-runtime-isolation`: V4.1 默认运行链与历史实现、Mock、历史数据资产隔离。
- `v41-compatibility-contract`: V4 公开 module 契约与关键行为的向后兼容验证。
- `v41-migration-validation`: 实体数据和配置迁移的 dry-run、校验、报告与安全失败处置。
- `v41-cutover-traceability`: 对照差异、历史资产弃用及切换/回退证据的统一跟踪。

### Modified Capabilities

None; this repository has no baseline OpenSpec capability specifications.

## Impact

Affected areas include the V4 module composition and its dependency boundaries, configuration parsing, migration tooling, documentation, and tests. The public V4 entry points remain stable. Historical `legacy/` code and fixtures remain available only for explicit regression or migration use, never as default runtime fallbacks.
