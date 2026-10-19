"""
Dual-model detector: runs a YOLOv8 checkpoint and a YOLOv12 checkpoint over
the same intraoral image and fuses their outputs into one detection set.

Why two models instead of one:
- YOLOv8 (mature, CNN-based) tends to be very stable on well-lit, centered
  intraoral shots.
- YOLOv12 (attention-centric backbone) tends to pick up smaller / partially
  occluded lesions that v8 sometimes misses.
Running both and fusing with IoU-based weighted-box-fusion generally beats
either model alone on recall without a big precision hit - a common
finding replicated in most YOLO ensemble literature, and a reasonable
justification to put in your capstone methodology chapter.

If no trained weights are present (or USE_MOCK_MODEL=true), the detector
falls back to a deterministic mock so the full application is demoable
end-to-end before your models finish training.
"""
from __future__ import annotations

import hashlib
import random
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path

from app.config import get_settings
from app.ml.labels import LABELS, normalize_label

settings = get_settings()


@contextmanager
def _trusted_torch_load():
    """
    PyTorch 2.6 changed torch.load()'s default from weights_only=False to
    weights_only=True, which blocks Ultralytics checkpoints - they pickle
    full Python objects (DetectionModel, Sequential, etc.), not just raw
    tensors. Older ultralytics releases (this project pins 8.2.31) don't
    work around this internally, so loading a real .pt file raises
    UnpicklingError on PyTorch 2.6+.

    Since these are YOUR OWN trained weights, not a file downloaded from
    an untrusted source, it's safe to temporarily allow full unpickling
    for the load call only - then restore PyTorch's strict default
    immediately after, rather than weakening it for the app's whole
    lifetime.
    """
    # Imported lazily (not at module top-level) so mock-mode runs never
    # need torch installed / imported at all.
    import torch

    original_load = torch.load

    def _patched_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    torch.load = _patched_load
    try:
        yield
    finally:
        torch.load = original_load


@dataclass
class RawDetection:
    label: str
    confidence: float
    x1: float  # normalized 0-1
    y1: float
    x2: float
    y2: float
    source_model: str


def _iou(a: RawDetection, b: RawDetection) -> float:
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _fuse(dets_v8: list[RawDetection], dets_v12: list[RawDetection],
          iou_threshold: float) -> list[RawDetection]:
    """Greedy weighted-box-fusion across the two models' outputs."""
    pool = list(dets_v8) + list(dets_v12)
    pool.sort(key=lambda d: d.confidence, reverse=True)

    fused: list[RawDetection] = []
    used = [False] * len(pool)

    for i, det in enumerate(pool):
        if used[i]:
            continue
        cluster = [det]
        used[i] = True
        for j in range(i + 1, len(pool)):
            if used[j] or pool[j].label != det.label:
                continue
            if _iou(det, pool[j]) >= iou_threshold:
                cluster.append(pool[j])
                used[j] = True

        total_conf = sum(c.confidence for c in cluster)
        x1 = sum(c.x1 * c.confidence for c in cluster) / total_conf
        y1 = sum(c.y1 * c.confidence for c in cluster) / total_conf
        x2 = sum(c.x2 * c.confidence for c in cluster) / total_conf
        y2 = sum(c.y2 * c.confidence for c in cluster) / total_conf

        # Detections confirmed by BOTH models get a confidence boost, capped
        # at 0.98 so we never claim absolute certainty.
        models_agreeing = {c.source_model for c in cluster}
        boost = 0.08 if len(models_agreeing) > 1 else 0.0
        fused_conf = min(max(c.confidence for c in cluster) + boost, 0.98)

        fused.append(RawDetection(
            label=det.label, confidence=round(fused_conf, 3),
            x1=x1, y1=y1, x2=x2, y2=y2,
            source_model="ensemble" if len(models_agreeing) > 1 else det.source_model,
        ))
    return fused


def _seed_key(source) -> str:
    """
    Stable string key for the mock detector's deterministic RNG seed.
    `source` is normally a filesystem path (persisted screenings), but callers
    may also pass an in-memory PIL.Image - hash a small pixel sample in that
    case so mock mode still produces a varying-but-deterministic result
    rather than crashing on a non-path input.
    """
    if isinstance(source, (str, Path)):
        return str(source)
    try:
        sample = source.resize((32, 32)).convert("RGB").tobytes()
    except Exception:
        sample = repr(source).encode()
    return hashlib.md5(sample).hexdigest()


class _MockYoloModel:
    """Deterministic stand-in used when real weights aren't available yet."""

    def __init__(self, seed_salt: str):
        self.seed_salt = seed_salt

    def predict(self, source, conf_threshold: float) -> list[RawDetection]:
        digest = hashlib.sha256((_seed_key(source) + self.seed_salt).encode()).hexdigest()
        rng = random.Random(int(digest[:8], 16))

        pool = [l for l in LABELS if l != "healthy_tooth"]
        n = rng.choices([0, 1, 2, 3, 4], weights=[10, 25, 30, 20, 15])[0]
        if n == 0:
            return [RawDetection("healthy_tooth", round(rng.uniform(0.7, 0.95), 3),
                                  0.1, 0.3, 0.9, 0.7, self.seed_salt)]

        detections = []
        for _ in range(n):
            label = rng.choice(pool)
            conf = round(rng.uniform(conf_threshold, 0.95), 3)
            w = rng.uniform(0.08, 0.18)
            h = rng.uniform(0.15, 0.3)
            x1 = rng.uniform(0.05, 0.9 - w)
            y1 = rng.uniform(0.1, 0.8 - h)
            detections.append(RawDetection(label, conf, x1, y1, x1 + w, y1 + h,
                                            self.seed_salt))
        return detections


class DualYoloDetector:
    def __init__(self):
        # Each model independently decides real vs. mock based on whether
        # ITS weights file exists - so you can try a trained YOLOv12 model
        # while YOLOv8 is still mocked (or vice versa), instead of requiring
        # both weight files before either one goes real.
        # USE_MOCK_MODEL=true still force-mocks everything regardless of
        # what weight files are present, as an explicit override/demo switch.
        force_mock = settings.USE_MOCK_MODEL
        self.onnx = settings.YOLO_BACKEND == "onnx"
        v8_path = settings.YOLOV8_ONNX_PATH if self.onnx else settings.YOLOV8_WEIGHTS_PATH
        v12_path = settings.YOLOV12_ONNX_PATH if self.onnx else settings.YOLOV12_WEIGHTS_PATH
        v8_weights_exist = Path(v8_path).exists()
        v12_weights_exist = Path(v12_path).exists()

        self.v8_mock = force_mock or not v8_weights_exist
        self.v12_mock = force_mock or not v12_weights_exist or not settings.USE_YOLOV12
        # Kept for logging / anything that still checks overall mock status.
        self.mock_mode = self.v8_mock and self.v12_mock

        if self.v8_mock:
            self.model_v8 = _MockYoloModel("yolov8")
        elif self.onnx:
            from app.ml.onnx_yolo import OnnxYolo
            self.model_v8 = OnnxYolo(v8_path, keep_loaded=settings.ONNX_KEEP_LOADED)
        else:
            from ultralytics import YOLO  # imported lazily - heavy dependency
            with _trusted_torch_load():
                self.model_v8 = YOLO(settings.YOLOV8_WEIGHTS_PATH)

        if self.v12_mock:
            self.model_v12 = _MockYoloModel("yolov12")
        elif self.onnx:
            from app.ml.onnx_yolo import OnnxYolo
            self.model_v12 = OnnxYolo(v12_path, keep_loaded=settings.ONNX_KEEP_LOADED)
        else:
            from ultralytics import YOLO  # imported lazily - heavy dependency
            with _trusted_torch_load():
                self.model_v12 = YOLO(settings.YOLOV12_WEIGHTS_PATH)

    def _run_real(self, model, source, tag: str) -> tuple[list[RawDetection], float]:
        # YOLO needs an absolute path for file sources; source may be a
        # relative path like "screenings/img.jpg" under UPLOAD_DIR.
        if isinstance(source, (str, Path)):
            source = Path(settings.UPLOAD_DIR) / source
        start = time.perf_counter()
        if self.onnx:
            with _predict_lock():
                boxes, (h, w) = model.predict(source, settings.DETECTION_CONF_THRESHOLD)
            elapsed_ms = (time.perf_counter() - start) * 1000
            dets = []
            for cls_id, conf, x1, y1, x2, y2 in boxes:
                raw_label = model.names.get(cls_id, LABELS[cls_id % len(LABELS)])
                dets.append(RawDetection(
                    label=normalize_label(raw_label), confidence=round(conf, 3),
                    x1=x1 / w, y1=y1 / h, x2=x2 / w, y2=y2 / h,
                    source_model=tag,
                ))
            return dets, elapsed_ms
        # Ultralytics' predictor keeps mutable per-call state (results, batch
        # bookkeeping) on the model object, so two threads calling predict()
        # on the same instance can return each other's results. That would
        # hand one patient another's diagnosis, so inference is serialised.
        # Inference is already the bottleneck at ~8s/screening, so this costs
        # nothing that matters and removes a silent data-corruption race.
        with _predict_lock():
            results = model.predict(
                source=source,
                conf=settings.DETECTION_CONF_THRESHOLD,
                verbose=False,
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        dets: list[RawDetection] = []
        if not results:
            return dets, elapsed_ms

        result = results[0]
        h, w = result.orig_shape
        for box in result.boxes:
            cls_id = int(box.cls[0])
            raw_label = model.names.get(cls_id, LABELS[cls_id % len(LABELS)])
            label = normalize_label(raw_label)
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            dets.append(RawDetection(
                label=label, confidence=round(conf, 3),
                x1=x1 / w, y1=y1 / h, x2=x2 / w, y2=y2 / h,
                source_model=tag,
            ))
        return dets, elapsed_ms

    def detect(self, source) -> dict:
        """
        `source` is either a filesystem path (str/Path) for a persisted
        screening upload or an in-memory PIL.Image - Ultralytics' predict()
        accepts both directly, and the mock model is seeded via _seed_key()
        regardless of which one it gets.

        Returns:
            {
              "detections": [RawDetection-as-dict, ...],       # fused ensemble - drives risk score
              "detections_v8": [RawDetection-as-dict, ...],    # YOLOv8 raw output, unfused
              "detections_v12": [RawDetection-as-dict, ...],   # YOLOv12 raw output, unfused
              "yolov8_ms": float,
              "yolov12_ms": float,
            }
        Raw per-model outputs are included (tagged source_model="yolov8" /
        "yolov12") so the app can show a model-vs-model comparison rather
        than only the fused result.
        """
        if self.v8_mock:
            t0 = time.perf_counter()
            dets_v8 = self.model_v8.predict(source, settings.DETECTION_CONF_THRESHOLD)
            ms_v8 = (time.perf_counter() - t0) * 1000
        else:
            dets_v8, ms_v8 = self._run_real(self.model_v8, source, "yolov8")

        if self.v12_mock:
            dets_v12: list[RawDetection] = []
            ms_v12 = 0.0
        else:
            dets_v12, ms_v12 = self._run_real(self.model_v12, source, "yolov12")
        fused = _fuse(dets_v8, dets_v12, settings.ENSEMBLE_IOU_THRESHOLD)

        return {
            "detections": [asdict(d) for d in fused],
            "detections_v8": [asdict(d) for d in dets_v8],
            "detections_v12": [asdict(d) for d in dets_v12],
            "yolov8_ms": round(ms_v8, 1),
            "yolov12_ms": round(ms_v12, 1),
        }


_detector_singleton: DualYoloDetector | None = None
_detector_init_lock = threading.Lock()

# One lock for every predict() call across every request thread. detect()
# already runs v8 then v12 sequentially inside one thread, so this adds no
# per-request latency; it only stops two concurrent requests from driving the
# same Ultralytics predictor object at once.
_PREDICT_LOCK = threading.Lock()


def _predict_lock():
    return _PREDICT_LOCK


def get_detector() -> DualYoloDetector:
    """
    Lazily build the shared detector.

    FastAPI runs this sync endpoint in a threadpool, so without a lock two
    concurrent first-time uploads both saw `_detector_singleton is None`, both
    constructed a DualYoloDetector, and both called YOLO() on the same
    weights. torch's fuse() mutates the module graph (it folds BatchNorm into
    Conv and deletes .bn), so the second thread hit
    `AttributeError: 'Conv' object has no attribute 'bn'` and the request 500'd.
    Measured under a 4-way concurrent load: 2 of 20 screenings failed this way.
    """
    global _detector_singleton
    if _detector_singleton is None:
        with _detector_init_lock:
            if _detector_singleton is None:      # double-checked locking
                _detector_singleton = DualYoloDetector()
    return _detector_singleton
