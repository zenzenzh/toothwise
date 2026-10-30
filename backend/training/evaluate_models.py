"""
Toothwise — YOLOv8 vs YOLOv12 model evaluation

Produces the real accuracy/precision/recall/mAP/inference-speed comparison
table for your thesis's Chapter 4 (the "Expected Results" table in your
session notes, filled in with real numbers instead of placeholders).

This is intentionally separate from the running backend: accuracy metrics
are a property of a trained model against a labeled test set, not
something you can compute from live, unlabeled patient photos. Run this
once after training finishes (in Colab, or locally if you have both .pt
files and the dataset).

Requirements: ultralytics (already in backend/requirements.txt)
    pip install ultralytics

Usage:
    python evaluate_models.py \
        --data /path/to/data.yaml \
        --yolov8 /path/to/yolov8_dental.pt \
        --yolov12 /path/to/yolov12_dental.pt \
        --split test

data.yaml must point at a labeled split (train/valid/test) - see
backend/training/data.yaml.template. Both models MUST be evaluated
against the exact same split for the comparison to be meaningful.

Output: prints a markdown table to stdout AND saves it to
comparison_results.md, ready to paste into your thesis.
"""
import argparse
import json
import time
from pathlib import Path

def evaluate(weights_path: str, data_yaml: str, split: str,
             tta: bool = False, imgsz: int = 640) -> dict:
    from ultralytics import YOLO

    model = YOLO(weights_path)

    # model.val() runs the standard YOLO validation loop: computes
    # precision, recall, mAP50, mAP50-95 against the labeled split.
    # augment=True is test-time augmentation (flips + rescales, merged).
    # Report it as its own row - it is slower and not what the live app runs.
    metrics = model.val(data=data_yaml, split=split, imgsz=imgsz,
                        augment=tta, verbose=False)

    precision = float(metrics.box.mp)       # mean precision across classes
    recall = float(metrics.box.mr)          # mean recall across classes
    map50 = float(metrics.box.map50)
    map50_95 = float(metrics.box.map)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Separate timing pass: model.val() includes NMS/loss overhead not
    # representative of single-image inference latency in production, so
    # time a handful of solo predict() calls instead, on the same images
    # val() just used, and report the average per-image time.
    val_images = list(Path(data_yaml).parent.glob(f"{split}/images/*"))[:20] or \
                 list(Path(data_yaml).parent.glob(f"{split}/images/**/*"))[:20]
    times_ms = []
    for img_path in val_images:
        t0 = time.perf_counter()
        model.predict(str(img_path), verbose=False)
        times_ms.append((time.perf_counter() - t0) * 1000)
    avg_ms = sum(times_ms) / len(times_ms) if times_ms else None

    return {
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "map50": round(map50 * 100, 2),
        "map50_95": round(map50_95 * 100, 2),
        "f1": round(f1 * 100, 2),
        "avg_inference_ms": round(avg_ms, 2) if avg_ms else None,
        "n_timed_images": len(times_ms),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Path to data.yaml")
    parser.add_argument("--yolov8", required=True, help="Path to trained YOLOv8 .pt weights")
    parser.add_argument("--yolov12", required=True, help="Path to trained YOLOv12 .pt weights")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--tta", action="store_true",
                        help="Evaluate with test-time augmentation")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    print(f"Evaluating YOLOv8 ({args.yolov8}) on '{args.split}' split...")
    v8 = evaluate(args.yolov8, args.data, args.split, args.tta, args.imgsz)

    print(f"Evaluating YOLOv12 ({args.yolov12}) on '{args.split}' split...")
    v12 = evaluate(args.yolov12, args.data, args.split, args.tta, args.imgsz)

    table = (
        "| Model | mAP50 | mAP50-95 | Precision | Recall | F1 Score | Avg Inference |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| YOLOv8  | {v8['map50']}% | {v8['map50_95']}% | {v8['precision']}% | {v8['recall']}% | {v8['f1']}% | {v8['avg_inference_ms']} ms |\n"
        f"| YOLOv12 | {v12['map50']}% | {v12['map50_95']}% | {v12['precision']}% | {v12['recall']}% | {v12['f1']}% | {v12['avg_inference_ms']} ms |\n"
    )

    print("\n" + table)

    out = Path("comparison_results.md")
    out.write_text(
        f"# Toothwise Model Comparison — YOLOv8 vs YOLOv12\n\n"
        f"Evaluated on the `{args.split}` split of `{args.data}` "
        f"(imgsz {args.imgsz}, TTA {'on' if args.tta else 'off'}).\n\n"
        f"{table}\n"
        f"Raw metrics (JSON):\n\n```json\n{json.dumps({'yolov8': v8, 'yolov12': v12}, indent=2)}\n```\n"
    )
    print(f"Saved to {out.resolve()}")


if __name__ == "__main__":
    main()
