# DVEntityLinking 使用说明

日期：2026-06-25

## 1. 环境准备

推荐运行环境：

- Python 3.12
- PowerShell 或 PyCharm
- 项目根目录：`D:\workspace\DVEntityLinking`

安装依赖：

```powershell
python -m pip install -e .
```

运行自动化测试：

```powershell
python -m pytest
```

## 2. PyCharm 直接启动当前 Web Demo

在 PyCharm 中创建 Python Run Configuration：

| 配置项 | 值 |
| --- | --- |
| Script path | `D:\workspace\DVEntityLinking\scripts\run_web_demo.py` |
| Working directory | `D:\workspace\DVEntityLinking` |
| Parameters | `--mode offline_demo --port 5015` |

启动后访问：

```text
http://127.0.0.1:5015/?query=Run%20Network%20quality%20monitoring%20for%20onlinecharging_docker.
```

Web demo 只维护 `scripts\run_web_demo.py` 一个入口。当前默认加载 V2 样例：`samples\real\v2_entity_examples.json` 和 `samples\real\v2_query_samples.json`；后续版本升级时修改该脚本默认 catalog 和 samples 即可。默认 `offline_demo` 不调用真实 LLM，只使用 confirmed samples 和 deterministic 规则。

`GET /` 由 React SPA 提供（`web/frontend/dist`）。首次运行或前端代码变更后需先构建：

```powershell
cd web/frontend
npm install
npm run build
```

`dist/` 不入库；缺失时 `GET /` 返回 503 并提示先 `npm run build`。旧版 SSR 页面保留在 `GET /classic`，供 acceptance smoke 使用。

## 2.1 前端开发模式（React SPA）

前端工程位于 `web/frontend`（Vite + React + TypeScript + Tailwind）。开发时两个终端：

```powershell
# 终端 1：Flask API
python scripts\run_web_demo.py --mode offline_demo --port 5015
# 终端 2：Vite dev server（/api 代理到 5015）
cd web/frontend
npm run dev
```

打开 `http://127.0.0.1:5173`。改动前端代码由 Vite 热更新，无需重启 Flask。前端单测：

```powershell
cd web/frontend
npm run test      # vitest
npm run build     # 产物到 web/frontend/dist
```

视觉证据（before/after 截图）由 dev-only 脚本生成，需先安装 playwright：

```powershell
pip install -r scripts\requirements-dev.txt
python -m playwright install chromium   # 或直接用系统 Chrome/Edge
python scripts\run_web_demo.py --mode offline_demo --port 5015   # 另起终端
python scripts\capture_screenshots.py --url http://127.0.0.1:5015 --label after
```

## 3. PyCharm 直接运行当前验收 Smoke

在 PyCharm 中创建 Python Run Configuration：

| 配置项 | 值 |
| --- | --- |
| Script path | `D:\workspace\DVEntityLinking\scripts\run_v2_acceptance_smoke.py` |
| Working directory | `D:\workspace\DVEntityLinking` |
| Parameters | `--mode offline_demo` |

命令行等价方式：

```powershell
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
```

脚本会输出 JSON 摘要，`ok=true` 表示默认离线验收 smoke 通过。

## 4. 查看日志

运行脚本都会写日志到：

```text
outputs/logs/
```

日志文件名示例：

- `web-demo-YYYYMMDD-HHMMSS.log`
- `v2-acceptance-smoke-YYYYMMDD-HHMMSS.log`

`outputs/` 已被 `.gitignore` 忽略，日志不会进入提交。

## 5. 可选真实 LLM 模式

真实 LLM 模式使用本地 ignored 配置：

```text
config/llm.local.json
```

启动 Web demo：

```powershell
python scripts\run_web_demo.py --mode llm_enabled_demo --llm-config config\llm.local.json --port 5015
```

运行验收 smoke：

```powershell
python scripts\run_v2_acceptance_smoke.py --mode llm_enabled_demo --llm-config config\llm.local.json
```

配置要求：

- `config/llm.local.json` 不提交 git。
- API key 推荐通过环境变量提供，例如 `DVEL_LLM_API_KEY`。
- 不记录 base URL、API key、Authorization header、完整请求或完整响应。

## 6. V1 Alarm 样例与评测

V1 已关闭；如需回看 V1 alarm-only Web 样例，仍使用同一个 Web 入口并显式加载 V1 样例：

```powershell
python scripts\run_web_demo.py --catalog samples\real\entity_examples.json --samples samples\real\query_samples.json --mode offline_demo --port 5015
```

运行 V1 acceptance smoke：

```powershell
python scripts\run_v1_acceptance_smoke.py --mode offline_demo
```

运行 V1 启动样例评测：

```powershell
python scripts\run_v1_evaluation.py
```

评测通过条件：16 条 Query 全部 pass，`no_match` 和 `not_required` 零误报，`precision=1.0`，`recall=1.0`。

V1 Web 页面默认展示运行状态、LLM 配置、实体链接结果、Mention 简要信息、样例实体目录、候选实体、实体详情和相似实体；完整 JSON 在“调试详情”中折叠展示。点击“查看全部样例实体”可展开当前加载 catalog 的所有实体，点击实体 ID 可查看字段名化的实体详情。

页面上的 LLM 配置是进程内配置，不写入 `config/llm.local.json`。保存后选择 `llm_enabled_demo` 再执行 Link，即可走真实 LLM nominal path；API key 只进入当前 Python 进程环境变量，不在页面状态、日志或提交文件中回显。

## 7. V2 多类型样例与评测

V2 是当前 Web demo 默认版本，启动时无需再传 catalog 和 samples：

```powershell
python scripts\run_web_demo.py --mode offline_demo --port 5015
```

在 PyCharm 中创建 Python Run Configuration：

| 配置项 | 值 |
| --- | --- |
| Script path | `D:\workspace\DVEntityLinking\scripts\run_web_demo.py` |
| Working directory | `D:\workspace\DVEntityLinking` |
| Parameters | `--mode offline_demo --port 5015` |

启动后访问：

```text
http://127.0.0.1:5015/?query=Run%20Network%20quality%20monitoring%20for%20onlinecharging_docker.
```

运行 V2 acceptance smoke：

```powershell
python scripts\run_v2_acceptance_smoke.py --mode offline_demo
```

运行 V2 启动样例评测：

```powershell
python scripts\run_v2_evaluation.py
```

评测通过条件：12 条 Query 全部 pass，`negative_false_positive=0`，`precision=1.0`，`recall=1.0`，并输出 `type_metrics`。

## 8. V3 两层存储 Mock 与 NER 评测

V3 初始实现显式启用 Redis/Gauss Mock 两层存储：

```powershell
python scripts\run_web_demo.py --storage-mode v3_mock --mode offline_demo --port 5015
```

运行 V3 acceptance smoke：

```powershell
python scripts\run_v3_acceptance_smoke.py
```

运行 V3 NER golden cases 评测：

```powershell
python scripts\run_v3_evaluation.py
```

V3 当前默认使用：

- `samples\real\v3_gauss_entities.json`
- `samples\real\v3_redis_entity_words.json`
- `samples\real\v3_ner_golden_cases.json`

评测通过条件：6 条 golden Query 全部 pass，`negative_false_positive=0`，`precision=1.0`，`recall=1.0`；`not_required` 不访问 storage，Redis/Gauss 冲突或 schema 错误 fail-closed。

## 9. 常用测试 Query

| 场景 | Query |
| --- | --- |
| 别名 + KPI | `RAN-A1 的 ASR 最近如何` |
| 多实体 | `DV RAN Site Alpha 的链路断告警和接入成功率一起看` |
| 歧义 | `CP01 是什么告警` |
| 无匹配 | `查询不存在的 Gamma 虚拟设备` |
| 空输入 | 空字符串或空格 |
| V1 告警精确匹配 | `Check ALM-51020 impact.` |
| V1 告警歧义 | `What should I do if certificate is about to expire?` |
| V1 短 ID 子串保护 | `What is alarm 51?` |
| V1 无需链接 | `Open the operations dashboard.` |
| V2 KPI + 网元类型 | `Run Network quality monitoring for onlinecharging_docker.` |
| V2 alarm + KPI | `Check ALM-51020 and CPU Usage.` |
| V2 partial | `Show CPU Usage for CloudHost-VM-1-1-000000.` |
| V3 Redis/Gauss linked | `Check ALM-51020 and CPU Usage.` |
| V3 partial | `Show CPU Usage and CloudHost-VM-1-1-000000.` |
| V3 not required | `Open the operations dashboard.` |

## 10. API 示例

状态：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5015/api/status"
```

实体链接：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:5015/api/link" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"RAN-A1 的 ASR 最近如何","mode":"offline_demo","allow_fallback":true}'
```

Top-K 检索：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:5015/api/retrieve" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"entity_id":"NE-DV-RAN-001","k":5}'
```

前端运行时 LLM 配置：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:5015/api/llm/config" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"enabled":true,"model":"qwen3.6-27b","base_url":"https://example/v1","api_key":"local-key","timeout_seconds":20}'
```
