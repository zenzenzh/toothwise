"""
Self-check for evaluate_image_level.py. Run it directly:

    python test_evaluate_image_level.py

Needs only PyYAML - model inference is stubbed, so no GPU, dataset or
ultralytics. Pins the metric arithmetic, the app-matching fusion rule, the
Roboflow folder layout, and that thresholds are tuned on val, not test.
"""
import json
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "evaluate_image_level.py"
ns = {"__name__": "evaluate_image_level_under_test", "__file__": str(SCRIPT)}
exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), ns)

NAMES = ["healthy_tooth", "cavity", "gum_inflammation", "plaque", "tartar"]
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def close(a, b):
    return a is not None and abs(a - b) < 1e-9


# --- metric arithmetic ----------------------------------------------------
truth = [True, True, False, False, True]
score = [0.9, 0.3, 0.6, 0.1, 0.0]
c = ns["confusion"](truth, score, 0.5)
check(c == {"tp": 1, "fp": 1, "fn": 2, "tn": 1}, f"confusion: {c}")
r = ns["rates"](c)
check(close(r["accuracy"], 2 / 5), f"accuracy {r}")
check(close(r["precision"], 1 / 2), f"precision {r}")
check(close(r["recall"], 1 / 3), f"recall {r}")
check(close(r["specificity"], 1 / 2), f"specificity {r}")
check(close(r["f1"], 0.4), f"f1 {r}")
check(close(ns["auroc"]([True, False], [0.9, 0.1]), 1.0), "auroc perfect")
check(close(ns["auroc"]([True, False], [0.5, 0.5]), 0.5), "auroc tie")
# pos {0.9,0.3,0.0} vs neg {0.6,0.1}: wins 0.9>both(2), 0.3>0.1(1) -> 3/6
check(close(ns["auroc"](truth, score), 0.5), "auroc mixed")
check(ns["auroc"]([True, True], [0.1, 0.2]) is None, "auroc single class")

# --- fusion mirrors app/ml/yolo_detector.py::_fuse ------------------------
box = [0.1, 0.1, 0.3, 0.3]
f = ns["fuse"]([[1, 0.60, *box]], [[1, 0.50, *box]])
check(len(f) == 1 and close(f[0][1], 0.68), f"agreement boost: {f}")
f = ns["fuse"]([[1, 0.95, *box]], [[1, 0.90, *box]])
check(close(f[0][1], 0.98), f"boost cap: {f}")
f = ns["fuse"]([[1, 0.60, *box]], [[2, 0.50, *box]])
check(len(f) == 2, "different labels never merge")
f = ns["fuse"]([[1, 0.60, *box]], [[1, 0.50, 0.6, 0.6, 0.9, 0.9]])
check(len(f) == 2 and close(max(d[1] for d in f), 0.60), "no overlap, no boost")

# --- deployed filter: cavity needs 0.5, others 0.25 -----------------------
kept = ns["deployed_filter"]([[1, 0.45, *box], [1, 0.55, *box], [4, 0.26, *box],
                              [4, 0.20, *box]], NAMES)
check([(d[0], d[1]) for d in kept] == [(1, 0.55), (4, 0.26)], f"deployed filter {kept}")

# --- end to end on a Roboflow-shaped dataset ------------------------------
# image name -> (label class ids, v8 dets, v12 dets)
B = box
CASES = {
    "val": {
        "v1": ([1], [[1, 0.40, *B]], [[1, 0.35, *B]]),
        "v2": ([], [[1, 0.30, *B]], []),
        "v3": ([4], [[4, 0.30, *B]], [[4, 0.20, *B]]),
        "v4": ([], [], []),
    },
    "test": {
        "t1": ([1, 4], [[1, 0.60, *B], [4, 0.30, *B]], [[1, 0.55, *B]]),
        "t2": ([], [[3, 0.10, *B]], []),
        "t3": ([1], [[1, 0.42, *B]], [[1, 0.40, *B]]),  # below app cavity floor
        "t4": ([2], [], [[2, 0.70, *B]]),
    },
}

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "ds"
    preds = {"YOLOv8": {}, "YOLOv12": {}}
    for split, folder in (("val", "valid"), ("test", "test")):
        (root / folder / "images").mkdir(parents=True)
        (root / folder / "labels").mkdir(parents=True)
        for name, (labels, d8, d12) in CASES[split].items():
            img = root / folder / "images" / f"{name}.jpg"
            img.write_bytes(b"")
            if labels:  # background images get no label file at all
                (root / folder / "labels" / f"{name}.txt").write_text(
                    "".join(f"{c} 0.5 0.5 0.1 0.1\n" for c in labels))
            preds["YOLOv8"][str(img)] = d8
            preds["YOLOv12"][str(img)] = d12
    # Roboflow export style: path points nowhere, entries are ../x/images
    (root / "data.yaml").write_text(
        "train: ../train/images\nval: ../valid/images\ntest: ../test/images\n"
        f"nc: 5\nnames: {NAMES}\n")

    calls = []

    def fake_predict(weights, images, imgsz, tta):
        calls.append((Path(weights).name, len(images)))
        model = "YOLOv8" if "v8" in weights else "YOLOv12"
        return {str(i): preds[model][str(i)] for i in images}

    ns["predict"] = fake_predict
    out = Path(tmp) / "out"
    out.mkdir()
    sys.argv = ["x", "--data", str(root / "data.yaml"), "--yolov8", "v8.pt",
                "--yolov12", "v12.pt", "--split", "test", "--out-dir", str(out)]
    ns["main"]()

    res = json.loads((out / "image_level_results.json").read_text())
    check(res["images"] == 4, f"image count {res['images']}")
    dep = res["results"]["deployed"]
    # Ensemble, deployed: cavity on t1 only (t3 is under the 0.5 floor).
    cav = dep["Ensemble"]["cavity"]
    check((cav["tp"], cav["fp"], cav["fn"], cav["tn"]) == (1, 0, 1, 2), f"deployed cavity {cav}")
    # v12 alone found gum_inflammation on t4.
    gum = dep["Ensemble"]["gum_inflammation"]
    check((gum["tp"], gum["fn"]) == (1, 0), f"deployed gum {gum}")
    anyf = dep["Ensemble"]["any_finding"]
    # t3's 0.42 cavity is under the app's floor, so it is missed here too.
    check(anyf["positives"] == 3 and anyf["tp"] == 2 and anyf["fn"] == 1,
          f"any_finding {anyf}")

    tuned = res["results"]["tuned on val (max F1)"]["Ensemble"]["cavity"]
    # On val, ensemble cavity scores are v1=0.48 (0.40+boost), v2=0.30:
    # thresholds 0.35..0.45 separate them; max-F1 picks the lowest, 0.35.
    check(close(tuned["threshold"], 0.35), f"tuned threshold {tuned['threshold']}")
    check((tuned["tp"], tuned["fn"]) == (2, 0), f"tuned cavity {tuned}")
    check("macro_avg" in dep["YOLOv8"], "macro avg present")
    check((out / "image_level_results.md").read_text().startswith("# Image-level"),
          "markdown written")

    # Second run must hit the cache, not re-predict.
    n = len(calls)
    ns["main"]()
    check(len(calls) == n, f"cache not used: {calls}")

if failures:
    print("FAIL")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("all image-level evaluation checks passed")
