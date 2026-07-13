# DVEntityLinking V2 前端改造补救功能设计说明书

---

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 特性名称 | V2 frontend remediation demo workbench |
| 版本号 | V2-FE-SR.2-closed |
| 编写日期 | 2026-06-02 |
| 编写人 | Codex |
| 审核人 | 独立功能设计评审 Bacon；闭环验证 Bohr |
| 状态 | 功能设计评审闭环已通过，可作为代码实现输入 |

## 版本历史

| 版本号 | 修改日期 | 修改人 | 修改描述 |
| --- | --- | --- | --- |
| V2-FE-SR.0-draft | 2026-06-02 | Codex | 基于已闭环的 V2 前端补救 IR 形成函数设计草稿。 |
| V2-FE-SR.1-draft | 2026-06-02 | Codex | 接受独立功能设计评审 4 个 P1 和 1 个 P2，补齐反向核查 schema、LLM 解释关联字段、负例 UI 测试、safe attributes fail-closed 和 catalog API 命名边界。 |
| V2-FE-SR.2-closed | 2026-06-02 | Codex | 记录独立功能设计闭环验证通过，4 个 P1 和 1 个 P2 均 Closed，可进入代码实现。 |

---

# 1 概述

## 1.1 目的

本文把已闭环的 V2 前端改造补救需求转换为可实现的前端工作台设计，明确 Flask Web demo 的模块边界、页面布局、交互状态、safe projection、安全边界、异常语义和设计级测试映射。

本文不替代 V2 已闭环的主功能设计 [SR.md](./SR.md)。本文只覆盖 V2 前端补救阻塞项。

## 1.2 范围

| 范围 | 设计结论 |
| --- | --- |
| 单 Web 入口 | 继续使用 `scripts/run_web_demo.py`，默认加载 V2 catalog 和 query samples。 |
| Web UI | 在 `src/dv_entity_linking/web.py` 内维护轻量 Flask 页面、CSS 和少量原生 JS。 |
| API | 复用现有实际接口 `/api/status`、`/api/link`、`/api/entities`、`/api/entities/<entity_id>`、`/api/retrieve`；如实现中发现字段不足，只允许新增 safe projection 字段，不改变实体链接核心语义。 |
| 多 mention 可视化 | 页面必须逐 mention 展示文本、类型、状态、span、linked entity、候选或 no-candidate reason。 |
| LLM 交互式安全解释 | 页面支持点击 mention、candidate 或 LLM status 查看关联脱敏解释和阶段摘要。 |
| 浏览器级验收证据 | 设计测试入口覆盖桌面 `1366x768`、窄屏 `390x844`、Query submit、catalog filter、candidate/detail linkage、debug collapsed 和截图/布局证据。 |

范围外：

- 不引入 React/Next.js 或生产级前端工程。
- 不新增实体 schema、链接算法、真实 DV 接口或默认真实 LLM 依赖。
- 不展示真实 secret/API key、真实 base URL、raw prompt、raw response 或完整 LLM 日志。

## 1.3 缩略语和术语

| 缩略语/术语 | 英文全称 | 中文解释 |
| --- | --- | --- |
| Workbench | Demo Workbench | 面向 demo 和评审的操作台式页面 |
| Safe projection | Safe Web Projection | 脱敏且适合页面展示的 API 投影 |
| Mention strip | Mention Strip | Query 中各 mention 的横向或纵向摘要区 |
| LLM safe explanation | LLM Interactive Safe Explanation | 与 mention/candidate 关联的脱敏解释和阶段摘要 |

## 1.4 参考文献

| 文档名称 | 文档编号 | 版本 | 来源 |
| --- | --- | --- | --- |
| V2 前端改造补救需求分析 | IR-DVEntityLinking-V2-FE-Remediation | V2-FE.2-closed | [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md) |
| V2 前端补救需求评审处置 | FRONTEND-REMEDIATION-REQ-DISP | 2026-06-01 | [FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| V2 前端补救需求闭环验证 | FRONTEND-REMEDIATION-REQ-CLOSURE | 2026-06-02 | [FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |
| V2 主功能设计 | SR-DVEntityLinking-V2 | V2.2 | [SR.md](./SR.md) |
| V2 前端补救功能设计评审 | FRONTEND-REMEDIATION-FD-REVIEW | 2026-06-02 | [FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| V2 前端补救功能设计评审处置 | FRONTEND-REMEDIATION-FD-DISP | 2026-06-02 | [FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md) |
| V2 前端补救功能设计闭环验证 | FRONTEND-REMEDIATION-FD-CLOSURE | 2026-06-02 | [FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| 当前 DV 流程 | DV-PROCESS | 2026-06-01 | [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md) |

---

# 2 需求实现设计

## 2.1 总体设计方案概述

V2 前端补救继续采用单进程 Flask demo，避免引入新的前端构建链。设计重点是把已有 API 的 safe projection 组织成可演示、可测试、可追踪的工作台页面：

```text
run_web_demo.py
  -> create_app(...)
  -> GET /
      renders workbench shell, CSS, JS
  -> GET /api/status
      runtime, catalog, llm safe config status
  -> POST /api/link
      query result, mention projections, candidates, stage summaries
  -> GET /api/entities
      catalog list and type counts
  -> GET /api/entities/<entity_id>
      entity detail safe projection
  -> GET /api/retrieve
      similar entities for selected entity
```

Catalog API 命名边界：本补救以当前代码中已存在的 `/api/entities` 和 `/api/entities/<entity_id>` 作为实际 Web catalog 接口。主 V2 SR 中的 `/api/catalog` 视为早期逻辑命名，不在本补救中新增第二套 endpoint；实现和测试统一使用 `/api/entities`，避免 catalog 接口分叉。

设计原则：

| 原则 | 设计约束 |
| --- | --- |
| 单入口 | 不恢复 `run_v1_web_demo.py`；历史版本通过显式参数加载。 |
| 信息密度 | 第一屏是实际 workbench，不做 landing page 或营销说明。 |
| 可测交互 | 关键元素使用稳定 `data-testid`，方便 Flask client 和浏览器级测试定位。 |
| 安全默认 | 页面只渲染 safe projection；完整 JSON 默认折叠；敏感真实值禁止进入 HTML、API 和日志。 |
| 反降级 | 如果浏览器级测试无法落地，必须回到评审或用户确认，不能用 marker/API projection 替代。 |

## 2.2 需求分解

### IR-V2-FE-001 V2 前端演示工作台补救

#### 2.2.1.1 IR 原始描述

V2 原确认前端方案为“运维工作台式演示 + LLM 交互式高亮/解释”，但原验收候选中前端改造未落实并被降级为 Web/API projection。当前补救要求重新按 DV 流程完成前端需求、设计、实现、测试和评审闭环。

#### 2.2.1.2 IR 结构化信息

| 字段 | 内容 |
| --- | --- |
| 需求优先级 | 高，V2 重新进入验收前阻塞 |
| 需求类型 | 功能性需求 + 可用性/可测试性需求 |
| 涉及模块 | `scripts/run_web_demo.py`、`src/dv_entity_linking/web.py`、`tests/test_web.py`、浏览器级 smoke |

#### 2.2.1.3 IR 与 SR 的分解关系

| IR 编号 | SR 编号 | 分解说明 |
| --- | --- | --- |
| IR-V2-FE-001 | SR-V2-FE-D01 | 页面信息架构和响应式布局 |
| IR-V2-FE-001 | SR-V2-FE-D02 | Query、多 mention 和 partial 可视化 |
| IR-V2-FE-001 | SR-V2-FE-D03 | Candidate/entity detail/catalog 联动 |
| IR-V2-FE-001 | SR-V2-FE-D04 | LLM 交互式安全解释和安全边界 |
| IR-V2-FE-001 | SR-V2-FE-D05 | 浏览器级验收证据和反降级追踪 |

### SR-V2-FE-D01 页面信息架构和响应式布局

#### 2.2.2.1 SR 描述

Web 首页必须直接呈现 V2 workbench，包含 runtime status、Query panel、Result summary、Mention strip、Candidate/Entity detail、Catalog panel、LLM overview 和折叠 debug JSON。

#### 2.2.2.2 SR 实现思路

在 Flask template 中保留一个 HTML 文档，使用语义化区域和稳定测试标识：

| 区域 | `data-testid` | 主要内容 |
| --- | --- | --- |
| Runtime status | `runtime-status` | mode、catalog loaded、entity_count、type_counts |
| Query panel | `query-panel` | Query 输入、sample selector、submit button |
| Result summary | `result-summary` | query status、mention count、linked count、partial/no_match reason |
| Mention strip | `mention-strip` | mention cards |
| Candidate/detail | `candidate-detail-panel` | selected mention candidates、selected entity detail、similar entities |
| Catalog panel | `catalog-panel` | type filter、entity list、type counts |
| LLM panel | `llm-safe-explanation-panel` | LLM status、stage summary、selected safe explanation |
| Debug panel | `debug-panel` | folded JSON details |

响应式规则：

| Viewport | 布局 |
| --- | --- |
| Desktop `1366x768` | 顶部 status + query，主体为 results/detail/catalog 三列或 2+1 grid；第一屏可见关键概览。 |
| Narrow `390x844` | 单列纵向布局；status、query、summary 在前，mention/candidate/catalog/LLM/debug 依次可滚动访问。 |

#### 2.2.2.3 功能实现刷新

页面初始化：

1. 浏览器加载 `/`。
2. JS 调用 `/api/status` 和 `/api/entities`。
3. 渲染 runtime status、catalog counts、sample query selector。
4. Debug JSON 默认 `<details>` collapsed。

布局不得依赖 viewport-width 字号缩放；固定格式控件使用 grid/flex 和 min/max constraints，避免按钮、卡片和状态文本挤压重叠。

#### 2.2.2.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | 页面失败时展示错误 banner，不影响后端链接服务。 |
| 可用性 | 是 | 第一屏直接进入操作台；窄屏可滚动访问关键内容。 |
| 安全性 | 是 | 不渲染真实敏感值；debug 默认折叠。 |
| 可维护性 | 是 | 区域和控件使用稳定 `data-testid`，减少脆弱文本断言。 |

#### 2.2.2.5 架构元素影响列表

| 架构元素 | 影响说明 | 修改类型 |
| --- | --- | --- |
| `src/dv_entity_linking/web.py` | 重构 HTML/CSS/JS template 和 safe projection 渲染 | 修改 |
| `tests/test_web.py` | 增加页面结构和交互断言 | 修改 |
| Browser smoke script | 增加真实浏览器或等价浏览器级证据 | 新增或修改 |

### SR-V2-FE-D02 Query、多 mention 和 partial 可视化

#### 2.2.3.1 SR 描述

提交英文多 mention Query 后，页面必须逐 mention 展示 `text`、`entity_type` 或 `predicted_type`、`status`、`span`、`linked_entity`、候选或 no-candidate reason。`partial` 必须清楚展示哪个 mention 成功、哪个 mention no_match/ambiguous/degraded。

#### 2.2.3.2 SR 实现思路

前端从 `/api/link` 的 safe result 中构造 `WorkbenchState`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `query_text` | string | 当前 Query |
| `query_status` | string | linked、partial、ambiguous、no_match、not_required、dependency_failed |
| `mentions[]` | array | Mention projection |
| `selected_mention_index` | number/null | 当前选中 mention |
| `selected_candidate_id` | string/null | 当前选中候选 |
| `stage_summaries[]` | array | LLM/deterministic 阶段摘要 |

Mention projection 最低字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `text` | 是 | mention 文本 |
| `span` | 是 | `[start, end]` |
| `status` | 是 | mention 级状态 |
| `entity_type` / `predicted_type` | 至少一个 | 类型展示 |
| `linked_entity` | status 为 linked 时必填 | linked entity safe summary |
| `candidates` | 有候选时必填 | candidate safe summary list |
| `no_candidate_reason` | 无候选时必填 | no_match/not_required/degraded 原因 |
| `degraded_stage` | 降级时必填 | 降级阶段 |

#### 2.2.3.3 功能实现刷新

交互流程：

1. 用户选择或输入英文 Query。
2. 点击 Link。
3. JS 发送 `POST /api/link`。
4. 页面更新 Result summary 和 Mention strip。
5. 默认选中第一个 mention；点击 mention 更新候选列表、实体详情和 LLM safe explanation。

异常语义：

| 状态 | UI 行为 |
| --- | --- |
| `linked` | 展示 linked entity 和候选；状态为成功色。 |
| `partial` | Query summary 显示 partial；mention card 分别展示 linked/no_match/ambiguous/degraded。 |
| `no_match` | 不展示伪 linked entity；展示 no-candidate reason。 |
| `not_required` | 不展示伪 mention 和伪候选；summary 说明无需链接。 |
| `dependency_failed` | 展示错误 banner 和 stage error，不伪造候选。 |

#### 2.2.3.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | API 错误保留上次成功结果或显示空状态，不混淆新旧结果。 |
| 可用性 | 是 | Mention 级状态无需展开 JSON 即可理解。 |
| 安全性 | 是 | Mention/candidate 只使用 safe projection。 |
| 可维护性 | 是 | Mention projection 字段集中生成和测试。 |

### SR-V2-FE-D03 Candidate/entity detail/catalog 联动

#### 2.2.4.1 SR 描述

候选、linked entity、entity detail、similar entities 和 catalog type filter 必须可联动。用户应能从 mention 进入 candidate，再进入实体详情，也能从 catalog 按类型过滤并查看实体详情。

#### 2.2.4.2 SR 实现思路

Candidate card 最低字段：

| 字段 | 说明 |
| --- | --- |
| `entity_id` | 实体 ID |
| `entity_type` | 实体类型 |
| `canonical_name` | 标准名 |
| `score` 或 `rank` | 候选排序证据 |
| `match_reason` | 可解释原因 |

Entity detail 只显示 safe fields：

| 字段 | 说明 |
| --- | --- |
| `entity_id` | 实体 ID |
| `entity_type` | 实体类型 |
| `canonical_name` | 标准名 |
| `aliases` | 可为空，不能自动生成未确认别名 |
| `description` | 已有 safe description |
| `attributes_safe[]` | 白名单过滤后的属性条目；未知或敏感 key fail-closed 省略 |
| `omitted_attribute_count` | 非敏感计数，仅表示有多少属性因非白名单或敏感规则未展示 |

`attributes_safe[]` 条目 schema：

| 字段 | 必填 | 规则 |
| --- | --- | --- |
| `key` | 是 | 仅允许白名单 key：`severity`、`category`、`domain`、`vendor`、`unit`、`task_type`、`measurement_type`、`object_type`、`ne_type`、`source_type`、`lifecycle_state`。 |
| `value` | 是 | 仅允许 string/number/bool 或 string list；禁止 nested object、URL、host、token-like value；单值展示长度上限 300 字符。 |
| `source` | 否 | 仅允许 `catalog`、`runtime_mock`、`derived_safe`。 |

属性 fail-closed 规则：

- 任意 key 命中 `api_key`、`token`、`secret`、`password`、`authorization`、`base_url`、`url`、`host`、`raw_request`、`raw_response`、`prompt`、`llm` 时必须省略。
- 未在白名单中的 key 必须省略，不得因为当前样例看似安全而直接透传。
- 省略详情不得记录原始 key/value，只允许增加 `omitted_attribute_count`。

#### 2.2.4.3 功能实现刷新

1. Catalog panel 初始化时展示 type counts 和 all entities。
2. 用户选择 entity type filter 后，只显示该类型实体。
3. 用户点击 candidate 或 catalog entity 后，detail panel 展示实体详情。
4. 如有 selected entity，调用 `/api/retrieve` 展示 similar entities。

#### 2.2.4.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | Retrieve 失败只影响 similar entities，不清空已选实体详情。 |
| 可用性 | 是 | 支持从 Query 结果和 catalog 两条路径进入详情。 |
| 安全性 | 是 | 仅展示 safe fields。 |
| 可维护性 | 是 | Candidate/detail/catalog 的选中状态统一在 JS state 管理。 |

### SR-V2-FE-D04 LLM 交互式安全解释和安全边界

#### 2.2.5.1 SR 描述

页面必须展示 LLM enabled/used/fallback/degraded/stage error；用户点击 mention、candidate 或 LLM status 时，展示关联的脱敏解释和阶段摘要。

#### 2.2.5.2 SR 实现思路

LLM safe explanation projection：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `enabled` | 是 | 当前模式是否允许 LLM |
| `used` | 是 | 本次请求是否使用 LLM |
| `fallback_used` | 是 | 是否 fallback |
| `degraded` | 是 | 是否降级 |
| `stage_statuses[]` | 是 | classify/extract/rerank/explain 等阶段 safe status |
| `llm_explanations[]` | 是 | 与 global/mention/candidate 关联的脱敏解释条目，可为空数组 |
| `error_code` | 否 | 结构化错误码 |
| `redaction_note` | 是 | 脱敏说明 |

`llm_explanations[]` 条目 schema：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `context_type` | 是 | `global`、`mention` 或 `candidate` |
| `mention_index` | `context_type=mention/candidate` 时必填 | 关联 `mentions[]` 的 0-based index |
| `candidate_id` | `context_type=candidate` 时至少与 `entity_id` 二选一 | 关联候选的稳定 ID；若候选无独立 ID，则使用 `entity_id` |
| `entity_id` | candidate 解释可选 | 关联 entity detail |
| `stage` | 是 | `need_linking`、`classify_type`、`extract_mention`、`retrieve_candidates`、`rerank`、`explain`、`fallback` |
| `stage_status` | 是 | `not_applicable`、`not_used`、`used`、`fallback_used`、`degraded`、`failed` |
| `safe_summary` | 是 | 脱敏解释摘要；不得含 raw prompt/raw response |
| `fallback_reason` | 否 | fallback 或 degraded 原因 |
| `error_code` | 否 | 结构化错误码 |
| `redaction_note` | 是 | 脱敏说明或 `redacted` |

禁止展示：

- 真实 secret/API key/token。
- 真实 base URL。
- raw prompt。
- raw response。
- 完整 LLM 日志。

允许展示：

- 字段名，例如 `api_key_env`、`base_url` label。
- password input 类型。
- 环境变量名。
- redacted/empty 配置状态。

#### 2.2.5.3 功能实现刷新

LLM panel 有三类触发：

| 触发 | UI 更新 |
| --- | --- |
| 点击 mention | 优先匹配 `context_type=mention` 且 `mention_index` 相同的 explanation；若不存在，展示该 mention 的 stage summary empty state。 |
| 点击 candidate | 优先匹配 `context_type=candidate` 且 `mention_index` 与 `candidate_id/entity_id` 相同的 explanation；若不存在，展示 candidate match reason 和 empty safe explanation。 |
| 点击 LLM status | 展示 `context_type=global` 的 explanations、本次请求全局 `stage_statuses` 和 redaction note。 |

若当前为 `offline_demo`，LLM panel 仍展示 disabled/not used 状态和 deterministic summary，避免空白。

空状态规则：找不到关联 explanation 时，UI 必须显示 `No LLM explanation for this item in current mode` 或等价短文本，并保留 stage summary；不得回退成与该 mention/candidate 无关的全局摘要。

#### 2.2.5.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | LLM 异常只影响解释和 rerank，不伪造 linked entity。 |
| 可用性 | 是 | 用户可以从结果对象直接打开相关解释。 |
| 安全性 | 是 | 白名单展示 safe explanation；真实敏感值 fail-closed。 |
| 可维护性 | 是 | LLM status 和 selected explanation 独立于业务事实字段。 |

### SR-V2-FE-D05 浏览器级验收证据和反降级追踪

#### 2.2.6.1 SR 描述

测试和 smoke 必须证明前端工作台真实可用，不能只证明 API 有字段或页面存在 marker。后续验收候选前必须完成用户确认需求反向核查表。

#### 2.2.6.2 SR 实现思路

测试层级：

| 层级 | 覆盖 |
| --- | --- |
| Flask client tests | HTML contains stable test ids；API safe projection；debug default collapsed；sensitive values absent。 |
| Browser/equivalent tests | Desktop/narrow viewport、Query submit、mention click、candidate detail linkage、catalog type filter、LLM panel interaction、screenshot/layout evidence。 |
| Acceptance smoke | 单入口 `run_web_demo.py`；默认 V2 catalog/samples；输出 evidence 文件和反向核查 JSON/Markdown。 |

浏览器级实现可选路线：

| 路线 | 条件 |
| --- | --- |
| Playwright/browser automation | 首选；可生成 screenshot 和 DOM/box assertions。 |
| 等价浏览器级 renderer | 若环境无法安装浏览器，必须证明 JS 交互、layout evidence 和 DOM state，不得退化为纯 API/marker。 |

#### 2.2.6.3 功能实现刷新

验收 evidence 最低包含：

| Evidence | 要求 |
| --- | --- |
| Desktop screenshot/layout | `1366x768`，关键区块可见且无重叠。 |
| Narrow screenshot/layout | `390x844`，关键区块可滚动访问且无重叠。 |
| Query submit | 英文多 mention Query 提交后 mention cards 可见。 |
| Candidate/detail linkage | 点击 candidate 或 linked entity 后 detail panel 更新。 |
| Catalog filter | 选择 entity type 后列表过滤和 count 一致。 |
| Debug collapsed | 初始 debug JSON 未展开。 |
| Security | 真实敏感值未出现在 HTML、API safe projection 或 smoke 日志。 |
| Traceability | 用户确认项映射到实现、测试和验收证据。 |

反向核查 artifact：

| 项 | 设计 |
| --- | --- |
| JSON 路径 | `outputs/logs/v2_frontend_traceability_check.json` |
| Markdown 路径 | `outputs/logs/v2_frontend_traceability_check.md` |
| 生成方 | V2 前端补救 acceptance smoke 或测试设计阶段确认的等价脚本 |
| 提交规则 | `outputs/**` 不入库；release/acceptance 文档只记录脱敏摘要和命令结果 |

反向核查条目 schema：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `decision_id` | 是 | D024、D028、D041、D042、D043、D003 等 |
| `user_confirmed_item` | 是 | 用户确认项原文或稳定摘要 |
| `ac_ids[]` | 是 | AC-V2-FE-001 至 AC-V2-FE-009 的一个或多个 |
| `design_items[]` | 是 | SR-V2-FE-D01 至 D05、接口或测试场景 ID |
| `implementation_files[]` | 实现阶段必填 | 具体文件路径，例如 `src/dv_entity_linking/web.py` |
| `browser_test_ids[]` | 浏览器级 AC 必填 | TC-V2-FE-WEB-* |
| `api_test_ids[]` | 如适用 | Flask/API 测试 ID |
| `evidence_artifacts[]` | 验收候选前必填 | screenshot、layout report、smoke JSON、pytest output 等路径 |
| `status` | 是 | `implemented`、`not_implemented`、`downgraded`、`needs_user_confirmation` |
| `downgrade_classification` | 非 implemented 时必填 | `none`、`weaker_ui`、`api_only`、`marker_only`、`missing_browser_evidence`、`scope_change` |
| `reviewer_result` | 评审/验收阶段必填 | `pass`、`fail`、`blocked` |
| `blocking_rule` | 是 | P0/P1 AC 若非 `implemented` + `pass`，阻塞验收候选；`downgraded` 必须用户确认后才能继续 |

#### 2.2.6.4 DFX 分析

| 检查项 | 是否符合 | 说明 |
| --- | --- | --- |
| 可靠性 | 是 | Smoke 失败阻塞验收候选。 |
| 可用性 | 是 | Evidence 直接覆盖用户能看到和点击的行为。 |
| 安全性 | 是 | 安全扫描按真实值和 raw payload 设计。 |
| 可维护性 | 是 | 测试映射回 AC-V2-FE-001 至 AC-V2-FE-009。 |

---

# 3 接口设计

## 3.1 接口概述

本设计优先复用现有 Flask API。允许新增 safe projection 字段，但不改变实体链接核心返回语义。

| 接口 | 变更 |
| --- | --- |
| `GET /` | 修改页面 shell、CSS 和 JS。 |
| `GET /api/status` | 保持现有接口；必要时补充 LLM safe config status。 |
| `POST /api/link` | 保持现有接口；补充前端所需 mention/candidate/stage safe projection。 |
| `GET /api/entities` | 保持现有接口；用于 catalog panel 和 type filter。 |
| `GET /api/retrieve` | 保持现有接口；用于 similar entities。 |

## 3.2 ER 接口设计

### 3.2.1 POST /api/link

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-001 |
| 接口路径 | `/api/link` |
| 请求方法 | POST |
| 请求参数 | `query`、`mode`、`allow_fallback` |
| 返回参数 | Query result safe projection，包含 query status、mentions、candidates、linked entities、stage summaries |
| 错误码 | `invalid_input`、`invalid_mode`、`llm_timeout`、`llm_http_error`、`llm_auth_error`、`llm_schema_error`、`dependency_failed` |

前端最低依赖字段：

| 字段路径 | 用途 |
| --- | --- |
| `status` | Query summary |
| `mentions[].text` | Mention card |
| `mentions[].span` | Mention card |
| `mentions[].status` | Mention card |
| `mentions[].entity_type` / `mentions[].predicted_type` | Mention card |
| `mentions[].linked_entity` | Detail linkage |
| `mentions[].candidates[]` | Candidate list |
| `mentions[].no_candidate_reason` | no_match/degraded explanation |
| `stage_statuses[]` | LLM panel |
| `safe_summary` | LLM panel |
| `llm_explanations[]` | LLM panel mention/candidate/global association |

### 3.2.2 GET /api/entities

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-002 |
| 接口路径 | `/api/entities` |
| 请求方法 | GET |
| 请求参数 | 可选 `entity_type` |
| 返回参数 | `entities[]`、`entity_count`、`type_counts` |
| 错误码 | `invalid_entity_type` |

说明：`/api/entities` 是本补救的实际 catalog list endpoint。主 V2 SR 中的 `/api/catalog` 为早期逻辑命名，本补救不新增 `/api/catalog` alias；后续实现、测试和文档引用统一使用 `/api/entities`。

### 3.2.3 GET /api/entities/<entity_id>

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-003 |
| 接口路径 | `/api/entities/<entity_id>` |
| 请求方法 | GET |
| 请求参数 | path 参数 `entity_id` |
| 返回参数 | entity detail safe projection，包含 `attributes_safe[]` 和 `omitted_attribute_count` |
| 错误码 | `invalid_entity_id`、`not_found` |

### 3.2.4 POST /api/retrieve

| 项目 | 内容 |
| --- | --- |
| 接口 ID | ER-V2-FE-004 |
| 接口路径 | `/api/retrieve` |
| 请求方法 | POST |
| 请求参数 | JSON `entity_id`、可选 `k` |
| 返回参数 | `results[]` safe entity summaries |
| 错误码 | `invalid_entity_id`、`not_found` |

## 3.3 IR 接口设计

### 3.3.1 WorkbenchState

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `runtime` | object | status API safe projection |
| `catalog` | object | entities、type counts、selected type |
| `query` | object | current query text、mode、allow_fallback |
| `result` | object/null | latest link result |
| `selectedMentionIndex` | number/null | 当前 mention |
| `selectedCandidateId` | string/null | 当前 candidate |
| `selectedEntityId` | string/null | 当前实体详情 |
| `llmPanelContext` | string | global、mention、candidate |
| `selectedExplanation` | object/null | 按 click resolution rule 解析出的 LLM safe explanation |
| `traceabilityCheck` | object/null | acceptance smoke 生成的反向核查摘要，只在 evidence/report 中使用 |
| `errors[]` | array | UI/API safe errors |

### 3.3.2 SafeRenderGuard

`SafeRenderGuard` 是实现约束，不一定需要独立类。所有 HTML/API/smoke 输出必须遵循：

- 只渲染 safe projection 字段。
- 对用户输入和 API 字符串做 HTML escaping。
- 不把 config raw value 注入 DOM。
- Debug JSON 默认折叠，且仍不包含真实敏感值。

---

# 4 数据库设计

本次前端补救不新增数据库表、索引或数据迁移。

| 项 | 结论 |
| --- | --- |
| 表结构设计 | 不涉及 |
| 索引设计 | 不涉及 |
| 数据迁移 | 不涉及 |

---

# 5 部署设计

## 5.1 部署架构

仍为本地单进程 demo：

```text
Python 3.12
  -> scripts/run_web_demo.py
  -> Flask app
  -> in-memory catalog/linking service
  -> browser at localhost
```

## 5.2 配置项

| 配置项 | 默认值 | 说明 | 是否可热更新 |
| --- | --- | --- | --- |
| `--catalog` | `samples/real/v2_entity_examples.json` | 当前默认 V2 entity catalog | 否 |
| `--samples` | `samples/real/v2_query_samples.json` | 当前默认 V2 query samples | 否 |
| `--mode` | `offline_demo` | 默认不依赖真实 LLM | 页面可选 |
| `DVEL_WEB_LLM_API_KEY` | unset | 本地进程环境变量，不回显真实值 | 进程内 |
| `DVEL_WEB_LLM_BASE_URL` | unset | 本地进程环境变量，不回显真实值 | 进程内 |

## 5.3 依赖组件

| 组件名称 | 版本要求 | 用途 |
| --- | --- | --- |
| Flask | `>=3,<4` | Web/API demo |
| pytest | 项目现有依赖 | 自动化测试 |
| Browser automation | 由测试设计阶段确认 | 浏览器级 evidence |

---

# 6 测试设计

## 6.1 测试场景

| 场景编号 | 场景名称 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- | --- |
| TS-V2-FE-001 | Desktop first viewport | 启动 Web demo | 打开 `1366x768` 页面 | runtime、query、summary、catalog、LLM overview 可见且无重叠 |
| TS-V2-FE-002 | Narrow responsive | 启动 Web demo | 打开 `390x844` 页面并滚动 | 关键区块可访问，无关键文本重叠 |
| TS-V2-FE-003 | Multi mention submit | V2 samples loaded | 提交英文多 mention Query | Mention cards 展示 text/type/status/span/linked/candidates |
| TS-V2-FE-004 | Partial explainability | partial sample | 提交 partial Query | 各 mention linked/no_match/degraded 原因可区分 |
| TS-V2-FE-005 | Candidate/detail linkage | 有候选结果 | 点击 mention/candidate/entity | Detail panel 和 similar entities 更新 |
| TS-V2-FE-006 | Catalog filter | V2 catalog loaded | 选择 entity type | 列表和 counts 与类型一致 |
| TS-V2-FE-007 | LLM safe explanation | offline 或 llm_enabled | 点击 mention/candidate/LLM status | 显示脱敏解释和 stage summary，无真实敏感值 |
| TS-V2-FE-008 | Debug collapsed/security | 页面初始加载 | 检查 debug 和 HTML/API/log | Debug 默认折叠，真实敏感值缺失 |
| TS-V2-FE-009 | Single web entry | 仓库脚本 | 检查 demo scripts | 只维护 `scripts/run_web_demo.py` |
| TS-V2-FE-010 | Standalone no_match UI | no_match sample | 提交 no_match Query | Query status 为 no_match；无 linked entity；无伪 candidate/detail；显示 no-candidate reason |
| TS-V2-FE-011 | Standalone not_required UI | not_required sample | 提交 not_required Query | Query status 为 not_required；无 mention/linked entity/candidate；显示无需链接原因；detail panel 不被伪更新 |
| TS-V2-FE-012 | Reverse traceability check | 前端补救实现和测试完成 | 生成反向核查 JSON/Markdown | 每个用户确认项均映射到 AC、设计项、实现文件、测试 ID 和 evidence；无 downgraded/not_implemented |

## 6.2 测试用例

| 用例编号 | 用例名称 | 所属场景 | 优先级 | 设计者 |
| --- | --- | --- | --- | --- |
| TC-V2-FE-WEB-001 | Desktop workbench first viewport browser check | TS-V2-FE-001 | P0 | Codex |
| TC-V2-FE-WEB-002 | Narrow viewport browser check | TS-V2-FE-002 | P1 | Codex |
| TC-V2-FE-WEB-003 | Multi mention query browser interaction | TS-V2-FE-003 | P0 | Codex |
| TC-V2-FE-WEB-004 | Partial mention status browser interaction | TS-V2-FE-004 | P0 | Codex |
| TC-V2-FE-WEB-005 | Candidate and entity detail linkage | TS-V2-FE-005 | P1 | Codex |
| TC-V2-FE-WEB-006 | Catalog type filter | TS-V2-FE-006 | P1 | Codex |
| TC-V2-FE-WEB-007 | LLM safe explanation interaction | TS-V2-FE-007 | P1 | Codex |
| TC-V2-FE-WEB-008 | Debug collapsed and sensitive value absence | TS-V2-FE-008 | P1 | Codex |
| TC-V2-FE-WEB-009 | Single web entry regression | TS-V2-FE-009 | P1 | Codex |
| TC-V2-FE-WEB-010 | Standalone no_match negative UI | TS-V2-FE-010 | P0 | Codex |
| TC-V2-FE-WEB-011 | Standalone not_required negative UI | TS-V2-FE-011 | P0 | Codex |
| TC-V2-FE-WEB-012 | Reverse traceability artifact schema | TS-V2-FE-012 | P0 | Codex |

## 6.3 验收标准

| IR AC | 设计测试映射 |
| --- | --- |
| AC-V2-FE-001 | TS-V2-FE-001、TS-V2-FE-002、TC-V2-FE-WEB-001、TC-V2-FE-WEB-002 |
| AC-V2-FE-002 | TS-V2-FE-003、TC-V2-FE-WEB-003 |
| AC-V2-FE-003 | TS-V2-FE-004、TC-V2-FE-WEB-004 |
| AC-V2-FE-004 | TS-V2-FE-010、TS-V2-FE-011、TC-V2-FE-WEB-010、TC-V2-FE-WEB-011 |
| AC-V2-FE-005 | TS-V2-FE-005、TS-V2-FE-006、TC-V2-FE-WEB-005、TC-V2-FE-WEB-006 |
| AC-V2-FE-006 | TS-V2-FE-007、TC-V2-FE-WEB-007 |
| AC-V2-FE-007 | TS-V2-FE-001、TS-V2-FE-002、TC-V2-FE-WEB-001、TC-V2-FE-WEB-002 |
| AC-V2-FE-008 | TS-V2-FE-001 至 TS-V2-FE-012 |
| AC-V2-FE-009 | TS-V2-FE-012、TC-V2-FE-WEB-012、`outputs/logs/v2_frontend_traceability_check.json`、`outputs/logs/v2_frontend_traceability_check.md` |

---

# 7 风险分析

| 风险编号 | 风险描述 | 风险等级 | 影响 | 应对措施 | 负责人 |
| --- | --- | --- | --- | --- | --- |
| R-V2-FE-001 | 浏览器自动化环境不可用 | 中 | AC-V2-FE-008 无法证明 | 测试设计阶段优先 Playwright；若不可用，必须提供等价浏览器级 renderer 和截图/布局证据，不得降级为 API/marker。 | 实现/测试负责人 |
| R-V2-FE-002 | `web.py` 内嵌 HTML/CSS/JS 继续膨胀 | 中 | 可维护性下降 | 在单文件内分段函数化 template/projection/render helpers；如设计评审认为必须拆文件，限定在 Web UI 边界内。 | 实现负责人 |
| R-V2-FE-003 | 后端 safe projection 字段不足 | 中 | 前端展示无法满足 AC | 只补 safe projection，不改核心链接语义；字段缺口必须在实现评审输入包列明。 | 实现负责人 |
| R-V2-FE-004 | LLM 解释被再次弱化为纯状态 | 高 | 重复静默降级 | TC-V2-FE-WEB-007 和评审输入包必须验证 mention/candidate/status 点击触发解释。 | 评审负责人 |
| R-V2-FE-005 | 安全扫描误判字段名为泄露 | 低 | 测试噪声 | 安全测试区分真实值和字段名；真实值使用本地 sentinel 验证不得回显。 | 测试负责人 |
| R-V2-FE-006 | 反向核查被写成叙述性摘要 | 高 | 验收候选前再次漏掉用户确认项 | 强制 JSON/Markdown 双 evidence；schema 中 `downgraded`、`not_implemented`、`needs_user_confirmation` 均阻塞 P0/P1 AC。 | 测试/验收负责人 |

---

# 附录 A 评审记录

| 评审日期 | 评审人 | 评审意见 | 处理状态 |
| --- | --- | --- | --- |
| 2026-06-02 | no-context 独立功能设计评审 Bacon | Ready for disposition；无 P0，4 个 P1，1 个 P2，要求补齐反向核查 schema、LLM 解释关联字段、负例 UI 测试、safe attributes fail-closed 和 catalog API 命名边界。 | 处置完成 |
| 2026-06-02 | independent verifier Bohr | 4 个 P1 和 1 个 P2 均 Closed；文档卫生 Passed；closed with recorded residual risk。 | 闭环通过 |

# 附录 B 功能设计评审输入包

请独立功能设计评审者只读复核：

- [SR-FRONTEND-REMEDIATION.md](./SR-FRONTEND-REMEDIATION.md)
- [IR-FRONTEND-REMEDIATION.md](./IR-FRONTEND-REMEDIATION.md)
- [FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md)
- [FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md)
- [SR.md](./SR.md)
- [../../process/DV_PROCESS.md](../../process/DV_PROCESS.md)
- [../../current/DECISIONS.md](../../current/DECISIONS.md)
- `src/dv_entity_linking/web.py`
- `scripts/run_web_demo.py`
- `tests/test_web.py`
- `tests/test_contract_artifacts.py`

评审重点：

- 是否完整覆盖 AC-V2-FE-001 至 AC-V2-FE-009。
- 是否仍存在把前端改造降级为 API/marker 的空间。
- LLM 交互式安全解释是否具备可实现的状态和触发设计。
- 多 mention、partial、candidate/detail/catalog 联动是否具备明确数据字段和交互路径。
- 安全边界是否既禁止真实敏感值，又不误伤字段名和 redacted 状态。
