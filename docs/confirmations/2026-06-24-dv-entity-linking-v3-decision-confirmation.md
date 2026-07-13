# DVEntityLinking V3 决策确认记录

确认时间：2026-06-24T18:14:23

## 1. Redis 单值冲突策略

- 决策：推荐：保持 value 为单实体 ID；冲突数据加载 fail-closed，不进入链接链路
- 补充：保持 V3 初始范围简单，先不扩大 Redis value 结构。

## 2. Redis key 范围

- 决策：推荐：canonical_name + 经确认 aliases；不自动生成别名
- 补充：aliases 必须来自已确认样例或用户确认清单。

## 3. 高斯结构化实体字段

- 决策：推荐：沿用最小字段 entity_id/entity_type/canonical_name/aliases/description
- 补充：类型专属字段后续单独确认，V3 初始先稳住存储边界。

## 4. NER 内部 schema

- 决策：推荐：允许内部 schema 扩展；外部 API 和样例提交字段受控
- 补充：内部 schema 用于 NER stage trace、storage lookup 和重构隔离。

## 5. LLM 在 V3 NER 中的角色

- 决策：推荐：默认离线 deterministic 可回归；LLM 作为可选分类/解释/rerank 增强
- 补充：默认验收不依赖真实 LLM，本地配置可做条件补证。

## 6. V3 样例数据策略

- 决策：推荐：复用 V1/V2 样例，新增 Redis/Gauss Mock artifacts 和 NER golden cases
- 补充：新增样例必须保持脱敏和 D003 边界，不引入真实生产 payload。

## 7. 签收

- 确认人：SL
- 结论：确认以上 V3 决策，可据此修订 IR 并进入独立需求评审
- 其他说明：TBD
