# 实体词匹配容量矩阵压测与演进优化报告

> 本报告承接 `MYSQL_INSTR_PRELIMINARY_BENCHMARK_20260717.md` 的预压测结论，在 5 万/10 万/20 万/50 万四档数据量下完成「数据量 × Query 长度 × 并发 × 冷热」全矩阵压测，定位性能根因并给出后续演进优化建议。报告作为优化前基线与容量风险证据，不作为正式上线容量验收。

## 1. 结论

当前 `MATCH_WORDS` 的反向包含查询 `WHERE INSTR(:query, normalized_key) > 0` 是系统性的 CPU 计算瓶颈，且无法通过加并发、预热缓存或加索引缓解：

- **时延随三因子近线性放大**：`O(数据量 × Query 长度 × 并发)`。50 万词条、超长 Query、并发 20 的 P50 已达 **113.4 秒**（逼近 120 秒客户端超时）。
- **吞吐在并发 5 即封顶**：50 万档 QPS 在 c=5/10/20 完全一致（short 2.6、medium 1.0、long 0.4、ultra 0.2），加并发零吞吐增益，只抬高单请求时延——典型 CPU 计算瓶颈特征。
- **冷热无差异**：四档数据量下冷/热 P50 比值均为 1.00，排除磁盘 I/O 瓶颈，坐实瓶颈在 INSTR 逐行扫描的 CPU 计算。
- **EXPLAIN 证据**：`INSTR(:query, normalized_key)` 函数作用于列，B-Tree 索引失效，强制全表扫描 + filesort；`uk_normalized_key`、`idx_entity_word_type` 均无法服务该谓词。

根因明确：**反向包含匹配无法走索引，每查询对全量词条做线性字符串扫描，并发只能争抢 CPU**。优化必须从匹配模型本身入手，内存多模式自动机（Aho-Corasick）是等效且数量级更优的正解。

## 2. 测试目标与范围

| 项目 | 内容 |
| --- | --- |
| 目标 | 在多数据量/多 Query 长度/多并发/冷热四维度下，量化当前 `MATCH_WORDS` 与 `QUERY_RECALL` 的时延与吞吐曲线，定位瓶颈并为优化提供基线 |
| 数据量 | 50,000 / 100,000 / 200,000 / 500,000 entity word（四档独立库） |
| Query 长度 | short(25) / medium(100) / long(300) / ultra(600) 归一化字符，均命中同一实体 `DV-MOCK-000000334` |
| 并发 | 1 / 5 / 10 / 20 |
| 温度 | 冷（FLUSH TABLES 后首波）/ 热（预热 3 轮后稳态） |
| 层级 | `remote_match`（MATCH_WORDS 单次远程调用）/ `query_recall`（MATCH_WORDS + BATCH_GET 端到端） |
| 采样 | 每格 10 秒采集；高数据量/低并发格样本数较少（如实记录 N） |
| 矩阵规模 | 4 × 4 × 4 × 2 × 2 = **256 格**，全部完成，1 格瞬时失败 |

未覆盖：并发 50/100、15 分钟以上持续压测、真实生产接口、数据发布并发、服务端 CPU/I/O/锁/连接池资源指标采集。冷数据为 FLUSH TABLES 近似（InnoDB buffer pool 可能保留页）。

## 3. 测试环境与数据

| 项目 | 内容 |
| --- | --- |
| 数据库 | 远程 MySQL 8.0，`utf8mb4_0900_ai_ci`，InnoDB |
| 连接配置 | 连接池 30，`connect_timeout=20s`，`read_timeout=120s`，客户端总超时 120s |
| 链路 | 远程公网；本地 werkzeug HTTP mock（127.0.0.1 随机端口）包装 `MySqlEntityDataMockSource` |
| 表结构 | `el_entity_word`（无 status 列）：PK(entity_word_id)、UK(normalized_key)、idx(entity_type)、idx(entity_id) |
| 匹配 SQL | `SELECT ... FROM el_entity_word WHERE INSTR(%s, normalized_key) > 0 ORDER BY priority DESC, entity_word_id ASC` |
| 数据版本 | 50k/100k/200k/500k 四档独立库，行数与预设一致（见附录） |
| entity 分布 | metric 80%，alarm/application/device/service 各 5%；每实体 3 词 |

## 4. 测试结果

**单位说明**：除特别注明外，所有延迟数值单位为**毫秒（ms）**；QPS 表单位为**次/秒（queries/sec）**；「比值」列为**无量纲**；失败表中的 N/错误数为**次数**。P50 为主指标，QPS 按成功返回请求计算。

### 4.1 数据量扩展（remote_match, warm, c=1，P50 延迟，单位 ms）

| volume | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 50k | 83.0 | 158.8 | 329.9 | 598.4 |
| 100k | 135.4 | 252.8 | 614.0 | 1146.0 |
| 200k | 210.2 | 490.0 | 1204.7 | 2252.6 |
| 500k | 487.6 | 1154.0 | 2916.0 | 5570.4 |

数据量 10 倍（50k→500k），P50 放大 5.9–9.9 倍，近线性。

### 4.2 并发扩展（remote_match, warm, 500k，P50 延迟，单位 ms）

| concurrency | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 1 | 487.6 | 1154.0 | 2916.0 | 5570.4 |
| 5 | 1852.5 | 4945.1 | 13680.8 | 26922.1 |
| 10 | 3691.5 | 10256.6 | 28080.7 | 54370.8 |
| 20 | 7396.5 | 20317.6 | 55698.9 | **113436.9** |

并发 20 倍（c1→c20），P50 放大 15–20 倍，近线性。无任何并行收益。

### 4.3 吞吐量 QPS（remote_match, warm, 500k，单位 次/秒）—— 关键证据

| concurrency | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2.0 | 0.9 | 0.3 | 0.2 |
| 5 | 2.6 | 1.0 | 0.4 | 0.2 |
| 10 | 2.6 | 1.0 | 0.4 | 0.2 |
| 20 | 2.6 | 1.0 | 0.4 | 0.2 |

**QPS 在 c=5 后完全封顶**，c5≈c10≈c20。再加并发零吞吐增益，仅抬高单请求时延。这是 CPU 计算瓶颈的决定性证据——INSTR 全表扫描把 MySQL CPU 打满，并发请求只能排队串行扫描。

### 4.4 Query 长度敏感（remote_match, warm, c=1，P50/P95/max 延迟，单位 ms）

| length (chars) | P50 | P95 | max |
| --- | ---: | ---: | ---: |
| short (25) | 83.0 | 94.9 | 100.7 |
| medium (100) | 158.8 | 171.3 | 178.4 |
| long (300) | 329.9 | 351.4 | 357.5 |
| ultra (600) | 598.4 | 615.0 | 615.0 |

Query 长度 24 倍（25→600），P50 放大 7.2 倍。INSTR 单行代价随 haystack 长度上升，与扫描行数相乘。

### 4.5 冷 vs 热（remote_match, c=1, medium，P50/max 延迟单位 ms，比值为无量纲）

| volume | cold P50 (ms) | warm P50 (ms) | cold max (ms) | warm max (ms) | 比值 (warm/cold) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 50k | 158.9 | 158.8 | 176.2 | 178.4 | 1.00 |
| 100k | 252.9 | 252.8 | 276.6 | 266.8 | 1.00 |
| 200k | 488.8 | 490.0 | 514.6 | 509.7 | 1.00 |
| 500k | 1172.7 | 1154.0 | 1184.1 | 1172.8 | 0.98 |

四档冷热比值均为 1.00。若是 I/O 瓶颈，冷应远慢于热；比值 1.00 排除磁盘 I/O，坐实瓶颈为 CPU 计算。（冷为 FLUSH TABLES 近似，结论方向不变：即使 buffer pool 全热，时延依旧由扫描计算决定。）

### 4.6 remote_match vs query_recall（warm, c=1, medium，P50 延迟单位 ms，比值为无量纲）

| volume | remote_match P50 (ms) | query_recall P50 (ms) | 比值 (qr/rm) |
| --- | ---: | ---: | ---: |
| 50k | 158.8 | 210.4 | 1.32 |
| 100k | 252.8 | 359.9 | 1.42 |
| 200k | 490.0 | 545.0 | 1.11 |
| 500k | 1154.0 | 1295.9 | 1.12 |

`query_recall` 比 `remote_match` 慢 11–42%（多一次 BATCH_GET + NER 固定开销）。数据量越大，扫描占比越高，比值趋近 1.1；小数据量下固定开销更显眼（1.32–1.42）。

### 4.7 query_recall 并发扩展（warm, 500k，P50 延迟，单位 ms）

| concurrency | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 1 | 548.6 | 1295.9 | 3163.8 | 5871.4 |
| 5 | 2533.8 | 5477.5 | 14326.7 | 28335.9 |
| 10 | 3930.7 | 11374.5 | 29417.2 | 56562.1 |
| 20 | 7739.3 | 21082.7 | 57646.4 | 109316.3 |

端到端层同样随并发近线性恶化，ultra/c20 P50 达 109 秒。

### 4.8 失败情况（N 与错误数单位为「次数」）

256 格中仅 1 格失败：`200k / long / c10 / cold / remote_match`，10 次请求中 1 次 `transport_error`（单次连接类瞬时错误，非系统性）。无正确性失败、无数据版本漂移。

## 5. 问题定位

### 5.1 根因：反向包含匹配无法走索引

匹配 SQL（`src/dv_entity_linking/performance_mock/mysql_source.py`）：

```sql
SELECT ... FROM el_entity_word
WHERE INSTR(%s, normalized_key) > 0
ORDER BY priority DESC, entity_word_id ASC
```

`INSTR(:query, normalized_key)` 的语义是"找出 `normalized_key` 作为子串出现在查询中的所有词条"。这是**多模式子串匹配**问题，方向为"模式包含在查询里"。函数作用于列，B-Tree 索引完全失效：`uk_normalized_key(normalized_key)`、`idx_entity_word_type(entity_type)` 都无法服务该谓词，强制对全量词条做逐行字符串判断 + filesort。

EXPLAIN 实测（50 万档）：`type=ALL`，全表扫描，`Using where; Using filesort`。早前 100 万档预压测同构 SQL 的 `EXPLAIN ANALYZE` 显示实际扫描全部 active 词、数据库内执行约 290 毫秒（无类型过滤）。

### 5.2 三项交叉证据

| 证据 | 观察 | 指向 |
| --- | --- | --- |
| QPS 并发封顶 | c=5/10/20 QPS 完全一致 | CPU 计算瓶颈，非连接/池/I/O |
| 冷热比值 1.00 | 四档冷≈热 | 排除磁盘 I/O，坐实 CPU 计算 |
| 三因子近线性 | 数据量×Query长度×并发均近线性放大 | 时延 = O(扫描行数 × haystack长度 × 并发排队) |

三者共同收敛到同一结论：**瓶颈是 INSTR 逐行扫描的 CPU 计算，加并发/预热/加索引均无法缓解**。

### 5.3 次要放大因素

1. **filesort**：`ORDER BY priority DESC, entity_word_id ASC` 无覆盖索引，命中行需排序。
2. **每请求固定开销**：每次取连接 `ping(reconnect=True)` + 每次 `match_words` 前查 `data_version`，各一个 RTT；远程公网链路下放大固定底噪。
3. **query_recall 双远程调用**：端到端比单次 match 多 11–42%。
4. **fetchall 全量取回**：命中行一次性拉取。

这些是次要项；即便全部消除，只要 INSTR 全表扫描仍在，时延仍由扫描主导。

## 6. 优化建议（按优先级）

### P0 — Aho-Corasick 内存多模式自动机（核心，必做）

- **问题**：INSTR 全表扫描使时延 `O(数据量 × Query 长度 × 并发)`，无法通过并发/缓存/索引缓解。
- **方案**：将全部 `normalized_key` 构建为 AC 自动机（Trie + failure 链），按 `data_version` 缓存于内存；查询时把归一化查询串在自动机上跑一遍，复杂度 `O(|Q| + 命中数)`，**与数据量无关**。命中集合上再做 `status`/`entity_type` 过滤与 `priority` 排序（命中数通常很小，内存处理毫秒级）。
- **等价性**：AC 找"模式出现在查询中" ⟺ `INSTR(:query, normalized_key) > 0`，逐行 INSTR 能命中的 AC 全部命中、无漏召。两侧均基于已 casefold+去空格的归一化串，口径一致。
- **与 data_version 缓存契合**：系统本就在每次操作前校验 `data_version`；自动机按版本缓存，版本未变即复用，版本变更才重建。P0 与下文 P1 一体。
- **预期收益**：50 万/超长/并发 20 的 P50 从 **113 秒 → 亚毫秒~毫秒级**（数量级 10⁴–10⁵ 提升）；QPS 不再封顶，随并发近线性增长直到 CPU/连接上限。数据量从 50k 扩到 500k 甚至 5M，单查询时延基本不变。
- **实现要点**：用 C 实现的 `pyahocorasick` 库（内存紧凑、微秒级查询）；构建按版本缓存，构建失败回退到当前 SQL 路径；status/entity_type 作为命中后过滤；保留 `MATCH_WORDS` 请求/响应契约不变。
- **工作量**：中。**风险**：内存占用（1M key 估算数百 MB，可用紧凑结构压缩）、构建时间（秒级，按版本缓存摊薄）、必须用 golden query 集做正确性回归（逐条比对 AC 与 INSTR 结果一致）。

### P1 — 消除每请求固定开销

- **问题**：每请求 `ping` + `data_version` 查询各一个 RTT，远程链路下放大固定底噪。
- **方案**：`data_version` 启动时读一次并缓存，配合版本号校验（P0 的自动机失效与版本变更联动）；`ping(reconnect=True)` 改为按需探测或移除（连接池本身已有健康检查语义）。
- **预期收益**：远程链路下每请求省约 2 RTT；小数据量/短 Query 格的固定占比下降明显（50k/short/c1 的 83ms 中固定部分可观）。
- **工作量**：小。**风险**：低，需保证 `data_version` 变更感知可靠（发布场景）。

### P2 — 连接池/超时与部署治理

- **问题**：`read_timeout=120s`，500k/ultra/c20 已逼近；公网链路 RTT 放大固定开销。
- **方案**：P0 落地后重设合理超时；连接池大小与目标并发对齐；性能压测与生产就近部署，消除公网 RTT。
- **预期收益**：P0 后本项问题基本消失；过渡期可缓解尾延迟与瞬时连接错误。
- **工作量**：小。**风险**：低。

### P3 — 优化后重新基线 + 容量门禁

- P0–P2 完成后，用**同一矩阵与同一 golden query 集**复测，建立优化后基线，与本报告逐格对比，量化收益。
- 明确 P95 延迟预算、目标 QPS、错误率 SLO 后计算 `N_max`；生产峰值建议不超过 `0.6 × N_max`。
- 补齐并发 50/100、15 分钟持续压测、真实接口端到端、服务端 CPU/I/O/锁/连接池指标。

### 建议执行顺序

P0 是数量级改善，应最先落地并用 golden query 集验证等价性；P1 与 P0 同期（共享 data_version 缓存）；P2/P3 在 P0 验证后跟进。P0 前不建议投入资源做并发/连接治理——只要全表扫描仍在，任何并发优化都被 CPU 瓶颈淹没（QPS 已证明 c=5 后加并发零收益）。

## 7. 风险与后续门禁

1. 当前实现呈明显的数据量/Query 长度/并发放大，5 万档并发 10/20 已出现长 Query 尾延迟跃升，50 万档 ultra/c20 P50 达 113 秒，**不具备直接作为生产容量基线的条件**。
2. `entity_types` 过滤可收窄前置集合（早前预压测显示 device 过滤使数据库内执行下降约 26 倍），但只能缓解特定查询，不能替代匹配模型优化。
3. 远程公网链路不适合作为生产低延迟结论；正式压测须在获授权的就近环境执行。
4. 正式上线前必须补齐：50/100 并发、生产峰值 1.5 倍数据、15 分钟持续压测、真实接口与 Query Recall 端到端、发布并发、CPU/I/O/锁/连接池资源指标。
5. 只有在明确 P95 预算与目标并发后才能计算 `N_max`；设计文档中的 INSTR 专项性能验收项继续保持未完成，直至 P0 落地并复测通过。

## 8. 复现入口

脚本：`scripts/run_volume_matrix_benchmark.py`

```powershell
# 1) 准备四档数据（幂等，已存在则复用）
python scripts/run_volume_matrix_benchmark.py --phase seed

# 2) 执行全矩阵（断点续跑，中断后重跑同一命令自动跳过已完成格）
python scripts/run_volume_matrix_benchmark.py --phase run --output-dir outputs/performance/volume_matrix

# 3) 一次完成准备+执行
python scripts/run_volume_matrix_benchmark.py --phase all --output-dir outputs/performance/volume_matrix
```

可调环境变量：`DV_MATRIX_DURATION`（每格采样秒数，默认 10）、`DV_MATRIX_WARMUPS`（热场景预热轮数，默认 3）。脚本只读取本地 `mysql_entity_data_mock_local.py` 配置的库，不在共享实例做任何删除/截断；冷场景仅 `FLUSH TABLES` 目标表。

## 9. 附录

### 9.1 产物清单

`outputs/performance/volume_matrix/`：

- `report.md`：本报告的机器生成对比表版本
- `matrix.json`：256 格全量明细
- `matrix.csv`：扁平表（volume/length/concurrency/temp/layer/N/p50/p95/p99/mean/max/qps/errors/passed）
- `cells/cell_*.json`：每格明细
- `run.log`：采集进度日志
- `provisioning.json` / `verification.json`：数据准备与校验记录

### 9.2 数据版本与校验（entity_words / entities 单位为「行数」）

| volume | entity_words (行) | entities (行) | 校验 |
| --- | ---: | ---: | --- |
| 50k | 50,000 | 16,667 | OK |
| 100k | 100,000 | 33,334 | OK |
| 200k | 200,000 | 66,667 | OK |
| 500k | 500,000 | 166,667 | OK |

四档库均用同一 seeder 逻辑生成，golden 实体 `DV-MOCK-000000334`（normalized_key `cpuusage000001001`）在所有档位均存在且被正确命中。

### 9.3 测试过程异常与环境备注

- 压测期间远程 MySQL 的 mock 库被外部进程反复 drop/重建（100k/200k/500k/50k 均被重置过，疑似并行的优化改造所致）。通过幂等 re-seed + 断点续跑补齐所有缺失格；由于行数与生成逻辑一致，已采集格的时延数据仍然有效。
- 期间 `performance_mock` 模块代码亦有外部修改：`el_entity_word`/`el_entity` 的 `status` 列与 `status='active'` 过滤被移除，当前匹配 SQL 为纯 `WHERE INSTR(...) > 0` 全表扫描（本报告结论基于当前代码形态）。
- 1 格瞬时失败（200k/long/c10/cold，1/10 transport_error）记为单次连接类瞬时错误，不影响趋势结论。

### 9.4 与预压测报告的衔接

本报告与 `MYSQL_INSTR_PRELIMINARY_BENCHMARK_20260717.md` 互为印证：预压测在 1 万/5 万/10 万档、并发 1/10/25 已发现 INSTR 的数据量与并发放大及长 Query 尾延迟跃升；本报告将矩阵扩展至 50 万档、四档 Query 长度、冷热对比与端到端 query_recall 层，并以 QPS 封顶与冷热无差两项新证据将根因锁定为 CPU 计算瓶颈。
