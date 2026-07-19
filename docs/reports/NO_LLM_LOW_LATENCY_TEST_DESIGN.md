# 无 LLM 低延时数据采集测试设计

状态：测试方案与采集器已就绪；低延时环境正式数据待独立执行。  
适用入口：`DVAIAgentService.MATCH_WORDS`、`QueryRecallFacade.recall()`。  
数据约束：只读既有持久化 Mock 数据，测试结束不删除、不清空、不重建数据库。

## 1. 目标与结论边界

本测试用于获取同机房或同一低延时网络内的原始性能数据，区分以下两类成本：

1. `remote_match`：仅调用生产兼容的 `MATCH_WORDS`，度量 P4 HTTP、连接池和 MySQL `INSTR` 查询的组合延迟。
2. `query_recall`：调用无版本后缀的 `QueryRecallFacade`，覆盖 P4、确定性 mention 识别/合并/确认、P8 候选决策、P9 批量详情读取和结果聚合。

本轮明确不使用 LLM。采集器同时采用三道约束：每个请求显式传入 `use_llm=False`、装配时不提供 mention enhancer、装配时不提供 candidate reranker。结果文件也固定记录 `llm.enabled=false`。

在业务方尚未确认 P4 P95 预算、端到端预算、目标 QPS 和错误率 SLO 前，测试只能给出数据、容量拐点候选和瓶颈判断，不能宣称生产容量验收通过。正式 `N_max` 还需在多个持久化数据档位上复用同一套测试；预计生产 entity word 数必须不高于 `0.6 × N_max`。

## 2. 测试资产

| 资产 | 用途 |
| --- | --- |
| `samples/mock/no_llm_low_latency_test_plan.json` | 固定 golden query、正确性期望、流量权重和 smoke/analysis/formal profile。 |
| `scripts/run_no_llm_low_latency_collection.py` | 预检、并发采集、原始 JSONL 压缩写入和汇总计算。 |
| `tests/performance/test_no_llm_mysql_low_latency.py` | 当前项目内的正式执行入口；读取既有 MySQL 配置并自动启动 localhost Mock。 |
| `scripts/run_mysql_entity_data_mock.py` | 检查既有数据并启动只读远程接口 Mock。 |
| `tests/test_no_llm_low_latency_collection.py` | 验证无 LLM 装配、P4/P9 调用次数、上下文规则和统计结果。 |

采集器使用线程级长连接，不把每次 TCP 建连作为业务查询耗时；每个并发梯度开始前对每个 worker 预热。查询文本和真实 endpoint host 不写入结果，原始样本仅记录 case 名称。

## 3. Golden query 矩阵

| Case | P4 预期 | 端到端预期 | 主要分析目的 |
| --- | ---: | --- | --- |
| `no_match_worst_scan` | 0 | `no_match` | 无命中全量扫描的尾延迟。 |
| `single_exact_hit` | 1 | `linked` | 最常见单 mention，端到端会执行 P4+P9。 |
| `multi_exact_hit` | 2 | `linked` | 多 mention、去重和一次批量详情读。 |
| `repeated_hit` | 1 | `linked` | 同一词多次出现时的 span 恢复成本。 |
| `long_query_hit` | 1 | `linked` | 长 Query 对 SQL 与 Python pipeline 的影响。 |
| `context_rule_pass` | 1 | `linked` | P4 命中且上下文确认通过。 |
| `context_rule_reject` | 1 | `no_match` | P4 命中但 Python 确认拒绝，证明两层统计不能混用。 |
| `structured_alarm_hit` | 1 | `linked` | 结构化 alarm token 与中英文混合文本。 |
| `type_filtered_device` | 1 | 不进入负载 | 类型过滤正确性预检。 |
| `explicit_bypass` | 不调用 | `not_required` | bypass 正确性预检，确认远程调用数为 0。 |

`weight=0` 的用例只参与预检，不参与负载，避免 bypass 或专项过滤场景稀释核心延迟分布。

## 4. Profile 与执行顺序

| Profile | 单个“层 × 并发”持续时间 | 并发 | 用途 |
| --- | ---: | --- | --- |
| `smoke` | 5 秒 | 1、10 | 环境连通和脚本自检。 |
| `analysis` | 120 秒 | 1、10、25、50、100 | 快速定位拐点、超时和资源风险。 |
| `formal` | 900 秒 | 1、10、25、50、100 | 每个梯度至少 15 分钟的正式原始数据。 |

默认同时执行两个层，因此完整 formal 约需 150 分钟，另加预热和预检。必须按以下顺序执行：

1. 固定代码提交、数据 preset、data version、MySQL 参数、Mock `threads/pool-size` 和机器规格。
2. 在当前项目所在机器关闭 VPN，保持 `scripts/mysql_entity_data_mock_local.py` 指向现有同一 MySQL；pytest 测试会自动在本机临时端口启动 Mock，不填写其他服务或数据库地址。
3. 运行测试文件，再运行 `smoke`；预检不通过时停止，不得继续产生性能结论。
4. 运行 `analysis`，确认没有连接池耗尽、客户端超时或机器资源失控。
5. 运行 `formal`；每个 run 完成后立即检查 `summary.json`，单个接口失败不阻止其他 worker 留下错误样本。
6. 如需突发测试，使用 `--duration-seconds 60 --concurrencies 100` 单独输出，禁止并入 15 分钟持续负载结果。
7. 冷缓存、服务重启、数据发布重叠均单独执行并使用不同 output 目录，禁止与热缓存稳态结果合并。

当前候选快照/原子切换能力尚未实现，因此“数据发布重叠”场景暂不执行，也不得伪造结果；待发布端口完成后复用本采集器并增加明确的 overlap 标签。

## 5. 交给执行模型的命令

以下命令均由辅助编程软件在当前项目根目录执行。测试文件直接读取当前项目已忽略的 MySQL 配置，在测试进程内自动启动 `127.0.0.1` Mock；不需要单独启动服务，也不需要传 `base-url`。测试只读现有持久化数据：

```powershell
$env:DV_RUN_MYSQL_PERFORMANCE = '1'
$env:DV_PERF_PROFILE = 'formal'
python -m pytest -s tests\performance\test_no_llm_mysql_low_latency.py
```

`formal` 从固定计划读取并发 1/10/25/50/100，每个“层 × 并发”持续 15 分钟。快速检查可将 `DV_PERF_PROFILE` 改为 `smoke` 或 `analysis`。`DV_PERF_POOL_SIZE` 必须小于 MySQL `max_connections`，并预留管理连接；不得使用 pytest-xdist/`-n` 并行启动多套压测。

## 6. 同步采集的资源证据

执行模型应在当前项目所在机器同步记录 5 秒粒度数据，并与 pytest 输出目录中的 UTC 开始/结束时间对齐；同时采集有权限读取的 MySQL 状态：

- 进程 CPU、机器 CPU、RSS/可用内存；
- 磁盘读 IOPS、吞吐、平均读等待、队列长度；
- 网络吞吐、重传或错误；
- MySQL `Threads_connected`、`Threads_running`、`Connections`、`Aborted_clients`、`Questions`、`Slow_queries`；
- `Innodb_buffer_pool_read_requests`、`Innodb_buffer_pool_reads`、`Innodb_buffer_pool_wait_free`；
- `Handler_read_rnd_next`、行锁等待次数/时间、临时表数；
- Mock 当前线程数、pool 大小、MySQL `max_connections`、buffer pool 大小；
- `EXPLAIN FORMAT=JSON` 和 `EXPLAIN ANALYZE`，至少覆盖无命中与类型过滤用例。

资源采集失败不会改变请求样本，但 formal 结果只能标记为“不完整证据”，不能用于生产准入。

## 7. 结果文件与安全边界

每次 pytest 执行默认生成 `outputs/performance/pytest_no_llm_<profile>_<UTC>/`：

```text
summary.json
samples/
  remote_match_c1.jsonl.gz
  remote_match_c10.jsonl.gz
  ...
  query_recall_c100.jsonl.gz
```

`summary.json` 包含整体和逐 case 的请求数、QPS、P50/P95/P99/mean/max、错误率、错误码、正确性失败、平均响应字节、平均远程调用数和 data-version 稳定性。原始 JSONL 每行保留 case、相对开始时间、单请求延迟、状态、错误码、响应大小和远程调用数，便于后续绘制时间序列和分布图。

结果不记录 endpoint host、原始 query、MySQL host、用户名、密码或完整响应。`outputs/*` 已被 Git 忽略；需要提交报告时只提炼聚合指标和匿名化环境信息，不提交原始地址或凭据。

## 8. 分析方法

执行完成后按以下顺序分析：

1. **先正确性**：`preflight.passed=true`、所有 run 的 `correctness_failures=0`、direct P4 的 data version 单一稳定。
2. **再可靠性**：按并发查看 error rate、错误码和超时首次出现的位置；不得只看成功请求延迟。
3. **定位 P4**：比较 `remote_match` 的 no-match、single、multi、long 和类型过滤；结合 `Handler_read_rnd_next`、buffer-pool miss 与磁盘等待确认扫描成本。
4. **定位 pipeline**：在同一 case/并发下比较 `query_recall` 与 `remote_match`。二者是独立分布，不能直接用“P95 相减”冒充逐请求 Python 开销；应同时比较中位数、尾部和 QPS。
5. **识别拐点**：并发增加但 QPS 不再增长、P95/P99 陡升、数据库运行线程/磁盘队列持续增加的位置为并发拐点候选。
6. **计算容量**：在不同持久化数据档位复测后，以目标并发下 P4 P95 首次超过已批准预算的数据量定义 `N_max`；若尚无预算，仅报告曲线，不计算虚假 `N_max`。
7. **增长余量**：只有当预计峰值 entity word `<= 0.6 × N_max`，且错误率、P95/P99 与资源水位均满足已批准 SLO，才能进入容量验收。

最低交付数据表应包含：代码提交、data version、entity/entity-word 数、机器规格、网络位置、threads/pool、MySQL 关键参数、层、并发、持续时间、请求数、QPS、P50/P95/P99/max、错误率、正确性失败、CPU/内存/磁盘/连接池峰值和结论。

## 9. 执行模型完成条件

执行模型只有在以下材料都存在时才算完成：

- `smoke`、`analysis`、`formal` 三份 `summary.json` 和全部 gzip 原始样本；
- 同时间段资源监控和 MySQL 状态快照；
- 无命中与类型过滤的执行计划；
- 一份匿名化分析报告，明确区分 P4 和端到端，不声称启用了 LLM；
- 所有异常均保留错误码和发生并发，单个异常没有导致后续接口/worker 数据丢失；
- 对尚未具备的发布重叠与未确认 SLO 明确标记为待办，而不是推断为通过。
