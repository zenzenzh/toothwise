"""
Toothwise - dataset class-balance audit.

Answers one question before you spend GPU time: is every class in
data_5class.yaml actually learnable from the data you have?

Motivation: the shipped checkpoints report healthy_tooth and plaque at a
maximum confidence of 0.002 (noise) on 48 real patient photos, i.e. those
two classes were never learned. A class name sitting in the yaml does NOT
mean the class has usable training data - Roboflow merges routinely leave
a declared class with zero boxes. No hyperparameter fixes that; only data
does. This script makes the deficit explicit so the retrain decision is
informed rather than guessed.

Run it BEFORE retraining, and again after any dataset change.

    Colab - upload audit_dataset.py to /content, then either:
        !python /content/audit_dataset.py --data /content/merged_dataset/data_5class.yaml
    ...or just paste the whole file into a cell and Run. --data is optional:
    with no arguments it searches for the dataset yaml itself, which is the
    usual case when the path differs between Colab runs.

    Local:
        python audit_dataset.py --data merged_dataset/data_5class.yaml

Standard library only apart from the yaml: PyYAML is used when importable
(any runtime that can train YOLO has it), with a small hand-rolled reader as
a fallback so this still runs in a bare runtime. No ultralytics, torch or
numpy needed, so it runs before the training environment is set up.

Self-check:
    python test_audit_dataset.py

Findings it reports:
  - instances per class, and the share of the dataset each one holds
  - images per class, and the median boxes/image
  - how often a class co-occurs with a pathology class on the same tooth
    (a healthy_tooth box sitting next to a cavity box for the same tooth is
    a labelling contradiction, not just imbalance)
  - background-only images (an image whose label file is empty or missing)
    these teach "nothing here" implicitly and are the honest source of a
    "healthy mouth" signal - they are NOT the same thing as a
    healthy_tooth box
  - a per-class verdict: DEAD / STARVED / WEAK / OK
"""
import argparse
import os
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

# Where a dataset yaml tends to live when this runs unattended. Ordered by
# likelihood so auto-discovery picks the intended one when several match.
SEARCH_ROOTS = ("/content", "/content/drive/MyDrive")
# Directories that never contain a user's dataset but are enormous.
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "site-packages",
             "__pycache__", ".cache", ".ipynb_checkpoints", "build", "dist"}
MAX_DEPTH = 5
MAX_HITS = 40

# Floor below which a class cannot be learned reliably, then the point at
# which it is safe to train on. Rough rules of thumb for a few-hundred-image
# capstone dataset, not a law - the verdict is a prompt to look, not a gate.
DEAD_BELOW = 30
STARVED_BELOW = 100
WEAK_BELOW = 300

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def _manual_yaml(text: str) -> dict:
    """
    Last-resort reader for the flat `path/train/val/names` YAML that Roboflow
    emits. Only used when PyYAML is unavailable. It understands the three
    shapes seen in the wild - list, dict and inline - which is all, and it
    is not a YAML parser: quoted keys, flow mappings, anchors and comments in
    odd places will defeat it. Prefer PyYAML.
    """
    out: dict = {"path": ".", "train": None, "val": None, "test": None,
                 "names": {}, "nc": None}
    section = None

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if not line.startswith((" ", "\t")):
            key, _, val = line.partition(":")
            key, val = _unquote(key), val.strip()
            section = None
            if key == "names":
                if val.startswith("["):          # names: [a, b, c]
                    items = [_unquote(v) for v in val.strip("[]").split(",")]
                    out["names"] = {i: n for i, n in enumerate(items) if n}
                else:
                    section = "names"
                continue
            if key == "nc":
                out["nc"] = val or None
            elif key in ("path", "train", "val", "test"):
                out[key] = val or True
            else:
                out[key] = val or True
            continue

        if section != "names":
            continue
        stripped = line.strip()
        if stripped.startswith("- "):            # list form
            out["names"][len(out["names"])] = _unquote(stripped[2:])
            continue
        if stripped == "-":
            continue
        k, _, v = stripped.partition(":")      # dict form
        try:
            out["names"][int(_unquote(k))] = _unquote(v)
        except ValueError:
            pass
    return out


def _normalise_names(raw) -> dict:
    """Coerce whatever `names` was into {int: str}. PyYAML hands back either
    a list (positional) or a mapping (explicit), and either may have string
    keys. Anything unrecognised yields {} so the caller can flag it."""
    if isinstance(raw, dict):
        out = {}
        for k, v in raw.items():
            try:
                out[int(_unquote(str(k)))] = str(v).strip()
            except (TypeError, ValueError):
                continue
        return out
    if isinstance(raw, (list, tuple)):
        return {i: str(v).strip() for i, v in enumerate(raw)
                if v is not None and str(v).strip()}
    return {}


def parse_yaml(path: Path) -> dict:
    """
    Read the dataset yaml. Uses PyYAML when it is importable - which is
    always true in any runtime capable of training YOLO - and only falls back
    to a hand-rolled reader otherwise. A hand-rolled reader looked like the
    dependency-free option, then returned zero classes for a real Roboflow
    export twice in a row, which is the worst possible failure for this
    script: it reports an empty table and then concludes every class is
    fine. PyYAML is the correct tool and it is already installed.
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")

    try:
        import yaml
        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            loaded = {}
    except Exception:
        loaded = _manual_yaml(text)

    out = {k: loaded.get(k) for k in ("path", "train", "val", "test", "nc")}
    out["names"] = _normalise_names(loaded.get("names"))
    out["root"] = path.parent

    declared = out.get("path")
    if isinstance(declared, str) and declared.strip() not in (".", "./", ""):
        out["root"] = (path.parent / declared).resolve()
    else:
        out["root"] = path.parent.resolve()
    return out


def label_dir_for(images_dir: Path) -> Path:
    """
    Ultralytics layout puts labels as a sibling of images inside the split
    dir: root/train/images/x.jpg  ->  root/train/labels/x.txt
    """
    return images_dir.parent / "labels"


def scan_split(images_dir: Path) -> dict:
    images = [p for p in sorted(images_dir.rglob("*")) if p.suffix.lower() in IMG_EXT]
    labels_dir = label_dir_for(images_dir)

    boxes: Counter = Counter()            # total boxes per class id
    per_class_per_image: dict = defaultdict(list)  # cid -> [count in each image it appears in]
    images_with_class: Counter = Counter()  # cid -> number of images containing it
    cooccur: Counter = Counter()          # frozenset/tuple of classes -> images
    empty = missing = unreadable = 0

    for img in images:
        txt = labels_dir / (img.stem + ".txt")
        if not txt.exists():
            missing += 1          # ultralytics reads this as "no annotations"
            continue
        try:
            raw = txt.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unreadable += 1
            continue

        ids: list[int] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ids.append(int(float(line.split()[0])))
            except (ValueError, IndexError):
                unreadable += 1
                continue

        if not ids:
            empty += 1
            continue

        boxes.update(ids)
        for cid, n in Counter(ids).items():
            images_with_class[cid] += 1
            per_class_per_image[cid].append(n)
        cooccur[tuple(sorted(set(ids)))] += 1

    return {"total_images": len(images), "boxes": boxes,
            "per_class_per_image": per_class_per_image,
            "images_with_class": images_with_class, "cooccur": cooccur,
            "empty": empty, "missing": missing, "unreadable": unreadable}


def verdict(n: int) -> str:
    if n == 0:
        return "DEAD - zero instances, cannot be learned"
    if n < DEAD_BELOW:
        return "DEAD - far too few, will not be learned"
    if n < STARVED_BELOW:
        return "STARVED - enough to fit, not to generalise"
    if n < WEAK_BELOW:
        return "WEAK - usable, expect poor recall"
    return "OK"


def looks_like_dataset_yaml(path: Path) -> bool:
    """A dataset yaml declares class names and at least one split. Checking
    that is what keeps unrelated yaml (CI configs, compose files) out of the
    auto-discovery results. Keys may be quoted, hence the character classes
    rather than a plain `"names:" in text` substring test."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    has_names = re.search(r"""(?m)^\s*['"]?names['"]?\s*:""", text)
    has_split = re.search(r"""(?m)^\s*['"]?(?:train|val)['"]?\s*:""", text)
    return bool(has_names and has_split)


def discover_data_yaml() -> list[Path]:
    """Search the usual Colab/Drive roots for a dataset yaml. Bounded by
    MAX_DEPTH and MAX_HITS because MyDrive can hold a lot of unrelated
    files and an unbounded walk would appear to hang."""
    roots = [Path(r) for r in SEARCH_ROOTS]
    here = globals().get("__file__")
    if here:
        roots.append(Path(here).resolve().parent)
    roots.append(Path.cwd())

    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        base_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            here_depth = len(Path(dirpath).parts) - base_depth
            if here_depth >= MAX_DEPTH:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if fn.endswith((".yaml", ".yml")):
                    cand = Path(dirpath) / fn
                    if looks_like_dataset_yaml(cand) and cand not in found:
                        found.append(cand)
            if len(found) >= MAX_HITS:
                return found
    return found


def resolve_data_yaml(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise SystemExit(
                f"not found: {p}\n"
                f"pass the yaml itself, e.g. --data /content/merged_dataset/data_5class.yaml"
            )
        return p

    print("no --data given, searching for the dataset yaml...")
    found = discover_data_yaml()
    if not found:
        raise SystemExit(
            "found no dataset yaml.\n"
            "A dataset yaml is a .yaml/.yml file containing both 'names:' and\n"
            "'train:' (or 'val:'). Looked under: "
            + ", ".join(str(r) for r in SEARCH_ROOTS) + "\n"
            "If your dataset is on Drive, mount it first:\n"
            "    from google.colab import drive; drive.mount('/content/drive')\n"
            "then re-run, or point at the file directly:\n"
            "    --data /content/drive/MyDrive/<folder>/data.yaml"
        )
    if len(found) > 1:
        listing = "\n".join(f"    {p}" for p in found[:MAX_HITS])
        raise SystemExit(
            f"found {len(found)} dataset yamls, so refusing to guess:\n{listing}\n"
            f"re-run with --data <the right one>"
        )
    print(f"found: {found[0]}")
    return found[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=None,
                    help="path to the dataset yaml; auto-discovered when omitted")
    ap.add_argument("--split", default="train", help="split to audit (default: train)")
    args = ap.parse_args()

    yaml_path = resolve_data_yaml(args.data)
    cfg = parse_yaml(yaml_path)
    names = {int(k): v for k, v in cfg["names"].items()}

    rel = cfg.get(args.split)
    images_dir = (Path(rel) if isinstance(rel, str) else Path(f"{args.split}/images"))
    if not images_dir.is_absolute():
        images_dir = cfg["root"] / images_dir
    if not images_dir.is_dir():
        raise SystemExit(f"split dir not found: {images_dir}\n"
                         f"yaml declared {args.split}: {rel!r} -> resolved {images_dir}")

    print(f"yaml      : {yaml_path}")
    print(f"root      : {cfg['root']}")
    print(f"split     : {args.split}  ->  {images_dir}")
    print(f"labels dir: {label_dir_for(images_dir)}")
    print(f"classes   : {len(names)}  {names}")
    print()

    if not names:
        # Do NOT bail out. The label files still give valid per-class counts
        # even when the yaml's names block is unreadable, and those counts are
        # the whole point. Report them keyed by raw class id and say loudly
        # that the ids are unmapped, rather than printing an empty table or -
        # worse - concluding every class is fine.
        print("!! COULD NOT READ ANY CLASS NAMES FROM THE YAML !!")
        print("   Ids below are raw label-file ids and are UNMAPPED. Roboflow")
        print("   writes names: as a list, a dict, or inline [a, b, c]; all three")
        print("   are supported, so an empty result means that block is malformed")
        print("   or missing. The counts are still valid - only the labels are not.")
        print()

    s = scan_split(images_dir)
    total_boxes = sum(s["boxes"].values())
    n_images = s["total_images"]
    background = s["empty"] + s["missing"]

    print(f"images: {n_images}   labelled: {n_images - background}   "
          f"background-only (empty/missing label): {background}   "
          f"unreadable: {s['unreadable']}")
    print(f"total boxes: {total_boxes}")
    print()

    print("per-class instances")
    print(f"{'id':>3}  {'name':20} {'boxes':>7} {'share':>7} {'imgs':>6} "
          f"{'boxes/img':>10}  verdict")
    print("-" * 96)
    # Iterate the union of declared names and ids actually seen in the label
    # files. A class declared but never labelled must still get a row showing
    # zero, and an id present in the data but absent from the yaml must show up
    # too - either gap is exactly the kind of defect worth seeing.
    row_ids = sorted(set(names) | set(s["boxes"]))
    label_of = lambda c: names.get(c) or f"id:{c} (unmapped)"
    for cid in row_ids:
        n = s["boxes"].get(cid, 0)
        share = (n / total_boxes * 100) if total_boxes else 0.0
        imgs = s["images_with_class"].get(cid, 0)
        counts = s["per_class_per_image"].get(cid, [])
        med = statistics.median(counts) if counts else 0
        print(f"{cid:>3}  {label_of(cid):20} {n:>7} {share:>6.1f}% {imgs:>6} "
              f"{med:>10.1f}  {verdict(n)}")

    unknown = sorted(set(s["boxes"]) - set(names))
    if unknown:
        print(f"\nWARNING: label files reference class ids not in the yaml: {unknown}")
        print("         these boxes are dropped at training time (or crash the run).")

    print("\nclass co-occurrence on the same image")
    print("(a healthy_tooth box sharing an image with a cavity box is a")
    print(" labelling contradiction - one tooth cannot be both)")
    rows = sorted(s["cooccur"].items(), key=lambda kv: -kv[1])[:12]
    if not rows:
        print("  (none - no image has any boxes)")
    for combo, n in rows:
        pretty = ", ".join(f"{names.get(c, f'id:{c}')}x{n}" for c in combo)
        print(f"  {n:>5}  {pretty}")

    print("\nbackground-only images (these are what actually teach")
    print("'no pathology here' - not a healthy_tooth box):")
    if n_images:
        print(f"  {background} of {n_images} images ({background / n_images * 100:.1f}%)"
              f"  [{s['empty']} empty label file, {s['missing']} missing label file]")
    else:
        print("  (no images found)")

    print("\n" + "=" * 96)
    dead = [label_of(c) for c in row_ids if s["boxes"].get(c, 0) < DEAD_BELOW]
    starved = [label_of(c) for c in row_ids
               if DEAD_BELOW <= s["boxes"].get(c, 0) < STARVED_BELOW]
    if dead:
        print(f"NOT LEARNABLE: {', '.join(dead)}")
        print("  Any checkpoint trained on this will report ~0.00 confidence for")
        print("  them forever. No threshold, no architecture, no longer schedule")
        print("  will fix it. Only data (or removing the class) will.")
    if starved:
        print(f"THIN: {', '.join(starved)}  - expect weak recall at best.")
    if not dead and not starved:
        print("All classes present in the data have usable instance counts.")
    if not names:
        print("\nNames are UNMAPPED, so the class names above could not be")
        print("confirmed and this summary cannot be trusted by name. Re-check")
        print("the 'names:' block in the yaml and re-run.")
    ratio = (max(s["boxes"].values()) / min(v for v in s["boxes"].values() if v)
             if any(s["boxes"].values()) else 0)
    if ratio:
        print(f"imbalance: largest/smallest non-zero class = {ratio:.0f}x")
        if ratio > 50:
            print("  A >50x imbalance biases the loss toward the majority class;")
            print("  consider oversampling the small classes or dropping them.")
    print("=" * 96)


if __name__ == "__main__":
    main()
