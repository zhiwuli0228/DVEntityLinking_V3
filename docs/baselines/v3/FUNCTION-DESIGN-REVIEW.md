# DVEntityLinking V3 功能设计评审记录

日期：2026-06-25

## 1 基本信息

| 项 | 内容 |
| --- | --- |
| review_type | Function design review |
| review_object | [SR.md](./SR.md) |
| reviewer | Codex |
| review_mode | Main-agent sealed/read-only review；未使用 no-context subagent |
| 未使用子代理原因 | 当前多代理工具要求用户明确授权子代理后才能 spawn；本轮用户要求继续推进但未显式要求子代理。 |
| expected_output | 独立功能设计评审记录 |
| initial_conclusion | Ready for disposition with P3 documentation finding |

## 2 Review Input Bundle

| 类别 | 文件 |
| --- | --- |
| review_object | [SR.md](./SR.md) |
| baseline_document | [IR.md](./IR.md) |
| baseline_document | [IR-SR-DECOMPOSITION.md](./IR-SR-DECOMPOSITION.md) |
| baseline_document | [REQUIREMENT-CLOSURE-VERIFICATION.md](./REQUIREMENT-CLOSURE-VERIFICATION.md) |
| baseline_document | [../../current/DATA_CONTRACT.md](../../current/DATA_CONTRACT.md) |
| baseline_document | [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) |
| baseline_document | [../../current/DECISIONS.md](../../current/DECISIONS.md) |

| 项 | 内容 |
| --- | --- |
| scope | 检查 V3 功能设计是否覆盖两层存储、Redis/Gauss Mock、NER pipeline、schema、接口、异常语义、回归和安全边界。 |
| out_of_scope | 不评审代码实现、完整测试用例、真实 Redis/Gauss 接入、真实 LLM live smoke 和 V2 before 证据问题。 |
| allowed_commands | `Get-Content`、`rg`、`python -m pytest`、`python -m compileall -q src scripts`、`git diff --check`。 |

## 3 Review Method

- 按功能设计评审视角只读检查 [SR.md](./SR.md) 与已闭环需求输入的一致性。
- 不修改评审对象，不写处置结论，不声明闭环。
- 对引用的当前态文档执行一致性检查，确认阶段状态是否会误导后续实现或验收。

## 4 Findings

### P0

无。

### P1

无。

### P2

无。

### P3

#### V3-SR-REVIEW-001 TEST_ACCEPTANCE 的 V3 阶段口径滞后

Issue -> [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) 的 V3 验收草案仍写明“当前主输出为 IR 和 IR-SR，尚未进入功能设计或实现”。

Current artifact behavior -> [SR.md](./SR.md) 已形成 V3 功能设计草稿，且 [../../current/DECISIONS.md](../../current/DECISIONS.md) D079、[../../PROJECT.md](../../PROJECT.md)、[../../README.md](../../README.md) 已记录 V3 SR 功能设计草稿存在并待独立评审。

Impact -> 这是低风险文档同步问题，但会让后续评审、实现或验收读者误以为 V3 仍停留在需求阶段。

Recommended correction -> 在功能设计评审处置中更新 [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) 的 V3 验收草案，明确当前主输出已包含 [SR.md](./SR.md)，状态为“功能设计草稿待独立评审、处置和闭环；尚未进入代码实现或专项验收命令阶段”。

## 5 Perspective Summary

| 视角 | 评审结果 |
| --- | --- |
| Module layering and dependency direction | [SR.md](./SR.md) 将 `EntityWordCache`、`StructuredEntityStore`、`EntityStorageRepository` 和 `NerPipeline` 分层，依赖方向清晰；`CatalogRepository` 保留 V1/V2 兼容边界。 |
| Interfaces, schemas, enums, and error objects | 覆盖 `StructuredEntityRecord`、`EntityWordRecord`、lookup result、startup report、NER stage/candidate schema、status 和 error code。 |
| Runtime flow and dependency handling | 定义先高斯 Mock 后 Redis Mock 的启动顺序、跨层校验、运行时 lookup 序列和 fail-closed/dependency_failed 语义。 |
| File paths, persistence, configuration, and secret handling | 指定 V3 Mock artifact 路径、单一 Web 入口 `scripts/run_web_demo.py`、`DVEL_STORAGE_MODE` 等配置，并约束不提交真实连接串或 token。 |
| Test mapping to requirements | 覆盖 storage contract、两层集成、NER pipeline、LLM optional fallback、V1/V2 回归和敏感扫描；V3 实现命令被明确为后续新增。 |

## 6 Verified Commands

本评审阶段已执行：

| 命令 | 结果 |
| --- | --- |
| `Get-Content` | 已读取 review object 和基线文档。 |
| `rg "尚未进入功能设计\|SR 功能设计\|FUNCTION-DESIGN\|功能设计"` | 发现 [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) 的 V3 验收草案存在阶段口径滞后。 |

完整自动化回归应在处置修订后重新执行。

## 7 Recommended Closure Actions

| Finding | 建议闭环动作 |
| --- | --- |
| V3-SR-REVIEW-001 | 接受并修订 [../../current/TEST_ACCEPTANCE.md](../../current/TEST_ACCEPTANCE.md) 的 V3 验收草案阶段描述；如需要，同步更新项目索引中的 V3 状态为“功能设计评审处置/闭环中”。 |

## 8 Disposition Readiness Conclusion

V3 SR 功能设计本体未发现 P0/P1/P2 阻塞项。评审结论为 ready for disposition with one P3 documentation finding。建议进入功能设计评审处置；处置和闭环验证完成前，不启动 V3 代码实现。
