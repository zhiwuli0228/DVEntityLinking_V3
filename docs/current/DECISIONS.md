# 当前决策台账

最后更新：2026-06-26

本文档集中保存影响范围、方向、真实 DV 内容、LLM 策略、验收语义和文档治理的用户决策。历史确认 JSON 和分散确认文件原则上合并到本台账；当前版本仍作为评审输入或用户签署证据引用的确认文件，可保留到对应评审、处置和闭环完成。

## 已确认决策

| ID | 日期 | 决策 |
| --- | --- | --- |
| D001 | 2026-05-25 | 项目目标为构建 DV 实体链接 demo，支撑运维 Copilot 和故障 Agent 的实体相关任务。 |
| D002 | 2026-05-25 | 使用 Python 3.12；考虑 Qwen3.6-27B，通过 OpenAI-compatible API 接入。 |
| D003 | 2026-05-25 | 涉及真实 DV 实体、字段、接口、数据样例、能力边界和 Mock 方式时，必须先确认。 |
| D004 | 2026-05-25 | V0 首批实体类型覆盖网络资源/网元、告警/事件、KPI/性能指标、拓扑/关系、知识/Runbook/案例。 |
| D005 | 2026-05-25 | V0 demo 形态采用轻量 Web UI，同时保留 JSON API 和自动化 smoke。 |
| D006 | 2026-05-25 | V0 baseline 依赖 L0 抽象合成 Mock；真实配置和完整日志不入库。 |
| D007 | 2026-05-26 | V0 验收反馈为“整体基本符合预期”；补齐 PyCharm 可直接启动脚本和使用说明后，用户确认“认可”。 |
| D008 | 2026-05-26 | V0 accepted and closed。 |
| D009 | 2026-05-31 | V1 仅考虑 `alarm` 一种实体类型，且为告警知识实体，不建模告警实例事件。 |
| D010 | 2026-05-31 | V1 使用 9 个 `alarm` 实体和 16 条 Query 作为项目样例，覆盖 linked、ambiguous、no_match 和 not_required。 |
| D011 | 2026-05-31 | V1 每个 Query 最多一个实体词，但必须考虑一个实体词对应多个实体的歧义场景。 |
| D012 | 2026-05-31 | V1 检索策略采用 Python 内存索引优先，不引入三方检索组件；SQLite FTS5 仅作为后续可选路线。 |
| D013 | 2026-05-31 | V1 准确率和召回率同等重要；验收必须充分覆盖无法匹配或不需要匹配场景。 |
| D014 | 2026-06-01 | IR 阶段必须完成需求分解，形成可指导功能设计的 SR 输入；IR 独立评审必须从功能设计视角检查 SR 拆分合理性。 |
| D015 | 2026-06-01 | V1 Web 默认视图需要减少调试字段，突出运行状态、实体链接结果、候选实体、实体详情、相似实体、实体目录查看和 mention 简要信息。 |
| D016 | 2026-06-01 | `samples/real` 样例字段保持实体链接最小必要集合，不再保留 `data_layer`、`can_commit`、`sensitive_level` 等非核心字段。 |
| D017 | 2026-06-01 | V1 用户确认“V1验收完成”，V1 accepted and closed。 |
| D018 | 2026-06-01 | 文档治理采用精简结构；IR、SR 主输出件按版本保留，其他过程文档合并或清理。 |
| D019 | 2026-06-01 | V2 正式启动需求分析；V2 功能设计和代码实现需等待 IR 独立评审、处置和闭环完成。 |
| D020 | 2026-06-01 | V2 实体结构暂不升级；任何新增字段、关系、类型专属 schema 或结构改动必须先与用户确认。 |
| D021 | 2026-06-01 | V2 新增实体范围拆为 `ne_type`、`ne_name`、`kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`；`ne_type` 可预置，`ne_name` 来源为运行时接口 Mock，KPI 来源包含配置预置、DVKnowledge 挖掘和运行时接口 Mock。 |
| D022 | 2026-06-01 | V2 数据预处理作为大模块统一管控预置数据、DVKnowledge KPI/网元类型挖掘、样例规范化、显式别名标注、去重和校验；运行时接口 Mock 独立成 SR，便于未来被真实 DV 接口整体替换。 |
| D023 | 2026-06-01 | V2 NER 采用分层分类思路，重点验证 LLM-based 抽取、分类、解释和 rerank；默认自动化仍保留离线回归和降级边界。 |
| D024 | 2026-06-01 | V2 前端采用方案 C：运维工作台式演示 + LLM 交互式高亮/解释；前端只服务项目演示，不做过度前端产品化。 |
| D025 | 2026-06-01 | V2 KPI 类实体不再笼统使用 `kpi_metric`，需求层拆为 `kpi_task_name`、`kpi_meas_objects`、`kpi_meas_type_key`；`kpi_meas_objects` 往往是实例化实体，若暂时挖不出来可以先忽略。 |
| D026 | 2026-06-01 | V2 网元相关实体拆为可预置的 `ne_type` 和运行时实例化的 `ne_name`；`ne_type` 可从 DVKnowledge 挖掘，`ne_name` 通过运行时接口 Mock 获取。 |
| D027 | 2026-06-01 | V2 新增 KPI/网元类实体的 `alias` 默认都为空；别名必须特殊标注并经确认，不得由预处理自动乱生成。 |
| D028 | 2026-06-01 | 用户确认 V2 启动样例：保留全部 `kpi_meas_type_key`、全部 `ne_type` 和全部 `ne_name`；`kpi_meas_objects` 本轮先忽略；`kpi_task_name` 在原候选基础上增加一个不同类型任务名；V2 必须支持多 mention Query，补充 Query 全部使用英文。 |
| D029 | 2026-06-01 | V2 IR 独立评审、处置和 no-context/sealed 闭环验证已完成，结论为 closed with recorded residual risk；可进入 V2 功能设计，残余风险为跨类型歧义、LLM 降级、多 mention precision/recall 公式需在功能设计和测试设计中固化。 |
| D030 | 2026-06-01 | V2 SR 功能设计初稿已形成；V2 代码实现需等待 SR 功能设计独立评审、处置和闭环完成。 |
| D031 | 2026-06-01 | V2 SR 功能设计独立评审已完成，结论为 ready for disposition；评审发现全部接受并进入处置，P1 聚焦多 mention 评测公式、LLM fallback 状态机、跨类型歧义判定和统一状态/错误枚举。 |
| D032 | 2026-06-01 | V2 SR 功能设计评审处置修订已完成；已补充统一状态/错误枚举、LLM fallback 状态机、跨类型歧义决策树、V2 评测公式、runtime mock schema、安全投影和补充测试映射，待独立闭环验证。 |
| D033 | 2026-06-01 | V2 SR 功能设计评审闭环验证已完成，结论为 closed；P1/P2/P3 均已关闭，可进入 V2 代码实现阶段。 |
| D034 | 2026-06-01 | V2 初始代码实现已完成本地验证；覆盖 V2 entity/query 样例加载、多 mention 链接、`partial` 聚合、V2 evaluation 和 V2 acceptance smoke，下一步进入独立实现评审。 |
| D035 | 2026-06-01 | V2 初始代码实现独立评审处置已完成；P1 全部接受并修复，P2 跨类型同名歧义作为初始实现残余风险记录，runtime mock adapter 仍保留为后续扩展项。 |
| D036 | 2026-06-01 | V2 初始代码实现评审 no-context/sealed 闭环验证已完成，结论为 closed with residual risk；P1 全部关闭，P2 跨类型同名歧义作为已记录残余风险非阻塞，可进入 V2 测试设计或后续实现扩展。 |
| D037 | 2026-06-01 | V2 测试设计与测试开发已完成，新增测试设计记录、type-level evaluation metrics、V2 dataset metadata fail-closed 测试和 smoke log artifact 检查；当前状态为待独立测试评审。 |
| D038 | 2026-06-01 | V2 独立测试评审已完成且无 P0/P1；P2/P3 均已接受并完成处置，当前待 no-context/sealed 独立闭环验证。 |
| D039 | 2026-06-01 | V2 测试评审处置 no-context/sealed 闭环验证已完成，结论为 closed with recorded residual risk；P2/P3 均已关闭，可进入文档卫生收口、demo 验收或下一轮 V2 扩展。 |
| D040 | 2026-06-01 | V2 进入验收阶段；验收候选记录已生成，默认离线验收通过，当前待用户确认是否 accepted and closed、accepted with recorded residual risk and closed，或进入下一轮 V2 扩展。 |
| D041 | 2026-06-01 | Web demo 启动脚本简化为只维护 `scripts\run_web_demo.py` 一个入口；当前版本默认加载 V2 样例，历史版本如需回看通过显式 `--catalog` 和 `--samples` 参数加载。 |
| D042 | 2026-06-01 | 用户确认改进 DV 流程：保留用户确认需求追踪矩阵、静默降级禁止、评审输入包增强、验收候选前反向核查和残余风险分级限制；排除前述第 1 项和第 3 项。 |
| D043 | 2026-06-01 | V2 验收候选撤回并标记为 blocked：V2 中已确认的重要前端改造要求未落实，原实现/测试/评审/验收将其降级为 Web/API projection，需回到实现、测试和独立评审后才能重新进入验收。 |
| D044 | 2026-06-01 | V2 前端改造补救重新进入 DV 流程，启动时完成需求分析草稿 [IR-FRONTEND-REMEDIATION.md](../baselines/v2/IR-FRONTEND-REMEDIATION.md)，当时要求必须进行独立需求评审、处置和闭环，不得越过需求门禁；后续状态见 D045、D046 和 D047。 |
| D045 | 2026-06-01 | V2 前端补救 no-context 独立需求评审已完成，4 个 P1 和 3 个 P2 全部接受并完成需求评审处置修订；当前待独立闭环验证，闭环未通过前不能进入功能设计或实现。 |
| D046 | 2026-06-02 | V2 前端补救需求评审闭环验证已通过，4 个 P1 和 3 个 P2 均 Closed，文档卫生 Passed；允许进入 V2 前端补救功能设计。 |
| D047 | 2026-06-02 | V2 前端补救功能设计草稿 [SR-FRONTEND-REMEDIATION.md](../baselines/v2/SR-FRONTEND-REMEDIATION.md) 已形成，当前待独立功能设计评审；评审、处置和闭环未完成前不得进入实现。 |
| D048 | 2026-06-02 | V2 前端补救独立功能设计评审已完成，4 个 P1 和 1 个 P2 全部接受并完成设计处置；当前待独立闭环验证，闭环未通过前不得进入实现。 |
| D049 | 2026-06-02 | V2 前端补救功能设计评审闭环验证已通过，结论为 closed with recorded residual risk；允许进入 V2 前端补救代码实现。V2 整体仍保持 blocked，不能验收关闭。 |
| D050 | 2026-06-02 | V2 前端补救代码实现已完成，记录见 [FRONTEND-REMEDIATION-IMPLEMENTATION.md](../baselines/v2/FRONTEND-REMEDIATION-IMPLEMENTATION.md)；已通过 V2 smoke、追踪矩阵、focused tests 和 Chrome CDP browser-equivalent 证据，覆盖第二个 mention `CPU Usage`、`DV-KPI-MTK-001` 候选/实体详情、candidate 级安全解释、卡片文字可读和窄屏无横向溢出。当前待独立实现评审、处置和闭环，V2 仍保持 blocked，不能直接验收。 |
| D051 | 2026-06-02 | V2 前端补救独立实现评审已完成，发现 1 个 P1 和 1 个 P2；均已接受并完成处置。P1 修复为 `AC-V2-FE-004` 单独进入 traceability artifact；P2 修复为 smoke 默认校验 browser-equivalent evidence 的 required checks、截图存在性和 freshness。当前待独立闭环验证，V2 仍保持 blocked，不能直接验收。 |
| D052 | 2026-06-02 | V2 前端补救实现评审闭环验证已通过，结论为 closed with recorded residual risk；FE-IMPL-001/P1 已 Closed，FE-IMPL-002/P2 已 Closed with recorded residual risk。允许进入测试设计/测试开发和独立测试评审门禁；V2 仍保持 blocked，不能直接验收。 |
| D053 | 2026-06-02 | V2 前端补救测试设计与测试开发已完成，记录见 [FRONTEND-REMEDIATION-TEST-DESIGN.md](../baselines/v2/FRONTEND-REMEDIATION-TEST-DESIGN.md)；覆盖 workbench、多 mention、第二个 mention 到 `DV-KPI-MTK-001` 联动、LLM 安全解释、负例、`attributes_safe[]`、traceability、browser evidence freshness 和单一 web demo 入口。当时待独立测试评审、处置和闭环；后续状态见 D054。 |
| D054 | 2026-06-02 | V2 前端补救独立测试评审已完成，发现 1 个 P1；该 P1 已接受并完成处置，新增 `/api/entities/<id>` unsafe attributes 负例，覆盖 forbidden key 和 token-like value 均不进入 `attributes_safe[]`。当前待独立闭环验证，V2 仍保持 blocked，不能直接验收。 |
| D055 | 2026-06-02 | V2 前端补救测试评审闭环验证已通过，FE-TEST-001/P1 已 Closed，无阻塞性残余风险。当前可进入验收候选前反向核查；反向核查未完成前，V2 仍保持 blocked，不能直接验收。 |
| D056 | 2026-06-02 | V2 前端补救验收候选前反向核查已完成本地修复和证据刷新；初次核查发现 D041 未进入 traceability artifact，已修复为 `traceability_decision_d041_status=implemented` 并补自动化断言。当时待独立核验；后续状态见 D057。 |
| D057 | 2026-06-02 | V2 前端补救验收候选前反向核查独立核验已通过，D024、D028、D041、D042、D043、D003 均进入 traceability artifact，AC-V2-FE-001 至 AC-V2-FE-009 均为 implemented/pass，无 downgraded/not_implemented/needs_user_confirmation。当时补救后验收候选已准备，但后续用户复核视觉风格不足；最新状态见 D058。 |
| D058 | 2026-06-02 | 用户复核确认上一轮 V2 前端补救虽完成多 mention、候选联动、LLM 安全解释和安全投影，但视觉风格仍接近基础表单和白色卡片分区，未明显体现 SigNoz、OpenGenerativeUI、Tambo 等参考原型吸收。用户确认重新进入 V2 前端视觉风格补救 DV 流程；当前需求草稿见 [IR-FRONTEND-VISUAL-REMEDIATION.md](../baselines/v2/IR-FRONTEND-VISUAL-REMEDIATION.md)，未完成独立需求评审、处置和闭环前，不得进入功能设计、实现、验收候选或 accepted/closed。 |
| D059 | 2026-06-02 | V2 前端视觉风格补救 no-context 独立需求评审已完成，结论为 ready for disposition；无 P0，2 个 P1、2 个 P2、1 个 P3 均已接受并完成需求评审处置修订。处置补齐 D003 真实 DV 内容/Mock 边界、visual traceability artifact schema、before/after canonical scenario、首屏结构边界和参考源 capture metadata。当前待独立闭环验证，闭环前不得进入功能设计或实现。 |
| D060 | 2026-06-02 | V2 前端视觉风格补救需求评审闭环验证已通过，结论为 closed with recorded residual risk；FE-VIS-REQ-001 至 FE-VIS-REQ-005 均 Closed。残余风险为视觉最终接受仍需人工判断，已通过 visual traceability schema、before/after canonical screenshots 和用户视觉接受门禁管理。当前允许进入功能设计；进入代码实现、验收候选或 accepted/closed 仍需后续 DV 门禁。 |
| D061 | 2026-06-02 | V2 前端视觉风格补救功能设计草稿 [SR-FRONTEND-VISUAL-REMEDIATION.md](../baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md) 已形成；设计明确 workbench shell、原型吸收映射、桌面/窄屏布局、selection state、LLM explanation component、visual traceability artifact schema、before/after canonical scenario 和 D003 内容边界。当前待独立功能设计评审、处置和闭环验证；闭环前不得进入代码实现、验收候选或 accepted/closed。 |
| D062 | 2026-06-02 | V2 前端视觉风格补救功能设计 no-context 独立评审已完成，结论为 ready for disposition；无 P0，3 个 P1、3 个 P2 均已接受并完成处置。处置补齐 `mention_results[]` API-to-UI adapter、visual traceability AC 阻塞字段、D003 content inventory、新旧 artifact 路径边界、窄屏文本重叠检查和 `/api/entities` 现有 `status=no_match` 错误语义。当前待独立闭环验证；闭环前不得进入代码实现、验收候选或 accepted/closed。 |
| D063 | 2026-06-02 | V2 前端视觉风格补救功能设计评审闭环验证已通过，结论为 closed with recorded residual risk；FE-VIS-SR-001 至 FE-VIS-SR-006 均 Closed。功能设计 [SR-FRONTEND-VISUAL-REMEDIATION.md](../baselines/v2/SR-FRONTEND-VISUAL-REMEDIATION.md) 已升至 `V2-FE-VIS-SR.2-closed`，可作为代码实现输入。V2 整体仍 blocked，进入验收候选或 accepted/closed 仍需代码实现、实现评审闭环、测试设计/开发、测试评审闭环、visual traceability evidence 和用户视觉接受门禁。 |
| D064 | 2026-06-02 | V2 前端视觉风格补救代码实现已完成，记录见 [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION.md)；实现将页面重构为 `visual-workbench-shell`、`status-band`、`query-command-zone`、`result-stream`、`entity-detail-zone`、`llm-explanation-component`、`catalog-filter-zone`，并生成 `outputs/logs/v2_frontend_browser_evidence.json`、`outputs/logs/v2_frontend_visual_traceability_check.json`。浏览器证据 `ok=true`，但 visual traceability 明确 `manual_user_acceptance_status=pending`，`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 因用户视觉接受和 before/after 对比未完成仍阻塞验收关闭。当前待独立实现评审、处置和闭环验证；V2 仍 blocked，不能 accepted/closed。 |
| D065 | 2026-06-02 | V2 前端视觉风格补救独立实现评审已完成，记录见 [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW.md)；评审发现 1 个 P1 和 2 个 P2，均已接受并完成处置，处置记录见 [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-REVIEW-DISPOSITION.md)。P1 修复 visual traceability 最小 schema 和 D003 inventory 字段，P2 修复单 Web 入口硬编码检查和截图非图片字节弱校验；`python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` 已通过，`browser_screenshot_images_valid=true`。当前待独立闭环验证；`manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 仍阻塞验收关闭。 |
| D066 | 2026-06-02 | V2 前端视觉风格补救实现评审 no-context 独立闭环验证已通过，记录见 [FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-IMPLEMENTATION-CLOSURE-VERIFICATION.md)；FE-VIS-IMPL-001、FE-VIS-IMPL-002、FE-VIS-IMPL-003 均 Closed，结论为 implementation review findings closed with recorded residual acceptance gates。当前可进入测试设计/开发；`manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 仍阻塞验收关闭，V2 不能 accepted/closed。 |
| D067 | 2026-06-04 | V2 前端视觉风格补救测试设计/开发已完成，记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-DESIGN.md)；覆盖 `TC-V2-FE-VIS-001` 至 `TC-V2-FE-VIS-009`、原型吸收矩阵、桌面/窄屏 browser evidence、`CPU Usage` 到 `DV-KPI-MTK-001` 联动、LLM explanation component、D003 content inventory、visual traceability blocker、before/after 门禁和单一 `scripts\run_web_demo.py` 入口。已新增伪图片截图失败回归和版本专用 Web demo 入口拒绝回归。当前待独立测试评审、处置和闭环验证；`manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 仍阻塞验收关闭，V2 不能 accepted/closed。 |
| D068 | 2026-06-04 | V2 前端视觉风格补救 no-context 独立测试评审已完成，记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW.md)；评审发现 FE-VIS-TEST-001/P1、FE-VIS-TEST-002/P1、FE-VIS-TEST-003/P2，均已接受并完成处置，处置记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-REVIEW-DISPOSITION.md)。处置补强完整 PNG/JPEG 图片结构校验、D003 runtime scan 和 forbidden downgrade blocker；`tests\test_demo_scripts.py` 通过，`12 passed`；`python scripts\run_v2_acceptance_smoke.py --log-dir outputs\logs` 通过，`d003_scan_ok=true`、`browser_screenshot_images_valid=true`。当前待独立闭环验证；`manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 仍阻塞验收关闭，V2 不能 accepted/closed。 |
| D069 | 2026-06-04 | V2 前端视觉风格补救测试评审 no-context 独立闭环验证已通过，记录见 [FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-TEST-CLOSURE-VERIFICATION.md)；FE-VIS-TEST-001、FE-VIS-TEST-002、FE-VIS-TEST-003 均 Closed，结论为 test review findings closed with recorded residual acceptance gates。no-context verifier 复跑 `tests\test_demo_scripts.py` 为 `12 passed`、`tests\test_demo_scripts.py tests\test_contract_artifacts.py` 为 `17 passed`、全量回归为 `80 passed`；当前可进入 before/after 对比准备和用户视觉接受前置步骤。`manual_user_acceptance_status=pending`、`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 仍阻塞验收关闭，V2 不能 accepted/closed。 |
| D070 | 2026-06-04 | V2 前端视觉风格补救验收前置核查已生成，记录见 [FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md](../baselines/v2/FRONTEND-VISUAL-REMEDIATION-ACCEPTANCE-PRECHECK.md)。本次仅使用单一入口 `scripts/run_web_demo.py` 启动 `offline_demo`，按 canonical query `Check ALM-51020 and CPU Usage.` 补采 after 桌面截图 `outputs/logs/v2_visual_acceptance_after_desktop_1366x768.png` 和窄屏截图 `outputs/logs/v2_visual_acceptance_after_narrow_390x844.png`；浏览器检查存在 workbench/status/query zones，窄屏 `hasHorizontalOverflow=false`。当前未发现旧版同场景 before 截图，且用户视觉接受仍未确认；`AC-V2-FE-VIS-007` 和 `AC-V2-FE-VIS-008` 继续 blocking，V2 不能 accepted/closed。 |
| D071 | 2026-06-04 | 用户确认“当前 after 视觉可以 accepted”。该确认仅关闭当前 after 视觉接受门禁：visual traceability 顶层 `manual_user_acceptance_status=accepted`，`AC-V2-FE-VIS-007` 可按 after 截图、browser evidence、visual traceability artifact 和用户确认关闭。该确认不替代旧版同场景 before 截图或替代 before 证据口径；`AC-V2-FE-VIS-008` 继续 blocking，V2 仍不能 accepted/closed。 |
| D072 | 2026-06-24 | 用户确认搁置 V2 遗留问题，进入 V3。V2 `AC-V2-FE-VIS-008` before 同场景截图或替代 before 证据口径仍未关闭，但不作为 V3 启动阻塞；V2 仍不得标记为 accepted/closed。 |
| D073 | 2026-06-24 | V3 重点之一为两层存储：实体词到实体 ID 的 KV 对走 Redis 缓存，Redis 接口使用 Mock；结构化实体数据存高斯数据库，高斯接口使用 Mock，并支持按实体 ID 查询。 |
| D074 | 2026-06-24 | V3 Redis Mock 当前硬约束为 key 是实体词，value 是实体 ID。若出现同一实体词对应多个实体、别名扩展或自动生成实体词 key，必须在功能设计前确认策略，不得静默改变为多值结构或自动别名规则。 |
| D075 | 2026-06-24 | V3 NER 部分需要详细设计，是本项目重中之重；必要时允许在需求和功能设计评审闭环后重构现有 NER、linker、catalog、service 和存储边界。 |
| D076 | 2026-06-24 | V3 启动时只进入需求分析草稿阶段，主输出为 [IR.md](../baselines/v3/IR.md) 和 [IR-SR-DECOMPOSITION.md](../baselines/v3/IR-SR-DECOMPOSITION.md)。功能设计、代码实现、测试设计和验收候选均需等待 V3 IR 独立评审、处置和闭环验证。 |
| D077 | 2026-06-24 | V3 GUI 决策确认已完成，原始记录为 [2026-06-24-dv-entity-linking-v3-decision-confirmation.json](../confirmations/2026-06-24-dv-entity-linking-v3-decision-confirmation.json)。确认结论：Redis value 保持单实体 ID，冲突数据加载 fail-closed 且不进入链接链路；Redis key 使用 `entity_name` + 经确认 `alias`，不自动生成别名；高斯结构化实体 V3 初始沿用最小字段 `entity_id`、`entity_type`、`entity_name`、`alias`、`desc`，类型专属字段后续单独确认；NER 允许内部 schema 扩展但外部 API 和样例提交字段受控；默认离线 deterministic 可回归，LLM 仅作为可选分类、解释和 rerank 增强；样例策略复用 V1/V2，并新增 Redis/Gauss Mock artifacts 和 NER golden cases，新增样例必须脱敏并遵守 D003。 |
| D078 | 2026-06-25 | V3 需求评审、评审处置和闭环验证已完成，记录见 [REQUIREMENT-REVIEW.md](../baselines/v3/REQUIREMENT-REVIEW.md)、[REQUIREMENT-REVIEW-DISPOSITION.md](../baselines/v3/REQUIREMENT-REVIEW-DISPOSITION.md) 和 [REQUIREMENT-CLOSURE-VERIFICATION.md](../baselines/v3/REQUIREMENT-CLOSURE-VERIFICATION.md)。评审无 P0/P1，P2/P3 均已关闭或以可接受残余风险关闭；V3 可进入功能设计阶段。代码实现仍需等待 V3 SR 功能设计评审、处置和闭环验证。 |
| D079 | 2026-06-25 | V3 SR 功能设计草稿已形成，记录见 [SR.md](../baselines/v3/SR.md)。设计覆盖两层存储接口、Redis/Gauss Mock artifact、cross-layer validation、NER pipeline 阶段、内部 schema、状态/错误语义、LLM 可选增强、V1/V2 回归和 V3 设计级测试映射。V3 代码实现不得在 SR 功能设计独立评审、处置和闭环验证完成前启动。 |
| D080 | 2026-06-25 | V3 SR 功能设计评审已完成，记录见 [FUNCTION-DESIGN-REVIEW.md](../baselines/v3/FUNCTION-DESIGN-REVIEW.md)。评审未发现 P0/P1/P2，仅发现 `TEST_ACCEPTANCE.md` V3 阶段口径滞后的 P3 文档同步项；该发现已接受并进入 [FUNCTION-DESIGN-REVIEW-DISPOSITION.md](../baselines/v3/FUNCTION-DESIGN-REVIEW-DISPOSITION.md) 处置。代码实现仍需等待功能设计评审闭环验证完成。 |
| D081 | 2026-06-25 | V3 SR 功能设计评审闭环验证已完成，记录见 [FUNCTION-DESIGN-CLOSURE-VERIFICATION.md](../baselines/v3/FUNCTION-DESIGN-CLOSURE-VERIFICATION.md)。V3-SR-REVIEW-001 已关闭，无 P0/P1/P2 阻塞；[SR.md](../baselines/v3/SR.md) 已升至 `V3-SR.2-closed`，可作为 V3 代码实现输入。 |
| D082 | 2026-06-25 | V3 初始代码实现已完成，记录见 [IMPLEMENTATION.md](../baselines/v3/IMPLEMENTATION.md)。实现包含 Redis/Gauss Mock 两层存储、`NerPipeline` 重构入口、V3 mock artifacts、golden cases、`run_v3_evaluation.py`、`run_v3_acceptance_smoke.py`、Web 单入口 `--storage-mode v3_mock` 和 focused tests；已通过 `python -m pytest` `88 passed`、V3 evaluation/smoke、compileall 和 `git diff --check`。当前待独立实现评审、处置和闭环验证；V3 仍不得进入验收候选或 accepted/closed。 |
| D083 | 2026-06-25 | V3 初始代码实现评审和处置已完成，记录见 [IMPLEMENTATION-REVIEW.md](../baselines/v3/IMPLEMENTATION-REVIEW.md) 和 [IMPLEMENTATION-REVIEW-DISPOSITION.md](../baselines/v3/IMPLEMENTATION-REVIEW-DISPOSITION.md)。评审发现 V3-IMPL-REVIEW-001/P2 和 V3-IMPL-REVIEW-002/P3，均已接受并修复：V3 `llm_enabled_demo` 不再在无 `llm` stage 时误报 `llm_used=true`，Redis Mock 已强校验 `metadata.key_scope`；新增 focused tests 后通过 `9 passed`、目标组合 `27 passed`、全量 `90 passed`。当前待独立闭环验证；V3 仍不得进入验收候选或 accepted/closed。 |
| D084 | 2026-06-25 | V3 初始代码实现评审闭环验证已完成，记录见 [IMPLEMENTATION-CLOSURE-VERIFICATION.md](../baselines/v3/IMPLEMENTATION-CLOSURE-VERIFICATION.md)。V3-IMPL-REVIEW-001/P2 和 V3-IMPL-REVIEW-002/P3 均 Closed，结论为 Closed with recorded residual future-work risks；当前可进入 V3 测试设计/开发。进入 V3 验收候选或 accepted/closed 前仍需完成测试设计/开发、测试评审、处置和闭环验证。 |
| D085 | 2026-06-25 | V3 测试设计与测试开发已完成，记录见 [TEST-DESIGN.md](../baselines/v3/TEST-DESIGN.md)。测试矩阵覆盖 Redis/Gauss Mock schema、duplicate key、dangling ID、key_scope fail-closed、NER linked/partial/no_match/not_required、Web/API storage projection、LLM usage 投影、V3 evaluation/smoke、文档治理和全量回归；已通过 focused `9 passed`、targeted `27 passed`、full `90 passed`、compileall、V3 evaluation/smoke 和 `git diff --check`。当前待独立测试评审、处置和闭环验证；V3 仍不得进入验收候选或 accepted/closed。 |
| D086 | 2026-06-25 | V3 测试评审和处置已完成，记录见 [TEST-REVIEW.md](../baselines/v3/TEST-REVIEW.md) 和 [TEST-REVIEW-DISPOSITION.md](../baselines/v3/TEST-REVIEW-DISPOSITION.md)。评审发现 V3-TEST-REVIEW-001/P1 和 V3-TEST-REVIEW-002/P2，均已接受并修复：新增 Gauss duplicate entity ID fail-closed、Gauss missing required field fail-closed 和 NER blank query invalid-input focused tests；[TEST-DESIGN.md](../baselines/v3/TEST-DESIGN.md) 已同步测试矩阵。处置后通过 focused `12 passed`、targeted `30 passed`、full `93 passed`、compileall、V3 evaluation/smoke 和 `git diff --check`。当前待独立闭环验证；V3 仍不得进入验收候选或 accepted/closed。 |
| D087 | 2026-06-25 | V3 测试评审闭环验证已完成，记录见 [TEST-CLOSURE-VERIFICATION.md](../baselines/v3/TEST-CLOSURE-VERIFICATION.md)。V3-TEST-REVIEW-001/P1 和 V3-TEST-REVIEW-002/P2 均 Closed，结论为 test review findings closed with recorded future-work risks；验证复跑 focused `12 passed`、targeted `30 passed`、full `93 passed`、compileall、V3 evaluation/smoke 和 `git diff --check`。当前可进入 V3 验收候选前置准备；正式进入 V3 验收候选或 accepted/closed 仍需后续验收记录和用户确认。 |
| D088 | 2026-06-26 | V3 验收候选前置核查和核验已完成，记录见 [ACCEPTANCE-PRECHECK.md](../baselines/v3/ACCEPTANCE-PRECHECK.md) 和 [ACCEPTANCE-PRECHECK-VERIFICATION.md](../baselines/v3/ACCEPTANCE-PRECHECK-VERIFICATION.md)。核查确认 D073/D074/D075/D077 已追踪到 artifacts、实现、测试和验收证据；V3 evaluation `total=6`、`pass=6`、`precision=1.0`、`recall=1.0`、`negative_false_positive=0`，V3 smoke `ok=true`、`linked_storage_redis_statuses=["hit","hit"]`。V2 smoke 当前因 V2 legacy visual `browser_evidence_fresh=false` 输出 `ok=false`，按 D072 作为 V2 遗留诊断项记录，不作为 V3 阻塞项。 |
| D089 | 2026-06-26 | V3 验收候选记录已准备，见 [../releases/V3.md](../releases/V3.md)。当前状态为 `Acceptance candidate prepared; pending user acceptance; not accepted/closed`；候选覆盖 Redis Mock、Gauss Mock、storage-backed NER pipeline、V3 mock artifacts、V3 golden cases、V1/V2 技术回归和默认离线 deterministic 验证。V3 accepted/closed 仍需用户后续确认。 |
| D090 | 2026-06-26 | 前端大整改：`GET /` 改由 React SPA 提供（`web/frontend`，Vite+React+TS+Tailwind），`scripts\run_web_demo.py` 仍为单入口托管 `dist`。后端仅 `src/dv_entity_linking/web.py` 的 `GET /`+`/assets` 路由调整，旧 SSR 保留在 `GET /classic` 供 acceptance smoke；V2 数据/算法/评测/样例和 V3 存储层不动。整改吸收 SigNoz（状态带密度）、doccano（Query 内 mention span 内联高亮）、CopilotKit（LLM 解释组件化）、Tremor（深色工作台 shell）原型原则。新增 `scripts/capture_screenshots.py`（playwright，dev-only）和 `scripts/requirements-dev.txt`。`tests/test_web.py` 删除 3 个 SSR HTML 断言、新增 SPA shell 断言。前端单测 `vitest` `3 passed`；全量 `pytest` `92 passed`；`compileall` 通过。 |
| D091 | 2026-06-26 | V2 `AC-V2-FE-VIS-008` before 同场景截图已补齐：整改前按 canonical scenario 采集 `outputs/logs/v2_frontend_before_desktop_1366x768.png` 和 `_narrow_390x844.png`，整改后采集 after 同场景截图；`scripts/run_v2_acceptance_smoke.py` 已接入 before 证据检测，真实运行 `visual_traceability_blocking_count=0`、`AC-V2-FE-VIS-008` 不再 blocking。`outputs/**` 不入库，截图作为本地证据保留。 |
| D092 | 2026-07-16 | V4.1 canonical entity dry-run 发现 `DV-ALM-002` 与 `DV-ALM-003` 的通用 confirmed alias 归一化冲突。用户确认按方案 1 处理：通用短语 `certificate is about to expire` 仅保留给 `DV-ALM-002`；从 `DV-ALM-003` 移除大小写等价的 alias，保留 `ALM-100003` 等带编号标识。该短语的历史结果由 ambiguous 调整为稳定链接 `DV-ALM-002`。 |
| D093 | 2026-07-16 | 用户确认 V4.1 的真实数据发布、Entity Data IR 冒烟、镜像/灰度与回退演练（OpenSpec 4.3）当前无条件执行，作为 deferred 发布遗留，不阻断 V4 功能与代码基线完整。历史 V1–V3 资产（OpenSpec 4.4）暂时预留作回归与审计，但必须持续禁止进入 V4/V4.1 默认运行链；V4 功能完整性记录据此生成。 |

## 仍需后续确认

| 方向 | 需确认内容 |
| --- | --- |
| V2 前端视觉风格补救验收前置核查 | after 视觉已由用户 accepted；before 同场景截图已补齐（D091），`AC-V2-FE-VIS-008` 不再 blocking。 |
| V2 前端视觉风格补救验收确认 | `AC-V2-FE-VIS-007`、`AC-V2-FE-VIS-008` 均已具备关闭口径（D090/D091）；V2 整体 accepted/closed 仍需用户确认。 |
| V2 跨类型同名歧义补强 | 当前实现闭环允许作为残余风险非阻塞；完整 V2 验收前需补充同 span 多类型候选保留样例与判定规则。 |
| 真实 LLM live smoke 常态化 | V3 已确认默认离线 deterministic、LLM 可选增强；未来若将真实 LLM live smoke 纳入默认或条件验收，仍需确认脱敏报告格式和稳定性门槛。 |
| V3 高斯类型专属字段扩展 | V3 初始已确认沿用最小字段；未来如新增类型专属字段、关系字段或展示字段，需另行确认。 |
| V3 真实 Redis/Gauss 适配器 | V3 初始仅做接口 Mock；未来若接入真实 Redis、GaussDB 或 DV 生产接口，需确认连接、认证、失败语义、脱敏和部署边界。 |
| V3 验收确认 | V3 验收候选已准备完成；仍需用户确认 accepted and closed、accepted with recorded residual risk and closed，或进入 V3 后续补强。 |
