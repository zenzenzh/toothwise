# Training the dental YOLOv8 + YOLO12 models

You have two options for the dataset. Given your capstone timeline, option A
is much faster.

## Option A — combine public dental datasets (fast)

Roboflow Universe has several relevant open datasets you can merge into one
project. Best matches for our 8 labels, checked while writing this guide:

- **dental data4** (~1,585 images) — healthy, caries, cavity, plaque
  https://universe.roboflow.com/search?q=class:cavity — search "dental data4"
- **dental data2** (~6,968 images) — healthy, caries, cavity, gingivitis, plaque
- **Dental Caries Detection using DL** (~1,162–2,890 images) — tooth-decay focus
  https://universe.roboflow.com/project-group13/dental-caries-detection-using-dl
- Search Roboflow Universe directly for `calculus` (tartar), `fracture`/`broken tooth`
  (cracked_tooth), `missing teeth` (missing_tooth), and `black stain`/`discoloration`
  (tooth_discoloration) — these classes are less common, so you'll likely need
  to combine 2-4 smaller datasets to cover all 8 labels reasonably.
  Browse: https://universe.roboflow.com/search?q=class%3Adental

**Workflow:**
1. Create a free Roboflow account and a new project.
2. Use Roboflow's "Universe" import / "Upload" to pull in images from the
   datasets above (Roboflow lets you fork/clone public projects directly,
   or download+reupload).
3. Don't worry about renaming classes to match ours exactly — the app
   normalizes common aliases automatically (`caries`→`cavity`,
   `gingivitis`→`gum_inflammation`, `calculus`→`tartar`, etc. — see
   `backend/app/ml/labels.py::LABEL_ALIASES`). If your dataset uses a name
   not in that list, add it there — one line.
4. Once merged, use Roboflow's Health Check to spot severe class imbalance
   (dental datasets are almost always cavity/healthy-heavy and
   missing_tooth/cracked_tooth-light — expect this and mention it as a
   limitation in your defense).
5. Generate a version → Export → **YOLOv8** format (this format also works
   for YOLO12 training, same annotation structure) → get the Python
   download snippet (uses your Roboflow API key).

## Option B — annotate your own CodiSmile clinic images (more authentic, slower)

Use Roboflow's free annotation tool, LabelImg, or CVAT. Aim for at least
80-150 images per class if possible; dental capstones commonly work with
300-800 total images and still get presentable results for a defense demo
(not production-grade, but sufficient to show the pipeline working).

## Then: train

Open `train_dental_yolo_colab.ipynb` in Google Colab (Runtime → Change
runtime type → GPU), follow the cells in order. It trains **both**
YOLOv8n and YOLO12n against the same dataset, shows you both confusion
matrices so you can sanity-check performance, then packages
`yolov8_dental.pt` and `yolov12_dental.pt` for download.

Drop both files into `backend/models_weights/`, set `USE_MOCK_MODEL=false`
in `backend/.env`, and restart the backend.

## After training: verify label alignment

Run this once in Colab (also in the notebook) to see exactly what class
names your trained model will emit:

```python
from ultralytics import YOLO
model = YOLO("/content/runs/detect/toothwise_yolov8/weights/best.pt")
print(model.names)
```

Cross-check the printed names against `LABELS` / `LABEL_ALIASES` in
`backend/app/ml/labels.py`. Anything not covered gets passed through
as-is (lowercased) rather than silently dropped, so it'll be obvious in
the detection results if something isn't mapping correctly.
