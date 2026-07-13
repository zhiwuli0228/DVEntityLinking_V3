from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "confirmations"
OUTPUT_JSON = OUTPUT_DIR / "2026-05-25-dv-entity-linking-v0-review-disposition-confirmation.json"
OUTPUT_MD = OUTPUT_DIR / "2026-05-25-dv-entity-linking-v0-review-disposition-confirmation.md"


def _text_value(widget: tk.Text) -> str:
    value = widget.get("1.0", tk.END).strip()
    return value if value else "TBD"


def _combo(parent: ttk.Frame, row: int, label: str, values: list[str], default: str) -> tk.StringVar:
    var = tk.StringVar(value=default)
    ttk.Label(parent, text=label, wraplength=360).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=6)
    ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=82).grid(
        row=row, column=1, sticky="w", pady=6
    )
    return var


def _text(parent: ttk.Frame, row: int, label: str, default: str, height: int = 4) -> tk.Text:
    ttk.Label(parent, text=label, wraplength=360).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=6)
    widget = tk.Text(parent, height=height, wrap=tk.WORD)
    widget.insert("1.0", default)
    widget.grid(row=row, column=1, sticky="nsew", pady=6)
    return widget


def _write_outputs(payload: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# DVEntityLinking V0 需求评审处置用户确认记录",
        "",
        f"确认时间：{payload['confirmed_at']}",
        "",
        "## 1. LLM 验收语义",
        "",
        f"- 决策：{payload['llm_acceptance']}",
        f"- 补充：{payload['llm_notes']}",
        "",
        "## 2. 真实 DV 数据保存边界",
        "",
        f"- 决策：{payload['data_persistence']}",
        f"- 补充：{payload['data_notes']}",
        "",
        "## 3. Mock baseline",
        "",
        f"- 决策：{payload['mock_baseline']}",
        f"- 补充：{payload['mock_notes']}",
        "",
        "## 4. 首批使用方优先级",
        "",
        f"- 决策：{payload['consumer_priority']}",
        f"- 补充：{payload['consumer_notes']}",
        "",
        "## 5. 签收",
        "",
        f"- 确认人：{payload['signoff_name']}",
        f"- 结论：{payload['signoff_decision']}",
        f"- 其他说明：{payload['signoff_notes']}",
        "",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def build_gui() -> None:
    root = tk.Tk()
    root.title("DVEntityLinking V0 需求评审 P1 处置确认")
    root.geometry("1260x760")
    root.minsize(1050, 680)

    style = ttk.Style()
    style.configure("Title.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
    style.configure("Hint.TLabel", foreground="#555")

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill=tk.BOTH, expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(2, weight=1)

    ttk.Label(outer, text="DVEntityLinking V0 需求评审 P1 处置确认", style="Title.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )
    ttk.Label(
        outer,
        text=(
            "两个独立需求评审均指出：LLM 验收语义、真实 DV 数据保存边界、Mock baseline 需要在修订 IR 前确认。"
            "请确认以下处置策略；不要填写 API key、token、cookie 或完整生产 payload。"
        ),
        wraplength=1180,
        style="Hint.TLabel",
    ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

    frame = ttk.Frame(outer, padding=8)
    frame.grid(row=2, column=0, sticky="nsew")
    frame.columnconfigure(1, weight=1)
    for idx in range(9):
        frame.rowconfigure(idx, weight=1 if idx in (1, 3, 5, 7) else 0)

    llm_acceptance = _combo(
        frame,
        0,
        "C001：LLM “必选主路径”的 V0 验收含义",
        [
            "推荐：必须实现可配置 LLM nominal path；自动化基线测试离线 deterministic/Mock 通过；有本地配置时执行真实 LLM smoke",
            "真实 LLM 调用是 V0 验收必选，缺少真实 Qwen API 不通过",
            "仅预留 LLM adapter，V0 不要求真实 LLM 路径",
            "TBD，暂不进入功能设计",
        ],
        "推荐：必须实现可配置 LLM nominal path；自动化基线测试离线 deterministic/Mock 通过；有本地配置时执行真实 LLM smoke",
    )
    llm_notes = _text(
        frame,
        1,
        "LLM 补充说明",
        "LLM 用于 NER、实体匹配和实体消歧主路径；fallback 必须输出 degraded 状态和原因。",
    )

    data_persistence = _combo(
        frame,
        2,
        "C002：真实 DV 数据保存边界",
        [
            "推荐：不默认包含未脱敏生产 payload；仅用户显式提供并确认范围的本地真实 DV artifact 可保存到 ignored 路径，不提交、不写文档、不作为默认样例",
            "允许未脱敏生产 payload 本地保存，但必须 ignored 且不提交",
            "只允许 L0/L1，不允许保存任何真实 DV artifact",
            "TBD，暂不进入功能设计",
        ],
        "推荐：不默认包含未脱敏生产 payload；仅用户显式提供并确认范围的本地真实 DV artifact 可保存到 ignored 路径，不提交、不写文档、不作为默认样例",
    )
    data_notes = _text(
        frame,
        3,
        "真实 DV 数据补充说明",
        "Demo 阶段不重点做脱敏工程，但密钥、token、cookie、完整生产 payload、敏感配置和完整 LLM 日志不得提交。",
    )

    mock_baseline = _combo(
        frame,
        4,
        "C003：V0 baseline 验收依赖哪个 Mock 层级",
        [
            "推荐：V0 baseline 仅依赖 L0 抽象合成 Mock；L1/L2 是可选增强，进入验收前需用户确认；样例和输出标记 data_layer/source",
            "V0 baseline 必须包含 L1 脱敏样例",
            "V0 baseline 必须包含 L2 模拟接口",
            "TBD，暂不进入功能设计",
        ],
        "推荐：V0 baseline 仅依赖 L0 抽象合成 Mock；L1/L2 是可选增强，进入验收前需用户确认；样例和输出标记 data_layer/source",
    )
    mock_notes = _text(frame, 5, "Mock 补充说明", "L2 模拟接口不得被描述为真实 DV 能力代表。")

    consumer_priority = _combo(
        frame,
        6,
        "C004：首批使用方优先级",
        [
            "推荐：V0 以实体链接能力闭环为主，不以某一使用方为 gating；样例至少覆盖一条 Copilot Query 和一条故障 Agent Query",
            "运维 Copilot 优先",
            "故障 Agent 优先",
            "TBD，暂不进入功能设计",
        ],
        "推荐：V0 以实体链接能力闭环为主，不以某一使用方为 gating；样例至少覆盖一条 Copilot Query 和一条故障 Agent Query",
    )
    consumer_notes = _text(frame, 7, "使用方补充说明", "Demo UI 展示顺序可在功能设计阶段再定。")

    signoff_frame = ttk.Frame(frame)
    signoff_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    signoff_frame.columnconfigure(1, weight=1)
    signoff_name = tk.StringVar(value="张清恒")
    signoff_decision = tk.StringVar(value="确认，允许据此修订 IR 并进入需求评审处置")
    ttk.Label(signoff_frame, text="确认人").grid(row=0, column=0, sticky="w", padx=(0, 8))
    ttk.Entry(signoff_frame, textvariable=signoff_name, width=24).grid(row=0, column=1, sticky="w", padx=(0, 24))
    ttk.Label(signoff_frame, text="确认结论").grid(row=0, column=2, sticky="w", padx=(0, 8))
    ttk.Combobox(
        signoff_frame,
        textvariable=signoff_decision,
        values=[
            "确认，允许据此修订 IR 并进入需求评审处置",
            "部分确认，未确认项保留 Needs user decision",
            "暂不确认，需要重新整理",
        ],
        state="readonly",
        width=44,
    ).grid(row=0, column=3, sticky="w")
    signoff_notes = _text(frame, 9, "其他说明", "TBD", 3)

    def save() -> None:
        payload = {
            "confirmed_at": datetime.now().isoformat(timespec="seconds"),
            "llm_acceptance": llm_acceptance.get(),
            "llm_notes": _text_value(llm_notes),
            "data_persistence": data_persistence.get(),
            "data_notes": _text_value(data_notes),
            "mock_baseline": mock_baseline.get(),
            "mock_notes": _text_value(mock_notes),
            "consumer_priority": consumer_priority.get(),
            "consumer_notes": _text_value(consumer_notes),
            "signoff_name": signoff_name.get().strip() or "TBD",
            "signoff_decision": signoff_decision.get(),
            "signoff_notes": _text_value(signoff_notes),
        }
        _write_outputs(payload)
        messagebox.showinfo("已保存", f"确认结果已保存到：\n{OUTPUT_MD}\n{OUTPUT_JSON}")

    buttons = ttk.Frame(outer)
    buttons.grid(row=3, column=0, sticky="ew", pady=(12, 0))
    ttk.Button(buttons, text="保存确认结果", command=save).pack(side=tk.RIGHT)
    ttk.Button(buttons, text="关闭", command=root.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    build_gui()
