# MySQL Entity Data Mock 持久化造数记录

## 结果

2026-07-17 已在授权 MySQL 的专用 `dv_entity_data_mock` 数据库完成 `large` 档持久化造数。该数据库不属于临时压测 schema，测试完成后不自动删除。

| 项目 | 结果 |
| --- | ---: |
| Entity | 333,334 |
| Entity word | 1,000,000 |
| Active entity word | 956,522 |
| Preset | `large` |
| Data version | `mock-large-1000000-20260717151801` |
| 状态 | `ready` |

## 完整性验证

- Seeder 首次远程连接中断时，已提交的 325,000 个实体被保留。
- Seeder 已改为连续主键前缀断点续写，随后补齐剩余实体和全部实体词，没有清空或覆盖已提交批次。
- `mock_metadata` 已写入唯一 ready data version。
- `MATCH_WORDS` 对确定性样例返回 1 个唯一命中，命中 key 为 `cpuusage000001001`。
- `BATCH_GET_ENTITIES` 返回 1 个对应实体，响应 data version 与词召回一致。
- 本次远程只读验证的 `MATCH_WORDS` 用时约 10.70 秒；该值包含远程网络延迟，不作为本地低延迟容量结论。

## 保留策略

- Mock Seeder 不提供自动清理或 TRUNCATE 入口。
- 重复执行相同 preset 时复用已完成数据。
- 写入中断时只从已验证的连续最大主键继续补齐。
- 如现有数据超过目标、出现主键间断或 ready metadata 与计数冲突，Seeder 停止并报告错误，不删除数据。
