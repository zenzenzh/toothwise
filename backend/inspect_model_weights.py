"""Inspect ToothWise YOLO checkpoints without fabricating evaluation metrics."""
from pathlib import Path

from ultralytics import YOLO
import torch


def main():
    for path in sorted(Path("models_weights").glob("*.pt")):
        model = YOLO(str(path))
        print(f"MODEL: {path.name}")
        print(f"SIZE_BYTES: {path.stat().st_size}")
        print(f"TASK: {model.task}")
        print(f"CLASSES: {model.names}")
        print(f"PARAMETERS: {sum(p.numel() for p in model.model.parameters())}")
        print(f"STRIDE: {model.model.stride.tolist()}")
        print(f"TRAINING_IMAGE_SIZE: {model.overrides.get('imgsz')}")
        print(f"TRAINING_DATA_REFERENCE: {model.overrides.get('data')}")
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        print(f"EPOCH: {checkpoint.get('epoch')}")
        print(f"BEST_FITNESS: {checkpoint.get('best_fitness')}")
        print(f"DATE: {checkpoint.get('date')}")
        print(f"TRAIN_ARGS: {checkpoint.get('train_args')}")
        print(f"TRAIN_METRICS: {checkpoint.get('train_metrics')}")
        results = checkpoint.get('train_results', {})
        for key in ('metrics/precision(B)', 'metrics/recall(B)', 'metrics/mAP50(B)', 'metrics/mAP50-95(B)'):
            values = results.get(key, [])
            if values:
                print(f"LAST_{key}: {values[-1]}")
        print()


if __name__ == "__main__":
    main()
