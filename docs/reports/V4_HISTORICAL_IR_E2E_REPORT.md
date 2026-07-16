# V4 历史业务数据 IR 端到端测试报告

测试日期：2026-07-15  
测试对象：V4 `create_entity_linking_module()` → IR URL → 平台 Client → 模拟远端实体数据服务 → `MATCH_WORDS` / `BATCH_GET_ENTITIES` → V4 NER pipeline  
测试入口：`python scripts/run_v4_historical_e2e.py`

## 范围

| 历史版本 | 实体数据装载方式 | Query 数据集 | 覆盖 Query 数 |
| --- | --- | --- | ---: |
| V1 | `entity_examples.json` | `query_samples.json` | 16 |
| V2 | V1 基线实体 + `v2_entity_examples.json` | `v2_query_samples.json` | 12 |
| V3 | `v3_gauss_entities.json` + `v3_redis_entity_words.json` | `v3_ner_golden_cases.json` | 6 |

所有 Query 均通过 V4 的公开工厂和 IR Client 执行；没有直接调用 `legacy` runtime，也没有跳过远端操作信封。

## 汇总

| 版本 | Query 数 | 通过 | 失败 | 结论 |
| --- | ---: | ---: | ---: | --- |
| V1 | 16 | 16 | 0 | 通过 |
| V2 | 12 | 12 | 0 | 通过 |
| V3 | 6 | 6 | 0 | 通过 |
| 总计 | 34 | 34 | 0 | **通过：达到历史业务样例全量迁移门槛** |

## 修复项

| 原始缺口 | 修复方式 | 回归结果 |
| --- | --- | --- |
| 纯数字已知/未知 ID | 新增 alarm 上下文的数字 mention 识别；远端词条 `priority` 参与重叠选择。 | V1 Q-001、Q-012、Q-013 通过。 |
| 同 span 多候选 | 聚合多个远端匹配词，批量读取详情并输出 Top-K `candidates` 与 `ambiguous`。 | V1 Q-005 通过。 |
| 非链接意图 | 补充 `system health summary` 与 dashboard bypass 策略。 | V1 Q-015、Q-016 与 V2/V3 非链接 Query 通过。 |

## 结论与后续修复顺序

V4 的远端 IR 调用、V1 负例/歧义/模式语义、V2 多类型多 mention/`partial` 和 V3 数据库召回/未知实体形态均已通过历史业务数据回归。当前结论仅覆盖仓库内 34 条脱敏历史 Query；新增业务数据、真实数据服务和真实平台增强器仍须接入同一脚本和验收规则。
