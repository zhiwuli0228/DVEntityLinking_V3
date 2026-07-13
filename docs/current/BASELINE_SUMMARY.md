# DVEntityLinking 基线总结

最后更新：2026-06-26

本文是对 DVEntityLinking 当前状态的设计、工程、实现、测试维度的结构化总结，用作后续落入基线的输入。权威入口仍为 `docs/PROJECT.md`、`docs/current/` 与各版本 `docs/baselines/`、`docs/releases/`。

---

## 1. 项目定位与目标

DVEntityLinking 是面向 DV 运维 Copilot 和故障 Agent 的**实体理解底座**，把自然语言 Query 中的实体词识别、归一化、链接到可查询的 DV 实体，并输出可解释、可评测的结构化结果。它不是单点问答能力，而是 Copilot、故障 Agent 和 Web/API 共用的实体服务层。

核心能力：实体目录构建、实体词表、Query 实体识别（NER）、候选召回、链接/消歧、实体查询、Top-K 相似检索、评测闭环与安全治理。

---

## 2. 整体架构

```text
scripts/run_web_demo.py (单 Web 入口)
  └─ Flask API (src/dv_entity_linking/web.py)
       ├─ GET /          → React SPA (web/frontend/dist)
       ├─ GET /classic   → 旧 SSR 页面（供 acceptance smoke）
       ├─ GET /assets/*  → SPA 静态资源
       └─ /api/{status,link,entities,entities/<id>,retrieve,llm/config,samples}
  └─ EntityLinkingService (service.py)
       ├─ V3 路径: NerPipeline + EntityStorageRepository (Redis/Gauss Mock)
       └─ V1/V2 路径: EntityExtractor + EntityLinker + EntityRetriever + CatalogRepository
  └─ React SPA (web/frontend, Vite+React+TS+Tailwind)
       ├─ api/client.ts (类型化 API 客户端)
       ├─ state/workbench.ts (useReducer 集中状态)
       ├─ lib/adapter.ts (LinkResult → UI mentions 适配器)
       └─ components/ (Shell/StatusBand/QueryText/ResultStream/EntityDetailZone/LlmExplanation/...)
```

双链路：默认 `legacy_catalog`（V1/V2 catalog 驱动），可选 `--storage-mode v3_mock`（V3 两层存储驱动）。Web 单入口 `run_web_demo.py` 统一托管。

---

## 3. 设计

### 3.1 数据契约

- **实体（EntityRecord）**：最小字段 `entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`；可选 `attributes`、`relations`、`data_layer`、`source`。V3 结构化实体沿用最小字段，类型专属字段待后续确认。
- **Query 样例**：`id`、`query`、`mentions[]`（`text`、`span` 0-based end-exclusive、`expected_entity_ids`、mention-level `expected_status`）、`expected_entities`、`expected_status`。V2 起支持多 mention，V2 Query 全英文。
- **链接结果（EntityLinkResult）**：`status`、`mentions[]`、`mention_results[]`、`linked_entity`、`candidates[]`、`confidence`、`disambiguation_reason`、`no_match_reason`、`bypass_reason`、`degraded`、`error_code`、`data_layer`、`source`、`stage_trace`（V3）、`mode_status`、`llm_explanations[]`。
- **安全投影**：`attributes_safe[]` 白名单（`SAFE_ATTRIBUTE_KEYS`）+ `FORBIDDEN_ATTRIBUTE_FRAGMENTS` 拦截 `api_key`/`token`/`secret`/`base_url`/`raw_request`/`raw_response` 等；`omitted_attribute_count` 计数；API 不回显真实 key/token/base URL/raw prompt/raw response。

### 3.2 实体类型与状态枚举

- **EntityType**：`alarm`、`network_resource`、`alarm_event`、`kpi_metric`、`topology_relation`、`knowledge_case`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`。
- **Status**：`linked`、`partial`、`ambiguous`、`no_match`、`not_required`、`dependency_failed`、`invalid_input`。
- **RunMode**：`offline_demo`（默认，不依赖真实 LLM/DV）、`llm_enabled_demo`、`mock_fallback`。
- **ErrorCode**：`invalid_input`、`invalid_mode`、`invalid_allow_fallback`、`catalog_load_failed`、`runtime_source_failed`、`query_dataset_load_failed`、`validation_failed`、`data_layer_not_confirmed`、`llm_timeout`、`llm_http_error`、`llm_auth_error`、`llm_schema_error`、`dependency_failed`、`output_write_failed`。
- **V3 存储枚举**：`StorageLookupStatus`（hit/miss/invalid_key/dependency_failed/entity_miss）、`StorageStartupStatus`（ready/failed）、`StorageErrorCode`（schema_error/missing_required_field/unsupported_schema_version/duplicate_entity_id/duplicate_key/dangling_entity_id/invalid_key/unconfirmed_data_layer）。

### 3.3 两层存储设计（V3）

- **Redis Mock（实体词 KV 缓存）**：key=规范化实体词（`normalize_entity_word`：NFKC + casefold + 去空白），value=单实体 ID。`key_scope` 强约束为 `['canonical_name','confirmed_aliases']`，`aliases_auto_generated` 必须为 false（D074：不自动生成别名）。duplicate key 映射多 ID → fail-closed；同 ID 重复 → 去重并 warning。
- **Gauss Mock（结构化实体存储）**：按 entity_id 查询 `StructuredEntityRecord`。duplicate entity_id、缺失必需字段、schema 错误 → fail-closed。
- **cross-layer validation**：Redis entity_id 必须在 Gauss 存在（否则 dangling），entity_word 必须是引用实体的 canonical_name 或 confirmed alias（否则 unconfirmed_data_layer）。
- **V3CatalogAdapter**：把 `EntityStorageRepository` 适配为 catalog 接口（`entities`/`get`/`by_type`/`search`/`neighbors`），`neighbors` 当前返回空（无关系建模）。

### 3.4 NER 与链接策略

- **V1（alarm-only）**：`AlarmIndexBundle` 精确索引，告警 ID 强特征，短 ID 子串保护（`51` 不命中 `51020`），phrase similarity 兜底。
- **V2（多类型）**：`EntityExtractor` 分层判断 need-linking → 类型内 mention 识别（catalog 名称/别名字面匹配 + 未知 entity-shaped token）；`EntityLinker` 候选召回（canonical 0.99/alias 0.92/partial 0.78/fuzzy 0.7×ratio + 类型加分 0.05）+ 排序 + `link_min_confidence=0.70`/`ambiguity_margin=0.08` 消歧 + 状态聚合（`partial_on_degraded` 多 mention 时生效）。
- **V3（storage-backed）**：`NerPipeline` 阶段化（query_validation → need_linking → mention_detection → storage_lookup → status_aggregation），known mentions（实体词字面匹配，最长非重叠）+ unknown entity-shaped token，storage 精确查找（hit→linked, miss→no_match, dependency_failed→partial/degraded），输出 `stage_trace` 和 `storage_lookup` 投影。
- **LLM 增强**：`llm_enabled_demo` 可选；LLM 抽取/消歧经 schema 校验后入链，失败按 `allow_fallback` 回退或返回 `dependency_failed`。

### 3.5 前端架构（React SPA）

- **栈**：Vite 5 + React 18 + TypeScript 5 + Tailwind 3，手写 Tremor 风格组件（无重型 UI 库依赖）。
- **状态**：`VisualWorkbenchState`（`useReducer`）集中 `runtime`/`catalog`/`query`/`mode`/`result`/`mentions`/`activeMentionIndex`/`activeCandidateId`/`activeEntityId`/`activeTypeFilter`/`llmContext`/`selectionSeq`/`debugCollapsed`。
- **适配器**：`adaptLinkResult` 把 `/api/link` 的 `mention_results[]` 纯函数映射为 UI `mentions[]`（不新增后端顶层字段），vitest 覆盖字段来源。
- **原型吸收**：SigNoz（`StatusBand` 指标密度）、doccano（`QueryText` Query 内 mention span 内联高亮+点击联动）、CopilotKit（`LlmExplanation` stage chips + context 切换）、Tremor（深色 `Shell` 工作台外壳）。

---

## 4. 工程

### 4.1 目录结构

```text
src/dv_entity_linking/   核心包（models/catalog/extraction/linking/alarm_index/retrieval/llm/service/web/evaluation/datasets/ner_pipeline/storage）
web/frontend/            React SPA 源码（src/{api,state,lib,components,styles}）
scripts/                 run_web_demo.py 单入口 + run_v{1,2,3}_evaluation/acceptance_smoke + demo_runtime + capture_screenshots（dev-only）
samples/real/            V1/V2/V3 脱敏样例与 Mock artifacts
tests/                   pytest（test_web/test_catalog/test_linking/test_retrieval/test_v2_runtime/test_v3_storage_ner/test_demo_scripts/test_contract_artifacts/test_run_repository/test_evaluation）
docs/                    baselines/<v>/、releases/、current/、process/
config/                  llm.local.json（ignored）
outputs/                 日志与证据（ignored）
```

### 4.2 技术栈与依赖

- **后端**：Python 3.12、Flask 3（唯一运行依赖）。无数据库、无外部检索组件，纯内存索引。
- **前端**：Node 18+，Vite/React/TS/Tailwind（`web/frontend/package.json`）；`npm run build` 产物到 `dist/`，由 Flask 托管；`npm run dev` 走 Vite 5173 代理 `/api`→5015。
- **dev-only**：`scripts/requirements-dev.txt`（playwright），用于 `capture_screenshots.py` 采 before/after 截图，可用系统 Chrome/Edge 免下载。

### 4.3 启动与构建

- **单 Web 入口**：`python scripts/run_web_demo.py --mode offline_demo --port 5015`。默认加载 V2 样例；`--storage-mode v3_mock` 切 V3 两层存储；`--catalog/--samples` 可回看历史版本。
- **前端构建**：首次或前端改后需 `cd web/frontend && npm install && npm run build`；`dist` 缺失时 `GET /` 返回 503 提示。
- **dev 模式**：Flask（5015）+ `npm run dev`（5173 热更新）。

### 4.4 配置与安全边界

- `config/llm.local.json` 本地 ignored；API key 经环境变量（`DVEL_LLM_API_KEY`/`DVEL_WEB_LLM_API_KEY`）；不记录 base URL、Authorization、完整请求/响应。
- 数据分层 `DataLayer`：L0_SYNTHETIC / L1_SANITIZED / L2_SIMULATED_INTERFACE / L3_REAL_READONLY / LOCAL_REAL_ARTIFACT；非 L0 需确认记录。
- D003：真实 DV 实体/字段/接口/样例/Mock 边界必须先确认；`outputs/**` 不入库。

---

## 5. 实现

### 5.1 核心模块职责

| 模块 | 职责 |
| --- | --- |
| `models.py` | 全部 dataclass/枚举契约（实体、链接结果、存储、错误等）+ `to_plain`/`clamp_score` |
| `catalog.py` | `CatalogRepository`：加载、schema 校验（V1/V2）、内存索引、data_layer 校验、关系校验 |
| `extraction.py` | `EntityExtractor`：规则/LLM NER、fallback、need-linking 判定 |
| `alarm_index.py` | `AlarmIndexBundle`：alarm 精确索引 + 短 ID 保护 + phrase 兜底 |
| `linking.py` | `EntityLinker`：候选召回、排序、消歧、状态聚合、LLM rerank |
| `retrieval.py` | `EntityRetriever`：实体查询 + Top-K 相似（名称/描述/类型/拓扑/知识关系评分） |
| `llm.py` | `LLMClient`/`OpenAICompatibleLLMClient`/`MockLLMClient` + `LLMConfig` |
| `evaluation.py` | `RunRepository` + query/mention/type-level 评测 |
| `datasets.py` | `QueryDatasetLoader`：样例 schema 校验与解析 |
| `ner_pipeline.py` | V3 `NerPipeline`：storage-backed NER + stage_trace |
| `storage.py` | V3 `GaussEntityStoreMock`/`RedisEntityWordCacheMock`/`EntityStorageRepository`/`V3CatalogAdapter` |
| `service.py` | `EntityLinkingService`：编排 V1/V2/V3 链路、LLM 配置、run 持久化 |
| `web.py` | Flask API + SPA 托管 + safe projection（`_safe_link_result`/`_safe_attributes`/`_build_llm_explanations` 等） |

### 5.2 版本演进

- **V0（closed）**：Mock 合成实体 demo，多类型、Web/API、真实 LLM 条件 smoke。
- **V1（closed）**：alarm-only，9 实体/16 Query，LLM 模式切换，短 ID 保护，负例零误报，precision/recall=1.0。
- **V2（blocked→AC-008 已解）**：扩展 `ne_type/ne_name/kpi_task_name/kpi_meas_type_key`，unified catalog（25 实体），英文多 mention Query，`partial` 聚合，type-level metrics。视觉补救 AC-V2-FE-VIS-008 经 before/after 截图证据已解（`blocking_count=0`）。
- **V3（acceptance candidate prepared）**：两层存储 Mock、storage-backed NER pipeline、V3 mock artifacts/golden cases、`--storage-mode v3_mock`、V1/V2 技术回归。等待用户验收确认。
- **前端整改（已验收）**：`GET /` 改由 React SPA 提供，旧 SSR 保留 `/classic` 供 smoke；后端仅 `web.py` 路由 + 3 smoke `/classic` + `test_web.py` 调整；V2 数据/算法/评测与 V3 存储层零改动。

### 5.3 前端 SPA 实现要点

- `GET /` 返回 `web/frontend/dist/index.html`，`/assets/*` 托管构建产物；`/classic` 保留旧 SSR 供 acceptance smoke（SSR `data-testid` 标记断言不变）。
- `run_v2_acceptance_smoke.py` 接入 before 截图检测：`outputs/logs/v2_frontend_before_{desktop,narrow}_*.png` 存在时 `AC-V2-FE-VIS-008` 标记 implemented、`blocking_count=0`。
- `capture_screenshots.py`（playwright）按 canonical scenario 采集 before/after 截图并写 `v2_frontend_browser_evidence.json`（含 17 项 region-observed checks）。
- `selectionSeq` 保证 mention/candidate 选中即使 `activeEntityId` 未变也触发详情重新拉取。

---

## 6. 测试

### 6.1 测试矩阵

| 层 | 工具 | 覆盖 |
| --- | --- | --- |
| 后端单测 | pytest | catalog/extraction/linking/retrieval/web API/evaluation/datasets/V2 runtime/V3 storage+NER |
| 契约/文档 | pytest (`test_contract_artifacts.py`) | 数据契约、决策台账、release/baseline 文档内容断言 |
| smoke 脚本 | pytest (`test_demo_scripts.py`) + 子进程 | v1/v2/v3 acceptance smoke、evaluation、browser evidence 校验、D003 扫描 |
| 前端单测 | vitest + @testing-library | `adaptLinkResult` 适配器字段来源、默认选中、storage_lookup 透传 |
| 视觉证据 | playwright（dev-only） | before/after 桌面/窄屏截图 + region-observed checks |

### 6.2 验收阈值与当前结果

| 验证 | 阈值/结果 |
| --- | --- |
| `python -m pytest` | **92 passed** |
| `python -m compileall -q src scripts` | 通过 |
| `npm run test`（vitest） | 3 passed |
| V1 evaluation | total=16, pass=16, precision=1.0, recall=1.0, negative_fp=0 |
| V2 evaluation | total=12, pass=12, precision=1.0, recall=1.0, 含 type_metrics |
| V3 evaluation | total=6, pass=6, precision=1.0, recall=1.0, negative_fp=0 |
| V2 acceptance smoke（真实运行） | `ok=true`、`browser_evidence_ok=true`、`visual_traceability_blocking_count=0`（AC-008 已解） |
| V3 acceptance smoke | `ok=true`、`linked_storage_redis_statuses=["hit","hit"]` |
| 敏感字段扫描 | 通过（无真实 key/token/base URL/raw payload） |

### 6.3 默认验证命令

```powershell
python -m pytest
python -m compileall -q src scripts
python scripts\run_v1_evaluation.py
python scripts\run_v1_acceptance_smoke.py --mode offline_demo
python scripts\run_v2_evaluation.py
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
python scripts\run_v3_evaluation.py
python scripts\run_v3_acceptance_smoke.py
git diff --check
cd web/frontend; npm run test; npm run build
```

---

## 7. 当前状态与版本基线

| 版本 | 状态 | 入口 |
| --- | --- | --- |
| V0 | closed | `docs/releases/V0.md` |
| V1 | closed | `docs/releases/V1.md` |
| V2 | AC-V2-FE-VIS-008 已解；整体 accepted/closed 仍待用户确认 | `docs/releases/V2.md` |
| V3 | Acceptance candidate prepared；pending user acceptance；not accepted/closed | `docs/releases/V3.md` |
| 前端整改 | 已验收通过；commit `0b1905f` | D090/D091 |

最近提交：`0b1905f Overhaul web frontend to React SPA workbench`、`f80dec9 Add V3 Redis/Gauss mock storage and NER pipeline`。

---

## 8. 残余风险与后续

| 项 | 状态 | 后续 |
| --- | --- | --- |
| V2 跨类型同名歧义 | 非阻塞残余风险 | 补同 span 多类型候选保留样例与判定规则 |
| V3 runtime mock adapter 深化 | confirmed-sample startup slice | 接真实 Redis/Gauss 前补 source lifecycle/失败语义 |
| V3 类型专属字段扩展 | 沿用最小字段 | 新增类型/关系/展示字段需单独确认 |
| 真实 LLM live smoke 常态化 | 默认不依赖真实 LLM | 若纳入条件验收需确认脱敏报告与稳定性门槛 |
| `web.py` 旧 SSR 死代码 | 保留在 `/classic` 供 smoke | 可作后续清理（约 1300 行 `_index_html`/`_render_*`） |
| 前端构建依赖 | 需 Node 18+，smoke 前需 `npm run build` | dist 不入库；缺 dist 时 `GET /` 503 提示 |

---

## 9. 基线落入建议

1. 本总结可作为 `docs/baselines/` 下一个基线快照的输入；建议基线命名按当前版本组合（V3 candidate + 前端整改）。
2. 落入基线前确认：V3 是否 accepted/closed、V2 是否随 AC-008 解除一并关闭、前端整改是否单独成基线项。
3. 基线应冻结当前 `pytest 92 passed`/`vitest 3 passed`/三版本 evaluation+smoke 结果作为回归基准。
4. 安全边界（D003、`config/llm.local.json` ignored、`outputs/**` 不入库、attributes_safe 白名单）须作为基线不变约束。
