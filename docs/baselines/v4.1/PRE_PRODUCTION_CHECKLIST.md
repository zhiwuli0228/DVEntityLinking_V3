# V4.1 预发布与切换清单

此清单将仓内已验证能力与需要授权的外部操作分开。V4 功能完整性不以未授权的生产切换为前提；但未满足外部项时不得将 V4.1 标为“生产已切换”。

## 已完成的仓内准备

- [x] 默认 module 不依赖历史运行资产的回归检查。
- [x] V4 公开 DTO/状态契约清单与兼容测试。
- [x] canonical entity 的 dry-run 校验、冲突拒绝和配置禁用检查。
- [x] V4/V4.1 全量自动化回归。

## Deferred 的生产切换项

- [x] V4 功能基线：`0054385c6526f142805fac9aa53b094abb03102a`，日期 2026-07-16；生产切换不在此基线结论内。
- [ ] 调用方盘点：列出宿主、owner、调用入口、流量级别和兼容验证结果。
- [ ] 数据授权：确认 canonical export 的权威来源、备份位置、发布权限和恢复责任人。
- [ ] 运行授权：确认 Entity Data IR 测试/生产环境、观测指标和回退路由权限。
- [ ] 历史资产 owner：为 `DEPRECATION_REGISTER.md` 的每个 `DEP-V4.1-*` 指定 owner、支持期限和删除批准人。

## 受控执行步骤

1. 对授权导出运行 dry-run：

   ```powershell
   python scripts\run_v41_migration_dry_run.py --input <canonical-export.json> --source-version <safe-version-id> --report outputs\logs\v41_migration_dry_run.json
   ```

2. 审核 report 的实体数、词条数、关系数和冲突数；保存备份与批准记录。
3. 由授权发布方将验证后的 bundle 发布至 Entity Data Service；记录输出 data version。
4. 使用 V4 场景对真实 Entity Data IR 做冒烟，验证 `MATCH_WORDS` 与 `BATCH_GET_ENTITIES` 的 data version 一致性。
5. 先镜像流量，再小范围灰度；观察链接状态分布、`dependency_failed` 比例、响应时间和差异数。
6. 触发阈值或安全问题时，仅切回已验证的 V4 应用/路由和对应数据版本；不得执行未经验证的反向迁移。

## 必须归档的证据

在 [TRACEABILITY.md](./TRACEABILITY.md) 增加 `MIG-V4.1-*` 与 `CUTOVER-V4.1-*`：输入/输出版本、dry-run 摘要、执行者、IR 冒烟、灰度指标、回退目标及批准人。不得记录凭据、IR URL 或完整原始 payload。
