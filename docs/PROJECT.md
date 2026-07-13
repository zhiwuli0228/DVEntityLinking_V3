# DVEntityLinking 项目总览

最后更新：2026-06-26

本文档是项目当前状态、范围、约束和后续规划的唯一权威入口。历史版本细节见 `docs/releases/`，IR/SR 主输出件见 `docs/baselines/`。

## 当前状态

| 项 | 状态 |
| --- | --- |
| 当前版本 | V3 acceptance candidate prepared; pending user acceptance; not accepted/closed |
| 已关闭版本 | V0、V1 |
| 当前活跃迭代 | V3 验收候选前置核查和核验已通过，候选记录已准备；重点交付为两层存储、Redis 缓存接口 Mock、高斯数据库接口 Mock 和 NER pipeline 详细设计/必要重构 |
| 技术栈 | Python 3.12、Flask Web/API、OpenAI-compatible LLM adapter |
| 默认验收模式 | `offline_demo`，不依赖真实 DV 和真实 LLM |

## 项目目标

DVEntityLinking 面向 DV 运维 Copilot 和故障 Agent，沉淀所有涉及实体的基础能力：

- 实体构建、实体词表、别名、标准名、类型和基础属性。
- Query 实体识别、匹配、链接、归一化和消歧。
- 实体查询、相似度检索、相关实体召回。
- 为后续真实 DV 运行时数据和 LLM 辅助链路提供可控 demo 基线。

## 已关闭版本

| 版本 | 结论 | 入口 |
| --- | --- | --- |
| V0 | Mock 实体链接 demo 已关闭；覆盖多类合成实体、Query 链接、实体查询、Top-K 检索、Web/API、真实 LLM 条件 smoke。 | [releases/V0.md](./releases/V0.md) |
| V1 | alarm-only 实体链接 demo 已关闭；覆盖 9 个 `alarm` 实体、16 条 Query、LLM 模式切换、短 ID 子串保护、负例零误报和 Web 核心展示。 | [releases/V1.md](./releases/V1.md) |

## 当前权威基线

| 类型 | 文件 |
| --- | --- |
| V0 IR | [baselines/v0/IR.md](./baselines/v0/IR.md) |
| V0 SR | [baselines/v0/SR.md](./baselines/v0/SR.md) |
| V1 IR | [baselines/v1/IR.md](./baselines/v1/IR.md) |
| V1 IR SR 分解 | [baselines/v1/IR-SR-DECOMPOSITION.md](./baselines/v1/IR-SR-DECOMPOSITION.md) |
| V1 SR | [baselines/v1/SR.md](./baselines/v1/SR.md) |
| V2 IR | [baselines/v2/IR.md](./baselines/v2/IR.md) |
| V2 前端补救 IR | [baselines/v2/IR-FRONTEND-REMEDIATION.md](./baselines/v2/IR-FRONTEND-REMEDIATION.md) |
| V2 前端视觉风格补救 IR | [baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md](./baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md) |
| V2 前端视觉风格补救需求评审 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW.md) |
| V2 前端视觉风格补救需求评审处置 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| V2 前端视觉风格补救需求闭环验证 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |
| V2 前端视觉风格补救功能设计 | [baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md](./baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md) |
| V2 前端视觉风格补救功能设计评审 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| V2 前端视觉风格补救功能设计评审处置 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md) |
| V2 前端视觉风格补救功能设计闭环验证 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| V2 前端视觉风格补救代码实现记录 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md) |
| V2 前端视觉风格补救实现评审 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md) |
| V2 前端视觉风格补救实现评审处置 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| V2 前端视觉风格补救实现评审闭环验证 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| V2 前端视觉风格补救测试设计与测试开发 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md) |
| V2 前端视觉风格补救测试评审 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md) |
| V2 前端视觉风格补救测试评审处置 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md) |
| V2 前端视觉风格补救测试评审闭环验证 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md) |
| V2 前端视觉风格补救验收前置核查 | [baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md) |
| V2 前端补救需求评审处置 | [baselines/v2/FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-REMEDIATION-REQUIREMENT-REVIEW-DISPOSITION.md) |
| V2 前端补救需求闭环验证 | [baselines/v2/FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md) |
| V2 前端补救功能设计 | [baselines/v2/SR-FRONTEND-REMEDIATION.md](./baselines/v2/SR-FRONTEND-REMEDIATION.md) |
| V2 前端补救功能设计评审 | [baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW.md) |
| V2 前端补救功能设计评审处置 | [baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md) |
| V2 前端补救功能设计闭环验证 | [baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| V2 前端补救代码实现记录 | [baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md](./baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md) |
| V2 前端补救实现评审 | [baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW.md](./baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW.md) |
| V2 前端补救实现评审处置 | [baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| V2 前端补救实现评审闭环验证 | [baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| V2 前端补救测试设计与测试开发 | [baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md](./baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md) |
| V2 前端补救测试评审 | [baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW.md](./baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW.md) |
| V2 前端补救测试评审处置 | [baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-REMEDIATION-TEST-REVIEW-DISPOSITION.md) |
| V2 前端补救测试评审闭环验证 | [baselines/v2/FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-REMEDIATION-TEST-CLOSURE-VERIFICATION.md) |
| V2 前端补救验收候选前反向核查 | [baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md](./baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK.md) |
| V2 前端补救验收前反向核查独立核验 | [baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md](./baselines/v2/FRONTEND-REMEDIATION-ACCEPTANCE-PRECHECK-VERIFICATION.md) |
| V2 IR SR 分解 | [baselines/v2/IR-SR-DECOMPOSITION.md](./baselines/v2/IR-SR-DECOMPOSITION.md) |
| V2 SR 功能设计 | [baselines/v2/SR.md](./baselines/v2/SR.md) |
| V2 初始实现评审处置与闭环 | [baselines/v2/IMPLEMENTATION-REVIEW-DISPOSITION.md](./baselines/v2/IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| V2 测试设计与测试开发 | [baselines/v2/TC-DVEntityLinking-V2-test-cases.md](./baselines/v2/TC-DVEntityLinking-V2-test-cases.md) |
| V2 测试评审处置 | [baselines/v2/TEST-REVIEW-DISPOSITION.md](./baselines/v2/TEST-REVIEW-DISPOSITION.md) |
| V2 验收候选记录 | [releases/V2.md](./releases/V2.md) |
| V3 IR | [baselines/v3/IR.md](./baselines/v3/IR.md) |
| V3 IR SR 分解 | [baselines/v3/IR-SR-DECOMPOSITION.md](./baselines/v3/IR-SR-DECOMPOSITION.md) |
| V3 SR 功能设计 | [baselines/v3/SR.md](./baselines/v3/SR.md) |
| V3 需求评审 | [baselines/v3/REQUIREMENT-REVIEW.md](./baselines/v3/REQUIREMENT-REVIEW.md) |
| V3 需求评审处置 | [baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md](./baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md) |
| V3 需求评审闭环验证 | [baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md](./baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md) |
| V3 功能设计评审 | [baselines/v3/FUNCTION-DESIGN-REVIEW.md](./baselines/v3/FUNCTION-DESIGN-REVIEW.md) |
| V3 功能设计评审处置 | [baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md) |
| V3 功能设计评审闭环验证 | [baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md) |
| V3 初始代码实现 | [baselines/v3/IMPLEMENTATION.md](./baselines/v3/IMPLEMENTATION.md) |
| V3 初始代码实现评审 | [baselines/v3/IMPLEMENTATION-REVIEW.md](./baselines/v3/IMPLEMENTATION-REVIEW.md) |
| V3 初始代码实现评审处置 | [baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md](./baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md) |
| V3 初始代码实现评审闭环验证 | [baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md](./baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md) |
| V3 测试设计与测试开发 | [baselines/v3/TEST-DESIGN.md](./baselines/v3/TEST-DESIGN.md) |
| V3 测试评审 | [baselines/v3/TEST-REVIEW.md](./baselines/v3/TEST-REVIEW.md) |
| V3 测试评审处置 | [baselines/v3/TEST-REVIEW-DISPOSITION.md](./baselines/v3/TEST-REVIEW-DISPOSITION.md) |
| V3 测试评审闭环验证 | [baselines/v3/TEST-CLOSURE-VERIFICATION.md](./baselines/v3/TEST-CLOSURE-VERIFICATION.md) |
| V3 验收候选前置核查 | [baselines/v3/ACCEPTANCE-PRECHECK.md](./baselines/v3/ACCEPTANCE-PRECHECK.md) |
| V3 验收候选前置核查核验 | [baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md](./baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md) |
| V3 验收候选记录 | [releases/V3.md](./releases/V3.md) |
| 当前数据契约 | [current/DATA_CONTRACT.md](./current/DATA_CONTRACT.md) |
| 当前验收与测试策略 | [current/TEST_ACCEPTANCE.md](./current/TEST_ACCEPTANCE.md) |
| 当前决策台账 | [current/DECISIONS.md](./current/DECISIONS.md) |

## 范围边界

当前已进入项目范围：

- 面向 demo 的实体目录和实体词表构建。
- 面向 Query 的实体识别、匹配、链接、归一化和消歧。
- 实体查询、Top-K 相似实体检索和可解释候选排序。
- Web demo、JSON API、PyCharm 可直接启动脚本和本地验收 smoke。
- OpenAI-compatible LLM 条件接入；真实配置仅允许本地 ignored 使用。

当前不默认进入范围：

- 真实 DV 生产写操作、自动修复、派单、变更或告警确认。
- 未确认的真实 DV 接口、字段、生产 payload 或实体类型。
- 未经确认的实体结构升级、类型专属字段或关系 schema。
- 真实 DV 运行时接口直连；V2 当前只启动文件驱动 Mock。
- 真实 Redis 或真实 GaussDB 直连；V3 当前只实现接口 Mock 与离线可回归验证。
- 生产级向量库、FTS 或外部检索组件强依赖。
- 提交真实 API key、token、base URL 或完整 LLM 请求响应日志。

## V3 当前方向

- 用户已确认搁置 V2 遗留视觉 before 证据问题，进入 V3；V2 仍未 accepted/closed，但不作为 V3 启动阻塞。
- V3 当前处于验收候选已准备、等待用户验收确认阶段，主输出件为 [baselines/v3/IR.md](./baselines/v3/IR.md)、[baselines/v3/IR-SR-DECOMPOSITION.md](./baselines/v3/IR-SR-DECOMPOSITION.md)、[baselines/v3/SR.md](./baselines/v3/SR.md)、[baselines/v3/REQUIREMENT-REVIEW.md](./baselines/v3/REQUIREMENT-REVIEW.md)、[baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md](./baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md)、[baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md](./baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md)、[baselines/v3/FUNCTION-DESIGN-REVIEW.md](./baselines/v3/FUNCTION-DESIGN-REVIEW.md)、[baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md)、[baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md)、[baselines/v3/IMPLEMENTATION.md](./baselines/v3/IMPLEMENTATION.md)、[baselines/v3/IMPLEMENTATION-REVIEW.md](./baselines/v3/IMPLEMENTATION-REVIEW.md)、[baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md](./baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md)、[baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md](./baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md)、[baselines/v3/TEST-DESIGN.md](./baselines/v3/TEST-DESIGN.md)、[baselines/v3/TEST-REVIEW.md](./baselines/v3/TEST-REVIEW.md)、[baselines/v3/TEST-REVIEW-DISPOSITION.md](./baselines/v3/TEST-REVIEW-DISPOSITION.md)、[baselines/v3/TEST-CLOSURE-VERIFICATION.md](./baselines/v3/TEST-CLOSURE-VERIFICATION.md)、[baselines/v3/ACCEPTANCE-PRECHECK.md](./baselines/v3/ACCEPTANCE-PRECHECK.md)、[baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md](./baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md) 和 [releases/V3.md](./releases/V3.md)。
- V3 两层存储：实体词到实体 ID 的 KV 对走 Redis 缓存接口 Mock；结构化实体数据走高斯数据库接口 Mock，至少支持按实体 ID 查询。
- Redis Mock 已确认：key 使用 `canonical_name` + 经确认 `aliases`，value 保持单实体 ID；同一实体词存在多实体冲突时加载 fail-closed，不进入链接链路。
- 高斯 Mock 已确认 V3 初始沿用最小实体字段：`entity_id`、`entity_type`、`canonical_name`、`aliases`、`description`；类型专属字段扩展后续另行确认。
- NER 是 V3 最高优先级，需详细设计 Query validation、need-linking、mention detection、type classification、entity-word normalization、Redis lookup、高斯 lookup、candidate construction 和状态聚合。
- NER 已确认允许内部 schema 扩展，外部 API 与样例提交字段受控；默认离线 deterministic 可回归，LLM 仅作为可选分类、解释或 rerank 增强。
- V3 样例策略已确认复用 V1/V2 已确认样例，并新增 Redis/Gauss Mock artifacts 和 NER golden cases；新增样例必须脱敏并遵守 D003。
- 必要时允许重构现有 `EntityExtractor`、`EntityLinker`、`CatalogRepository` 和 `EntityLinkingService` 边界；当前初始实现、测试评审闭环、验收候选前置核查和候选记录均已完成，进入 accepted/closed 前仍需用户验收确认。
- V3 默认仍离线可回归，不连接真实 Redis、高斯数据库、真实 DV 生产接口或真实 LLM 作为默认验收依赖。

## V2 当前方向

- 实体类型扩展到 `alarm`、`ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`；实体结构字段暂不升级，任何字段/关系/schema 改动必须先确认。
- 数据预处理作为统一模块，管控预置配置、DVKnowledge KPI/网元类型候选挖掘、样例规范化、显式别名标注、去重和校验；新增类型的 `aliases` 默认必须为空，不得自动生成。
- 运行时接口 Mock 独立成 SR，通过读取文件模拟 DV 启动时拉取 `ne_name` 和可能的 KPI 运行时数据，未来可整体替换为真实 DV 接口。
- NER 采用分层分类思路，先判断是否需要链接和候选实体类型，再进入类型内 mention 识别。
- V2 重点验证 LLM-based 方法，覆盖抽取、分类、解释和 rerank，同时保留默认离线回归。
- 前端采用方案 C：运维工作台式演示 + LLM 交互式高亮/解释；只服务 demo，不做过度前端产品化。
- V2 启动样例已确认并落入 `samples/real/v2_entity_examples.json` 和 `samples/real/v2_query_samples.json`；补充 Query 全部为英文，且 V2 必须支持多 mention。
- Web demo 启动脚本只维护 `scripts\run_web_demo.py` 一个入口；当前默认加载 V2 样例，历史版本回看通过显式 `--catalog` 和 `--samples` 参数加载。
- V2 IR 独立评审、处置和 no-context/sealed 闭环验证已完成，结论为 closed with recorded residual risk。
- V2 SR 功能设计独立评审、处置和 no-context/sealed 闭环验证已完成，结论为 closed；该主 SR 当时已作为 V2 初始代码实现输入。
- V2 初始代码实现已覆盖已确认样例的 unified catalog、英文多 mention Query、`partial` 聚合、V2 evaluation 和 V2 acceptance smoke；实现评审处置和 no-context/sealed 闭环验证已完成，结论为 closed with residual risk。
- V2 测试设计与测试开发已形成 [baselines/v2/TC-DVEntityLinking-V2-test-cases.md](./baselines/v2/TC-DVEntityLinking-V2-test-cases.md)，补充 type-level metrics、V2 dataset metadata fail-closed 和 smoke log artifact 检查；独立测试评审、处置和 no-context/sealed 闭环验证已完成，结论为 closed with recorded residual risk。
- V2 原验收候选曾撤回并标记为 blocked，原因是已确认的重要前端改造要求未落实；上一轮前端功能补救已完成反向核查和独立核验，但用户复核确认视觉风格仍未明显吸收参考原型，不能作为最终验收候选。
- V2 前端视觉风格补救已按用户确认重新进入 DV 流程，需求文档见 [baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md](./baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md)。独立需求评审已完成，2 个 P1、2 个 P2、1 个 P3 均已接受并完成处置；独立闭环验证结论为 closed with recorded residual risk，记录见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-REQUIREMENT-CLOSURE-VERIFICATION.md)。当前功能设计见 [baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md](./baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md)，独立功能设计评审见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW.md)，处置见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-REVIEW-DISPOSITION.md)，闭环验证见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-FUNCTION-DESIGN-CLOSURE-VERIFICATION.md)。代码实现记录见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md)，实现评审见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md)，处置见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)，闭环验证见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)，测试设计/开发见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md)，测试评审见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md)，测试评审处置见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)，测试评审闭环验证见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)，验收前置核查见 [baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md](./baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md)。当前 after 证据已补采且用户确认当前 after 视觉 accepted，`AC-V2-FE-VIS-007` 可关闭；`AC-V2-FE-VIS-008` 仍因 before 同场景截图或替代 before 证据口径未确认而阻塞，进入验收候选或版本关闭前必须关闭该项。

## 文档治理规则

- IR、SR 主输出件按版本保留在 `docs/baselines/<version>/`。
- 当前工作只维护 `docs/current/` 下少量权威文档。
- 每个关闭版本或验收候选版本只保留一份 `docs/releases/<version>.md`。
- 评审输入、闭环输入、临时确认 JSON、一次性过程记录原则上不长期保留在 HEAD；但当前版本仍作为评审输入或用户签署证据引用的 GUI/确认文件可保留到对应评审、处置和闭环完成。完成后如已合并到台账，可再按文档卫生规则清理。
- 涉及方向、范围、真实 DV 内容、LLM 策略和验收语义的用户确认，统一追加到 [current/DECISIONS.md](./current/DECISIONS.md)。
- 用户明确确认的重要需求必须从 IR/SR 追踪到实现、测试和验收；发现静默降级或漏项时不得进入验收候选。
