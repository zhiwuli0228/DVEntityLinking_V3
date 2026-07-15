# DVEntityLinking V4 功能设计说明书

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 特性名称 | DVEntityLinking V4：可嵌入 Python Module、实体数据 REST 集成与数据库实体词撞词 |
| 版本号 | V4-SR.1-draft |
| 编写日期 | 2026-07-14 |
| 状态 | 功能设计草稿；待评审后作为实现输入 |
| 上游需求 | [V4 IR](./IR.md) |

## 版本历史

| 版本号 | 日期 | 修改说明 |
| --- | --- | --- |
| V4-SR.1-draft | 2026-07-14 | 基于 V4 IR 与当前 V1–V3 实现，定义 module、REST、数据库撞词、位置映射、可选抽取与迁移设计。 |

---

# 1 概述

## 1.1 目的

本文将 V4 IR 转换为可实现的功能设计。V4 将当前项目从直接运行的 Flask demo 演进为可嵌入宿主 Python 项目的实体链接 module；实体数据由外部实体数据微服务和一个关系型数据库管理。本 module 不执行 SQL，也不维护数据写入，而是通过 REST 接收“数据库已命中的实体词”和实体详情，在本地完成 span 还原、边界/上下文确认、重叠消除、可选抽取结果合并和状态聚合。

## 1.2 范围

### 范围内

| 范围项 | 设计说明 |
| --- | --- |
| Python module | 定义不依赖 Flask 的门面、配置、依赖注入和同步/异步调用边界。 |
| IR 数据访问 | 定义实体词批量匹配、实体详情批量读取、健康/版本接口的请求、响应和错误映射。 |
| 数据库撞词 | 数据服务使用 `normalized_query` 反向包含 `normalized_key`，每条 Query 一次批量匹配调用。 |
| Python 确认 | 定义归一化位置映射、原文 span 还原、`match_mode`、最长非重叠和 Query 状态聚合。 |
| 可选实体抽取 | 定义可插拔抽取器及其 schema 校验、合并和回退。 |
| 数据 schema | 定义 `el_entity`、`el_entity_word` 的逻辑字段、投影生成和 canonical entity schema。 |
| 迁移与验证 | V3 Mock 对照、REST contract stub、V1/V2/V3 回归和 V4 golden cases。 |

### 范围外

| 范围外项 | 说明 |
| --- | --- |
| 数据库直连 | module 不保存连接串、不建连接池、不执行 SQL。 |
| 实体数据写入 API | 由实体数据微服务负责，module 只读。 |
| Redis、向量库、图数据库 | 不作为 V4 的必需依赖。 |
| 本地长期词表快照 | 不作为 V4 首期默认；后续可在相同 `MentionCandidateProvider` 接口下补充。 |
| 自动别名和关系推断 | 仅接受已确认 alias 与显式关系。 |
| 宿主 Web 框架 | Flask/ FastAPI / Agent 框架由宿主自行选择。 |

## 1.3 术语

| 术语 | 说明 |
| --- | --- |
| Entity Data Service | 外部实体数据微服务，拥有数据库、实体发布和实体词匹配能力。 |
| Module | 本项目提供给宿主 Python 项目的可调用实体链接组件。 |
| 数据库撞词 | 数据服务在 `el_entity_word` 中查询“归一化 Query 包含归一化实体词”。 |
| NormalizedQuery | 原文、归一文本及归一位置到原文位置映射的不可变对象。 |
| 最终确认 | module 对数据库命中执行 span 还原、边界/上下文规则和重叠消除。 |

---

# 2 需求实现设计

## 2.1 总体设计方案

```mermaid
flowchart LR
  H["Host Python Application"] --> F["EntityLinkingModule"]
  Q["Query + Agent Context"] --> F
  F --> N["NormalizedQuery Builder"]
  F --> X["Optional Entity Extractor"]
  N --> C["EntityDataRestClient.match_words"]
  C --> D["Entity Data Service"]
  D --> DB["el_entity_word / el_entity"]
  C --> P["NerPipeline Confirm & Merge"]
  X --> P
  P --> B["EntityDataRestClient.batch_get"]
  B --> D
  P --> R["EntityLinkResult"]
```

一条正常 Query 最多两次数据服务调用：

1. `match_words`：数据库批量撞词，返回命中的实体词记录；
2. `batch_get`：对最终保留 mention 的去重实体 ID 批量读取详情。

`match_words` 命中不等于 `linked`。数据库的职责是找到可能命中的词；module 的职责是将命中安全还原为原文 mention 并形成最终状态。

## 2.2 需求分解

| IR 编号 | SR 编号 | 分解说明 |
| --- | --- | --- |
| IR-V4-001 | SR-V4-A01 | Python module 门面、配置与宿主集成边界。 |
| IR-V4-001 | SR-V4-A02 | NormalizedQuery、位置映射和 canonical schema。 |
| IR-V4-001 | SR-V4-A03 | Entity Data Service REST client 与错误语义。 |
| IR-V4-001 | SR-V4-A04 | 数据库实体词匹配、Python 最终确认与可选抽取合并。 |
| IR-V4-001 | SR-V4-A05 | 实体表、实体词投影、数据发布与校验边界。 |
| IR-V4-001 | SR-V4-A06 | V3 到 V4 的兼容迁移与适配器替换。 |
| IR-V4-001 | SR-V4-A07 | 合同、golden case、回归和安全验证。 |

### SR-V4-A01 Python Module 门面与宿主集成

#### 设计

新增具体的 `EntityLinkingModule` 作为宿主唯一依赖的业务入口，并提供 `create_entity_linking_module()` 工厂函数。Flask Web/API 改为可选 adapter，只调用该门面，不再是核心运行前提。`Protocol` 只用于 module 内部的依赖端口，不能作为宿主实例化的公开对象。

```python
class EntityLinkingModule:
    def __init__(
        self,
        *,
        data_client: EntityDataClient,
        extractor: EntityExtractor | None = None,
        config: ModuleConfig,
    ) -> None: ...

    def link(self, request: LinkRequest) -> EntityLinkResult: ...

    async def link_async(self, request: LinkRequest) -> EntityLinkResult: ...


def create_entity_linking_module(config: ModuleConfig) -> EntityLinkingModule: ...
```

| 对象 | 核心字段 | 说明 |
| --- | --- | --- |
| `LinkRequest` | `query`、`agent_context`、`entity_types`、`extraction_mode`、`allow_fallback` | `query` 必填；上下文必须是安全投影。 |
| `EntityLinkResult` | `status`、`mention_results`、`mode_status`、`errors`、`service_trace` | 延续既有 Query/mention 状态语义。 |
| `ModuleConfig` | `entity_data_ir_url`、timeout、失败策略、抽取器配置 | 不序列化 secret、token 或 IR URL 到结果。 |

module 构造时通过依赖注入接收 `EntityDataClient`、`EntityExtractor | None` 和 `NerPipeline`。不得在领域代码中读取 Flask request、环境变量或具体 HTTP 库。

#### 公开集成契约

宿主模块和 `main` 方法只感知以下三类公开对象：

```python
from dv_entity_linking import (
    LinkRequestV1,
    LinkResponseV1,
    create_entity_linking_module,
)

linker = create_entity_linking_module(config)
response: LinkResponseV1 = linker.link(LinkRequestV1(query="Check CPU Usage."))
```

| 公开对象 | 稳定性规则 | 明确不暴露 |
| --- | --- | --- |
| `LinkRequestV1` | 只承载 Query、可选上下文、类型提示和运行选项；新增字段必须有默认值。 | Flask request、HTTP session、数据库查询参数。 |
| `LinkResponseV1` | 只包含版本化状态、mention、安全实体摘要、错误和安全 trace；已有字段不改名/删改语义。 | `EntityRecord`、`EntityWordRecord`、数据库列、REST 原始响应。 |
| `EntityLinkingModule.link()` | 入口方法签名在 V4 生命周期内保持稳定；同步/异步调用返回同一响应语义。 | 内部 pipeline、抽取器、缓存、SQL/HTTP 实现。 |
| `create_entity_linking_module()` | 唯一默认组装入口；内部实现可替换。 | 要求宿主理解依赖注入细节。 |

核心领域对象只在内部层流转。无论 `attributes`、`relationships`、实体词表字段、数据库撞词方式或 REST 数据服务怎样演进，均由 module 内部 adapter 映射成稳定的 `LinkResponseV1`。宿主不导入 `domain`、`infrastructure` 或 `legacy` 子包。

当公开请求或响应确需不兼容变化时，新增 `V2` DTO 或新的门面方法，并保留 `V1` 至明确的弃用窗口结束；不得借由修改内部实体 schema 让集成方被动适配。

#### Package 结构

V4 不继续把宿主门面、pipeline、HTTP client 与 Flask adapter 平铺在同一级。建议采用“少层、明确依赖方向”的 package 结构：

```text
src/dv_entity_linking/
├── __init__.py                 # 唯一稳定导出：门面、工厂、V1 DTO
├── module.py                   # 组装门面和依赖；宿主的主要入口
├── application/
│   ├── dto.py                  # LinkRequest、EntityLinkResult、safe trace
│   └── link_entities.py        # 单一用例编排，不依赖 HTTP/Flask
├── domain/
│   ├── models.py               # EntityRecord、EntityWordMatch、Mention 等领域对象
│   ├── normalization.py        # NormalizedQuery 和位置映射
│   ├── matching.py             # 边界、上下文、重叠消除与聚合规则
│   └── ports.py                # EntityDataClient、EntityExtractor 等 Protocol
├── infrastructure/
│   ├── entity_data_ir.py       # 平台 Client + IR URL 的生产适配器
│   ├── entity_data_rest.py     # 仅本地联调的直连 HTTP 适配器
│   ├── extractors/             # 可选规则/LLM 抽取器实现
│   └── v3_mock.py              # 迁移期 V3 JSON Mock adapter
├── adapters/
│   └── flask.py                # 可选；把 Flask 请求映射到 module 门面
└── legacy/                     # V1/V2 兼容 catalog/evaluation，仅迁移期保留
```

依赖方向固定为：`adapters`、`infrastructure` → `application`、`domain`；`application` → `domain`；`domain` 不依赖 HTTP、数据库、Flask、环境变量或具体抽取器。`module.py` 是唯一允许把平台 Client、IR URL、配置和可选抽取器组装在一起的位置。

历史 V1–V3 脚本、测试和 demo 必须显式从 `legacy/` 导入；V4 新代码不得依赖 legacy。根目录不保留同名兼容转发文件，最终且当前只保留 `__init__.py` 与 `module.py`，使宿主只能看到公开 V4 门面。

宿主只需使用稳定公开入口，而不依赖内部目录。默认集成使用工厂函数；宿主已有 HTTP client、鉴权或测试 stub 时，才直接构造门面并注入依赖：

```python
from dv_entity_linking import (
    LinkRequest,
    ModuleConfig,
    create_entity_linking_module,
)

module = create_entity_linking_module(ModuleConfig(...))
result = module.link(LinkRequest(query="Check CPU Usage."))
```

```python
from dv_entity_linking import EntityLinkingModule, ModuleConfig
from my_project.clients import EntityDataServiceClient

module = EntityLinkingModule(
    data_client=EntityDataServiceClient(...),
    config=ModuleConfig(...),
)
```

迁移时不要求一次移动全部 V1–V3 文件：先建立上述新边界，将现有 `NerPipeline`、`models` 和 V3 Mock 包装为实现；在 V4 contract 与回归稳定后再逐步收拢旧的平铺模块。

失败策略：

| 场景 | `FAIL_FAST` | `DEGRADED` |
| --- | --- | --- |
| 启动健康检查失败 | module 初始化失败。 | 宿主可启动；链接请求返回 `dependency_failed`。 |
| 单次匹配/详情调用失败 | 直接返回结构化错误。 | 同左；不得伪造 `no_match`。 |
| 可选抽取器失败 | 若 fallback 禁止则 dependency failed。 | 跳过抽取器，继续确定性路径。 |

### SR-V4-A02 归一化、位置映射与 canonical schema

#### 设计

归一化必须同时服务数据库匹配和原文 span 还原。定义：

```python
@dataclass(frozen=True)
class NormalizedQuery:
    original_text: str
    normalized_text: str
    normalized_to_original: tuple[int, ...]
    normalization_version: str
```

算法以原文字符为单位执行 Unicode NFKC、`casefold()` 和 Unicode 空白删除。每个保留的归一化字符记录其原文字符索引；若一个原文字符展开为多个归一化字符，各字符映射到相同原文索引。由归一区间 `[start, end)` 还原原文 span 的规则为：

```text
original_start = normalized_to_original[start]
original_end = normalized_to_original[end - 1] + 1
```

还原后必须验证：span 非越界、原文非空、重新归一化后的文本与 `normalized_key` 一致；否则丢弃该命中并记录安全 trace，不能构造伪 mention。

canonical entity schema 固定为 `entity_id`、`entity_type`、`entity_name`、`alias`、`desc`、`attributes`、`relationships`。旧字段 `canonical_name`、`aliases`、`description` 不得由 REST client 或 module 输出。

### SR-V4-A03 Entity Data IR Client

#### 设计

定义协议抽象，具体 HTTP 客户端可替换：

```python
class EntityDataClient(Protocol):
    def match_words(self, request: EntityWordMatchRequest) -> EntityWordMatchResponse: ...
    def batch_get(self, request: EntityBatchGetRequest) -> EntityBatchGetResponse: ...
    def health(self) -> EntityDataHealth: ...
```

| 接口 | 请求 | 成功响应 | 错误映射 |
| --- | --- | --- | --- |
| `match_words` | `normalized_query`、`entity_types?`、`expected_data_version?` | `matches[]`、`data_version`、`contract_version` | timeout、auth、transport、schema、version mismatch → `dependency_failed`。 |
| `batch_get` | 去重 `entity_ids[]`、`expected_data_version?` | `entities[]`、`missing_ids[]`、`data_version` | transport/schema → dependency failed；已匹配 ID 缺失 → `entity_miss`。 |
| `health` | client contract version | service status、data version、contract version | 启动报告或安全 trace。 |

`matches[]` 最小字段：`entity_word_id`、`entity_id`、`entity_type`、`entity_word`、`normalized_key`、`source`、`match_mode`、`min_context_required`、`context_keywords`、`priority`。响应 `data_version` 必须在同一 Query 的 `match_words` 和 `batch_get` 中一致；否则当前 Query 返回 `dependency_failed`，避免词表与详情跨版本混合。

生产 IR Client 只暴露已脱敏的 `adapter`、平台错误分类、延迟、contract/data version 和错误码。它不得将 Authorization、IR URL、响应原文或栈追踪放入 `EntityLinkResult`。直连 HTTP client 仅用于本地联调和契约测试。

### SR-V4-A04 数据库撞词与 Python 最终确认

#### 数据服务匹配规则

实体数据微服务仅对 active 词条执行逻辑匹配：

```sql
WHERE status = 'active'
  AND INSTR(:normalized_query, normalized_key) > 0
```

可选 `entity_type` 过滤必须在该查询中生效。数据库返回命中的词记录而非 `linked` 结论；同一词多次出现时，module 负责枚举所有位置。禁止将 Query 切词后逐 token 发起 REST 请求。

#### Module pipeline

| 阶段 | 输入 | 输出 | 关键规则 |
| --- | --- | --- | --- |
| P1 validate | `LinkRequest` | 合法 Query 或 invalid input | 空白 Query 不调用远端服务。 |
| P2 normalize | 原文 Query | `NormalizedQuery` | 生成位置映射。 |
| P3 need-linking | Query/context | bypass 或继续 | `not_required` 不调用匹配接口。 |
| P4 database match | normalized Query | `EntityWordMatch[]` | 一次 `match_words` 调用。 |
| P5 optional extract | Query/context | extracted mentions | schema、span、置信度均合法才参与合并。 |
| P6 restore/confirm | 命中词 + NormalizedQuery | confirmed mentions | 枚举位置，恢复 span，应用 match mode。 |
| P7 merge/select | DB、正则、抽取 mention | 非重叠 mention | 起点优先；同起点更长优先；再按 priority。 |
| P8 detail lookup | entity IDs | entity records | 一次 `batch_get` 调用。 |
| P9 aggregate | mention results | Query result | 保持 linked/partial/ambiguous/no_match/not_required/dependency_failed。 |

`match_mode` 规则：

| 模式 | 应用侧确认 |
| --- | --- |
| `EXACT_WORD` | ASCII 字母数字边界必须成立。 |
| `STRUCTURED_TOKEN` | 保留结构化符号，按实体词前后 token 边界确认。 |
| `CONTEXT_REQUIRED` | 除边界外，Query 邻近上下文必须包含确认的 `context_keywords`；否则丢弃命中。 |

可选抽取器的输出只可补充候选 mention；它不能跳过数据库实体词匹配去生成实体 ID。若抽取 mention 未能在数据库命中或正则规则中得到可确认实体，则保留为 unknown/no_match mention，不能直接链接。

### SR-V4-A05 实体数据与投影设计

#### 逻辑表

| 表 | 职责 | 关键约束 |
| --- | --- | --- |
| `el_entity` | 权威实体记录。 | `entity_id` 主键；canonical schema；`attributes_json` JSON 安全；关系目标必须存在。 |
| `el_entity_word` | 标准名和确认 alias 的匹配投影。 | `normalized_key` 由词面重算；active key 单值映射；仅 `entity_name` / `confirmed_alias` 来源。 |

`el_entity_word` 除 `entity_id` 外冗余 `entity_type`、`match_mode`、`min_context_required`、`context_keywords_json`、`priority`，使匹配接口无需先读取实体详情。`attributes`、`relationships`、`desc` 不生成词条。

#### 发布流程

```text
source records
→ schema / alias / relation / 安全校验
→ transaction 写入 el_entity
→ 由 entity_name + confirmed alias 重建 el_entity_word
→ 重新计算 normalized_key 与冲突校验
→ 发布 data_version
```

不同 active 实体出现同一 `normalized_key` 时按当前 V3 单值契约 fail-closed。若未来需要多值词表，必须另行改变 IR、接口、状态与评测，不能通过降低唯一约束实现。

### SR-V4-A06 迁移与兼容设计

| 当前 V3 | V4 目标 | 迁移策略 |
| --- | --- | --- |
| `GaussEntityStoreMock` | `EntityDataClient.batch_get` | 用 REST contract stub 先替换调用点；保留 Mock adapter 做对照。 |
| `RedisEntityWordCacheMock` | `EntityDataClient.match_words` | 改为一次 Query 批量匹配，而不是逐实体词 lookup。 |
| `EntityStorageRepository` | REST storage facade | `NerPipeline` 仅依赖 facade/Protocol。 |
| `_detect_known_mentions` 扫描内存词表 | 根据数据库命中恢复并确认 mention | 保留最长非重叠和边界语义。 |
| Flask Web demo | host adapter | demo 继续作为集成样例，不成为 module 必需依赖。 |

迁移必须保持 canonical schema 原子性；旧字段不能在新适配器中静默双读。迁移阶段保留 `V3MockEntityDataClient`，让同一 golden Query 同时经过 V3 Mock 与 V4 REST stub，比较 mention 文本、span、entity ID、状态和安全错误语义。

### SR-V4-A07 设计级测试、回归与安全

| 测试类别 | 最小覆盖 |
| --- | --- |
| NormalizedQuery | NFKC、casefold、空白删除、符号、重复位置、展开字符和 span 还原。 |
| REST contract | match/batch/health 成功、空匹配、timeout、auth、坏 schema、版本不一致。 |
| 数据库匹配 | 标准名、确认 alias、多次出现、类型过滤、短普通词和上下文限制。 |
| Pipeline | DB 命中、正则、抽取器合并、最长非重叠、unknown mention、所有 Query 状态。 |
| 数据 schema | canonical 字段、attributes 安全投影、relationships 悬挂/重复拒绝、词表冲突 fail-closed。 |
| Module 集成 | 无 Flask 运行、同步/异步入口、`FAIL_FAST`/`DEGRADED`、宿主 adapter。 |
| 回归 | V1/V2/V3 evaluation 与 smoke；V4 golden cases 对照 V3 Mock。 |

新增 V4 golden cases 至少覆盖：`CPU Usage` 的位置映射、同一词重复出现、`ALM-5102` 不命中 `ALM-51020`、`SYSTEM` 缺少上下文不链接、服务失败不等于 `no_match`、详情跨版本不一致、抽取器失败回退。

---

# 3 接口设计

## 3.1 宿主 Module 接口

| 接口 ID | 输入 | 输出 | 约束 |
| --- | --- | --- |
| IR-V4-MODULE-LINK | `LinkRequest` | `EntityLinkResult` | 同步入口；不得依赖 Flask。 |
| IR-V4-MODULE-LINK-ASYNC | `LinkRequest` | awaitable `EntityLinkResult` | 复用同一领域语义；不得出现不同状态定义。 |

## 3.2 Entity Data Service 统一 REST 接口

所有业务数据操作统一使用实体数据服务发布的 `entity_data_ir_url`。请求使用稳定信封，`operation` 是服务端受控枚举，决定 `payload` 的严格 schema；它不是可传递 SQL 或任意查询条件的自由字段。平台 Client 以该 URL 发起内部调用，module 不拼接部署层 HTTP 地址。

```json
{
  "contract_version": "v1",
  "operation": "MATCH_WORDS",
  "request_id": "write-only-idempotency-key",
  "expected_data_version": "optional",
  "payload": {}
}
```

| 操作枚举 | 调用方 | 调用次数 | `payload` 语义 | 写入 |
| --- | --- | --- | --- | --- |
| `MATCH_WORDS` | Entity Data IR Client | 每 Query 最多一次 | `normalized_query`、可选 `entity_types`、可选 `expected_data_version` | 否 |
| `BATCH_GET_ENTITIES` | Entity Data IR Client | 每 Query 最多一次 | `entity_ids[]`、可选 `expected_data_version` | 否 |
| `UPSERT_ENTITY` | 受控数据管理调用方 | 按需 | 完整 canonical `entity` | 是 |
| `DELETE_ENTITY` | 受控数据管理调用方 | 按需 | `entity_id` | 是 |
| `REBUILD_ENTITY_WORDS` | 受控运维调用方 | 按需 | 可选 `entity_ids[]` | 是 |

读取 `MATCH_WORDS` 示例：

```json
{
  "contract_version": "v1",
  "operation": "MATCH_WORDS",
  "payload": {
    "normalized_query": "checkcpuusagenow",
    "entity_types": ["kpi_meas_type_key"]
  }
}
```

统一响应外壳为 `contract_version`、`operation`、`status`、`data_version`、`data` 和可选 `error`。响应中的每个 match 必须携带原始 `entity_word`；module 不接受只有 `normalized_key` 的响应。写操作必须携带 `request_id` 用于幂等；读写操作必须使用不同权限。健康检查仍可使用 `GET /health` 或 `GET /v1/entity-data:status`。

---

# 4 数据库设计

数据库由实体数据微服务实现；本节是其对 module 的逻辑契约，不要求本项目执行建表 SQL。

## 4.1 `el_entity`

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `entity_id` | 是 | 稳定主键。 |
| `entity_type`、`entity_name`、`desc` | 是 | canonical common fields。 |
| `alias_json`、`attributes_json`、`relationships_json` | 是 | 分别默认 `[]`、`{}`、`[]`。 |
| `status`、`data_version` | 是 | 发布与读取一致性。 |

## 4.2 `el_entity_word`

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `entity_word_id`、`entity_id`、`entity_type` | 是 | ID 与匹配时类型过滤。 |
| `entity_word`、`normalized_key` | 是 | 原文词与数据库撞词 key。 |
| `source` | 是 | `entity_name` 或 `confirmed_alias`。 |
| `match_mode`、`min_context_required`、`context_keywords_json`、`priority` | 是 | module 最终确认控制字段。 |
| `status`、`data_version` | 是 | active 查询与版本一致性。 |

最小索引：`el_entity(entity_id)`、`el_entity_word(entity_id)`、active `normalized_key` 的唯一约束，以及按 status/type 的过滤索引。`INSTR` 的执行计划和后续全文优化属于实体数据微服务的性能实现，但不得改变接口结果集语义。

---

# 5 部署、配置与安全

| 配置 | 说明 |
| --- | --- |
| `entity_linking.entity_data_ir_url` | 目标服务发布的 IR URL；不得写入日志或 API 响应。 |
| `entity_linking.timeout_ms` | 平台 Client 调用超时。 |
| `entity_linking.startup_failure_policy` | `FAIL_FAST` 或 `DEGRADED`。 |
| `entity_linking.extractor.mode` | `disabled`、规则或已确认的外部抽取器。 |
| `entity_linking.contract_version` | module 期望的数据服务契约版本。 |

禁止提交或投影数据库连接串、数据服务凭据、Authorization、token、完整 Query 上下文、完整 HTTP 响应、完整 LLM 请求/响应和不安全 attributes。

---

# 6 实现前置项与 AR

| AR 编号 | 内容 | 状态 |
| --- | --- | --- |
| AR-V4-SR-001 | 确认 REST 鉴权、超时、重试和契约版本协商。 | 待确认 |
| AR-V4-SR-002 | 确认数据库产品及 `INSTR`/全文匹配的性能基线。 | 待确认 |
| AR-V4-SR-003 | 确认可选抽取器首期实现与置信度阈值。 | 待确认 |
| AR-V4-SR-004 | 定义 V4 REST contract stub 与 golden case 数据集。 | 待实现 |
