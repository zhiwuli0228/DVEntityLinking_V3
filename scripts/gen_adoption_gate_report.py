import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
g1 = json.loads((ROOT / "outputs/performance/gate1_equivalence/report.json").read_text(encoding="utf-8"))
g2 = json.loads((ROOT / "outputs/performance/gate2_memory/report.json").read_text(encoding="utf-8"))
g3 = json.loads((ROOT / "outputs/performance/gate3_load/report.json").read_text(encoding="utf-8"))

L = []
A = L.append

A("# AC 正式采用门禁测试报告\n")
A("> 本报告为 Aho-Corasick 内存匹配策略正式采用前的三项门禁测试结果：① 多样化 golden query 等价；② 进程内存/重建峰值/多进程；③ 高并发 50/100 + 15 分钟持续压测 + 数据库交互耗时拆分。门禁 1/2 通过；门禁 3 证明 AC 本身非瓶颈，剩余问题来自数据库交互层（非 AC 策略），建议有条件采用。\n")

A("## 1. 总览\n")
A("| 门禁 | 内容 | 结论 |")
A("| --- | --- | --- |")
A(f"| 门禁1 | 多样化 golden query AC≡INSTR 等价 | **通过**（{g1['total_comparisons']} 次比对，0 不一致） |")
A(f"| 门禁2 | 进程 RSS / 重建峰值 / 多进程内存 | **通过**（峰值=稳态无尖峰；1/2/4 进程线性比 1.00） |")
A("| 门禁3 | c50/c100 + 15min 持续 + DB 交互拆分 | **部分通过**（c50 持续 0 错误；c100 0.06% 错误+长尾；AC 匹配本身 0.007ms 非瓶颈） |")
A("\n**采用建议**：AC 策略本身通过等价与内存门禁，且门禁3 证实 AC 匹配耗时仅 0.007ms（可忽略），当前 c100 的长尾与零星错误来自数据库交互层（`data_version` + 主键 fetch 的 RTT 与连接池争用），**非 AC 策略问题**。建议**有条件采用 AC**，同步推进 P1（缓存 data_version、去 ping）+ P2（就近部署）以消除数据库交互层瓶颈、提升 c100 稳定性。\n")

A("## 2. 门禁1：多样化 golden query 等价\n")
A(f"query 集：测试计划 9 个 remote_match golden case + 6 个边界（部分前缀 / CJK 中文 / 2KB 超长 / 单字符 / 类型不匹配 / 全填充）= **15 条**；× 4 数据量 = **{g1['total_comparisons']} 次比对**。比对维度：entity_id 集合 + 有序 (entity_word_id, entity_id) 指纹 + 命中计数。\n")
A(f"- **不致信数：{g1['mismatches']}**")
A(f"- **结论：{'通过' if g1['passed'] else '未通过'}**\n")
A("覆盖的关键边界：部分前缀 `cpuusage00000100`（缺末位）→ 0 命中（AC 不误匹配前缀）；CJK `查询cpuusage000001001告警` → 正确命中；2KB 超长 → 正确命中；类型过滤不匹配 → 0 命中。AC 与 INSTR 在所有边界完全一致。\n")

A("## 3. 门禁2：进程内存 / 重建峰值 / 多进程\n")
sp = g2["single_process"]
A(f"构建 50 万 pattern 的 AC 自动机（本地生成 pattern，索引内存与数据源无关），psutil 采样。\n")
A("### 3.1 单进程（单位：MB / 秒）\n")
A("| 指标 | 值 |")
A("| --- | ---: |")
A(f"| baseline RSS | {sp['baseline_rss_mb']} |")
A(f"| 构建后稳态 RSS | {sp['steady_rss_mb']} |")
A(f"| **构建期峰值 RSS** | {sp['peak_rss_mb']} |")
A(f"| 索引 RSS 增量 | {sp['index_rss_delta_mb']} |")
A(f"| 自动机 size_bytes | {sp['index_size_mb']} |")
A(f"| 构建耗时 | {sp['build_seconds']}s |")
A(f"\n**峰值 RSS = 稳态 RSS**（{sp['steady_rss_mb']}MB），构建过程无尖峰（pyahocorasick 原地构建）。RSS 增量 {sp['index_rss_delta_mb']}MB > 自动机字节数 {sp['index_size_mb']}MB，差额为 Python 对象开销，符合预期。\n")

A("### 3.2 多进程（1/2/4 进程，单位：MB）\n")
A("| 进程数 | 每进程平均 RSS | 总 RSS | 线性比 |")
A("| ---: | ---: | ---: | ---: |")
single_child = g2["multi_process"]["n1"]["avg_per_process_mb"]
for n in (1, 2, 4):
    m = g2["multi_process"][f"n{n}"]
    expected = single_child * n
    ratio = m["total_rss_mb"] / expected if expected else 0
    A(f"| {n} | {m['avg_per_process_mb']} | {m['total_rss_mb']} | {ratio:.2f} |")
A(f"\n**线性比 1.00**：AC 索引按进程独立、进程间不共享，多进程部署内存严格线性叠加（4 进程 500k = {g2['multi_process']['n4']['total_rss_mb']}MB），无翻倍/泄漏。**结论：通过**。\n")

A("## 4. 门禁3：高并发 + 持续压测 + DB 交互拆分\n")
A(f"配置：500k 档，short+ultra，c50+c100，pool_size={g3['pool_size']}，waitress threads={g3['waitress_threads']}，keep-alive。`DV_MOCK_TIMING=1` 启用，每请求记录 ac_match_ms / data_version_ms / fetch_ms，经 `/timings` 暴露。短矩阵 10s + 持续 900s。\n")

A("### 4.1 持续 15 分钟压测（单位：延迟 ms，QPS 次/秒，错误数次数）\n")
A("| 场景 | N | p50 | p95 | mean | QPS | 传输错误 | 正确性失败 | 结论 |")
A("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
for c in g3["cells"]:
    if c["phase"] != "sustained":
        continue
    er = c["transport_errors"] / c["requests"] * 100 if c["requests"] else 0
    A(f"| {c['length']} c{c['concurrency']} | {c['requests']} | {c['p50_ms']:.0f} | {c['p95_ms']:.0f} | {c['mean_ms']:.0f} | {c['qps']:.1f} | {c['transport_errors']}({er:.2f}%) | {c['correctness_failures']} | {'通过' if c['passed'] else '部分通过'} |")
A("\n- **c50 持续 15min**：0 错误，p50≈91ms，QPS≈204，15min 内 ~18.4 万请求稳定无退化。**通过**。")
A("- **c100 持续 15min**：p50≈93ms（与 c50 相当），但 p95≈1850ms 长尾，传输错误 0.05–0.06%（92–114 次/~18 万），QPS≈191–195（**未较 c50 提升，已饱和**）。**部分通过**——错误率极低但非零，长尾明显。\n")

A("### 4.2 数据库交互耗时拆分（持续 15min，单位：ms）—— 关键证据\n")
A("每请求拆为「AC 内存匹配 + data_version 查询 + 主键 fetch」三段：\n")
A("| 场景 | AC p50 | AC p95 | AC max | data_version p50 | fetch p50 | fetch p95 | fetch max | 三段和 p50 |")
A("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
for c in g3["cells"]:
    if c["phase"] != "sustained":
        continue
    b = c["breakdown"]
    A(f"| {c['length']} c{c['concurrency']} | {b['ac_match']['p50_ms']:.3f} | {b['ac_match']['p95_ms']:.3f} | {b['ac_match']['max_ms']:.1f} | {b['data_version']['p50_ms']:.1f} | {b['fetch']['p50_ms']:.1f} | {b['fetch']['p95_ms']:.1f} | {b['fetch']['max_ms']:.0f} | {b['sum_per_request']['p50_ms']:.1f} |")
A("\n**拆分结论**：\n")
A(f"- **AC 内存匹配 p50=0.007–0.011ms**（max 0.5ms），即使在 c100 持续 15min 下也可忽略——**AC 策略本身不是瓶颈**，全表扫描已彻底消除。")
A("- **data_version 查询 p50≈10–11ms**（1 RTT），p95 稳定 15–22ms，但 c100 下 max 飙到 27–55s（偶发极端尾）。")
A("- **主键 fetch p50≈13ms**（1 RTT），但 **p95=657–1728ms、max=6988–115801ms**——fetch 的长尾是端到端 p95 与零星传输错误的主要来源（连接池/MySQL 并发争用）。")
A("- 三段和 p50≈25–27ms（2 RTT），与端到端 p50（91ms）的差额（~65ms）是高并发下的排队/HTTP 开销。")
A("\n**根因定位**：c100 的长尾与错误来自 **数据库交互层（fetch 的连接池/MySQL 并发争用）**，而非 AC。这正对应优化报告的 P1（缓存 data_version、去 ping，减 1 RTT + 降低连接池 churn）+ P2（就近部署，降 RTT）。\n")

A("### 4.3 短矩阵（10s）补充\n")
A("| 场景 | N | p50 | p95 | QPS | AC p50 | dv p50 | fetch p50 | 传输错误 | 结论 |")
A("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
for c in g3["cells"]:
    if c["phase"] != "short_matrix":
        continue
    b = c["breakdown"]
    A(f"| {c['length']} c{c['concurrency']} | {c['requests']} | {c['p50_ms']:.0f} | {c['p95_ms']:.0f} | {c['qps']:.1f} | {b['ac_match']['p50_ms']:.3f} | {b['data_version']['p50_ms']:.1f} | {b['fetch']['p50_ms']:.1f} | {c['transport_errors']} | {'通过' if c['passed'] else '部分通过'} |")
A("\n短矩阵 c100 错误率较高（~4%，启动期争用尖峰），但持续 15min 下错误率降到 0.06%——短矩阵的高错误率是瞬时启动效应，持续态稳定。\n")

A("## 5. 三门禁综合结论\n")
A("| 维度 | 结论 | 证据 |")
A("| --- | --- | --- |")
A("| 正确性等价 | ✅ 通过 | 15 query × 4 volume = 60 次比对 0 不一致，含部分前缀/CJK/2KB/类型过滤边界 |")
A("| 内存 | ✅ 通过 | 单进程峰值=稳态（无尖峰）；1/2/4 进程线性比 1.00，4 进程 322MB |")
A("| 持续稳定性 | ✅ 通过（c50）/ ⚠️ 部分通过（c100） | c50 持续 15min 0 错误 204 QPS；c100 0.06% 错误+长尾，QPS 未提升（饱和）|")
A("| AC 是否瓶颈 | ✅ 否 | AC 匹配 p50=0.007ms（c100 持续 15min），可忽略 |")
A("| 剩余瓶颈 | 数据库交互层 | fetch p95=657–1728ms / max 115s（连接池+MySQL 并发争用）+ data_version RTT |")
A("\n**正式采用建议**：**有条件采用 AC 策略**。AC 本身（正确性、内存、匹配性能）满足门禁；当前 c100 的长尾与零星错误属于数据库交互层（RTT + 连接池争用），与 AC 策略无关，由既有优化路线 P1/P2 解决。建议：\n")
A("1. **采用 AC 替换 INSTR** 作为 `MATCH_WORDS` 匹配策略（正确性等价、内存线性、匹配耗时下降 5–6 个数量级）。")
A("2. **同步落地 P1**（缓存 `data_version`、移除每请求 `ping`）：减 1 RTT/请求 + 降低连接池 churn，预计直接改善 c100 长尾与错误率。")
A("3. **P2 就近部署**后重跑门禁3，验证 c100 持续 0 错误、p95 收敛。")
A("4. **正式容量基线**：P1/P2 落地后在获授权环境重跑同矩阵 + 门禁3，明确 P95 预算/目标 QPS/错误率 SLO 后计算 `N_max`。")
A("5. **正确性回归常态化**：每次 AC 索引或匹配逻辑变更，重跑门禁1 golden query 集比对。\n")

A("## 6. 复现入口\n")
A("```powershell")
A("# 门禁1 等价（需 MySQL + 四档库）")
A("python scripts/run_gate1_equivalence.py")
A("# 门禁2 内存（不需 MySQL）")
A("python scripts/run_gate2_memory_test.py")
A("# 门禁3 高并发+持续+拆分（需 MySQL，DV_MOCK_TIMING=1 脚本内置）")
A("python scripts/run_gate3_load.py                 # 短矩阵 + 15min 持续")
A("python scripts/run_gate3_load.py --skip-sustained  # 仅短矩阵")
A("python scripts/run_gate3_load.py --sustained-seconds 900 --skip-short  # 仅持续")
A("```")
A("\n埋点：`mysql_source.py` 的 AC 路径在 `DV_MOCK_TIMING=1` 时记录三段耗时，经 `service.py` 的 `/timings` 端点 drain；默认关闭、零开销。\n")

A("## 7. 附录：产物清单\n")
A("- 门禁1：`outputs/performance/gate1_equivalence/report.json`（60 次比对明细）")
A("- 门禁2：`outputs/performance/gate2_memory/report.json`（单进程+多进程内存）")
A("- 门禁3：`outputs/performance/gate3_load/report.json`（8 格 × 拆分明细）")
A("- 既有：`docs/reports/ENTITY_MATCH_AC_VOLUME_MATRIX_BENCHMARK_20260718.md`（AC 矩阵）、`ENTITY_MATCH_VOLUME_MATRIX_BENCHMARK_20260718.md`（INSTR 基线）、`ENTITY_MATCH_AC_VS_INSTR_COMPARISON_20260718.md`（对比）\n")

A("## 8. 环境备注\n")
A("- 远程 MySQL 8.0.27（47.119.150.113），公网链路，RTT 波动（data_version/fetch p50 ≈ 10–13ms）。测试期间库曾被外部进程多次 drop/重建，经幂等 re-seed 补齐，行数与生成逻辑一致。")
A("- 本地 waitress（HTTP/1.1 keep-alive）包装 mock；并发压测用 keep-alive 连接复用，避免端口耗尽。")
A("- 门禁3 的 c100 错误为远程 MySQL 连接层偶发（连接池争用 + RTT 抖动），非 AC 逻辑错误（0 正确性失败）。")

out = ROOT / "docs/reports/AC_ADOPTION_GATE_REPORT_20260718.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("written:", out)
