# V5 来源接入清单

状态：接口未授权前仅使用 fixture adapter；不得填写真实 URL、凭据或 payload。

| 来源类别 | V5 adapter | 当前状态 | 接入门禁 |
| --- | --- | --- | --- |
| 运行时数据 | `RuntimeSourceAdapter` | 待接入 | owner、认证、分页/游标、字段映射、稳定主键。 |
| 知识库数据 | `KnowledgeSourceAdapter` | 待接入 | owner、认证、导出范围、字段映射、更新 SLA。 |
| Entity Data Service 写入 | `EntityPublisher` | 待接入 | 批量更新、对账、原子切换、回退契约。 |

所有 adapter 只产出 V4 schema 实体；不得添加来源、版本、时间或快照实体字段。
