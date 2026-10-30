"""
Toothwise - second-round training to raise YOLOv8 / YOLOv12 scores.

The first run (60 epochs, imgsz 640, from COCO weights) plateaued at
mAP50 ~0.47 (v8) / ~0.45 (v12) by epoch ~35, so simply adding epochs will
not move the numbers. This run changes the things that do:

  1. Starts from the already fine-tuned dental checkpoints instead of COCO,
     so the GPU time goes into improvement rather than re-learning teeth.
  2. Trains at imgsz 960. Plaque, early cavities and tartar lines are small
     relative to a full-mouth photo; at 640 many of them shrink to a few
     pixels. This is usually the single biggest no-new-data gain.
  3. Cosine LR, a longer close_mosaic tail, and mild mixup for the
     imbalanced classes.
  4. Validates with test-time augmentation (TTA) as well as without, and
     prints both so the thesis can report them separately and honestly.

It does NOT fix the plaque class (AP50 ~0.07, 492 of 554 plaque boxes missed
entirely). That is a labelling problem - run audit_dataset.py and relabel /
add plaque images - no hyperparameter recovers it.

Colab (Runtime -> GPU), after uploading both .pt files and the dataset:

    !pip install -q 'ultralytics>=8.3'
    !python retrain_improved.py --data /content/merged_dataset/data_5class.yaml \
        --yolov8 /content/yolov8_dental.pt --yolov12 /content/yolov12_dental.pt

On a T4 expect roughly 2-4 h per model at imgsz 960; pass --imgsz 800 or
--epochs 60 if Colab time is short. If CUDA runs out of memory, pass
--batch 8 (or 4).
"""
import argparse
import json
import shutil
from pathlib import Path


def train_one(tag: str, weights: str, args) -> Path:
    from ultralytics import YOLO

    model = YOLO(weights)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        cos_lr=True,
        close_mosaic=15,
        mixup=0.1,
        lr0=0.002,          # fine-tuning from dental weights: lower than 0.01
        warmup_epochs=2,
        cache=True,
        seed=0,
        name=f"toothwise_{tag}_r2",
        exist_ok=True,
    )
    best = Path(model.trainer.best)
    out = Path(args.out_dir) / f"{tag}_dental_r2.pt"
    shutil.copy(best, out)
    return out


def score(weights: Path, args, tta: bool) -> dict:
    from ultralytics import YOLO

    m = YOLO(str(weights)).val(data=args.data, split=args.split,
                               imgsz=args.imgsz, augment=tta, verbose=False)
    p, r = float(m.box.mp), float(m.box.mr)
    return {
        "precision": round(p * 100, 2),
        "recall": round(r * 100, 2),
        "f1": round((2 * p * r / (p + r) if p + r else 0.0) * 100, 2),
        "map50": round(float(m.box.map50) * 100, 2),
        "map50_95": round(float(m.box.map) * 100, 2),
        "per_class_ap50": [round(float(x) * 100, 2) for x in m.box.ap50],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--yolov8", required=True, help="current yolov8_dental.pt")
    ap.add_argument("--yolov12", required=True, help="current yolov12_dental.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--batch", type=int, default=-1, help="-1 = auto-fit GPU")
    ap.add_argument("--patience", type=int, default=30)
    ap.add_argument("--split", default="val", choices=["val", "test"])
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--only", choices=["yolov8", "yolov12"],
                    help="train just one model (e.g. second Colab session)")
    args = ap.parse_args()

    results = {}
    for tag, w in (("yolov8", args.yolov8), ("yolov12", args.yolov12)):
        if args.only and args.only != tag:
            continue
        new_w = train_one(tag, w, args)
        results[tag] = {
            "weights": str(new_w),
            "plain": score(new_w, args, tta=False),
            "tta": score(new_w, args, tta=True),
        }
        print(f"\n{tag}: {json.dumps(results[tag], indent=2)}", flush=True)

    Path(args.out_dir, "retrain_r2_results.json").write_text(json.dumps(results, indent=2))
    print("\n| Model | Eval | mAP50 | mAP50-95 | Precision | Recall | F1 |")
    print("|---|---|---|---|---|---|---|")
    for tag, r in results.items():
        for mode in ("plain", "tta"):
            s = r[mode]
            print(f"| {tag} | {mode} | {s['map50']} | {s['map50_95']} | "
                  f"{s['precision']} | {s['recall']} | {s['f1']} |")


if __name__ == "__main__":
    main()
