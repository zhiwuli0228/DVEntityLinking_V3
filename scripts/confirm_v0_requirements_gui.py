from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "confirmations"
OUTPUT_JSON = OUTPUT_DIR / "2026-05-25-dv-entity-linking-v0-requirement-confirmation.json"
OUTPUT_MD = OUTPUT_DIR / "2026-05-25-dv-entity-linking-v0-requirement-confirmation.md"

PROJECT_NAME = "DVEntityLinking"


def _clean(value: str) -> str:
    value = value.strip()
    return value if value else "TBD"


def _entry(parent: ttk.Frame, row: int, label: str, default: str = "", width: int = 74) -> tk.StringVar:
    var = tk.StringVar(value=default)
    ttk.Label(parent, text=label, wraplength=300).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
    ttk.Entry(parent, textvariable=var, width=width).grid(row=row, column=1, sticky="ew", pady=5)
    return var


def _combo(parent: ttk.Frame, row: int, label: str, values: list[str], default: str | None = None) -> tk.StringVar:
    var = tk.StringVar(value=default or values[0])
    ttk.Label(parent, text=label, wraplength=300).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
    ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=52).grid(
        row=row, column=1, sticky="w", pady=5
    )
    return var


def _text(parent: ttk.Frame, row: int, label: str, default: str = "", height: int = 4) -> tk.Text:
    ttk.Label(parent, text=label, wraplength=300).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
    widget = tk.Text(parent, height=height, wrap=tk.WORD)
    widget.insert("1.0", default)
    widget.grid(row=row, column=1, sticky="nsew", pady=5)
    return widget


def _tab(notebook: ttk.Notebook, title: str) -> ttk.Frame:
    frame = ttk.Frame(notebook, padding=14)
    frame.columnconfigure(1, weight=1)
    notebook.add(frame, text=title)
    return frame


def _check_group(parent: ttk.Frame, row: int, label: str, options: list[tuple[str, bool]]) -> dict[str, tk.BooleanVar]:
    ttk.Label(parent, text=label, wraplength=300).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
    box = ttk.Frame(parent)
    box.grid(row=row, column=1, sticky="ew", pady=5)
    values: dict[str, tk.BooleanVar] = {}
    for index, (text, default) in enumerate(options):
        var = tk.BooleanVar(value=default)
        ttk.Checkbutton(box, text=text, variable=var).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 24), pady=2)
        values[text] = var
    return values


def _selected(values: dict[str, tk.BooleanVar]) -> list[str]:
    return [name for name, var in values.items() if var.get()]


def _text_value(widget: tk.Text) -> str:
    return _clean(widget.get("1.0", tk.END))


def _write_outputs(payload: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = [
        "# DVEntityLinking V0 需求分析用户确认记录",
        "",
        f"确认时间：{payload['confirmed_at']}",
        f"项目：`{payload['project_name']}`",
        "",
        "## 1. 范围和目标",
        "",
    ]
    for key, value in payload["scope"].items():
        lines.append(f"- {key}：{value}")

    lines.extend(["", "## 2. 首批实体和场景", ""])
    lines.append("- 首批实体类型：" + "、".join(payload["entity_types"]))
    lines.append("- Query 场景：" + "、".join(payload["query_scenarios"]))
    lines.append("- 相似度检索语义：" + "、".join(payload["retrieval_semantics"]))
    lines.append(f"- 其他实体或场景补充：{payload['entity_notes']}")

    lines.extend(["", "## 3. Mock 和真实 DV 边界", ""])
    for key, value in payload["mock_strategy"].items():
        lines.append(f"- {key}：{value}")

    lines.extend(["", "## 4. LLM 和外部依赖", ""])
    for key, value in payload["llm"].items():
        lines.append(f"- {key}：{value}")

    lines.extend(["", "## 5. 输出契约和验收", ""])
    lines.append("- 实体链接输出字段：" + "、".join(payload["output_contract"]))
    lines.append("- V0 验收项：" + "、".join(payload["acceptance_items"]))
    lines.append(f"- 验收补充：{payload['acceptance_notes']}")

    lines.extend(["", "## 6. 安全和日志", ""])
    for key, value in payload["security"].items():
        lines.append(f"- {key}：{value}")

    lines.extend(["", "## 7. 决策签收", ""])
    for key, value in payload["signoff"].items():
        lines.append(f"- {key}：{value}")

    lines.append("")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def build_gui() -> None:
    root = tk.Tk()
    root.title("DVEntityLinking V0 需求分析确认")
    root.geometry("1220x860")
    root.minsize(1040, 720)

    style = ttk.Style()
    style.configure("Title.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
    style.configure("Hint.TLabel", foreground="#555")

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill=tk.BOTH, expand=True)

    ttk.Label(outer, text="DVEntityLinking V0 需求分析确认", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
    ttk.Label(
        outer,
        text=(
            "请确认正式 IR 需求分析前的范围、Mock、LLM、输出契约和验收边界。"
            "未知项可以保留 TBD；请不要填写 API key、token、cookie、完整生产 payload 或敏感生产数据。"
        ),
        wraplength=1150,
        style="Hint.TLabel",
    ).pack(anchor="w", pady=(0, 12))

    notebook = ttk.Notebook(outer)
    notebook.pack(fill=tk.BOTH, expand=True)

    scope_tab = _tab(notebook, "范围")
    scope = {
        "V0 定位": _combo(scope_tab, 0, "V0 是否定位为实体链接 demo，不做生产接入", ["是", "否，需要产品化范围", "TBD"], "是"),
        "首批使用方": _combo(scope_tab, 1, "首批使用方", ["运维 Copilot + 故障 Agent", "仅运维 Copilot", "仅故障 Agent", "TBD"], "运维 Copilot + 故障 Agent"),
        "Demo 形态": _combo(scope_tab, 2, "V0 demo 形态", ["CLI + HTTP API", "仅 CLI", "仅 HTTP API", "轻量 Web UI", "对接前序项目", "TBD"], "CLI + HTTP API"),
        "当前范围": _text(
            scope_tab,
            3,
            "当前范围",
            "实体词表/目录构建；Query 实体匹配与链接；实体查询；相似度检索；Mock 数据与可选 LLM 辅助。",
        ),
        "当前非范围": _text(
            scope_tab,
            4,
            "当前非范围",
            "真实 DV 生产接入；写操作闭环；自动修复/派单/变更；未脱敏生产数据；生产级权限和向量库运维。",
        ),
    }
    scope_tab.rowconfigure(3, weight=1)
    scope_tab.rowconfigure(4, weight=1)

    entities_tab = _tab(notebook, "实体与场景")
    entity_types = _check_group(
        entities_tab,
        0,
        "首批实体类型",
        [
            ("网络资源/网元", True),
            ("告警/事件", True),
            ("KPI/性能指标", True),
            ("拓扑/关系", True),
            ("知识/Runbook/案例", True),
            ("服务/业务对象", False),
            ("工单/变更", False),
        ],
    )
    query_scenarios = _check_group(
        entities_tab,
        1,
        "首批 Query 场景",
        [
            ("精确名称匹配", True),
            ("别名/缩写匹配", True),
            ("模糊匹配", True),
            ("多实体 Query", True),
            ("歧义消解", True),
            ("查无结果降级", True),
            ("故障 Agent 诊断链路", True),
            ("运维 Copilot 查询", True),
        ],
    )
    retrieval_semantics = _check_group(
        entities_tab,
        2,
        "相似度检索语义",
        [
            ("名称/别名相似", True),
            ("语义相似", True),
            ("类型相同", True),
            ("拓扑相邻", True),
            ("告警共现", False),
            ("KPI 异常模式相似", False),
            ("历史案例相似", False),
        ],
    )
    entity_notes = _text(entities_tab, 3, "实体或场景补充", "TBD", 5)
    entities_tab.rowconfigure(3, weight=1)

    mock_tab = _tab(notebook, "Mock")
    mock_strategy = {
        "默认 Mock 层级": _combo(
            mock_tab,
            0,
            "默认 Mock 层级",
            ["L0 抽象合成 Mock", "L1 脱敏样例 Mock", "L2 模拟接口 Mock", "L3 真实 DV 只读接入", "TBD"],
            "L0 抽象合成 Mock",
        ),
        "是否允许使用用户提供的脱敏样例": _combo(mock_tab, 1, "是否允许使用用户提供的脱敏样例", ["TBD", "允许", "不允许", "后续再确认"], "TBD"),
        "是否允许模拟 DV 接口返回": _combo(mock_tab, 2, "是否允许模拟 DV 接口返回", ["允许", "不允许", "TBD"], "允许"),
        "真实 DV 字段是否可写入需求": _combo(
            mock_tab,
            3,
            "真实 DV 字段/接口未确认前是否可写入需求",
            ["不允许，必须标记 TBD", "允许写入用户确认项", "TBD"],
            "不允许，必须标记 TBD",
        ),
        "Mock 数据补充说明": _text(mock_tab, 4, "Mock 数据补充说明", "所有 Mock 必须明确标注为 demo 数据；不得伪装成真实 DV 事实。", 5),
    }
    mock_tab.rowconfigure(4, weight=1)

    llm_tab = _tab(notebook, "LLM")
    llm = {
        "Qwen3.6-27B 在 V0 中的角色": _combo(
            llm_tab,
            0,
            "Qwen3.6-27B 在 V0 中的角色",
            ["可选辅助，默认关闭真实调用", "必选主路径", "仅预留 adapter，不参与 V0", "TBD"],
            "可选辅助，默认关闭真实调用",
        ),
        "OpenAI-compatible API 信息": _entry(llm_tab, 1, "OpenAI-compatible API base URL / model / auth 现状", "TBD"),
        "是否允许保存 LLM 请求响应": _combo(
            llm_tab,
            2,
            "是否允许保存完整 LLM 请求响应",
            ["不允许", "仅本地开发显式开启且不提交", "允许脱敏摘要", "TBD"],
            "不允许",
        ),
        "LLM 失败时需求行为": _combo(
            llm_tab,
            3,
            "LLM 不可用或超时时的需求行为",
            ["走确定性/Mock 降级，demo 仍可运行", "直接失败", "TBD"],
            "走确定性/Mock 降级，demo 仍可运行",
        ),
        "LLM 使用补充": _text(llm_tab, 4, "LLM 使用补充", "实体链接主路径应保留可测试的确定性接口；LLM 可用于候选补全、Query 改写、解释生成。", 5),
    }
    llm_tab.rowconfigure(4, weight=1)

    output_tab = _tab(notebook, "输出与验收")
    output_contract = _check_group(
        output_tab,
        0,
        "实体链接输出字段",
        [
            ("标准实体 ID", True),
            ("实体类型", True),
            ("标准名", True),
            ("候选列表", True),
            ("置信度", True),
            ("消歧理由", True),
            ("来源/证据", True),
            ("无匹配原因", True),
        ],
    )
    acceptance_items = _check_group(
        output_tab,
        1,
        "V0 验收项",
        [
            ("可加载 Mock 实体目录", True),
            ("可执行 Query 实体链接", True),
            ("可返回候选和置信度", True),
            ("可执行实体查询", True),
            ("可执行 Top-K 相似度检索", True),
            ("可演示无匹配/歧义/依赖失败降级", True),
            ("可输出 Copilot/Agent 可消费结构", True),
            ("可运行自动化测试", True),
        ],
    )
    acceptance_notes = _text(output_tab, 2, "验收补充", "TBD", 5)
    output_tab.rowconfigure(2, weight=1)

    security_tab = _tab(notebook, "安全与签收")
    security = {
        "是否允许保存用户 Query": _combo(security_tab, 0, "是否允许保存用户 Query", ["仅 Mock/脱敏样例", "不允许", "允许本地保存", "TBD"], "仅 Mock/脱敏样例"),
        "是否允许保存实体链接中间结果": _combo(
            security_tab, 1, "是否允许保存实体链接中间结果", ["仅 Mock/脱敏样例", "不允许", "允许本地保存", "TBD"], "仅 Mock/脱敏样例"
        ),
        "是否允许保存真实 DV 数据": _combo(security_tab, 2, "是否允许保存真实 DV 数据", ["不允许", "仅用户确认的脱敏样例", "允许本地保存", "TBD"], "不允许"),
        "敏感信息处理": _text(
            security_tab,
            3,
            "敏感信息处理说明",
            "不记录 API key、token、cookie、完整生产 payload、原始生产数据和完整 LLM 日志。",
            4,
        ),
    }
    signoff = {
        "确认人": _entry(security_tab, 4, "确认人/标识", "TBD"),
        "确认结论": _combo(
            security_tab,
            5,
            "确认结论",
            ["确认，允许基于以上内容开展 IR 需求分析", "部分确认，未确认项在 IR 中标记 TBD", "暂不确认，需要重新整理", "TBD"],
            "确认，允许基于以上内容开展 IR 需求分析",
        ),
        "补充说明": _text(security_tab, 6, "补充说明", "TBD", 4),
    }
    security_tab.rowconfigure(3, weight=1)
    security_tab.rowconfigure(6, weight=1)

    def save() -> None:
        payload = {
            "project_name": PROJECT_NAME,
            "confirmed_at": datetime.now().isoformat(timespec="seconds"),
            "scope": {
                "V0 定位": scope["V0 定位"].get(),
                "首批使用方": scope["首批使用方"].get(),
                "Demo 形态": scope["Demo 形态"].get(),
                "当前范围": _text_value(scope["当前范围"]),
                "当前非范围": _text_value(scope["当前非范围"]),
            },
            "entity_types": _selected(entity_types),
            "query_scenarios": _selected(query_scenarios),
            "retrieval_semantics": _selected(retrieval_semantics),
            "entity_notes": _text_value(entity_notes),
            "mock_strategy": {
                "默认 Mock 层级": mock_strategy["默认 Mock 层级"].get(),
                "是否允许使用用户提供的脱敏样例": mock_strategy["是否允许使用用户提供的脱敏样例"].get(),
                "是否允许模拟 DV 接口返回": mock_strategy["是否允许模拟 DV 接口返回"].get(),
                "真实 DV 字段是否可写入需求": mock_strategy["真实 DV 字段是否可写入需求"].get(),
                "Mock 数据补充说明": _text_value(mock_strategy["Mock 数据补充说明"]),
            },
            "llm": {
                "Qwen3.6-27B 在 V0 中的角色": llm["Qwen3.6-27B 在 V0 中的角色"].get(),
                "OpenAI-compatible API 信息": _clean(llm["OpenAI-compatible API 信息"].get()),
                "是否允许保存 LLM 请求响应": llm["是否允许保存 LLM 请求响应"].get(),
                "LLM 失败时需求行为": llm["LLM 失败时需求行为"].get(),
                "LLM 使用补充": _text_value(llm["LLM 使用补充"]),
            },
            "output_contract": _selected(output_contract),
            "acceptance_items": _selected(acceptance_items),
            "acceptance_notes": _text_value(acceptance_notes),
            "security": {
                "是否允许保存用户 Query": security["是否允许保存用户 Query"].get(),
                "是否允许保存实体链接中间结果": security["是否允许保存实体链接中间结果"].get(),
                "是否允许保存真实 DV 数据": security["是否允许保存真实 DV 数据"].get(),
                "敏感信息处理": _text_value(security["敏感信息处理"]),
            },
            "signoff": {
                "确认人": _clean(signoff["确认人"].get()),
                "确认结论": signoff["确认结论"].get(),
                "补充说明": _text_value(signoff["补充说明"]),
            },
        }
        _write_outputs(payload)
        messagebox.showinfo("已保存", f"确认结果已保存到：\n{OUTPUT_MD}\n{OUTPUT_JSON}")

    buttons = ttk.Frame(outer)
    buttons.pack(fill=tk.X, pady=(12, 0))
    ttk.Button(buttons, text="保存确认结果", command=save).pack(side=tk.RIGHT)
    ttk.Button(buttons, text="关闭", command=root.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    build_gui()
