# DV Entity Linking V4 Module

`dv_entity_linking` 是可嵌入其他 Python 服务的实体召回与链接模块。调用方只使用稳定的 V1 门面；数据库、实体词投影、HTTP 协议细节和历史实现均属于内部实现。

## 1. 快速开始

在宿主项目的依赖装配层创建一次模块实例，再注入各业务 module：

```python
from dv_entity_linking import (
    LinkRequestV1,
    ModuleConfig,
    create_entity_linking_module,
)


entity_linker = create_entity_linking_module(
    ModuleConfig(
        entity_data_ir_url="ir://entity-data/entity-data:execute",
        timeout_ms=2_000,
    ),
    platform_client=platform_client,  # 由项目平台提供
)


def handle_query(query: str):
    return entity_linker.link(
        LinkRequestV1(
            query=query,
            entity_types=("alarm", "metric"),  # 可选：缩小召回范围
        )
    )
```

业务 module 不应自行创建数据库连接、HTTP Client 或拼接部署地址，也不应导入 `domain`、`infrastructure`、`legacy` 中的类。它只接收已创建的 `EntityLinkingModule` 并调用 `link()`。

## 2. 公开 API

以下是唯一面向宿主的稳定导入路径：

```python
from dv_entity_linking import (
    EntityLinkingModule,
    LinkRequestV1,
    LinkResponseV1,
    ModuleConfig,
    create_entity_linking_module,
)
```

| 对象 | 用途 |
| --- | --- |
| `create_entity_linking_module(config)` | 推荐的模块工厂；根据配置选择实体数据服务客户端。 |
| `EntityLinkingModule.link(request)` | 同步实体召回与链接入口。 |
| `EntityLinkingModule.link_async(request)` | 异步调用形式；当前保持与同步入口相同语义。 |
| `LinkRequestV1` | 输入 Query、可选实体类型提示及安全上下文。 |
| `LinkResponseV1` | Query 级状态、命中 mention、实体详情与安全诊断摘要。 |
| `ModuleConfig` | 模块部署配置，不是业务请求参数。 |

不得从 `dv_entity_linking.legacy` 导入任何对象作为新的集成方式。该目录仅保留 V1–V3 迁移和回归兼容实现。

## 3. 请求与返回

```python
result = entity_linker.link(LinkRequestV1(query="检查 ALM-51020 的 CPU Usage"))

if result.status == "linked":
    for mention in result.mentions:
        print(mention.text)                 # Query 中的原始命中文字
        print(mention.span)                 # 原始 Query 的 [start, end) 位置
        print(mention.entity.entity_id)     # 稳定实体 ID
        print(mention.entity.entity_name)   # canonical 名称
elif result.status == "no_match":
    pass  # 数据服务正常，但没有通过最终确认的实体
else:
    raise RuntimeError(result.error_code)
```

`LinkRequestV1` 的关键字段：

| 字段 | 说明 |
| --- | --- |
| `query` | 必填，待识别的原始文本。空文本返回 `invalid_input`。 |
| `entity_types` | 可选实体类型白名单；为空表示不限定类型。 |
| `agent_context` | 可选安全上下文；不应放入密码、token 或完整敏感记录。 |
| `extraction_mode` | 当前默认 `disabled`；可选抽取能力必须经过 span/schema 校验后才能影响结果。 |
| `allow_fallback` | 为将来的抽取失败回退保留。 |

`LinkResponseV1.status`：

| 状态 | 含义 | 调用方建议 |
| --- | --- | --- |
| `linked` | 已完成候选词确认并取得实体详情。 | 使用 `mentions`。 |
| `no_match` | 数据服务正常，但没有确认命中。 | 按普通文本或未识别实体处理。 |
| `invalid_input` | Query 为空或无有效内容。 | 修正调用参数。 |
| `dependency_failed` | 实体数据服务超时、鉴权、协议或版本一致性失败。 | 重试、降级或报错；不得当作 `no_match`。 |

`mention.text` 和 `mention.span` 始终对应原始 Query；归一化后的词只用于内部数据库召回，不能作为用户可见的命中文本。

## 4. 模块如何完成实体召回

```text
原始 Query
  → 归一化（保留归一化位置到原文位置的映射）
  → Entity Data Service：MATCH_WORDS
  → 本地：边界、上下文、重叠确认并恢复原文 span
  → Entity Data Service：BATCH_GET_ENTITIES
  → LinkResponseV1
```

数据库负责第一阶段候选词召回；Python 模块负责最终确认。数据库命中不是直接 `linked`，因此调用方不需要也不应自行复现撞词逻辑。

每个 Query 最多进行两次数据服务读取：一次 `MATCH_WORDS`，一次 `BATCH_GET_ENTITIES`。

## 5. 实体数据服务契约

生产配置下，模块使用 `ModuleConfig.entity_data_ir_url` 指定实体数据服务发布的内部通信 URL（IR URL）。该 URL 只应在应用启动/配置层设置；不要散落在业务 module 中。平台提供的 `platform_client` 接收该 IR URL 并完成寻址、鉴权、传输和平台级重试，module 不感知服务部署地址或 HTTP 细节。

所有业务数据调用使用同一个入口：

```text
{entity_data_ir_url}
```

请求信封示例：

```json
{
  "contract_version": "v1",
  "operation": "MATCH_WORDS",
  "payload": {
    "normalized_query": "checkcpuusage",
    "entity_types": ["metric"]
  }
}
```

支持的受控操作为：

| operation | 使用者 | 说明 |
| --- | --- | --- |
| `MATCH_WORDS` | 链接模块 | 从 `el_entity_word` 召回候选实体词。 |
| `BATCH_GET_ENTITIES` | 链接模块 | 批量获取最终实体详情。 |
| `UPSERT_ENTITY` | 受控数据管理端 | 写入实体，并原子重建其实体词投影。 |
| `DELETE_ENTITY` | 受控数据管理端 | 逻辑删除实体及有效词投影。 |
| `REBUILD_ENTITY_WORDS` | 运维/数据管理端 | 重建指定或全部实体词投影。 |

写操作必须提供唯一 `request_id` 以支持幂等重试，且必须与查询操作使用不同权限。`operation` 只能是已发布的枚举值；接口不是通用 SQL 执行器。

## 6. 数据约束

- `el_entity` 是实体权威数据，包含 `entity_id`、`entity_type`、`entity_name`、`alias`、`desc`、`attributes`、`relationships`。
- `el_entity_word` 是可重建检索投影，只能由 `entity_name` 和已确认 alias 派生。
- 写入实体时，服务必须在同一事务内更新实体和其词投影，并拒绝 active `normalized_key` 对应多个实体的冲突。
- 词表归一化用于候选召回；最终边界、上下文和最长不重叠规则始终在模块内执行。
- `attributes`、`relationships` 和 `desc` 不会自动派生为匹配词。

## 7. 本地开发与测试

不设置 `entity_data_ir_url` 时，工厂会使用仓库内 V3 JSON Mock 作为离线验收适配器：

```python
from dv_entity_linking import create_entity_linking_module

entity_linker = create_entity_linking_module()
```

这仅用于本地演示、迁移对照和测试；部署环境必须配置真实实体数据服务。Mock 不是生产数据库实现，也不代表 Redis 运行依赖。

## 8. 演进规则

- V1 DTO 的字段名称和语义保持兼容；破坏性变更新增 V2 DTO/入口，不在 V1 中静默改义。
- 增加数据服务能力时，新增 `operation` 与其独立 payload schema，不修改既有 operation 的语义。
- 不要让宿主依赖内部 REST 响应、数据库表、`EntityDataClient` 或内部实体模型。
- IR URL、平台 Client、超时和重试策略属于应用装配层；业务 module 只处理 `LinkResponseV1`。

更完整的需求与实现设计请参阅仓库中的 `docs/baselines/v4/IR.md` 和 `docs/baselines/v4/SR.md`。
