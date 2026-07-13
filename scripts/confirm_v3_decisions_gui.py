from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "confirmations"
OUTPUT_JSON = OUTPUT_DIR / "2026-06-24-dv-entity-linking-v3-decision-confirmation.json"
OUTPUT_MD = OUTPUT_DIR / "2026-06-24-dv-entity-linking-v3-decision-confirmation.md"


def _clean(value: str) -> str:
    value = value.strip()
    return value if value else "TBD"


def _combo(parent: ttk.Frame, row: int, label: str, values: list[str], default: str) -> tk.StringVar:
    var = tk.StringVar(value=default)
    ttk.Label(parent, text=label, wraplength=360).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=6)
    ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=86).grid(
        row=row, column=1, sticky="ew", pady=6
    )
    return var


def _text(parent: ttk.Frame, row: int, label: str, default: str = "", height: int = 3) -> tk.Text:
    ttk.Label(parent, text=label, wraplength=360).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=6)
    widget = tk.Text(parent, height=height, wrap=tk.WORD)
    widget.insert("1.0", default)
    widget.grid(row=row, column=1, sticky="nsew", pady=6)
    return widget


def _text_value(widget: tk.Text) -> str:
    return _clean(widget.get("1.0", tk.END))


def _write_outputs(payload: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# DVEntityLinking V3 决策确认记录",
        "",
        f"确认时间：{payload['confirmed_at']}",
        "",
        "## 1. Redis 单值冲突策略",
        "",
        f"- 决策：{payload['redis_conflict_strategy']}",
        f"- 补充：{payload['redis_conflict_notes']}",
        "",
        "## 2. Redis key 范围",
        "",
        f"- 决策：{payload['redis_key_scope']}",
        f"- 补充：{payload['redis_key_notes']}",
        "",
        "## 3. 高斯结构化实体字段",
        "",
        f"- 决策：{payload['gauss_field_scope']}",
        f"- 补充：{payload['gauss_field_notes']}",
        "",
        "## 4. NER 内部 schema",
        "",
        f"- 决策：{payload['ner_schema_scope']}",
        f"- 补充：{payload['ner_schema_notes']}",
        "",
        "## 5. LLM 在 V3 NER 中的角色",
        "",
        f"- 决策：{payload['llm_role']}",
        f"- 补充：{payload['llm_notes']}",
        "",
        "## 6. V3 样例数据策略",
        "",
        f"- 决策：{payload['sample_strategy']}",
        f"- 补充：{payload['sample_notes']}",
        "",
        "## 7. 签收",
        "",
        f"- 确认人：{payload['signoff_name']}",
        f"- 结论：{payload['signoff_decision']}",
        f"- 其他说明：{payload['signoff_notes']}",
        "",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def build_gui() -> None:
    root = tk.Tk()
    root.title("DVEntityLinking V3 决策确认")
    root.geometry("1280x840")
    root.minsize(1100, 720)

    style = ttk.Style()
    style.configure("Title.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
    style.configure("Hint.TLabel", foreground="#555")

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill=tk.BOTH, expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(2, weight=1)

    ttk.Label(outer, text="DVEntityLinking V3 决策确认", style="Title.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )
    ttk.Label(
        outer,
        text=(
            "请确认 V3 进入独立需求评审前必须固定的设计输入。"
            "这些决策会写入 docs/confirmations，并同步到 IR 和 DECISIONS。"
            "请不要填写真实 Redis/Gauss 连接串、账号、密码、token 或真实 DV payload。"
        ),
        wraplength=1200,
        style="Hint.TLabel",
    ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

    frame = ttk.Frame(outer, padding=8)
    frame.grid(row=2, column=0, sticky="nsew")
    frame.columnconfigure(1, weight=1)
    for idx in range(18):
        frame.rowconfigure(idx, weight=1 if idx % 3 == 2 else 0)

    redis_conflict_strategy = _combo(
        frame,
        0,
        "V3-HD-001：同一个实体词对应多个实体时，Redis 单值 KV 如何处理？",
        [
            "推荐：保持 value 为单实体 ID；冲突数据加载 fail-closed，不进入链接链路",
            "允许运行时返回 ambiguous；需要额外冲突记录和歧义展示",
            "调整为多值 value，即 Redis value 为实体 ID 列表",
            "TBD，暂不进入功能设计",
        ],
        "推荐：保持 value 为单实体 ID；冲突数据加载 fail-closed，不进入链接链路",
    )
    redis_conflict_notes = _text(frame, 1, "补充说明", "保持 V3 初始范围简单，先不扩大 Redis value 结构。")

    redis_key_scope = _combo(
        frame,
        3,
        "V3-HD-002：Redis key 的实体词范围？",
        [
            "推荐：canonical_name + 经确认 aliases；不自动生成别名",
            "仅 canonical_name；不使用 aliases",
            "canonical_name + aliases + 自动生成别名",
            "TBD，暂不进入功能设计",
        ],
        "推荐：canonical_name + 经确认 aliases；不自动生成别名",
    )
    redis_key_notes = _text(frame, 4, "补充说明", "aliases 必须来自已确认样例或用户确认清单。")

    gauss_field_scope = _combo(
        frame,
        6,
        "V3-HD-003：高斯 Mock 结构化实体字段范围？",
        [
            "推荐：沿用最小字段 entity_id/entity_type/canonical_name/aliases/description",
            "最小字段 + 通用字段 source/data_layer/updated_at",
            "加入类型专属字段，例如 alarm/KPI/网元专属属性",
            "TBD，暂不进入功能设计",
        ],
        "推荐：沿用最小字段 entity_id/entity_type/canonical_name/aliases/description",
    )
    gauss_field_notes = _text(frame, 7, "补充说明", "类型专属字段后续单独确认，V3 初始先稳住存储边界。")

    ner_schema_scope = _combo(
        frame,
        9,
        "V3-HD-004：NER 是否允许新增内部中间 schema？",
        [
            "推荐：允许内部 schema 扩展；外部 API 和样例提交字段受控",
            "不允许新增内部 schema；尽量复用现有模型",
            "允许同步扩展外部 API schema",
            "TBD，暂不进入功能设计",
        ],
        "推荐：允许内部 schema 扩展；外部 API 和样例提交字段受控",
    )
    ner_schema_notes = _text(frame, 10, "补充说明", "内部 schema 用于 NER stage trace、storage lookup 和重构隔离。")

    llm_role = _combo(
        frame,
        12,
        "V3-HD-005：LLM 在 V3 NER 中的角色？",
        [
            "推荐：默认离线 deterministic 可回归；LLM 作为可选分类/解释/rerank 增强",
            "LLM 是 NER 必经主路径；无 LLM 不通过 V3 验收",
            "V3 暂不考虑 LLM；全部离线规则实现",
            "TBD，暂不进入功能设计",
        ],
        "推荐：默认离线 deterministic 可回归；LLM 作为可选分类/解释/rerank 增强",
    )
    llm_notes = _text(frame, 13, "补充说明", "默认验收不依赖真实 LLM，本地配置可做条件补证。")

    sample_strategy = _combo(
        frame,
        15,
        "V3-HD-006：V3 样例数据策略？",
        [
            "推荐：复用 V1/V2 样例，新增 Redis/Gauss Mock artifacts 和 NER golden cases",
            "只使用全新 V3 样例，不复用 V1/V2",
            "先不新增样例，只做设计文档",
            "TBD，暂不进入功能设计",
        ],
        "推荐：复用 V1/V2 样例，新增 Redis/Gauss Mock artifacts 和 NER golden cases",
    )
    sample_notes = _text(frame, 16, "补充说明", "新增样例必须保持脱敏和 D003 边界，不引入真实生产 payload。")

    signoff_frame = ttk.Frame(outer, padding=(8, 12, 8, 0))
    signoff_frame.grid(row=3, column=0, sticky="ew")
    signoff_frame.columnconfigure(1, weight=1)

    signoff_name = tk.StringVar(value="User")
    ttk.Label(signoff_frame, text="确认人").grid(row=0, column=0, sticky="w", padx=(0, 8))
    ttk.Entry(signoff_frame, textvariable=signoff_name, width=24).grid(row=0, column=1, sticky="w")

    signoff_decision = tk.StringVar(value="确认以上 V3 决策，可据此修订 IR 并进入独立需求评审")
    ttk.Label(signoff_frame, text="结论").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
    ttk.Combobox(
        signoff_frame,
        textvariable=signoff_decision,
        values=[
            "确认以上 V3 决策，可据此修订 IR 并进入独立需求评审",
            "部分确认，未确认项继续保持 Needs user decision",
            "暂不确认，V3 IR 继续保持草稿",
        ],
        state="readonly",
        width=72,
    ).grid(row=1, column=1, sticky="w", pady=(8, 0))

    signoff_notes = _text(signoff_frame, 2, "其他说明", "", height=2)

    button_frame = ttk.Frame(outer)
    button_frame.grid(row=4, column=0, sticky="e", pady=(12, 0))

    def submit() -> None:
        payload = {
            "schema_version": "v3.decision_confirmation.1",
            "confirmed_at": datetime.now().isoformat(timespec="seconds"),
            "redis_conflict_strategy": _clean(redis_conflict_strategy.get()),
            "redis_conflict_notes": _text_value(redis_conflict_notes),
            "redis_key_scope": _clean(redis_key_scope.get()),
            "redis_key_notes": _text_value(redis_key_notes),
            "gauss_field_scope": _clean(gauss_field_scope.get()),
            "gauss_field_notes": _text_value(gauss_field_notes),
            "ner_schema_scope": _clean(ner_schema_scope.get()),
            "ner_schema_notes": _text_value(ner_schema_notes),
            "llm_role": _clean(llm_role.get()),
            "llm_notes": _text_value(llm_notes),
            "sample_strategy": _clean(sample_strategy.get()),
            "sample_notes": _text_value(sample_notes),
            "signoff_name": _clean(signoff_name.get()),
            "signoff_decision": _clean(signoff_decision.get()),
            "signoff_notes": _text_value(signoff_notes),
        }
        _write_outputs(payload)
        messagebox.showinfo("已保存", f"确认记录已保存：\n{OUTPUT_JSON}")
        root.destroy()

    ttk.Button(button_frame, text="保存确认", command=submit).pack(side=tk.RIGHT, padx=(8, 0))
    ttk.Button(button_frame, text="取消", command=root.destroy).pack(side=tk.RIGHT)

    root.mainloop()


if __name__ == "__main__":
    build_gui()
