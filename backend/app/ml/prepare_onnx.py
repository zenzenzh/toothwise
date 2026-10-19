"""
Prepares the ONNX models for YOLO_BACKEND=onnx.

GitHub rejects files over 100 MB, so each exported model is stored in git as
<name>.onnx.part01, .part02, ... (under 50 MB each, byte-for-byte slices).
At build time this joins the parts back and saves an onnxruntime-optimized
copy (<name>.opt.onnx). The server loads the .opt.onnx files with graph
optimization switched off, which needs less memory and time per load - the
key to fitting a 512 MB host. Outputs are identical to the .pt models.

    python -m app.ml.prepare_onnx            # join parts + optimize (build step)
    python -m app.ml.prepare_onnx --split    # after re-exporting: split .onnx into parts
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

WEIGHTS = Path(__file__).resolve().parents[2] / "models_weights"
MODELS = ("yolov8_dental", "yolov12_dental")
PART_BYTES = 45 * 1024 * 1024


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split() -> None:
    for name in MODELS:
        src = WEIGHTS / f"{name}.onnx"
        for old in WEIGHTS.glob(f"{name}.onnx.part*"):
            old.unlink()
        data = src.read_bytes()
        for i in range(0, len(data), PART_BYTES):
            (WEIGHTS / f"{name}.onnx.part{i // PART_BYTES + 1:02d}").write_bytes(data[i:i + PART_BYTES])
        (WEIGHTS / f"{name}.onnx.sha256").write_text(_sha256(src) + "\n")
        print(f"{name}: {len(data) / 1e6:.1f} MB -> {-(-len(data) // PART_BYTES)} parts")


def join_and_optimize() -> None:
    import onnxruntime as ort

    for name in MODELS:
        parts = sorted(WEIGHTS.glob(f"{name}.onnx.part*"))
        joined = WEIGHTS / f"{name}.onnx"
        if parts:
            with joined.open("wb") as out:
                for part in parts:
                    out.write(part.read_bytes())
            expected = (WEIGHTS / f"{name}.onnx.sha256").read_text().strip()
            if _sha256(joined) != expected:
                raise SystemExit(f"{name}: joined model does not match its checksum")
        if not joined.exists():
            raise SystemExit(f"{name}: no .onnx file or parts in {WEIGHTS}")

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        opts.optimized_model_filepath = str(WEIGHTS / f"{name}.opt.onnx")
        ort.InferenceSession(str(joined), opts, providers=["CPUExecutionProvider"])
        if parts:
            joined.unlink()  # keep only the optimized copy on the server
        print(f"{name}: ready -> {name}.opt.onnx")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", action="store_true")
    args = parser.parse_args()
    split() if args.split else join_and_optimize()
