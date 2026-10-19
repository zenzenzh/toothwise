"""
Lightweight YOLO inference with onnxruntime - no PyTorch, no Ultralytics.

Used when YOLO_BACKEND=onnx (production on small hosts such as Render's
512 MB free tier, where PyTorch alone does not fit). Pre- and
post-processing mirror Ultralytics' predict() defaults so results match the
.pt models: letterbox to the model's square input with grey (114) padding,
RGB 0-1 input, then per-class NMS at IoU 0.7, max 300 boxes, boxes scaled
back to the original image.

Models are exported with deploy/export_onnx.py (see docs/DEPLOYMENT.md).
"""
from __future__ import annotations

import ast
from pathlib import Path

import cv2
import numpy as np

NMS_IOU = 0.7          # Ultralytics predict() default
MAX_DET = 300          # Ultralytics predict() default
MAX_WH = 7680          # class offset for batched per-class NMS (Ultralytics)


def _letterbox(img: np.ndarray, size: int, stride: int | None) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize keeping aspect ratio and pad (Ultralytics LetterBox). With a
    stride (dynamic-shape model) pad only to the next stride multiple, like
    Ultralytics' rectangular inference on .pt models; else pad to a square."""
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    new_w, new_h = int(round(w * r)), int(round(h * r))
    dw, dh = size - new_w, size - new_h
    if stride:
        dw, dh = dw % stride, dh % stride
    dw, dh = dw / 2, dh / 2
    if (w, h) != (new_w, new_h):
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return img, r, (left, top)


def _nms(boxes: np.ndarray, scores: np.ndarray, iou: float) -> list[int]:
    """Greedy NMS over xyxy boxes, highest score first."""
    order = scores.argsort()[::-1]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if len(keep) >= MAX_DET:
            break
        rest = order[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        overlap = inter / (areas[i] + areas[rest] - inter + 1e-9)
        order = rest[overlap <= iou]
    return keep


def _load_bgr(source) -> np.ndarray:
    if isinstance(source, (str, Path)):
        img = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not read image: {source}")
        return img
    # PIL.Image
    rgb = np.asarray(source.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


class OnnxYolo:
    """Minimal drop-in for the bits of ultralytics.YOLO the detector uses.

    keep_loaded=False opens the model only for each predict() and frees it
    afterwards, so two models never sit in memory together (~400 MB peak for
    both instead of ~520 MB) at the cost of ~0.5 s per model per screening.
    """

    def __init__(self, path: str, threads: int = 2, keep_loaded: bool = True):
        self.path = str(path)
        self.threads = threads
        self.keep_loaded = keep_loaded
        session = self._open()
        self.input_name = session.get_inputs()[0].name
        meta = session.get_modelmeta().custom_metadata_map
        shape = session.get_inputs()[0].shape  # [1, 3, H, W] or symbolic
        self.session = session if keep_loaded else None
        del session
        self.names: dict[int, str] = ast.literal_eval(meta["names"]) if "names" in meta else {}
        dynamic = not isinstance(shape[2], int)
        imgsz = ast.literal_eval(meta["imgsz"]) if "imgsz" in meta else [640, 640]
        self.imgsz = int(shape[2]) if not dynamic else int(imgsz[0])
        self.stride = int(meta.get("stride", 32)) if dynamic else None

    def _open(self):
        import onnxruntime as ort  # imported lazily: only needed in onnx mode

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.threads
        opts.inter_op_num_threads = 1
        # Keep memory small on 512 MB hosts: no arena pre-allocation growth.
        opts.enable_cpu_mem_arena = False
        if self.path.endswith(".opt.onnx"):
            # Already optimized by app.ml.prepare_onnx: skip it at load.
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        return ort.InferenceSession(self.path, sess_options=opts, providers=["CPUExecutionProvider"])

    def predict(self, source, conf: float) -> tuple[list[tuple[int, float, float, float, float, float]], tuple[int, int]]:
        """Returns ([(cls_id, conf, x1, y1, x2, y2) in original pixels], (h, w))."""
        img = _load_bgr(source)
        h0, w0 = img.shape[:2]
        padded, gain, (pad_x, pad_y) = _letterbox(img, self.imgsz, self.stride)
        blob = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255.0

        session = self.session or self._open()
        out = session.run(None, {self.input_name: blob})[0][0]  # (4 + nc, anchors)
        del session
        preds = out.T
        scores_all = preds[:, 4:]
        cls_ids = scores_all.argmax(axis=1)
        scores = scores_all[np.arange(len(cls_ids)), cls_ids]
        mask = scores > conf
        if not mask.any():
            return [], (h0, w0)
        xywh, scores, cls_ids = preds[mask, :4], scores[mask], cls_ids[mask]

        boxes = np.empty_like(xywh)
        boxes[:, 0] = xywh[:, 0] - xywh[:, 2] / 2
        boxes[:, 1] = xywh[:, 1] - xywh[:, 3] / 2
        boxes[:, 2] = xywh[:, 0] + xywh[:, 2] / 2
        boxes[:, 3] = xywh[:, 1] + xywh[:, 3] / 2

        keep = _nms(boxes + (cls_ids[:, None] * MAX_WH), scores, NMS_IOU)
        boxes, scores, cls_ids = boxes[keep], scores[keep], cls_ids[keep]

        boxes[:, [0, 2]] = ((boxes[:, [0, 2]] - pad_x) / gain).clip(0, w0)
        boxes[:, [1, 3]] = ((boxes[:, [1, 3]] - pad_y) / gain).clip(0, h0)
        return (
            [(int(c), float(s), *map(float, b)) for c, s, b in zip(cls_ids, scores, boxes)],
            (h0, w0),
        )
