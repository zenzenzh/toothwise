# ToothWise Model Weights Evaluation

## Scope

This evaluation inspects the validation metrics embedded in the two trained
YOLO checkpoints. Both were trained at 640 px for 60 epochs with batch size 12
against the referenced five-class dataset:
`/content/merged_dataset/data_5class.yaml`.

Classes, in checkpoint order:

1. `healthy_tooth`
2. `cavity`
3. `gum_inflammation`
4. `plaque`
5. `tartar`

## Saved validation metrics

| Model | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| YOLOv8 | 53.96% | 49.73% | 46.83% | 26.80% |
| YOLOv12 | 49.43% | 49.05% | 45.02% | 25.87% |

## Interpretation

YOLOv8 has the stronger saved validation result on all four aggregate
metrics. Compared with YOLOv12, it has a 4.53 percentage-point precision
advantage, a 0.67 percentage-point recall advantage, a 1.81 percentage-point
mAP50 advantage, and a 0.93 percentage-point mAP50-95 advantage.

These are validation metrics saved in the checkpoints; they are not an
independent clinical evaluation. Per-class metrics, a confusion matrix, and a
fresh test-set result cannot be reproduced in this repository because the
referenced dataset and labels are not present locally. The models should be
evaluated again on a patient-disjoint held-out test split before any clinical
accuracy claim is made.

## Deployment compatibility

The checkpoints and the current `app/ml/labels.py` use the same five-class
order, so their label mapping is compatible with the application.
