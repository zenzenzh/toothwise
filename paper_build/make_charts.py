"""Re-plot the Chapter IV result charts for print.

Reads chapter4_figures/training_metrics.json and eval_results.json (written by
extract_training_metrics.py) and draws each chart at its printed width
(6.0 in) so the smallest text is about 7.5 pt. Charts are saved as opaque RGB
PNGs at 300 dpi; bar series also carry hatching so they stay distinguishable
on a black-and-white printer.

    python paper_build/make_charts.py OUT_DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chapter4_figures"
COLORS = {"YOLOv8": "#1f5fae", "YOLOv12": "#d4561f", "Ensemble": "#178a5f"}
HATCH = {"YOLOv8": "", "YOLOv12": "////", "Ensemble": "...."}
STYLE = {"YOLOv8": "-", "YOLOv12": "--"}
INK, INK2, GRID = "#000000", "#222222", "#b8b8b8"
CLASS_LABELS = ["Healthy tooth", "Cavity", "Gum\ninflammation", "Plaque", "Tartar"]

plt.rcParams.update({
    "font.family": "Liberation Serif", "font.size": 9, "axes.edgecolor": INK2,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "hatch.linewidth": 0.8, "hatch.color": "#ffffff",
})


def style(ax, title, ylabel, xlabel=""):
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold", pad=6)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)


def save(fig, path):
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    # Opaque RGB: some printers drop or blacken images that carry an alpha channel.
    from PIL import Image
    Image.open(path).convert("RGB").save(path, optimize=True)


def training_curves(data, out):
    fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.35))
    for ax, (key, title, yl) in zip(axes, [("map50", "mAP@50 (validation)", "mAP@50"),
                                           ("map50_95", "mAP@50-95 (validation)", "mAP@50-95")]):
        style(ax, title, yl, "Epoch")
        for name, d in data.items():
            ep = d["per_epoch"]
            ax.plot(ep["epoch"], ep[key], STYLE[name], color=COLORS[name], linewidth=1.6, label=name)
            ax.annotate(f"{ep[key][-1]:.3f}", (ep["epoch"][-1], ep[key][-1]),
                        xytext=(-2, 5 if name == "YOLOv8" else -11), textcoords="offset points",
                        ha="right", fontsize=8)
        ax.set_xlim(0, 61)
        ax.set_ylim(0, max(max(d["per_epoch"][key]) for d in data.values()) * 1.2)
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.tight_layout()
    save(fig, out / "fig_training_curves.png")


def bars(ax, series, keys, width):
    n = len(series)
    for i, (name, vals) in enumerate(series.items()):
        xs = [k + (i - (n - 1) / 2) * (width + 0.02) for k in range(len(keys))]
        ax.bar(xs, vals, width=width, color=COLORS[name], hatch=HATCH[name],
               edgecolor="black", linewidth=0.6, label=name)
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.012, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)


def final_metrics(data, out):
    keys = [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score"),
            ("map50", "mAP@50"), ("map50_95", "mAP@50-95")]
    fig, ax = plt.subplots(figsize=(6.0, 2.4))
    style(ax, "Final validation metrics (epoch 60)", "Score (0 to 1)")
    bars(ax, {n: [d["final"][k] for k, _ in keys] for n, d in data.items()}, keys, 0.36)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([lbl for _, lbl in keys], fontsize=9)
    ax.set_ylim(0, 0.68)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    fig.tight_layout()
    save(fig, out / "fig_final_metrics.png")


def per_class_map(ev, out):
    series = {}
    for name in ("YOLOv8", "YOLOv12", "Ensemble"):
        d = ev["shared"][name]
        vals = dict(zip(d["class_index"], d["ap50"]))
        series[name] = [vals.get(k, 0.0) for k in range(5)]
    fig, ax = plt.subplots(figsize=(6.0, 2.55))
    style(ax, "Per-class mAP@50 on the test split", "mAP@50")
    bars(ax, series, CLASS_LABELS, 0.26)
    ax.set_xticks(range(5))
    ax.set_xticklabels(CLASS_LABELS, fontsize=8.5)
    ax.set_ylim(0, 1.0)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=3)
    fig.tight_layout()
    save(fig, out / "fig_perclass_map50.png")


def confusion(ev, out):
    cmap = LinearSegmentedColormap.from_list("b", ["#ffffff", "#c6dbf3", "#6a9fd8", "#1f5fae", "#0b2f5e"])
    ticks = ["Healthy", "Cavity", "Gum infl.", "Plaque", "Tartar", "Backgr."]
    fig, axes = plt.subplots(1, 3, figsize=(6.0, 2.85))
    for ax, name in zip(axes, ("YOLOv8", "YOLOv12", "Ensemble")):
        m = np.array(ev["shared"][name]["confusion_matrix"], dtype=float)
        col = m.sum(0, keepdims=True)
        norm = np.divide(m, col, out=np.zeros_like(m), where=col > 0)
        norm[:, 5] = 0
        ax.imshow(norm, cmap=cmap, vmin=0, vmax=1)
        for r in range(6):
            for c in range(6):
                if r == 5 and c == 5:
                    continue
                v = norm[r, c] if c < 5 else m[r, c]
                ax.text(c, r, f"{v:.2f}".lstrip("0") if c < 5 and v < 1 else f"{int(v)}" if c == 5 else "1.0",
                        ha="center", va="center", fontsize=6.6,
                        color="white" if (c < 5 and v > 0.5) else INK)
        ax.set_xticks(range(6)); ax.set_yticks(range(6))
        ax.set_xticklabels(ticks, rotation=50, ha="right", fontsize=7)
        ax.set_yticklabels(ticks if name == "YOLOv8" else [], fontsize=7)
        ax.set_title(name, fontsize=9, fontweight="bold")
        ax.set_xlabel("True class", fontsize=7.5)
        ax.tick_params(length=0)
        ax.set_xticks(np.arange(-.5, 6), minor=True); ax.set_yticks(np.arange(-.5, 6), minor=True)
        ax.grid(which="minor", color="#888", linewidth=0.4)
        ax.tick_params(which="minor", length=0)
    axes[0].set_ylabel("Predicted class", fontsize=7.5)
    fig.tight_layout(w_pad=0.4)
    save(fig, out / "fig_confusion_matrices.png")


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads((SRC / "training_metrics.json").read_text(encoding="utf-8"))
    ev = json.loads((SRC / "eval_results.json").read_text(encoding="utf-8"))
    training_curves(data, out)
    final_metrics(data, out)
    per_class_map(ev, out)
    confusion(ev, out)
    print("charts written to", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
