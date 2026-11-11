"""
ToothWise - does any TEST photo also appear in TRAIN (or VALID)?

Run in Colab after the dataset is at /content/merged_dataset:
    %run /content/toothwise/backend/training/check_test_leakage.py

Checks, per test photo: identical file (md5), same Roboflow original file
name (augmented copies share it), and near-identical image (64-bit
difference hash, also against the mirrored photo, <= NEAR bits apart).
Writes data_5class_clean.yaml whose test split excludes photos found in
train, so evaluate_image_level.py can be re-run on a leak-free test set.
Shows a few flagged pairs - check them by eye, dental photos look alike.
"""
# ToothWise - duplicate / leakage check between test and train (and val)
import os, re, glob, hashlib, csv
from collections import Counter
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageOps

ROOT = "/content/merged_dataset"
EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
NEAR = 4   # max differing bits (of 64) to call two photos near-identical

def imgs(split):
    return sorted(f for f in glob.glob(f"{ROOT}/{split}/images/*") if f.lower().endswith(EXT))

def origin(path):
    # Roboflow names files "<original>_jpg.rf.<random>.jpg"; augmented copies share <original>
    return re.sub(r"\.rf\.[0-9a-f]+$", "", os.path.splitext(os.path.basename(path))[0])

def dhash(im):
    px = np.asarray(im.convert("L").resize((9, 8), Image.BILINEAR), dtype=np.int16)
    bits = (px[:, 1:] > px[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)

def fingerprint(path):
    try:
        with open(path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        im = Image.open(path)
        im.draft("RGB", (128, 128))   # fast JPEG decode at low resolution
        im = im.convert("RGB")
        return path, md5, dhash(im), dhash(ImageOps.mirror(im))
    except Exception:
        return path, None, None, None

def scan(split):
    files = imgs(split)
    with Pool(os.cpu_count()) as p:
        rows = p.map(fingerprint, files, chunksize=64)
    print(f"{split}: {len(rows)} images fingerprinted")
    return [r for r in rows if r[1] is not None]

train, val, test = scan("train"), scan("valid"), scan("test")

# --- 1. originals vs augmented copies (Roboflow file names) ---
for name, rows in (("train", train), ("valid", val), ("test", test)):
    n_orig = len({origin(r[0]) for r in rows})
    print(f"{name}: {len(rows)} files from {n_orig} original photos "
          f"(~{len(rows) / max(n_orig, 1):.1f} copies each)")

# --- 2. test photos that also appear in train / valid ---
def leaks(test_rows, other_rows):
    other_md5 = {r[1]: r[0] for r in other_rows}
    other_origin = {origin(r[0]): r[0] for r in other_rows}
    other_hash = np.array([r[2] for r in other_rows], dtype=np.uint64)
    found = {}   # test image -> (reason, matching image)
    for path, md5, h, hm in test_rows:
        if md5 in other_md5:
            found[path] = ("identical file", other_md5[md5])
        elif origin(path) in other_origin:
            found[path] = ("same original file name", other_origin[origin(path)])
        else:
            dist = np.minimum(np.bitwise_count(other_hash ^ np.uint64(h)),
                              np.bitwise_count(other_hash ^ np.uint64(hm)))
            j = int(dist.argmin())
            if dist[j] <= NEAR:
                found[path] = ("near-identical image", other_rows[j][0])
    return found

for other_name, other in (("train", train), ("valid", val)):
    f = leaks(test, other)
    print(f"\nTest photos also in {other_name}: {len(f)} of {len(test)} "
          f"({100 * len(f) / len(test):.1f}%)")
    for why, n in Counter(v[0] for v in f.values()).most_common():
        print(f"   {n:5d}  {why}")
    with open(f"/content/test_leaks_{other_name}.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([("test_image", "reason", f"{other_name}_match")] +
                                 [(k, *v) for k, v in sorted(f.items())])
    if other_name == "train":
        leaked_train = f

# --- 3. clean test list + yaml, to re-run the evaluation without leaked photos ---
clean = [r[0] for r in test if r[0] not in leaked_train]
open(f"{ROOT}/test_clean.txt", "w").write("\n".join(clean) + "\n")
yaml_text = open(f"{ROOT}/data_5class.yaml").read()
yaml_text = re.sub(r"(?m)^test:.*$", "test: test_clean.txt", yaml_text)
open(f"{ROOT}/data_5class_clean.yaml", "w").write(yaml_text)
print(f"\nClean test set: {len(clean)} photos -> {ROOT}/data_5class_clean.yaml")
print("Lists of leaked photos saved to /content/test_leaks_train.csv and test_leaks_valid.csv")

# --- 4. look at a few flagged pairs yourself (left: test, right: train) ---
import random
from IPython.display import display
pairs = random.Random(0).sample(sorted(leaked_train.items()), min(6, len(leaked_train)))
for t, (why, m) in pairs:
    a, b = Image.open(t).convert("RGB"), Image.open(m).convert("RGB")
    a.thumbnail((300, 300)); b.thumbnail((300, 300))
    canvas = Image.new("RGB", (a.width + b.width + 10, max(a.height, b.height)), "white")
    canvas.paste(a, (0, 0)); canvas.paste(b, (a.width + 10, 0))
    print(why, "|", os.path.basename(t), "<->", os.path.basename(m))
    display(canvas)
