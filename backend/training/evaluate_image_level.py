"""
Toothwise - image-level (per photo) evaluation of YOLOv8, YOLOv12 and the
ensemble.

evaluate_models.py scores BOXES: a finding only counts if the predicted box
overlaps the annotated box by IoU >= 0.5. This script scores PHOTOS, which
is the question a screening tool actually answers: "does this photo show a
cavity / gum inflammation / plaque / tartar?"

For every image and every class:
    ground truth = the label file has at least one box of that class
    prediction   = the model's highest confidence for that class >= threshold
and from that, per class: accuracy, precision, recall (sensitivity),
specificity, F1, plus AUROC (threshold-free). An extra "any_finding" row
asks "does this photo show ANY problem (cavity, gum inflammation, plaque or
tartar)?" - the patient-facing screening decision.

Two threshold settings are reported, never mixed:
  deployed - the thresholds the live app uses (0.25, cavity 0.5).
  tuned    - per class, the threshold that maximises F1 on the VALIDATION
             split, then applied unchanged to the evaluation split. Thresholds
             are never chosen on the split being reported - that would
             inflate the numbers. Only available when --split test.

The ensemble reproduces app/ml/yolo_detector.py::_fuse (same-label boxes
with IoU >= 0.5 merge; +0.08 confidence when both models agree, cap 0.98).
The app's braces-bracket filter needs pixel colours and is not applied.

What to write in Chapter 4: state that these are image-level metrics, the
split, the number of images and positives per class (the table prints them),
and which threshold setting each row uses.

Colab (Runtime -> GPU):
    !pip install -q 'ultralytics>=8.3'
    !python evaluate_image_level.py --data /content/merged_dataset/data_5class.yaml \
        --yolov8 /content/yolov8_dental.pt --yolov12 /content/yolov12_dental.pt \
        --split test

Predictions are cached to image_level_cache_<split>.json, so re-running
(e.g. after editing thresholds) does not repeat inference. Delete the cache
after retraining - it is keyed by weights filename, not file contents.

Output: a markdown table on stdout and in image_level_results.md, and every
number in image_level_results.json.

Self-check (no GPU, dataset or ultralytics needed):
    python test_evaluate_image_level.py
"""
import argparse
import json
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# Must match app/config.py so "deployed" means what the app really does.
DEPLOYED_CONF = 0.25
DEPLOYED_CLASS_CONF = {"cavity": 0.5}
ENSEMBLE_IOU = 0.5
AGREEMENT_BOOST = 0.08
FUSED_CAP = 0.98

# Detections below this never change an image-level decision at any
# threshold we report, and dropping them keeps the fusion loop fast.
KEEP_FLOOR = 0.05
MAX_DETS_PER_MODEL = 100
PREDICT_CHUNK = 32  # images per predict() call; bounds RAM use

HEALTHY = "healthy_tooth"
ANY_FINDING = "any_finding"
THRESHOLD_GRID = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95


# ---------------------------------------------------------------- dataset

def _read_yaml(path: Path) -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def class_names(cfg: dict) -> list[str]:
    names = cfg["names"]
    if isinstance(names, dict):
        return [names[k] for k in sorted(names, key=int)]
    return list(names)


def _split_key(cfg: dict, split: str) -> str:
    if split in cfg:
        return split
    if split == "val" and "valid" in cfg:
        return "valid"
    raise SystemExit(f"data yaml has no '{split}' entry (keys: {sorted(cfg)})")


def split_images(yaml_path: Path, cfg: dict, split: str) -> list[Path]:
    """Images of a split, resolved the way Ultralytics does: relative to
    `path:` (itself relative to the yaml), as a dir, a .txt list, or a list."""
    root = Path(cfg.get("path") or ".")
    if not root.is_absolute():
        root = (yaml_path.parent / root).resolve()
    if not root.exists():  # Roboflow's "path: ../" often points nowhere useful
        root = yaml_path.parent.resolve()

    entries = cfg[_split_key(cfg, split)]
    entries = entries if isinstance(entries, list) else [entries]
    images: list[Path] = []
    for e in entries:
        p = Path(e)
        if not p.is_absolute():
            p = root / p
            if not p.exists():  # "../valid/images" from a Roboflow export
                p = yaml_path.parent / e.lstrip("./")
        if p.is_dir():
            images += [q for q in p.rglob("*") if q.suffix.lower() in IMG_EXT]
        elif p.suffix == ".txt" and p.is_file():
            for line in p.read_text().splitlines():
                if line.strip():
                    q = Path(line.strip())
                    images.append(q if q.is_absolute() else root / q)
        else:
            raise SystemExit(f"split '{split}' entry not found: {p}")
    return sorted(set(images))


def label_path(img: Path) -> Path:
    """Ultralytics convention: last /images/ -> /labels/, extension -> .txt."""
    parts = list(img.parts)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "images":
            parts[i] = "labels"
            break
    return Path(*parts).with_suffix(".txt")


def ground_truth(img: Path) -> set[int]:
    lp = label_path(img)
    if not lp.is_file():
        return set()  # background-only image
    present = set()
    for line in lp.read_text().splitlines():
        tok = line.split()
        if tok:
            present.add(int(float(tok[0])))
    return present


# ---------------------------------------------------------------- inference

def predict(weights: str, images: list[Path], imgsz: int, tta: bool) -> dict:
    """{image path: [[cls, conf, x1, y1, x2, y2] (normalised)]}"""
    from ultralytics import YOLO

    model = YOLO(weights)
    out = {}
    # Ultralytics decodes a list source into memory all at once, which runs
    # Colab out of RAM on a few thousand photos - so feed it small chunks.
    # Results come back in input order; key by our own path, not r.path.
    for start in range(0, len(images), PREDICT_CHUNK):
        chunk = images[start:start + PREDICT_CHUNK]
        results = model.predict([str(p) for p in chunk], conf=KEEP_FLOOR,
                                imgsz=imgsz, augment=tta, verbose=False)
        for img, r in zip(chunk, results):
            dets = []
            if r.boxes is not None and len(r.boxes):
                for c, s, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(),
                                   r.boxes.xyxyn.tolist()):
                    dets.append([int(c), float(s), *b])
            dets.sort(key=lambda d: d[1], reverse=True)
            out[str(img)] = dets[:MAX_DETS_PER_MODEL]
        done = start + len(chunk)
        if done % 320 == 0 or done == len(images):
            print(f"  {Path(weights).name}: {done}/{len(images)}", flush=True)
    return out


def _iou(a, b) -> float:
    ix1, iy1 = max(a[2], b[2]), max(a[3], b[3])
    ix2, iy2 = min(a[4], b[4]), min(a[5], b[5])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = ((a[4] - a[2]) * (a[5] - a[3]) + (b[4] - b[2]) * (b[5] - b[3]) - inter)
    return inter / union if union > 0 else 0.0


def fuse(d8: list, d12: list) -> list:
    """Same rule as app/ml/yolo_detector.py::_fuse, on [cls, conf, box] rows."""
    pool = [(d, "v8") for d in d8] + [(d, "v12") for d in d12]
    pool.sort(key=lambda t: t[0][1], reverse=True)
    used = [False] * len(pool)
    fused = []
    for i, (det, src) in enumerate(pool):
        if used[i]:
            continue
        used[i] = True
        sources = {src}
        for j in range(i + 1, len(pool)):
            other, osrc = pool[j]
            if not used[j] and other[0] == det[0] and _iou(det, other) >= ENSEMBLE_IOU:
                used[j] = True
                sources.add(osrc)
        conf = min(det[1] + (AGREEMENT_BOOST if len(sources) > 1 else 0.0), FUSED_CAP)
        fused.append([det[0], conf, *det[2:]])
    return fused


def class_scores(dets: list, nc: int) -> list[float]:
    """Highest confidence per class in one image (0.0 when absent)."""
    s = [0.0] * nc
    for d in dets:
        if 0 <= d[0] < nc and d[1] > s[d[0]]:
            s[d[0]] = d[1]
    return s


# ---------------------------------------------------------------- metrics

def confusion(truth: list[bool], score: list[float], thr: float) -> dict:
    tp = fp = fn = tn = 0
    for t, s in zip(truth, score):
        p = s >= thr
        if t and p:
            tp += 1
        elif p:
            fp += 1
        elif t:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _ratio(a: int, b: int):
    return a / b if b else None


def rates(c: dict) -> dict:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    p, r = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    return {
        "accuracy": _ratio(tp + tn, tp + fp + fn + tn),
        "precision": p,
        "recall": r,
        "specificity": _ratio(tn, tn + fp),
        "f1": (2 * p * r / (p + r)) if p and r else (0.0 if p is not None and r is not None else None),
    }


def auroc(truth: list[bool], score: list[float]):
    """Mann-Whitney AUROC with tie handling; None if one class is absent."""
    pos = [s for t, s in zip(truth, score) if t]
    neg = [s for t, s in zip(truth, score) if not t]
    if not pos or not neg:
        return None
    ranked = sorted((s, t) for t, s in zip(truth, score))
    rank_sum, i = 0.0, 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1
        avg = (i + j + 1) / 2  # 1-based average rank of the tie block
        rank_sum += avg * sum(1 for k in range(i, j) if ranked[k][1])
        i = j
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def best_f1_threshold(truth: list[bool], score: list[float]) -> float:
    best, best_thr = -1.0, DEPLOYED_CONF
    for thr in THRESHOLD_GRID:
        f1 = rates(confusion(truth, score, thr))["f1"] or 0.0
        if f1 > best:
            best, best_thr = f1, thr
    return best_thr


def rows_for(names: list[str], gts: list[set], scores: list[list[float]]) -> dict:
    """{row name: (truth list, score list)} incl. the any_finding row."""
    rows = {}
    for k, n in enumerate(names):
        rows[n] = ([k in g for g in gts], [s[k] for s in scores])
    finding_ids = [k for k, n in enumerate(names) if n != HEALTHY]
    rows[ANY_FINDING] = ([any(k in g for k in finding_ids) for g in gts],
                         [max(s[k] for k in finding_ids) for s in scores])
    return rows


def deployed_threshold(row: str) -> float:
    return DEPLOYED_CLASS_CONF.get(row, DEPLOYED_CONF)


def evaluate_rows(rows: dict, thresholds: dict) -> dict:
    out = {}
    for name, (truth, score) in rows.items():
        thr = thresholds[name]
        c = confusion(truth, score, thr)
        out[name] = {"threshold": thr, "positives": sum(truth), "images": len(truth),
                     **c, **rates(c), "auroc": auroc(truth, score)}
    per_class = [v for k, v in out.items() if k != ANY_FINDING]
    out["macro_avg"] = {m: _mean([v[m] for v in per_class])
                        for m in ("accuracy", "precision", "recall", "specificity", "f1", "auroc")}
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------- reporting

def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def markdown(results: dict, split: str, n_images: int) -> str:
    lines = [f"# Image-level evaluation ({split} split, {n_images} images)\n"]
    for setting, by_model in results.items():
        lines.append(f"\n## Thresholds: {setting}\n")
        lines.append("| Model | Class | Thr | Positives | Accuracy | Precision | "
                     "Recall | Specificity | F1 | AUROC |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for model, res in by_model.items():
            for row, v in res.items():
                if row == "macro_avg":
                    lines.append(f"| {model} | **macro avg (5 classes)** | | | "
                                 f"{_pct(v['accuracy'])} | {_pct(v['precision'])} | "
                                 f"{_pct(v['recall'])} | {_pct(v['specificity'])} | "
                                 f"{_pct(v['f1'])} | {_pct(v['auroc'])} |")
                else:
                    lines.append(f"| {model} | {row} | {v['threshold']:.2f} | "
                                 f"{v['positives']}/{v['images']} | {_pct(v['accuracy'])} | "
                                 f"{_pct(v['precision'])} | {_pct(v['recall'])} | "
                                 f"{_pct(v['specificity'])} | {_pct(v['f1'])} | "
                                 f"{_pct(v['auroc'])} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- driver

def deployed_filter(dets: list, names: list[str]) -> list:
    """Per-model thresholds the app applies BEFORE fusion."""
    return [d for d in dets
            if 0 <= d[0] < len(names) and d[1] >= deployed_threshold(names[d[0]])]


def model_scores(preds: dict, images: list[Path], names: list[str],
                 deployed: bool) -> dict:
    """{model name: [per-image class scores]} for v8, v12 and the ensemble.

    deployed=True filters each model's boxes the way the app does before
    fusing, so the ensemble matches the live pipeline. deployed=False keeps
    every box down to KEEP_FLOOR so thresholds can be tuned afterwards."""
    keyed = {m: [p.get(str(img), []) for img in images] for m, p in preds.items()}
    if deployed:
        keyed = {m: [deployed_filter(d, names) for d in dets] for m, dets in keyed.items()}
    nc = len(names)
    out = {m: [class_scores(d, nc) for d in dets] for m, dets in keyed.items()}
    if "YOLOv8" in keyed and "YOLOv12" in keyed:
        out["Ensemble"] = [class_scores(fuse(a, b), nc)
                           for a, b in zip(keyed["YOLOv8"], keyed["YOLOv12"])]
    return out


def load_predictions(split: str, images: list[Path], weights: dict, args) -> dict:
    cache = Path(args.out_dir) / f"image_level_cache_{split}.json"
    data = json.loads(cache.read_text()) if cache.is_file() else {}
    key_of = {m: f"{Path(w).name}|imgsz={args.imgsz}|tta={args.tta}"
              for m, w in weights.items()}
    for m, w in weights.items():
        cached = data.get(key_of[m], {})
        if all(str(i) in cached for i in images):
            print(f"{m} {split}: using cached predictions", flush=True)
            continue
        print(f"{m} {split}: predicting {len(images)} images...", flush=True)
        data[key_of[m]] = predict(w, images, args.imgsz, args.tta)
        cache.write_text(json.dumps(data))
    return {m: data[key_of[m]] for m in weights}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="dataset yaml")
    ap.add_argument("--yolov8", help="yolov8_dental.pt")
    ap.add_argument("--yolov12", help="yolov12_dental.pt")
    ap.add_argument("--split", default="test", choices=["val", "test"],
                    help="split to report (default test)")
    ap.add_argument("--imgsz", type=int, default=640,
                    help="inference size; use 960 for retrain_improved.py weights")
    ap.add_argument("--tta", action="store_true", help="test-time augmentation")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    weights = {m: w for m, w in (("YOLOv8", args.yolov8), ("YOLOv12", args.yolov12)) if w}
    if not weights:
        raise SystemExit("pass --yolov8 and/or --yolov12")

    yaml_path = Path(args.data).resolve()
    cfg = _read_yaml(yaml_path)
    names = class_names(cfg)

    def prepare(split):
        images = split_images(yaml_path, cfg, split)
        if not images:
            raise SystemExit(f"no images found for split '{split}'")
        gts = [ground_truth(i) for i in images]
        return images, gts, load_predictions(split, images, weights, args)

    images, gts, preds = prepare(args.split)
    results = {"deployed": {}}
    for m, s in model_scores(preds, images, names, deployed=True).items():
        rows = rows_for(names, gts, s)
        results["deployed"][m] = evaluate_rows(rows, {r: deployed_threshold(r) for r in rows})

    if args.split == "test":
        val_images, val_gts, val_preds = prepare("val")
        val_scores = model_scores(val_preds, val_images, names, deployed=False)
        results["tuned on val (max F1)"] = {}
        for m, s in model_scores(preds, images, names, deployed=False).items():
            val_rows = rows_for(names, val_gts, val_scores[m])
            thr = {r: best_f1_threshold(t, sc) for r, (t, sc) in val_rows.items()}
            results["tuned on val (max F1)"][m] = evaluate_rows(rows_for(names, gts, s), thr)
    else:
        print("\n(--split val: skipping tuned thresholds; tuning and reporting on "
              "the same split would inflate the numbers)")

    md = markdown(results, args.split, len(images))
    print("\n" + md)
    out = Path(args.out_dir)
    (out / "image_level_results.md").write_text(md)
    (out / "image_level_results.json").write_text(json.dumps(
        {"split": args.split, "images": len(images), "imgsz": args.imgsz,
         "tta": args.tta, "class_names": names, "results": results}, indent=2))
    print(f"Saved {out.resolve() / 'image_level_results.md'} and .json")


if __name__ == "__main__":
    main()
