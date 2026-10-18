"""
Pull the real YOLOv8 / YOLOv12 training metrics out of the trained
checkpoints in backend/models_weights and draw the Chapter IV figures.

Ultralytics stores the full per-epoch results table (train_results) and the
final validation metrics (train_metrics) inside every saved .pt file, so the
numbers here come straight from the training runs - nothing is typed in.

Run with the backend venv (it has torch, ultralytics and matplotlib):
    backend\\venv\\Scripts\\python.exe extract_training_metrics.py

Optional: pass the folder that holds job_b_test.json from the
test-split evaluation to copy those results into chapter4_figures as
eval_results.json; the per-class and confusion-matrix figures are drawn
whenever eval_results.json exists.
    backend\\venv\\Scripts\\python.exe extract_training_metrics.py <eval_out folder>

Writes:
    chapter4_figures/training_metrics.json
    chapter4_figures/eval_results.json (when evaluation results are given)
    chapter4_figures/fig_perclass_map50.png, fig_confusion_matrices.png
    chapter4_figures/fig_training_curves.png
    chapter4_figures/fig_final_metrics.png
"""
import json
import sys
import warnings

import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
WEIGHTS = ROOT / "backend" / "models_weights"
OUT = ROOT / "chapter4_figures"
OUT.mkdir(exist_ok=True)

MODELS = {"YOLOv8": "yolov8_dental.pt", "YOLOv12": "yolov12_dental.pt"}
# Validated default categorical slots 1-3 (dataviz palette), light mode.
COLORS = {"YOLOv8": "#2a78d6", "YOLOv12": "#eb6834", "Ensemble": "#1baf7a"}
CLASS_LABELS = ["Healthy tooth", "Cavity", "Gum\ninflammation", "Plaque", "Tartar"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
FONT = "Book Antiqua"


def load(path: Path) -> dict:
    ck = torch.load(path, map_location="cpu", weights_only=False)
    tr = ck["train_results"]
    tm = ck["train_metrics"]
    ta = ck["train_args"]
    model = ck["model"]
    p, r = tm["metrics/precision(B)"], tm["metrics/recall(B)"]
    return {
        "file": path.name,
        "trained_utc": ck.get("date"),
        "ultralytics_version": ck.get("version"),
        "class_names": [model.names[i] for i in sorted(model.names)],
        "parameters": int(sum(t.numel() for t in model.parameters())),
        "model_yaml": model.yaml.get("yaml_file"),
        "train_args": {k: ta.get(k) for k in (
            "epochs", "imgsz", "batch", "optimizer", "lr0", "patience",
            "seed", "pretrained", "data")},
        "final": {
            "precision": p,
            "recall": r,
            "f1": 2 * p * r / (p + r),
            "map50": tm["metrics/mAP50(B)"],
            "map50_95": tm["metrics/mAP50-95(B)"],
            "val_box_loss": tm["val/box_loss"],
            "val_cls_loss": tm["val/cls_loss"],
            "val_dfl_loss": tm["val/dfl_loss"],
        },
        "per_epoch": {
            "epoch": [int(e) for e in tr["epoch"]],
            "precision": tr["metrics/precision(B)"],
            "recall": tr["metrics/recall(B)"],
            "map50": tr["metrics/mAP50(B)"],
            "map50_95": tr["metrics/mAP50-95(B)"],
            "train_cls_loss": tr["train/cls_loss"],
            "val_cls_loss": tr["val/cls_loss"],
        },
    }


def style_axes(ax, title, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontfamily=FONT, pad=8)
    ax.set_xlabel("Epoch", fontsize=9, color=INK2, fontfamily=FONT)
    ax.set_ylabel(ylabel, fontsize=9, color=INK2, fontfamily=FONT)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)


def training_curves(data):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), dpi=200, facecolor=SURFACE)
    panels = [("map50", "mAP@50 on the validation split", "mAP@50"),
              ("map50_95", "mAP@50-95 on the validation split", "mAP@50-95")]
    for ax, (key, title, ylabel) in zip(axes, panels):
        style_axes(ax, title, ylabel)
        for name, d in data.items():
            ep = d["per_epoch"]
            ax.plot(ep["epoch"], ep[key], color=COLORS[name], linewidth=2, label=name)
            # Direct label at the last point, in text ink.
            ax.annotate(f"{name} {ep[key][-1]:.3f}", (ep["epoch"][-1], ep[key][-1]),
                        xytext=(-4, 6 if name == "YOLOv8" else -12),
                        textcoords="offset points", ha="right",
                        fontsize=8, color=INK, fontfamily=FONT)
        ax.set_xlim(0, 61)
        ax.set_ylim(0, max(max(d["per_epoch"][key]) for d in data.values()) * 1.18)
    axes[0].legend(frameon=False, fontsize=8, loc="lower right", prop={"family": FONT})
    fig.tight_layout()
    fig.savefig(OUT / "fig_training_curves.png", facecolor=SURFACE)
    plt.close(fig)


def final_metrics(data):
    keys = [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score"),
            ("map50", "mAP@50"), ("map50_95", "mAP@50-95")]
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=200, facecolor=SURFACE)
    style_axes(ax, "Final validation metrics (epoch 60)", "Score (0 to 1)")
    ax.set_xlabel("")
    width, gap = 0.36, 0.02
    for i, (name, d) in enumerate(data.items()):
        xs = [k + (i - 0.5) * (width + gap) for k in range(len(keys))]
        vals = [d["final"][k] for k, _ in keys]
        ax.bar(xs, vals, width=width, color=COLORS[name], label=name)
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.01, f"{v:.3f}", ha="center", va="bottom",
                    fontsize=7.5, color=INK, fontfamily=FONT)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([lbl for _, lbl in keys], fontfamily=FONT, fontsize=9)
    ax.set_ylim(0, 0.65)
    ax.legend(frameon=False, fontsize=8, loc="upper right", prop={"family": FONT})
    fig.tight_layout()
    fig.savefig(OUT / "fig_final_metrics.png", facecolor=SURFACE)
    plt.close(fig)


def per_class_map(ev):
    series = {k: ev["shared"][k] for k in ("YOLOv8", "YOLOv12", "Ensemble")}
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=200, facecolor=SURFACE)
    style_axes(ax, "Per-class mAP@50 on the test split", "mAP@50")
    ax.set_xlabel("")
    width, gap = 0.26, 0.02
    for i, (name, d) in enumerate(series.items()):
        vals = dict(zip(d["class_index"], d["ap50"]))
        xs = [k + (i - 1) * (width + gap) for k in range(5)]
        ys = [vals.get(k, 0.0) for k in range(5)]
        ax.bar(xs, ys, width=width, color=COLORS[name], label=name)
        for x, v in zip(xs, ys):
            ax.text(x, v + 0.01, f"{v:.2f}", ha="center", va="bottom", fontsize=6.5, color=INK, fontfamily=FONT)
    ax.set_xticks(range(5))
    ax.set_xticklabels(CLASS_LABELS, fontfamily=FONT, fontsize=8.5)
    ax.set_ylim(0, 1.0)
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=3, prop={"family": FONT})
    fig.tight_layout()
    fig.savefig(OUT / "fig_perclass_map50.png", facecolor=SURFACE)
    plt.close(fig)


def confusion_figure(ev):
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#ffffff", "#cde2fb", "#6da7ec", "#2a78d6", "#104281"])
    ticks = ["Healthy", "Cavity", "Gum infl.", "Plaque", "Tartar", "Background"]
    # Drawn at its printed size (6.3 in wide) so the cell labels stay legible.
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 2.75), dpi=300, facecolor=SURFACE)
    for ax, name in zip(axes, ("YOLOv8", "YOLOv12", "Ensemble")):
        m = np.array(ev["shared"][name]["confusion_matrix"])  # rows predicted, columns true
        col = m.sum(0, keepdims=True)
        norm = np.divide(m, col, out=np.zeros_like(m), where=col > 0)
        norm[:, 5] = 0  # background column has no ground truth to normalize by
        ax.imshow(norm, cmap=cmap, vmin=0, vmax=1)
        for r in range(6):
            for c in range(6):
                if c == 5 and r == 5:
                    continue
                v = norm[r, c] if c < 5 else m[r, c]
                txt = f"{v:.2f}" if c < 5 else f"{int(v)}"
                ax.text(c, r, txt, ha="center", va="center", fontsize=5,
                        color="#ffffff" if (c < 5 and v > 0.55) else INK, fontfamily=FONT)
        ax.set_xticks(range(6)); ax.set_yticks(range(6))
        ax.set_xticklabels(ticks, rotation=45, ha="right", fontsize=5.5, fontfamily=FONT, color=INK2)
        ax.set_yticklabels(ticks if name == "YOLOv8" else [], fontsize=5.5, fontfamily=FONT, color=INK2)
        ax.set_title(name, fontsize=8, color=INK, fontfamily=FONT)
        ax.set_xlabel("True class", fontsize=6, color=INK2, fontfamily=FONT)
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    axes[0].set_ylabel("Predicted class", fontsize=6, color=INK2, fontfamily=FONT)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(OUT / "fig_confusion_matrices.png", facecolor=SURFACE)
    plt.close(fig)


def main():
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
        ev = {"shared": json.loads((src / "job_b_test.json").read_text())}
        (OUT / "eval_results.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    if (OUT / "eval_results.json").exists():
        ev = json.loads((OUT / "eval_results.json").read_text(encoding="utf-8"))
        per_class_map(ev)
        confusion_figure(ev)
    data = {name: load(WEIGHTS / f) for name, f in MODELS.items()}
    (OUT / "training_metrics.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    training_curves(data)
    final_metrics(data)
    for name, d in data.items():
        f = d["final"]
        print(f"{name}: P={f['precision']:.4f} R={f['recall']:.4f} F1={f['f1']:.4f} "
              f"mAP50={f['map50']:.4f} mAP50-95={f['map50_95']:.4f} params={d['parameters']:,}")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
