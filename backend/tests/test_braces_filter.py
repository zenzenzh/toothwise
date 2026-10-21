"""Tests for the braces / cavity false-positive filters in yolo_detector."""
from PIL import Image, ImageDraw

from app.ml import yolo_detector as yd
from app.ml.yolo_detector import RawDetection

ENAMEL = (238, 226, 200)
STEEL = (150, 152, 158)
CARIES = (90, 55, 25)


def _mouth(spots: list[tuple[tuple[int, int, int, int], tuple[int, int, int]]]) -> Image.Image:
    """A 400x200 cream "tooth row" with coloured squares painted on it."""
    img = Image.new("RGB", (400, 200), ENAMEL)
    draw = ImageDraw.Draw(img)
    for box, colour in spots:
        draw.rectangle(box, fill=colour)
    return img


def _box(label, conf, px_box, model):
    x1, y1, x2, y2 = px_box
    return RawDetection(label, conf, x1 / 400, y1 / 200, x2 / 400, y2 / 200, model)


class _Stub:
    def __init__(self, dets):
        self.dets = dets

    def predict(self, source, conf_threshold):
        return list(self.dets)


def _detector(v8, v12):
    det = yd.DualYoloDetector.__new__(yd.DualYoloDetector)
    det.v8_mock, det.v12_mock, det.onnx = True, False, False
    det.model_v8 = _Stub(v8)
    det._run_real = lambda model, source, tag: (list(v12), 0.0)
    det.model_v12 = None
    return det


# Tooth boxes around each painted square (brackets sit mid-tooth).
TOOTH_A = (20, 40, 100, 160)
TOOTH_B = (120, 40, 200, 160)
TOOTH_C = (220, 40, 300, 160)
BRACKET_A = (45, 80, 75, 110)
BRACKET_B = (145, 80, 175, 110)
LESION_C = (245, 80, 275, 110)


def test_metal_fraction_separates_bracket_from_caries():
    hsv = yd._load_hsv(_mouth([(BRACKET_A, STEEL), (LESION_C, CARIES)]))
    assert yd._metal_fraction(hsv, _box("cavity", 0.9, TOOTH_A, "yolov8")) > 0.08
    assert yd._metal_fraction(hsv, _box("cavity", 0.9, TOOTH_C, "yolov8")) == 0.0


def test_braces_are_not_reported_as_cavities():
    img = _mouth([(BRACKET_A, STEEL), (BRACKET_B, STEEL), (LESION_C, CARIES)])
    v8 = [_box("cavity", 0.8, b, "yolov8") for b in (TOOTH_A, TOOTH_B, TOOTH_C)]
    v12 = [_box("cavity", 0.8, b, "yolov12") for b in (TOOTH_A, TOOTH_B, TOOTH_C)]
    result = _detector(v8, v12).detect(img)

    assert result["orthodontic_appliance"] is True
    fused = result["detections"]
    assert len(fused) == 1 and fused[0]["label"] == "cavity"
    assert fused[0]["x1"] == TOOTH_C[0] / 400
    assert len(result["detections_v8"]) == len(result["detections_v12"]) == 1


def test_low_confidence_and_single_model_cavities_are_dropped():
    img = _mouth([(LESION_C, CARIES)])
    v8 = [_box("cavity", 0.45, TOOTH_A, "yolov8"),   # below cavity floor
          _box("cavity", 0.70, TOOTH_C, "yolov8")]   # v8 only, no agreement
    v12 = [_box("plaque", 0.40, TOOTH_B, "yolov12")]  # other labels untouched
    result = _detector(v8, v12).detect(img)

    assert result["orthodontic_appliance"] is False
    assert [d["label"] for d in result["detections"]] == ["plaque"]
    assert [d["confidence"] for d in result["detections_v8"]] == [0.70]


def test_single_bracket_is_not_flagged_as_braces():
    img = _mouth([(BRACKET_A, STEEL)])
    v8 = [_box("cavity", 0.8, TOOTH_A, "yolov8")]
    v12 = [_box("cavity", 0.8, TOOTH_A, "yolov12")]
    result = _detector(v8, v12).detect(img)
    assert result["detections"] == []
    assert result["orthodontic_appliance"] is False
