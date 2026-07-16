# DV Entity Linking V4/V5 Module

`dv_entity_linking` 是可嵌入其他 Python 服务的实体召回、链接与实体构建模块。V4 `*V1` DTO 保留为兼容层；V5 新集成推荐使用无版本后缀的 Query Recall 门面。实体构建、共享 REST 工具与链接 pipeline 相互独立；数据库、实体词投影、HTTP 协议细节和历史实现均属于内部实现。

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
| `create_entity_linking_module(config, platform_client=...)` | 唯一生产装配工厂；必须通过平台 Client 调用 Entity Data IR URL。 |
| `EntityLinkingModule.link(request)` | 同步实体召回与链接入口。 |
| `EntityLinkingModule.link_async(request)` | 异步调用形式；当前保持与同步入口相同语义。 |
| `LinkRequestV1` | 输入 Query、可选实体类型提示及安全上下文。 |
| `LinkResponseV1` | Query 级状态、命中 mention、实体详情与安全诊断摘要。 |
| `ModuleConfig` | 模块部署配置，不是业务请求参数。 |

V5 的新增能力通过各自的稳定子模块暴露，避免把构建或传输实现耦合进 V4 linker：

```python
from dv_entity_linking.entity_build_plugin import (
    DailyRefreshScheduler,
    EntityBuildPlugin,
    EntityBuildTaskRunner,
    build_task_runner_from_config,
)
from dv_entity_linking.query_recall import QueryRecallFacade, RecallConfigProvider
from dv_entity_linking.infrastructure.rest_tool import RestRequest, RestRequestTool
```

`RestRequestTool` 是共享基础设施；`QueryRecallFacade` 是 V5 的简化查询门面；`EntityBuildPlugin`、`EntityBuildTaskRunner` 和 `DailyRefreshScheduler` 只负责实体构建与更新编排。

不得从 `dv_entity_linking.legacy` 导入任何对象作为新的集成方式。该目录仅保留 V1–V3 迁移和回归兼容实现。

## 3. V5 推荐查询入口

新宿主建议在 V4 linker 外包一层 V5 `QueryRecallFacade`。默认仅传原始 `query`，LLM、Top-K、回退及实体类型由可热加载配置控制：

```python
from dv_entity_linking.query_recall import QueryRecallFacade, RecallConfigProvider

query_recall = QueryRecallFacade(
    entity_linker,
    RecallConfigProvider("config/query_recall.json"),
)

result = query_recall.recall("检查 ALM-51020 的 CPU Usage", top_k=3)
```

返回类型为无版本后缀的 `QueryRecallResult`，包含 `query`、`status`、`mentions`、`candidates`、`top_entity_id`、`error_code` 与 `degraded`。`LinkRequestV1` / `LinkResponseV1` 仅作为兼容适配层，新的调用面不应继续扩散版本后缀。

配置文件示例：

```json
{
  "recall": {
    "use_llm": false,
    "top_k": 3,
    "allow_fallback": true,
    "entity_types": ["alarm", "metric"]
  }
}
```

每次新请求前都会校验配置；有效配置原子生效，无效配置继续使用最近一次有效值。

## 4. V4 兼容请求与返回

```python
result = entity_linker.link(LinkRequestV1(query="检查 ALM-51020 的 CPU Usage"))

if result.status in {"linked", "partial"}:
    for mention in result.mentions:
        print(mention.text)                 # Query 中的原始命中文字
        print(mention.span)                 # 原始 Query 的 [start, end) 位置
        print(mention.entity.entity_id)     # 稳定实体 ID
        print(mention.entity.entity_name)   # canonical 名称
elif result.status in {"no_match", "not_required"}:
    pass  # 无确认实体，或该 Query 本身不需要实体链接
else:
    raise RuntimeError(result.error_code)
```

`LinkRequestV1` 的关键字段：

| 字段 | 说明 |
| --- | --- |
| `query` | 必填，待识别的原始文本。空文本返回 `invalid_input`。 |
| `entity_types` | 可选实体类型白名单；为空表示不限定类型。 |
| `agent_context` | 可选安全上下文；不应放入密码、token 或完整敏感记录。 |
| `extraction_mode` | 默认 `disabled`；启用时使用宿主注入的 LLM mention 抽取器和可选候选 reranker。 |
| `allow_fallback` | 抽取器失败或输出非法时是否继续确定性路径；为 `false` 时返回结构化依赖失败。reranker 失败始终保留确定性 Top-K 与 `ambiguous`。 |

`LinkResponseV1.status`：

| 状态 | 含义 | 调用方建议 |
| --- | --- | --- |
| `linked` | 已完成候选词确认并取得实体详情。 | 使用 `mentions`。 |
| `partial` | 至少一个 mention 已链接，另有 unknown、未匹配、歧义或降级 mention。 | 逐项读取 `mentions[].status`，不得把 Query 整体当成失败。 |
| `ambiguous` | 候选无法安全收敛为唯一实体。 | 使用 mention 或顶层 `candidates` 请求用户/上游消歧。 |
| `no_match` | 数据服务正常，但没有确认命中。 | 按普通文本或未识别实体处理。 |
| `not_required` | Query 不要求实体链接，未执行实体召回。 | 按 `bypass_reason` 继续普通处理。 |
| `invalid_input` | Query 为空或无有效内容。 | 修正调用参数。 |
| `dependency_failed` | 实体数据服务超时、鉴权、协议或版本一致性失败。 | 重试、降级或报错；不得当作 `no_match`。 |

`mention.text` 和 `mention.span` 始终对应原始 Query；归一化后的词只用于内部数据库召回，不能作为用户可见的命中文本。每个 mention 都可读取 `source`、`predicted_type`、`confidence`、`candidates`、`no_match_reason`、`storage_lookup`；调用方应保留 unknown/no-match mention，不能只读取已链接实体。

## 5. 模块如何完成实体召回

```text
原始 Query
  → need-linking / not-required
  → 归一化（保留归一化位置到原文位置的映射）
  → Entity Data Service：MATCH_WORDS
  → 本地：已知词恢复、未知实体形态、边界/上下文/重叠确认
  → 可选 LLM mention 抽取（严格 span/schema 校验，可回退）
  → 候选与置信度判断
  → 可选 LLM rerank（仅已有歧义候选；失败保留 Top-K）
  → mention 级状态与 Query 聚合
  → Entity Data Service：BATCH_GET_ENTITIES
  → LinkResponseV1
```

数据库负责第一阶段候选词召回；Python 模块负责完整 NER、候选决策和最终确认。数据库命中不是直接 `linked`，数据库 miss 也不等于没有实体，因为模块仍会识别未知实体形态。

每个 Query 最多进行两次数据服务读取：一次 `MATCH_WORDS`，一次 `BATCH_GET_ENTITIES`。

## 6. 实体数据服务契约与共享 REST 工具

生产配置下，模块使用 `ModuleConfig.entity_data_ir_url` 指定实体数据服务发布的内部通信 URL（IR URL）。该 URL 只应在应用启动/配置层设置；不要散落在业务 module 中。平台提供的 `platform_client` 接收该 IR URL 并完成寻址、鉴权、传输和平台级重试，module 不感知服务部署地址或 HTTP 细节。

`RestRequestTool` 对 REST 调用统一承接 URL、请求方法、参数、请求体、超时和受控重试；V4 的 REST 数据适配器与 V5 的实体构建 source 均通过它发起请求。调用方只传递请求描述，不感知 urllib、平台传输、鉴权映射或错误归类等内部细节。该工具是常驻共享能力，但不依赖 V5 构建插件。

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

## 7. V5 实体构建与定时更新

V5 `EntityBuildPlugin` 是独立、可插拔的构建组件，不被 V4 linking pipeline 调用；未来可整体迁入 Entity Data Service。构建结果严格复用 V4 实体 schema：`entity_id`、`entity_type`、`entity_name`、`alias`、`desc`、`attributes`、`relationships`，不得新增来源、版本、时间或快照实体字段。

接口必须统一返回 cursor 分页包：

```json
{
  "items": [{"entity_id": "DV-ALM-001", "entity_type": "alarm", "entity_name": "ALM-51020", "alias": ["51020"]}],
  "has_more": true,
  "next_cursor": "opaque-token"
}
```

通用配置 source 自动使用 `cursor` 和 `page_size` 逐页拉取；`has_more=true` 却缺少 `next_cursor` 时 fail-closed，保留当前已发布数据。

```json
{
  "entity_build": {
    "page_size": 100,
    "retry_count": 2,
    "once_endpoints": [{"name": "bootstrap", "url": "..."}],
    "daily_endpoints": [{"name": "runtime", "url": "..."}]
  }
}
```

新增同构接口时只增加配置项，不需要新增 adapter 或调度代码。每个 endpoint 独立重试和隔离：单接口失败后继续处理后续接口，保留该接口最近一次成功数据；成功接口照常更新，整轮状态为 `partial`。

一次接口由 `run_once()` 显式执行并缓存成功结果。每日接口由 `run_daily()` 执行；`DailyRefreshScheduler` 以 `Asia/Shanghai` 时区在每日 `00:00` 放行一次。宿主按分钟调用 `run_if_due(now)`，因此可替换为平台 cron 或框架 scheduler。

## 8. 数据约束

- `el_entity` 是实体权威数据，包含 `entity_id`、`entity_type`、`entity_name`、`alias`、`desc`、`attributes`、`relationships`。
- `el_entity_word` 是可重建检索投影，只能由 `entity_name` 和已确认 alias 派生。
- 写入实体时，服务必须在同一事务内更新实体和其词投影，并拒绝 active `normalized_key` 对应多个实体的冲突。
- 词表归一化用于候选召回；最终边界、上下文和最长不重叠规则始终在模块内执行。
- `attributes`、`relationships` 和 `desc` 不会自动派生为匹配词。

## 9. 本地开发与测试

`create_entity_linking_module()` 没有默认后备路径：缺少 `entity_data_ir_url` 或 `platform_client` 时会立即抛出配置错误。V3 Mock、Gauss JSON 和 Redis JSON 仅属于 `legacy/` 与测试代码；测试必须直接向 `EntityLinkingModule(data_client=...)` 显式注入 fake 或 V3 Mock，公开工厂绝不会加载它们。

V4 运行时禁止 Redis、缓存词表和本地持久化实体快照作为召回或实体详情来源。单次 `link()` 调用中的临时归一化、候选和详情变量仅用于该请求的编排，不构成缓存。

V5 相关回归可运行 `tests/test_v5_query_recall.py`、`tests/test_v5_entity_build_plugin.py` 与 `tests/test_rest_tool.py`；完整测试集仍需同时覆盖 V1–V4 的兼容用例。

## 10. 演进规则

- `LinkRequestV1` / `LinkResponseV1` 保留为 V4 兼容层；新 V5 DTO、字段和方法不得新增版本后缀。
- 增加数据服务能力时，新增 `operation` 与其独立 payload schema，不修改既有 operation 的语义。
- 不要让宿主依赖内部 Entity Data IR 响应、数据库表、`EntityDataClient` 或内部实体模型。
- IR URL、平台 Client、超时和重试策略属于应用装配层；业务 module 只处理 `LinkResponseV1`。
- Web adapter 是安装可选项：需要历史 Flask demo 时安装 `dv-entity-linking[web]`；核心 module 不安装 Flask。

更完整的需求与实现设计请参阅仓库中的 `docs/baselines/v4/IR.md` 和 `docs/baselines/v4/SR.md`。
