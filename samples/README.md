# Samples

本目录用于存放 DVEntityLinking 的样例数据。

- `mock/`：抽象合成样例。
- `real/`：用户明确确认可提交的真实/启动样例。

未脱敏真实 DV 数据不得直接放入本目录。未脱敏 Query、实体 payload、完整 LLM 请求响应和敏感配置必须保存在 git ignored 路径，例如 `samples/local_real_dv/` 或 `outputs/local_real_dv/`。

涉及真实 DV 内容时，应先在对应迭代的样例接收清单中记录用户确认结论。V1 起样例文件只保留实体链接所需核心字段，不再在每条记录中重复提交/敏感分层说明。

V2 启动样例：

- `real/v2_entity_examples.json`：用户确认的 V2 新增实体样例，覆盖 `ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_type_key`；`kpi_meas_objects` 本轮先忽略；运行时通过 `base_entity_files` 合并 V1 `alarm` 基线。
- `real/v2_query_samples.json`：英文 Query 样例，支持多 mention，并覆盖 linked、partial、no_match、not_required，以及 alarm + 新增实体同 Query。
- `real/v4_query_scenarios.json`：V4 场景化 Query 集；除文本 Query 外，使用 `fixture`、LLM 配置和入口字段描述 IR、降级、健康与异步所需的可控依赖。

V2 新增 KPI/网元类实体的 `alias` 默认必须为空数组；只有用户显式确认的别名才能写入。

V3 两层存储与 NER 样例：

- `real/v3_gauss_entities.json`：高斯 Mock 结构化实体样例，schema 为 `v3.gauss_entities.1`，当前 7 个实体，只保留 `entity_id`、`entity_type`、`entity_name`、`alias`、`desc`。
- `real/v3_redis_entity_words.json`：Redis Mock 实体词 KV 样例，schema 为 `v3.redis_entity_words.1`，key 来源限于 `entity_name` 和经确认 `alias`，value 为单实体 ID。
- `real/v3_ner_golden_cases.json`：V3 NER pipeline golden cases，schema 为 `v3.ner_golden_cases.1`，覆盖 linked、partial、no_match 和 not_required。

V3 不提交真实 Redis/Gauss 连接串、账号、密码、真实 DV payload 或完整 LLM 请求响应。
