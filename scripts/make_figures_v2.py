#!/usr/bin/env python3
"""Redraw the blocked denominator figure. No detection rates are computed."""
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "figures"
NAVY, ORANGE, GREEN, RED, GRAY = "#1f4e79", "#e07b39", "#3a9a5b", "#b23a48", "#6b7280"
SOURCE = "artifacts/blocking_audit.json; artifacts/diagnostic_rosters.json; analysis/config.json; results.json"


def use_cjk():
    from matplotlib import font_manager

    listed = subprocess.check_output(["fc-list", "Noto Sans CJK SC", "file"], text=True)
    paths = [line.split(":")[0].strip() for line in listed.splitlines() if line.strip()]
    if not paths:
        raise SystemExit("Noto Sans CJK SC is not installed")
    for path in paths:
        font_manager.fontManager.addfont(path)
    plt.rcParams.update({
        "font.family": "Noto Sans CJK SC",
        "font.weight": "regular",
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "text.color": "#222222",
        "svg.fonttype": "path",
        "font.size": 8,
    })


def strip_png_text(path):
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("not a png")
    out = bytearray(data[:8])
    i = 8
    while i + 8 <= len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8]
        end = i + 12 + length
        if ctype not in (b"tEXt", b"iTXt", b"zTXt"):
            out += data[i:end]
        i = end
        if ctype == b"IEND":
            break
    Path(path).write_bytes(out)
    width = int.from_bytes(out[16:20], "big")
    if width != 1600:
        raise SystemExit(f"width {width} != 1600")


def load():
    audit = json.loads((ROOT / "artifacts" / "blocking_audit.json").read_text(encoding="utf-8"))
    rosters = json.loads((ROOT / "artifacts" / "diagnostic_rosters.json").read_text(encoding="utf-8"))
    config = json.loads((ROOT / "analysis" / "config.json").read_text(encoding="utf-8"))
    result = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    if audit.get("scientific_aggregation_performed"):
        raise SystemExit("audit says scientific aggregation ran; refused to draw the blocked figure")
    if result["M"]["status"] != "not_tested":
        raise SystemExit(f"M status is {result['M']['status']}, not not_tested")
    return audit, rosters, config, result


def main():
    use_cjk()
    audit, rosters, config, result = load()
    counts = audit["issue_count_by_reason"]
    issues = [issue for record in audit["files"] for issue in record.get("issues", [])]
    n_sars = sum(1 for issue in issues if issue["reason"] == "target_not_in_frozen_alias_dictionary"
                 and issue["raw_target"] == "SARS-CoV-2")
    empties = [issue for issue in issues if issue["reason"] == "empty_target_key"]
    if n_sars != counts["target_not_in_frozen_alias_dictionary"]:
        raise SystemExit("SARS-CoV-2 row count does not match the reason total")
    if len(empties) != counts["empty_target_key"]:
        raise SystemExit("empty-target count does not match the reason total")
    designs = sorted({issue["raw_design"] for issue in empties})
    settings = sorted({issue["raw_setting"] for issue in empties})
    wn = config["thresholds"]["WN"]
    wd = config["thresholds"]["WD"]
    setting_name = config["settings"]
    setting_labels = ", ".join(f"{item}→{setting_name.get(item, item)}" for item in settings)
    join = rosters["join_counts"]
    gate_g = result["gates"]["G"]["status"]
    gate_i = result["gates"]["I"]["status"]

    fig, ax = plt.subplots(figsize=(8.0, 6.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.text(0.50, 0.955, "蛋白质水印：分母审计被阻断", ha="center", va="center", fontsize=13, color=NAVY)
    fig.text(0.50, 0.905, "Protein watermark: the denominator audit is blocked", ha="center", va="center", fontsize=9, color=NAVY)
    fig.text(0.04, 0.845, "公开体外记录。作者已披露筛选。未重算检出率。  Public in-vitro records; selection was disclosed; no rates recomputed.",
             fontsize=7.5, color="#333333")

    boxes = [
        (0.02, "1  生成候选\nGenerated",
         "数量未知\nCount unknown\n\n筛选前检出\n不可识别\n\n留存代价\n不可识别", "#f4f7fb", NAVY),
        (0.265, "2  已披露筛选\nDisclosed selection",
         "结构质量\nStructural quality\n+ g 值阈值\n+ g threshold\n+ 排序 ranking\n\n已结合骨架被选入\nBinding backbones", "#f4f7fb", NAVY),
        (0.51, "3  公开入选记录\nPublic records",
         "完整名册\n未核验\nRoster not verified\n\n靶标键未过\n锁定连接规则\n\nGate G: " + gate_g, "#fff4ec", ORANGE),
        (0.755, "4  检出审计\nDetection audit",
         f"WN  K/N 未评估\nnot evaluated\n阈值 threshold {wn}\n\nWD  K/N 未评估\nnot evaluated\n阈值 threshold {wd}\n\nM：未检验\nnot tested", "#fff4ec", ORANGE),
    ]
    for x, title, body, face, edge in boxes:
        ax.add_patch(FancyBboxPatch((x, 0.36), 0.225, 0.40, boxstyle="round,pad=0.008,rounding_size=0.015",
                                     facecolor=face, edgecolor=edge, linewidth=1.2))
        ax.text(x + 0.112, 0.735, title, ha="center", va="top", fontsize=7.5, color=edge)
        ax.text(x + 0.112, 0.655, body, ha="center", va="top", fontsize=6.4, linespacing=1.22)
    for left, right in ((0.245, 0.265), (0.490, 0.510), (0.735, 0.755)):
        ax.add_patch(FancyArrowPatch((left, 0.56), (right, 0.56), arrowstyle="-|>", mutation_scale=8, color=NAVY, lw=1))

    ax.text(0.02, 0.32,
            f"阻断原因 Why blocked: 未登记靶标 SARS-CoV-2 共 {n_sars} 行；空靶标键 {len(empties)} 行"
            f"（设计 design {', '.join(designs)}；设置 setting {setting_labels}）。未推断别名或补键。",
            fontsize=7, color=ORANGE, va="top")
    ax.text(0.02, 0.26,
            "目标量是「水印且被选入」条件下的检出。资格未通过不是漏检证据，也不否定论文表述。\n"
            "The estimand is detection given watermarking AND selection. "
            "Failure to qualify these rows is not evidence of missed detections.",
            fontsize=6.5, color="#333333", va="top")
    ax.text(0.02, 0.16,
            f"诊断连接（不是科学分母）Diagnostic join, not a scientific denominator: "
            f"matched {join['matched']}，left_only {join['left_only']}，right_only {join['right_only']}。"
            f" Gate I: {gate_i}。",
            fontsize=6.5, color="#333333", va="top")
    ax.text(0.02, 0.08,
            f"数据来源 Source: {SOURCE}\n上游提交 upstream {result['upstream_commit']}。论文与许可链接见 SOURCES.md。",
            fontsize=6.5, color=GRAY, va="top")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.82, bottom=0.02)
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / "figure1.png"
    svg = OUT / "figure1.svg"
    fig.savefig(png, dpi=200)
    fig.savefig(svg)
    plt.close(fig)
    strip_png_text(png)
    print("wrote figures/figure1.png")
    print("wrote figures/figure1.svg")


if __name__ == "__main__":
    main()
