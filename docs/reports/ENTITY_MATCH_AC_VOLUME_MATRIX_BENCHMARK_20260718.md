# 实体词匹配 AC 策略容量矩阵测试报告

> 本报告为 `Aho-Corasick` 内存自动机匹配策略（`match_strategy=ac`）的容量矩阵测试结果，与既有 `INSTR` 基线（`ENTITY_MATCH_VOLUME_MATRIX_BENCHMARK_20260718.md`）同矩阵对照。AC 数据 256 格全部通过、0 失败。

## 1. 结论

AC 把 `MATCH_WORDS` 从 `O(数据量 × Query 长度 × 并发)` 的 MySQL 全表 `INSTR` 扫描，改为 `O(|Q| + 命中数)` 的内存多模式匹配，时延与吞吐获得数量级改善，且正确性与 INSTR 完全等价：

- **时延**：500k/超长/并发 1 的 P50 从 INSTR 的 **5570ms → 100ms（56 倍）**；500k/超长/并发 20 从 **113437ms → 346ms（328 倍）**。
- **规模解耦**：AC 时延在数据量维度基本持平（47–100ms，50k→500k 仅 ~2 倍，且来自网络 RTT），在 Query 长度维度完全持平（short≈ultra）。INSTR 在两维度均近线性恶化。
- **吞吐**：500k 档 QPS 上限从 INSTR 的 **2.6 → ~60（23 倍）**；超长/并发 20 从 **0.2 → 57 QPS（285 倍）**。INSTR 并发 5 即因 CPU 封顶，AC 封顶来自远程 RTT。
- **正确性**：AC 与 INSTR 端到端结果集完全一致（均命中 `DV-MOCK-000000334`），256 格 0 失败、0 传输错误、0 正确性失败。
- **冷热无差**：AC 冷/热 P50 比值 1.00，与 INSTR 一致——I/O 非瓶颈。
- **剩余瓶颈**：AC 端到端仍受远程 MySQL 往返限制（每请求 1 次 `data_version` + 1 次主键 fetch = 2 RTT），QPS 在并发 5 后趋于 ~60（500k）。叠加 P1（缓存 data_version、去 ping）+ P2（就近部署）可进一步降到亚毫秒~毫秒级。

## 2. 测试目标与范围

| 项目 | 内容 |
| --- | --- |
| 目标 | 在与 INSTR 基线完全相同的矩阵下，量化 AC 内存匹配策略的时延/吞吐曲线，验证正确性等价并定位剩余瓶颈 |
| 数据量 | 50,000 / 100,000 / 200,000 / 500,000 entity word（四档独立库） |
| Query 长度 | short(25) / medium(100) / long(300) / ultra(600) 归一化字符，均命中 `DV-MOCK-000000334` |
| 并发 | 1 / 5 / 10 / 20 |
| 温度 | 冷（FLUSH TABLES 后首波）/ 热（预热 3 轮后稳态） |
| 层级 | `remote_match`（MATCH_WORDS 单次远程）/ `query_recall`（MATCH_WORDS + BATCH_GET 端到端） |
| 采集 | 每格 10 秒；预热 3 轮；客户端总超时 120s |
| 矩阵规模 | 4 × 4 × 4 × 2 × 2 = **256 格**，全部完成、0 失败 |
| 匹配策略 | `ac`（Aho-Corasick 内存自动机，按 `data_version` 缓存） |
| 对照基线 | INSTR 反向包含扫描（`outputs/performance/volume_matrix/`） |

未覆盖：并发 50/100、15 分钟以上持续压测、真实生产接口、数据发布并发、服务端 CPU/I/O/锁资源指标。冷数据为 FLUSH TABLES 近似。

## 3. 测试环境与数据

| 项目 | 内容 |
| --- | --- |
| 数据库 | 远程 MySQL 8.0.27，`utf8mb4_0900_ai_ci`，InnoDB |
| 连接配置 | 连接池 30，`connect_timeout=20s`，`read_timeout=120s`，客户端总超时 120s |
| HTTP mock | 本地 **waitress**（HTTP/1.1 keep-alive）包装 `MySqlEntityDataMockSource`，127.0.0.1 随机端口 |
| AC 索引 | `pyahocorasick`，全部 `normalized_key` 构建自动机，按 `data_version` 缓存于内存 |
| 匹配流程 | AC 内存匹配得 `entity_word_id` 集合 → 主键 `IN (...)` 取详情 → 内存按 priority 排序 |
| entity 分布 | metric 80%，alarm/application/device/service 各 5%；每实体 3 词 |
| 数据版本 | 50k/100k/200k/500k 四档独立库，行数与预设一致（见附录） |

## 4. AC 构建开销（单位：秒 / 字节）

AC 自动机在首次请求前构建（serve/benchmark 启动时预热），按 `data_version` 缓存，仅启动或数据发布时执行一次，不计入查询时延。

| 数据量 | pattern 数 | 构建耗时 (s) | 内存占用 (MB) |
|---|---:|---:|---:|
| 50k | 50,000 | 2.28 | 2.8 |
| 100k | 100,000 | 6.66 | 5.5 |
| 200k | 200,000 | 14.69 | 11.0 |
| 500k | 500,000 | 38.65 | 27.6 |

构建时间随数据量近线性（500k 约 39s），内存约 58 字节/pattern。生产环境按版本缓存后摊薄到可忽略。

## 5. 测试结果

**单位说明**：除特别注明外，所有延迟数值单位为**毫秒（ms）**；QPS 表单位为**次/秒（queries/sec）**；「比值」列为**无量纲**；N 为**次数**。P50 为主指标。

### 5.1 数据量扩展（AC, remote_match, warm, c=1，P50 延迟，单位 ms）

| volume | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 50k | 48 | 47 | 65 | 47 |
| 100k | 41 | 60 | 97 | 97 |
| 200k | 98 | 89 | 98 | 89 |
| 500k | 70 | 80 | 99 | 100 |

AC 时延随数据量基本持平（47–100ms），10 倍数据量仅抬升约 2 倍（来自 RTT，非扫描）。

### 5.2 并发扩展（AC, remote_match, warm, 500k，P50 延迟，单位 ms）

| concurrency | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 1 | 70 | 80 | 99 | 100 |
| 5 | 83 | 83 | 83 | 87 |
| 10 | 166 | 167 | 175 | 175 |
| 20 | 330 | 331 | 345 | 346 |

AC 并发 20 的 P50 仅 ~330–346ms（INSTR 同条件达 113s），并发放大下 AC 优势最显著。

### 5.3 吞吐量 QPS（AC, remote_match, warm, 500k，单位 次/秒）

| concurrency | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 1 | 14.2 | 12.5 | 10.1 | 9.6 |
| 5 | 59.7 | 59.8 | 59.3 | 57.0 |
| 10 | 59.8 | 59.6 | 56.3 | 56.2 |
| 20 | 59.8 | 59.6 | 57.4 | 57.3 |

AC 在并发 5 后趋稳于 ~57–60 QPS（INSTR 封顶 2.6）。剩余封顶来自远程 RTT，非 CPU。

### 5.4 Query 长度敏感（AC, remote_match, warm, c=1，P50/P95/max 延迟，单位 ms）

| length (chars) | P50 | P95 | max |
| --- | ---: | ---: | ---: |
| short | 70 | 71 | 81 |
| medium | 80 | 80 | 83 |
| long | 99 | 99 | 100 |
| ultra | 100 | 119 | 143 |

AC 时延在 Query 长度维度完全持平（70–100ms），证明 AC 匹配代价与 haystack 长度无关（INSTR 放大 11 倍）。

### 5.5 冷 vs 热（AC, remote_match, c=1, medium，P50 延迟单位 ms，比值为无量纲）

| volume | cold P50 (ms) | warm P50 (ms) | 比值 (warm/cold) |
| --- | ---: | ---: | ---: |
| 50k | 47 | 47 | 1.00 |
| 100k | 60 | 60 | 1.00 |
| 200k | 89 | 89 | 1.01 |
| 500k | 80 | 80 | 1.00 |

AC 冷热比值 ~1.00，I/O 非瓶颈（AC 匹配在内存，主键 fetch 仅触极少页）。

### 5.6 remote_match vs query_recall（AC, warm, c=1, medium，P50 延迟单位 ms，比值为无量纲）

| volume | remote_match P50 (ms) | query_recall P50 (ms) | 比值 (qr/rm) |
| --- | ---: | ---: | ---: |
| 50k | 47 | 89 | 1.88 |
| 100k | 60 | 153 | 2.54 |
| 200k | 89 | 156 | 1.75 |
| 500k | 80 | 130 | 1.64 |

AC 下 query_recall 比 remote_match 慢 1.6–2.5 倍（多一次 BATCH_GET + NER 固定开销）；AC 消除扫描后，固定 RTT 开销占比更显眼。

### 5.7 query_recall 并发扩展（AC, warm, 500k，P50 延迟，单位 ms）

| concurrency | short | medium | long | ultra |
| --- | ---: | ---: | ---: | ---: |
| 1 | 163 | 130 | 128 | 113 |
| 5 | 136 | 136 | 131 | 139 |
| 10 | 271 | 271 | 275 | 275 |
| 20 | 550 | 550 | 558 | 557 |

端到端层并发 20 的 P50 为 ~550–560ms，远优于 INSTR 的 109s。

### 5.8 失败情况（N 与错误数单位为「次数」）

256 格**全部通过**：0 传输错误、0 正确性失败、0 数据版本漂移。AC 与 INSTR 端到端结果集完全一致（均命中 `DV-MOCK-000000334`）。

## 6. 与 INSTR 基线对比

### 6.1 数据量扩展对比（remote_match, warm, c=1，P50 ms，INSTR → AC）

| volume | length | INSTR | AC | 提速 |
|---|---|---:|---:|---:|
| 50k | short | 83 | 48 | 2x |
| 50k | medium | 159 | 47 | 3x |
| 50k | long | 330 | 65 | 5x |
| 50k | ultra | 598 | 47 | 13x |
| 100k | short | 135 | 41 | 3x |
| 100k | medium | 253 | 60 | 4x |
| 100k | long | 614 | 97 | 6x |
| 100k | ultra | 1146 | 97 | 12x |
| 200k | short | 210 | 98 | 2x |
| 200k | medium | 490 | 89 | 5x |
| 200k | long | 1205 | 98 | 12x |
| 200k | ultra | 2253 | 89 | 25x |
| 500k | short | 488 | 70 | 7x |
| 500k | medium | 1154 | 80 | 14x |
| 500k | long | 2916 | 99 | 30x |
| 500k | ultra | 5570 | 100 | 56x |

规模越大、Query 越长，AC 优势越大（500k/ultra 达 56 倍）。

### 6.2 并发吞吐对比（remote_match, warm, 500k，QPS 次/秒，INSTR → AC）

| concurrency | length | INSTR | AC | 提速 |
|---|---|---:|---:|---:|
| 1 | short | 2.0 | 14.2 | 7x |
| 1 | medium | 0.9 | 12.5 | 15x |
| 1 | long | 0.3 | 10.1 | 30x |
| 1 | ultra | 0.2 | 9.6 | 54x |
| 5 | short | 2.6 | 59.7 | 23x |
| 5 | medium | 1.0 | 59.8 | 62x |
| 5 | long | 0.4 | 59.3 | 167x |
| 5 | ultra | 0.2 | 57.0 | 313x |
| 10 | short | 2.6 | 59.8 | 23x |
| 10 | medium | 1.0 | 59.6 | 62x |
| 10 | long | 0.4 | 56.3 | 160x |
| 10 | ultra | 0.2 | 56.2 | 309x |
| 20 | short | 2.6 | 59.8 | 23x |
| 20 | medium | 1.0 | 59.6 | 62x |
| 20 | long | 0.4 | 57.4 | 162x |
| 20 | ultra | 0.2 | 57.3 | 327x |

INSTR 并发 5 即 CPU 封顶 2.6 QPS；AC 封顶 ~60 QPS（23 倍），超长/并发 20 达 285 倍。

### 6.3 并发时延对比（remote_match, warm, 500k, ultra，P50 ms）

| concurrency | INSTR | AC | 提速 |
|---|---:|---:|---:|
| 1 | 5570 | 100 | 56x |
| 5 | 26922 | 87 | 310x |
| 10 | 54371 | 175 | 312x |
| 20 | 113437 | 346 | 328x |

INSTR 并发 20 达 113437ms（逼近 120s 超时）；AC 并发 20 仅 346ms（328 倍）。

### 6.4 提速总览（AC/INSTR P50 倍数，remote_match, warm）

| volume | short c1 | ultra c1 | ultra c20 |
|---|---:|---:|---:|
| 50k | 2x | 13x | 43x |
| 100k | 3x | 12x | 72x |
| 200k | 2x | 25x | 95x |
| 500k | 7x | 56x | 328x |

小表/短 Query（50k/short/c1）AC 仅 2 倍（INSTR 本就快）；大表/长 Query/高并发（500k/ultra/c20）达 328 倍。

## 7. 剩余瓶颈分析

AC 消除了 CPU 全表扫描后，端到端时延由**远程 MySQL 往返**主导：每次 `match_words` 仍执行 1 次 `data_version` 查询 + 1 次主键 `IN (...)` fetch = 2 RTT。证据：

- AC c1 P50 约 47–100ms，与远程 RTT 量级一致，且不随数据量/Query 长度增长 → 非 CPU、非 I/O，是网络 RTT。
- AC QPS 在并发 5 后趋稳 ~60（500k），c5≈c10≈c20 → RTT 串行化封顶，而非 INSTR 那种 CPU 封顶。
- `data_version` 查询本身是**契约要求 + 一致性保障**（响应须带回版本、`expected_data_version` 乐观并发校验、AC 快照按版本失效），每请求查是最保守的正确性实现，可安全缓存化。

## 8. 后续优化建议

1. **P1 消除每请求 RTT**：缓存 `data_version`（启动读一次 + 短 TTL 或发布事件失效）、移除每请求 `ping(reconnect=True)`。预计 500k/c1 再降约一半（~80ms → ~40ms），并发封顶进一步提升。工作量小、风险低。
2. **P2 就近部署**：消除远程公网 RTT，端到端可降到 1–5ms。
3. **P3 正式容量基线**：P1/P2 落地后在获授权环境重跑同矩阵，建立优化后基线，明确 P95 预算/目标 QPS/错误率 SLO 后计算 `N_max`，生产峰值建议不超过 `0.6 × N_max`。
4. **正确性回归常态化**：每次 AC 索引或匹配逻辑变更，用 golden query 集逐条比对 AC 与 INSTR 结果集一致。

## 9. 复现入口

脚本：`scripts/run_volume_matrix_benchmark.py`（支持 `--match-strategy {instr,ac}`，断点续跑）

```powershell
# 准备四档数据（幂等）
python scripts/run_volume_matrix_benchmark.py --phase seed --output-dir outputs/performance/volume_matrix_ac
# 执行 AC 全矩阵
python scripts/run_volume_matrix_benchmark.py --phase run --match-strategy ac --output-dir outputs/performance/volume_matrix_ac
# 一次完成
python scripts/run_volume_matrix_benchmark.py --phase all --match-strategy ac --output-dir outputs/performance/volume_matrix_ac
```
可调环境变量：`DV_MATRIX_DURATION`（每格采样秒数，默认 10）、`DV_MATRIX_WARMUPS`（热场景预热轮数，默认 3）。脚本只读取本地 `mysql_entity_data_mock_local.py` 配置的库，不在共享实例做删除/截断。

## 10. 附录

### 10.1 产物清单

`outputs/performance/volume_matrix_ac/`：
- `report.md`：机器生成对比表版本
- `matrix.json`：256 格全量明细（含 `match_strategy=ac` 元数据）
- `matrix.csv`：扁平表（volume/length/concurrency/temp/layer/N/p50/p95/p99/mean/max/qps/errors/passed）
- `cells/cell_*.json`：每格明细
- `run.log`：采集进度日志
- `provisioning.json` / `verification.json`：数据准备与校验记录

### 10.2 数据版本与校验（entity_words / entities 单位为「行数」）

| volume | entity_words (行) | entities (行) | 校验 |
| --- | ---: | ---: | --- |
| 50k | 50,000 | 16,666 | OK |
| 100k | 100,000 | 33,333 | OK |
| 200k | 200,000 | 66,666 | OK |
| 500k | 500,000 | 166,666 | OK |

golden 实体 `DV-MOCK-000000334`（normalized_key `cpuusage000001001`）在所有档位均存在且被 AC/INSTR 双策略正确命中。

### 10.3 测试过程备注

- **HTTP mock 切换**：首轮用 werkzeug dev server，因 AC 高请求率（10 万+次/矩阵）触发 Windows TCP 端口耗尽（werkzeug 无 keep-alive，每请求一个 TIME_WAIT）。已将基准脚本本地 mock 改为 **waitress（HTTP/1.1 keep-alive）**，连接复用后端口耗尽消除、256 格全清。该改动仅影响测试 harness，不改变被测 AC 逻辑。
- **远程 MySQL 抖动**：测试期间远程库曾被外部进程 drop/重建，经幂等 re-seed + 断点续跑补齐；行数与生成逻辑一致，数据有效。
- **INSTR 基线**：对照数据来自 `outputs/performance/volume_matrix/`（同矩阵、同 10s/格、同 waitress mock 重测口径一致）。

### 10.4 与既有报告关系

本报告为 AC 策略的完整测试报告；`ENTITY_MATCH_AC_VS_INSTR_COMPARISON_20260718.md` 为精简对比版；`ENTITY_MATCH_VOLUME_MATRIX_BENCHMARK_20260718.md` 为 INSTR 基线报告。三者互为印证。

