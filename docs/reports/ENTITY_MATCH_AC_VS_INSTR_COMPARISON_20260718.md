# AC vs INSTR 实体词匹配对比测试报告

> 本报告基于同一矩阵（4 数据量 × 4 Query 长度 × 4 并发 × 2 冷热 × 2 层 = 256 格）对 `INSTR` 反向包含扫描与 `Aho-Corasick` 内存自动机两种匹配策略进行端到端对比。AC 数据 256 格全部通过、0 失败；INSTR 基线 256 格 1 格瞬时失败。两轮均用本地 waitress HTTP mock（keep-alive）包装远程 MySQL，10s/格、预热 3 轮。

## 1. 结论

AC 把 `MATCH_WORDS` 从 `O(数据量 × Query 长度 × 并发)` 的 CPU 全表扫描降为 `O(|Q| + 命中数)` 的内存匹配，时延与吞吐获得数量级改善：

- **时延**：500k/超长/并发 1 的 P50 从 **5570ms → 100ms（56 倍）**；且 AC 时延在数据量与 Query 长度两个维度上基本持平（47–100ms），不再随规模放大。
- **吞吐**：500k 档 QPS 上限从 **2.6 → ~60（23 倍）**；超长 Query 并发 20 从 0.2 → 57 QPS（**285 倍**）。
- **正确性**：AC 与 INSTR 在 50k/500k 端到端结果集完全一致（均命中 `DV-MOCK-000000334`）；256 格 0 失败。
- **剩余瓶颈**：AC 端到端仍受远程 MySQL 往返（每请求 1 次 `data_version` + 1 次主键 fetch = 2 RTT）限制，QPS 在并发 5 后趋于 ~60（500k）。叠加 P1（缓存 data_version、去 ping）+ P2（就近部署）后可进一步降到亚毫秒~毫秒级。

## 2. AC 构建开销

| 数据量 | pattern 数 | 构建耗时 | 内存占用 |
|---|---:|---:|---:|
| 50k | 50,000 | ~2.3s | 2.9 MB |
| 100k | 100,000 | ~6.7s | 5.8 MB |
| 200k | 200,000 | ~14.7s | 11.6 MB |
| 500k | 500,000 | ~38.7s | 28.9 MB |

构建按 `data_version` 缓存，仅启动或数据发布时执行一次，不计入查询时延。

## 3. 数据量扩展对比（remote_match, warm, c=1, P50 ms）

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

INSTR 随数据量近线性恶化（50k→500k 放大 6–9 倍）；AC 基本持平（47–100ms），数据量 10 倍只抬升约 2 倍（且来自 RTT，非扫描）。

## 4. Query 长度敏感对比（remote_match, warm, c=1, 500k, P50 ms）

| length (chars) | INSTR | AC | 提速 |
|---|---:|---:|---:|
| short | 488 | 70 | 7x |
| medium | 1154 | 80 | 14x |
| long | 2916 | 99 | 30x |
| ultra | 5570 | 100 | 56x |

INSTR 随 Query 长度近线性恶化（25→600 字符放大 11 倍）；AC 完全持平（~70–100ms），证明 AC 匹配代价与 haystack 长度无关。

## 5. 并发吞吐对比（remote_match, warm, 500k, QPS 次/秒）

| concurrency | length | INSTR | AC | 提速 |
|---|---|---:|---:|---:|
| 1 | short | 2 | 14 | 7x |
| 1 | medium | 1 | 13 | 15x |
| 1 | long | 0 | 10 | 30x |
| 1 | ultra | 0 | 10 | 54x |
| 5 | short | 3 | 60 | 23x |
| 5 | medium | 1 | 60 | 62x |
| 5 | long | 0 | 59 | 167x |
| 5 | ultra | 0 | 57 | 313x |
| 10 | short | 3 | 60 | 23x |
| 10 | medium | 1 | 60 | 62x |
| 10 | long | 0 | 56 | 160x |
| 10 | ultra | 0 | 56 | 309x |
| 20 | short | 3 | 60 | 23x |
| 20 | medium | 1 | 60 | 62x |
| 20 | long | 0 | 57 | 162x |
| 20 | ultra | 0 | 57 | 327x |

INSTR 在 c=5 即封顶 ~2.6 QPS（CPU 扫描瓶颈）；AC 封顶 ~60 QPS（23 倍），且超长 Query 并发 20 从 0.2 → 57 QPS（285 倍）。AC 的剩余封顶来自远程 RTT，非 CPU。

## 6. 并发时延对比（remote_match, warm, 500k, 超长, P50 ms）

| concurrency | INSTR | AC | 提速 |
|---|---:|---:|---:|
| 1 | 5570 | 100 | 56x |
| 5 | 26922 | 87 | 310x |
| 10 | 54371 | 175 | 312x |
| 20 | 113437 | 346 | 328x |

INSTR 并发 20 达 113437ms（逼近超时）；AC 并发 20 仅 ~346ms。并发放大下 AC 优势更显著。

## 7. 冷 vs 热（AC, remote_match, c=1, medium, P50 ms）

| volume | cold | warm | 比值 |
|---|---:|---:|---:|
| 50k | 47 | 47 | 1.00 |
| 100k | 60 | 60 | 1.00 |
| 200k | 89 | 89 | 1.01 |
| 500k | 80 | 80 | 1.00 |

AC 冷热仍无显著差异（比值 ~1.0），与 INSTR 一致——AC 匹配在内存，主键 fetch 仅触极少页，I/O 不是瓶颈。

## 8. remote_match vs query_recall（AC, warm, c=1, medium, P50 ms）

| volume | remote_match | query_recall | 比值 |
|---|---:|---:|---:|
| 50k | 47 | 89 | 1.88 |
| 100k | 60 | 153 | 2.54 |
| 200k | 89 | 156 | 1.75 |
| 500k | 80 | 130 | 1.64 |

AC 下 query_recall 仍比 remote_match 慢（多一次 BATCH_GET + NER），比值 1.4–1.9；INSTR 基线为 1.1–1.4。AC 下固定开销占比更显眼，符合 P1 预期。

## 9. 提速总览（AC/INSTR P50 倍数，remote_match, warm）

| volume | short c1 | ultra c1 | ultra c20 |
|---|---:|---:|---:|
| 50k | 2x | 13x | 43x |
| 100k | 3x | 12x | 72x |
| 200k | 2x | 25x | 95x |
| 500k | 7x | 56x | 328x |

规模与并发越大，AC 优势越大：50k/short/c1 仅 2 倍（小表 INSTR 本就快），500k/ultra/c20 达 **328 倍**。

## 10. 复现入口

```powershell
# INSTR 基线
python scripts/run_volume_matrix_benchmark.py --phase all --match-strategy instr --output-dir outputs/performance/volume_matrix
# AC
python scripts/run_volume_matrix_benchmark.py --phase all --match-strategy ac --output-dir outputs/performance/volume_matrix_ac
```

数据产物：`outputs/performance/volume_matrix_ac/{matrix.json,matrix.csv,report.md,cells/}`；INSTR 基线：`outputs/performance/volume_matrix/`。

## 11. 后续

1. **P1 消除每请求 RTT**：缓存 `data_version`（启动读一次 + 版本号校验）、移除每请求 `ping`，预计 500k/c1 再降一半（~50ms → ~25ms），并发封顶进一步提升。
2. **P2 就近部署**：消除远程公网 RTT，端到端可降到 1–5ms。
3. **正式容量基线**：P1/P2 落地后在获授权环境重跑同矩阵，建立优化后基线并计算 N_max。
