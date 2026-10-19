"""
Re-export the YOLO checkpoints to ONNX after retraining, then split them for
git. Needs the full development environment (PyTorch + Ultralytics):

    cd backend
    .venv/Scripts/python.exe ../deploy/export_onnx.py

Writes models_weights/<name>.onnx (dynamic input size, no NMS baked in, so
app/ml/onnx_yolo.py reproduces Ultralytics' rectangular inference exactly),
then models_weights/<name>.onnx.part01... + .sha256 for committing.
Commit the .part* and .sha256 files; the .onnx files are git-ignored.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from ultralytics import YOLO  # noqa: E402

from app.ml.prepare_onnx import split  # noqa: E402
from app.ml.yolo_detector import _trusted_torch_load  # noqa: E402

for name in ("yolov8_dental", "yolov12_dental"):
    with _trusted_torch_load():
        model = YOLO(str(BACKEND / "models_weights" / f"{name}.pt"))
    model.export(format="onnx", imgsz=640, opset=17, simplify=True, dynamic=True, nms=False)

split()
print("Done. Commit models_weights/*.onnx.part* and *.onnx.sha256.")
