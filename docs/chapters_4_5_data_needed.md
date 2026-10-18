# Chapters 4 and 5: data still needed

The draft is `ToothWise_Chapters_4_and_5_v2.docx`. Every missing value in it is written as **[TBD …]** and highlighted yellow.

To rebuild the draft after filling in data:

1. Run `backend\venv\Scripts\python.exe extract_training_metrics.py`. This reads the metrics from the `.pt` files and redraws the figures.
2. Run `python generate_chapters_4_and_5_v2.py`.

## Already filled with real numbers

- **YOLOv8 / YOLOv12 overall results** (Tables 16 and 20, Figures 19 and 20). The precision, recall, mAP@50 and mAP@50-95 come from `train_metrics` stored in `backend/models_weights/*.pt`. They were measured on the validation split (5,299 images) at epoch 60.
- **Dataset sources, class remap and split counts** (Tables 12 and 13). These come from the outputs of the Colab notebook `Downloads/train_dental_yolov12_5class_2.ipynb`.
- **Training configuration** (Table 15). This comes from `train_args` in the checkpoints.
- **CPU inference speed** (Table 18). Measured on 2026-10-18 on the i7-13620H laptop.
- **KNN holdout results** (Table 20). From `python -m app.ml.evaluate_knn`.
- **Backend tests: 84 passed** (Table 21).
- **Lighthouse and axe results** (Table 22). From `docs/frontend_polish_plan.md`.

## Data the team must supply

### Model results

These need the merged dataset, which is in Colab or on Drive (`/content/merged_dataset/data_5class.yaml`).

1. **Per-class P / R / mAP for both models** (Table 17) and **instances per class** (Table 14). Run `model.val(data=..., split='val')` and copy the per-class rows.
2. **Test-split results.** Run the same with `split='test'`. The paper should ideally report the test split rather than the validation split.
3. **Fused-ensemble metrics** (the ensemble column in Table 16, and Section 4.1.6). Run the fusion from `backend/app/ml/yolo_detector.py::_fuse` over the test split. `backend/training/evaluate_models.py` only evaluates the two models separately, so this needs a small extension.
4. **YOLOv8 variant name** (Table 15). It has 25.86 M parameters, which matches **yolov8m**. Confirm from the notebook.
5. **GPU inference time on the T4** (Table 18 has a placeholder row). This is optional.
6. **Test-split background image count** (Table 13).

### "Overnight re-run"

No newer training output was found on this laptop. The checkpoints in `backend/models_weights` are dated 2026-09-10 (YOLOv8) and 2026-09-23 (YOLOv12).

If the re-run produced new `best.pt` files, copy them over these two files and run the two scripts again. Every number in the draft will update.

### Survey (Tuesday)

The ISO/IEC 25010 survey covers Section 4.3 and Tables 23–33.

- Actual respondent counts per group, and demographics (age, gender, experience).
- Every rating for items FS1–FS5, PE1–PE4, US1–US5, RE1–RE4, SP1–SP4 and CP1–CP4, so the weighted mean and SD can be computed for each item and each characteristic.
- The means split by IT experts and clinical users (Table 33).
- Common themes from the open-ended Section D answers, for the discussion paragraphs.

### Screening time and consistency (SOP 5)

This is Section 4.4, Tables 34–35. Nothing has been collected yet.

- Timed screenings, manual versus with Toothwise: number of patients, mean time and SD.
- Agreement with the dentist's findings, manual versus Toothwise: percentage agreement or Cohen's kappa, and missed findings.

### KNN against real cases

- The number of dentist-confirmed tiers and the KNN accuracy on them. Run `python -m app.ml.evaluate_knn` after the clinic has confirmed some screenings.

## Inconsistencies to fix in other chapters

- **SOP 4 in Chapter 1** lists the six characteristics as "security, privacy, usability, reliability, performance efficiency, and data protection". The survey instrument actually uses Functional Suitability, Performance Efficiency, Usability, Reliability, Security & Privacy, and Compatibility & Portability, and Chapter 4 follows the instrument. Update the SOP 4 wording to match.
- **The old `ToothWise_Chapters_4_and_5.docx` contains invented results.** Examples: 94.3% ensemble sensitivity, a 4.68 survey mean, a 65.6% reduction in screening time, and kappa 0.91. None of these come from real data, and they contradict the real mAP@50 of about 0.46. Do not submit that file. The same invented "Table 15" is referenced at the end of `ToothWise_ISO25010_Evaluation_Tool_and_Responses.docx` (Part II).
- **`backend/models_weights/README.md`** still describes the old 8-class label set. The trained weights use 5 classes.
