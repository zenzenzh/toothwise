"""
Fast checks for the onnxruntime YOLO backend (app/ml/onnx_yolo.py).
The letterbox/NMS helpers are tested without any model; the full-model test
runs only when the prepared .opt.onnx files exist (python -m
app.ml.prepare_onnx) and onnxruntime is installed.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ml import onnx_yolo


def test_letterbox_rect_pads_to_stride_multiple():
    img = np.zeros((500, 1200, 3), dtype=np.uint8)  # 500 * 640/1200 = 267 px -> pad to 288
    out, gain, (pad_x, pad_y) = onnx_yolo._letterbox(img, 640, 32)
    assert gain == pytest.approx(640 / 1200)
    assert out.shape[1] == 640 and out.shape[0] % 32 == 0
    assert pad_x == 0 and pad_y > 0


def test_letterbox_square_without_stride():
    img = np.zeros((300, 600, 3), dtype=np.uint8)
    out, _, _ = onnx_yolo._letterbox(img, 640, None)
    assert out.shape[:2] == (640, 640)


def test_nms_keeps_best_and_drops_overlaps():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 10, 10], [20, 20, 30, 30]], dtype=np.float32)
    scores = np.array([0.9, 0.8, 0.7], dtype=np.float32)
    assert onnx_yolo._nms(boxes, scores, 0.7) == [0, 2]


WEIGHTS = Path(__file__).resolve().parents[1] / "models_weights"
OPT = [WEIGHTS / "yolov8_dental.opt.onnx", WEIGHTS / "yolov12_dental.opt.onnx"]


@pytest.mark.skipif(not all(p.exists() for p in OPT), reason="run python -m app.ml.prepare_onnx first")
def test_prepared_models_load_and_predict():
    pytest.importorskip("onnxruntime")
    from PIL import Image
    img = Image.new("RGB", (320, 240), (210, 180, 170))
    for path in OPT:
        model = onnx_yolo.OnnxYolo(str(path), keep_loaded=False)
        assert model.session is None  # freed after reading metadata
        assert set(model.names.values()) >= {"cavity", "plaque", "tartar"}
        boxes, (h, w) = model.predict(img, 0.25)
        assert (h, w) == (240, 320)
        for cls_id, conf, x1, y1, x2, y2 in boxes:
            assert 0 <= x1 <= x2 <= w and 0 <= y1 <= y2 <= h and conf > 0.25
