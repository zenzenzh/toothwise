"""Per-model, per-class max confidence on the real uploaded patient photos.

The earlier 0.851/0.824/0.707/0.002/0.002 numbers came from the FUSED
same-label box fusion of both checkpoints, so they cannot be attributed to one
model. This separates them, which is what the comparison needs: if a class is
learned by v8 but not v12, that is an architecture/training problem; if
neither learns it on dataset images, the labels are the problem.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
WEIGHTS = {
    "yolov8": BACKEND / "models_weights" / "yolov8_dental.pt",
    "yolov12": BACKEND / "models_weights" / "yolov12_dental.pt",
}
IMG_DIR = BACKEND / "uploads" / "screenings"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

CONFIDENCE_FLOOR = 0.001


def main() -> int:
    from ultralytics import YOLO
    import numpy as np

    images = sorted(p for p in IMG_DIR.rglob("*")
                    if p.suffix.lower() in IMG_EXT)
    if not images:
        print(f"no images under {IMG_DIR}")
        return 1
    print(f"{len(images)} real patient photos from {IMG_DIR}\n")

    names: dict[int, str] = {}
    for tag, wpath in WEIGHTS.items():
        if not wpath.is_file():
            print(f"skip {tag}: {wpath} missing")
            continue
        model = YOLO(str(wpath))
        names = {int(k): v for k, v in model.names.items()}

        # class id -> highest confidence seen on any photo
        best_per_class: dict[int, float] = {}
        # images where the class fired at all above a usable threshold
        hit_imgs: dict[int, set] = {}

        # CPU inference is ~8s/image here, so stream a batch to keep the
        # loop in C and print progress. A per-image predict() call takes
        # well over ten minutes for both checkpoints and looks like a hang.
        for done, r in enumerate(model.predict([str(p) for p in images],
                                               conf=CONFIDENCE_FLOOR,
                                               stream=True, verbose=False), 1):
            name = Path(r.path).name
            if r.boxes is not None and len(r.boxes):
                conf = r.boxes.conf.cpu().numpy()
                cls = r.boxes.cls.cpu().numpy().astype(int)
                for c, s in zip(cls, conf):
                    c = int(c)
                    if s > best_per_class.get(c, -1.0):
                        best_per_class[c] = float(s)
                    if s >= 0.25:
                        hit_imgs.setdefault(c, set()).add(name)
            print(f"  {tag}: {done}/{len(images)} {name}", flush=True)

        print(f"=== {tag} ({wpath.name}) ===")
        print(f"{'id':>3}  {'name':20} {'max conf':>9} {'imgs>=0.25':>11}")
        for cid in sorted(names):
            mc = best_per_class.get(cid)
            print(f"{cid:>3}  {names[cid]:20} "
                  f"{(f'{mc:.4f}' if mc is not None else '   none'):>9} "
                  f"{len(hit_imgs.get(cid, ())):>11}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
