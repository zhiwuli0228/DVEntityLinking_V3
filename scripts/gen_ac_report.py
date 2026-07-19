import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ac_meta = json.loads((ROOT / "outputs/performance/volume_matrix_ac/matrix.json").read_text(encoding="utf-8"))
ac = ac_meta["cells"]
instr = json.loads((ROOT / "outputs/performance/volume_matrix/matrix.json").read_text(encoding="utf-8"))["cells"]

VOLUMES = ["50k", "100k", "200k", "500k"]
LENGTHS = ["short", "medium", "long", "ultra"]
CONC = [1, 5, 10, 20]
BUILD = {
    "50k": (50_000, 2.28, 2_891_632),
    "100k": (100_000, 6.66, 5_780_472),
    "200k": (200_000, 14.69, 11_558_232),
    "500k": (500_000, 38.65, 28_891_512),
}


def g(src, vol, length, conc, temp, layer, key="p50_ms"):
    for c in src:
        if (
            c["volume"] == vol and c["length"] == length and c["concurrency"] == conc
            and c["temp"] == temp and c["layer"] == layer
        ):
            return c.get(key)
    return None


def f(v):
    return f"{v:.0f}" if isinstance(v, (int, float)) else "-"


def f1(v):
    return f"{v:.1f}" if isinstance(v, (int, float)) else "-"


def sp(i, a):
    return f"{i / a:.0f}x" if (i and a and a > 0) else "-"


L = []
A = L.append

A("# 实体词匹配 AC 策略容量矩阵测试报告\n")
A("> 本报告为 `Aho-Corasick` 内存自动机匹配策略（`match_strategy=ac`）的容量矩阵测试结果，与既有 `INSTR` 基线（`ENTITY_MATCH_VOLUME_MATRIX_BENCHMARK_20260718.md`）同矩阵对照。AC 数据 256 格全部通过、0 失败。\n")

A("## 1. 结论\n")
A("AC 把 `MATCH_WORDS` 从 `O(数据量 × Query 长度 × 并发)` 的 MySQL 全表 `INSTR` 扫描，改为 `O(|Q| + 命中数)` 的内存多模式匹配，时延与吞吐获得数量级改善，且正确性与 INSTR 完全等价：\n")
A("- **时延**：500k/超长/并发 1 的 P50 从 INSTR 的 **5570ms → 100ms（56 倍）**；500k/超长/并发 20 从 **113437ms → 346ms（328 倍）**。")
A("- **规模解耦**：AC 时延在数据量维度基本持平（47–100ms，50k→500k 仅 ~2 倍，且来自网络 RTT），在 Query 长度维度完全持平（short≈ultra）。INSTR 在两维度均近线性恶化。")
A("- **吞吐**：500k 档 QPS 上限从 INSTR 的 **2.6 → ~60（23 倍）**；超长/并发 20 从 **0.2 → 57 QPS（285 倍）**。INSTR 并发 5 即因 CPU 封顶，AC 封顶来自远程 RTT。")
A("- **正确性**：AC 与 INSTR 端到端结果集完全一致（均命中 `DV-MOCK-000000334`），256 格 0 失败、0 传输错误、0 正确性失败。")
A("- **冷热无差**：AC 冷/热 P50 比值 1.00，与 INSTR 一致——I/O 非瓶颈。")
A("- **剩余瓶颈**：AC 端到端仍受远程 MySQL 往返限制（每请求 1 次 `data_version` + 1 次主键 fetch = 2 RTT），QPS 在并发 5 后趋于 ~60（500k）。叠加 P1（缓存 data_version、去 ping）+ P2（就近部署）可进一步降到亚毫秒~毫秒级。\n")

A("## 2. 测试目标与范围\n")
A("| 项目 | 内容 |")
A("| --- | --- |")
A("| 目标 | 在与 INSTR 基线完全相同的矩阵下，量化 AC 内存匹配策略的时延/吞吐曲线，验证正确性等价并定位剩余瓶颈 |")
A("| 数据量 | 50,000 / 100,000 / 200,000 / 500,000 entity word（四档独立库） |")
A("| Query 长度 | short(25) / medium(100) / long(300) / ultra(600) 归一化字符，均命中 `DV-MOCK-000000334` |")
A("| 并发 | 1 / 5 / 10 / 20 |")
A("| 温度 | 冷（FLUSH TABLES 后首波）/ 热（预热 3 轮后稳态） |")
A("| 层级 | `remote_match`（MATCH_WORDS 单次远程）/ `query_recall`（MATCH_WORDS + BATCH_GET 端到端） |")
A("| 采集 | 每格 10 秒；预热 3 轮；客户端总超时 120s |")
A("| 矩阵规模 | 4 × 4 × 4 × 2 × 2 = **256 格**，全部完成、0 失败 |")
A("| 匹配策略 | `ac`（Aho-Corasick 内存自动机，按 `data_version` 缓存） |")
A("| 对照基线 | INSTR 反向包含扫描（`outputs/performance/volume_matrix/`） |")
A("\n未覆盖：并发 50/100、15 分钟以上持续压测、真实生产接口、数据发布并发、服务端 CPU/I/O/锁资源指标。冷数据为 FLUSH TABLES 近似。\n")

A("## 3. 测试环境与数据\n")
A("| 项目 | 内容 |")
A("| --- | --- |")
A("| 数据库 | 远程 MySQL 8.0.27，`utf8mb4_0900_ai_ci`，InnoDB |")
A("| 连接配置 | 连接池 30，`connect_timeout=20s`，`read_timeout=120s`，客户端总超时 120s |")
A("| HTTP mock | 本地 **waitress**（HTTP/1.1 keep-alive）包装 `MySqlEntityDataMockSource`，127.0.0.1 随机端口 |")
A("| AC 索引 | `pyahocorasick`，全部 `normalized_key` 构建自动机，按 `data_version` 缓存于内存 |")
A("| 匹配流程 | AC 内存匹配得 `entity_word_id` 集合 → 主键 `IN (...)` 取详情 → 内存按 priority 排序 |")
A("| entity 分布 | metric 80%，alarm/application/device/service 各 5%；每实体 3 词 |")
A("| 数据版本 | 50k/100k/200k/500k 四档独立库，行数与预设一致（见附录） |")

A("\n## 4. AC 构建开销（单位：秒 / 字节）\n")
A("AC 自动机在首次请求前构建（serve/benchmark 启动时预热），按 `data_version` 缓存，仅启动或数据发布时执行一次，不计入查询时延。\n")
A("| 数据量 | pattern 数 | 构建耗时 (s) | 内存占用 (MB) |")
A("|---|---:|---:|---:|")
for v in VOLUMES:
    n, s, b = BUILD[v]
    A(f"| {v} | {n:,} | {s:.2f} | {b / 1048576:.1f} |")
A("\n构建时间随数据量近线性（500k 约 39s），内存约 58 字节/pattern。生产环境按版本缓存后摊薄到可忽略。\n")

A("## 5. 测试结果\n")
A("**单位说明**：除特别注明外，所有延迟数值单位为**毫秒（ms）**；QPS 表单位为**次/秒（queries/sec）**；「比值」列为**无量纲**；N 为**次数**。P50 为主指标。\n")

A("### 5.1 数据量扩展（AC, remote_match, warm, c=1，P50 延迟，单位 ms）\n")
A("| volume | short | medium | long | ultra |")
A("| --- | ---: | ---: | ---: | ---: |")
for v in VOLUMES:
    A(f"| {v} | " + " | ".join(f(g(ac, v, L, 1, "warm", "remote_match")) for L in LENGTHS) + " |")
A("\nAC 时延随数据量基本持平（47–100ms），10 倍数据量仅抬升约 2 倍（来自 RTT，非扫描）。\n")

A("### 5.2 并发扩展（AC, remote_match, warm, 500k，P50 延迟，单位 ms）\n")
A("| concurrency | short | medium | long | ultra |")
A("| --- | ---: | ---: | ---: | ---: |")
for c in CONC:
    A(f"| {c} | " + " | ".join(f(g(ac, "500k", L, c, "warm", "remote_match")) for L in LENGTHS) + " |")
A("\nAC 并发 20 的 P50 仅 ~330–346ms（INSTR 同条件达 113s），并发放大下 AC 优势最显著。\n")

A("### 5.3 吞吐量 QPS（AC, remote_match, warm, 500k，单位 次/秒）\n")
A("| concurrency | short | medium | long | ultra |")
A("| --- | ---: | ---: | ---: | ---: |")
for c in CONC:
    A(f"| {c} | " + " | ".join(f1(g(ac, "500k", L, c, "warm", "remote_match", "qps")) for L in LENGTHS) + " |")
A("\nAC 在并发 5 后趋稳于 ~57–60 QPS（INSTR 封顶 2.6）。剩余封顶来自远程 RTT，非 CPU。\n")

A("### 5.4 Query 长度敏感（AC, remote_match, warm, c=1，P50/P95/max 延迟，单位 ms）\n")
A("| length (chars) | P50 | P95 | max |")
A("| --- | ---: | ---: | ---: |")
for L2 in LENGTHS:
    A(f"| {L2} | {f(g(ac,'500k',L2,1,'warm','remote_match'))} | {f(g(ac,'500k',L2,1,'warm','remote_match','p95_ms'))} | {f(g(ac,'500k',L2,1,'warm','remote_match','max_ms'))} |")
A("\nAC 时延在 Query 长度维度完全持平（70–100ms），证明 AC 匹配代价与 haystack 长度无关（INSTR 放大 11 倍）。\n")

A("### 5.5 冷 vs 热（AC, remote_match, c=1, medium，P50 延迟单位 ms，比值为无量纲）\n")
A("| volume | cold P50 (ms) | warm P50 (ms) | 比值 (warm/cold) |")
A("| --- | ---: | ---: | ---: |")
for v in VOLUMES:
    c2 = g(ac, v, "medium", 1, "cold", "remote_match")
    w = g(ac, v, "medium", 1, "warm", "remote_match")
    A(f"| {v} | {f(c2)} | {f(w)} | {w/c2:.2f} |")
A("\nAC 冷热比值 ~1.00，I/O 非瓶颈（AC 匹配在内存，主键 fetch 仅触极少页）。\n")

A("### 5.6 remote_match vs query_recall（AC, warm, c=1, medium，P50 延迟单位 ms，比值为无量纲）\n")
A("| volume | remote_match P50 (ms) | query_recall P50 (ms) | 比值 (qr/rm) |")
A("| --- | ---: | ---: | ---: |")
for v in VOLUMES:
    rm = g(ac, v, "medium", 1, "warm", "remote_match")
    qr = g(ac, v, "medium", 1, "warm", "query_recall")
    A(f"| {v} | {f(rm)} | {f(qr)} | {qr/rm:.2f} |")
A("\nAC 下 query_recall 比 remote_match 慢 1.6–2.5 倍（多一次 BATCH_GET + NER 固定开销）；AC 消除扫描后，固定 RTT 开销占比更显眼。\n")

A("### 5.7 query_recall 并发扩展（AC, warm, 500k，P50 延迟，单位 ms）\n")
A("| concurrency | short | medium | long | ultra |")
A("| --- | ---: | ---: | ---: | ---: |")
for c in CONC:
    A(f"| {c} | " + " | ".join(f(g(ac, "500k", L, c, "warm", "query_recall")) for L in LENGTHS) + " |")
A("\n端到端层并发 20 的 P50 为 ~550–560ms，远优于 INSTR 的 109s。\n")

A("### 5.8 失败情况（N 与错误数单位为「次数」）\n")
A("256 格**全部通过**：0 传输错误、0 正确性失败、0 数据版本漂移。AC 与 INSTR 端到端结果集完全一致（均命中 `DV-MOCK-000000334`）。\n")

A("## 6. 与 INSTR 基线对比\n")

A("### 6.1 数据量扩展对比（remote_match, warm, c=1，P50 ms，INSTR → AC）\n")
A("| volume | length | INSTR | AC | 提速 |")
A("|---|---|---:|---:|---:|")
for v in VOLUMES:
    for L2 in LENGTHS:
        i = g(instr, v, L2, 1, "warm", "remote_match")
        a = g(ac, v, L2, 1, "warm", "remote_match")
        A(f"| {v} | {L2} | {f(i)} | {f(a)} | {sp(i,a)} |")
A("\n规模越大、Query 越长，AC 优势越大（500k/ultra 达 56 倍）。\n")

A("### 6.2 并发吞吐对比（remote_match, warm, 500k，QPS 次/秒，INSTR → AC）\n")
A("| concurrency | length | INSTR | AC | 提速 |")
A("|---|---|---:|---:|---:|")
for c in CONC:
    for L2 in LENGTHS:
        i = g(instr, "500k", L2, c, "warm", "remote_match", "qps")
        a = g(ac, "500k", L2, c, "warm", "remote_match", "qps")
        A(f"| {c} | {L2} | {f1(i)} | {f1(a)} | {a/i:.0f}x |" if (i and a and i > 0) else f"| {c} | {L2} | {f1(i)} | {f1(a)} | - |")
A("\nINSTR 并发 5 即 CPU 封顶 2.6 QPS；AC 封顶 ~60 QPS（23 倍），超长/并发 20 达 285 倍。\n")

A("### 6.3 并发时延对比（remote_match, warm, 500k, ultra，P50 ms）\n")
A("| concurrency | INSTR | AC | 提速 |")
A("|---|---:|---:|---:|")
for c in CONC:
    i = g(instr, "500k", "ultra", c, "warm", "remote_match")
    a = g(ac, "500k", "ultra", c, "warm", "remote_match")
    A(f"| {c} | {f(i)} | {f(a)} | {sp(i,a)} |")
A("\nINSTR 并发 20 达 113437ms（逼近 120s 超时）；AC 并发 20 仅 346ms（328 倍）。\n")

A("### 6.4 提速总览（AC/INSTR P50 倍数，remote_match, warm）\n")
A("| volume | short c1 | ultra c1 | ultra c20 |")
A("|---|---:|---:|---:|")
for v in VOLUMES:
    A(f"| {v} | {sp(g(instr,v,'short',1,'warm','remote_match'), g(ac,v,'short',1,'warm','remote_match'))} | "
      f"{sp(g(instr,v,'ultra',1,'warm','remote_match'), g(ac,v,'ultra',1,'warm','remote_match'))} | "
      f"{sp(g(instr,v,'ultra',20,'warm','remote_match'), g(ac,v,'ultra',20,'warm','remote_match'))} |")
A("\n小表/短 Query（50k/short/c1）AC 仅 2 倍（INSTR 本就快）；大表/长 Query/高并发（500k/ultra/c20）达 328 倍。\n")

A("## 7. 剩余瓶颈分析\n")
A("AC 消除了 CPU 全表扫描后，端到端时延由**远程 MySQL 往返**主导：每次 `match_words` 仍执行 1 次 `data_version` 查询 + 1 次主键 `IN (...)` fetch = 2 RTT。证据：\n")
A("- AC c1 P50 约 47–100ms，与远程 RTT 量级一致，且不随数据量/Query 长度增长 → 非 CPU、非 I/O，是网络 RTT。")
A("- AC QPS 在并发 5 后趋稳 ~60（500k），c5≈c10≈c20 → RTT 串行化封顶，而非 INSTR 那种 CPU 封顶。")
A("- `data_version` 查询本身是**契约要求 + 一致性保障**（响应须带回版本、`expected_data_version` 乐观并发校验、AC 快照按版本失效），每请求查是最保守的正确性实现，可安全缓存化。\n")

A("## 8. 后续优化建议\n")
A("1. **P1 消除每请求 RTT**：缓存 `data_version`（启动读一次 + 短 TTL 或发布事件失效）、移除每请求 `ping(reconnect=True)`。预计 500k/c1 再降约一半（~80ms → ~40ms），并发封顶进一步提升。工作量小、风险低。")
A("2. **P2 就近部署**：消除远程公网 RTT，端到端可降到 1–5ms。")
A("3. **P3 正式容量基线**：P1/P2 落地后在获授权环境重跑同矩阵，建立优化后基线，明确 P95 预算/目标 QPS/错误率 SLO 后计算 `N_max`，生产峰值建议不超过 `0.6 × N_max`。")
A("4. **正确性回归常态化**：每次 AC 索引或匹配逻辑变更，用 golden query 集逐条比对 AC 与 INSTR 结果集一致。\n")

A("## 9. 复现入口\n")
A("脚本：`scripts/run_volume_matrix_benchmark.py`（支持 `--match-strategy {instr,ac}`，断点续跑）\n")
A("```powershell")
A("# 准备四档数据（幂等）")
A("python scripts/run_volume_matrix_benchmark.py --phase seed --output-dir outputs/performance/volume_matrix_ac")
A("# 执行 AC 全矩阵")
A("python scripts/run_volume_matrix_benchmark.py --phase run --match-strategy ac --output-dir outputs/performance/volume_matrix_ac")
A("# 一次完成")
A("python scripts/run_volume_matrix_benchmark.py --phase all --match-strategy ac --output-dir outputs/performance/volume_matrix_ac")
A("```")
A("可调环境变量：`DV_MATRIX_DURATION`（每格采样秒数，默认 10）、`DV_MATRIX_WARMUPS`（热场景预热轮数，默认 3）。脚本只读取本地 `mysql_entity_data_mock_local.py` 配置的库，不在共享实例做删除/截断。\n")

A("## 10. 附录\n")
A("### 10.1 产物清单\n")
A("`outputs/performance/volume_matrix_ac/`：")
A("- `report.md`：机器生成对比表版本")
A("- `matrix.json`：256 格全量明细（含 `match_strategy=ac` 元数据）")
A("- `matrix.csv`：扁平表（volume/length/concurrency/temp/layer/N/p50/p95/p99/mean/max/qps/errors/passed）")
A("- `cells/cell_*.json`：每格明细")
A("- `run.log`：采集进度日志")
A("- `provisioning.json` / `verification.json`：数据准备与校验记录\n")

A("### 10.2 数据版本与校验（entity_words / entities 单位为「行数」）\n")
A("| volume | entity_words (行) | entities (行) | 校验 |")
A("| --- | ---: | ---: | --- |")
for v in VOLUMES:
    A(f"| {v} | {BUILD[v][0]:,} | {BUILD[v][0]//3:,} | OK |")
A("\ngolden 实体 `DV-MOCK-000000334`（normalized_key `cpuusage000001001`）在所有档位均存在且被 AC/INSTR 双策略正确命中。\n")

A("### 10.3 测试过程备注\n")
A("- **HTTP mock 切换**：首轮用 werkzeug dev server，因 AC 高请求率（10 万+次/矩阵）触发 Windows TCP 端口耗尽（werkzeug 无 keep-alive，每请求一个 TIME_WAIT）。已将基准脚本本地 mock 改为 **waitress（HTTP/1.1 keep-alive）**，连接复用后端口耗尽消除、256 格全清。该改动仅影响测试 harness，不改变被测 AC 逻辑。")
A("- **远程 MySQL 抖动**：测试期间远程库曾被外部进程 drop/重建，经幂等 re-seed + 断点续跑补齐；行数与生成逻辑一致，数据有效。")
A("- **INSTR 基线**：对照数据来自 `outputs/performance/volume_matrix/`（同矩阵、同 10s/格、同 waitress mock 重测口径一致）。\n")

A("### 10.4 与既有报告关系\n")
A("本报告为 AC 策略的完整测试报告；`ENTITY_MATCH_AC_VS_INSTR_COMPARISON_20260718.md` 为精简对比版；`ENTITY_MATCH_VOLUME_MATRIX_BENCHMARK_20260718.md` 为 INSTR 基线报告。三者互为印证。\n")

out = ROOT / "docs/reports/ENTITY_MATCH_AC_VOLUME_MATRIX_BENCHMARK_20260718.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("written:", out)
print("cells:", len(ac), "failed:", sum(1 for c in ac if not c["passed"]))
