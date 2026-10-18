# Chapters 4 and 5: data still needed

Chapter 4 is finished for the trained models. It appears in three files:

- `ToothWise_Chapters_1-4.pdf`: the paper with Chapter 4 inserted (pages 61–83).
- `ToothWise_Chapter_4_paper.docx`: an editable Chapter 4 in the paper's style.
- `ToothWise_Chapters_4_and_5_v2.docx`: Chapters 4 and 5 together.

Every value that still needs data is written as **[TBD …]** and highlighted yellow.

To rebuild after the data changes:

1. Run `backend\venv\Scripts\python.exe extract_training_metrics.py [eval_out folder]`. This reads the training metrics from the `.pt` files. If you pass an evaluation output folder, it also copies that folder's `job_b_test.json` into `chapter4_figures/eval_results.json`. Then it redraws all the figures.
2. Run `python generate_chapters_4_and_5_v2.py --paper` to build the paper-style Chapter 4. Run it without `--paper` to build the Chapters 4 and 5 file.
3. Run `python build_chapters_1_4_pdf.py`. This needs PyMuPDF and Microsoft Word.

## Already filled with real numbers

- **Validation results** (Table 16, Figures 19–20). These come from `train_metrics` stored in `backend/models_weights/*.pt`: 5,299 images, epoch 60.
- **Test-split results** (Tables 14 and 16–22, Figures 21–22). These cover 2,930 held-out images and were run on 2026-10-18 on this laptop. Results are given overall and per class for YOLOv8, YOLOv12 and the fused ensemble.
  - The test split was rebuilt from the four Roboflow zips in Downloads using the notebook's exact remap. The image counts and the 2,833 validation background images match the training log.
  - One prediction pass was scored with the Ultralytics matching rule.
  - Accuracy is defined as correct / (correct + wrong class + false alarms + missed), at confidence 0.25 and IoU 0.45.
- **Dataset sources, class remap and split counts** (Tables 12 and 13), and **training configuration** (Table 15, YOLOv8m and YOLOv12m).
- **CPU inference speed** (Table 21), **KNN holdout results** (Table 24), **84 backend tests passed** (Table 25), and the **Lighthouse and axe results** (Table 26).

## Data the team must supply

### "Overnight re-run"

No newer training output was found on this laptop. The checkpoints in `backend/models_weights` are dated 2026-09-10 (YOLOv8) and 2026-09-23 (YOLOv12).

If the re-run produced new `best.pt` files, copy them over these two files and run the two scripts again. Every number in the draft will update.

### Survey (Tuesday)

The ISO/IEC 25010 survey covers Section 4.3 and Tables 27–37.

- Actual respondent counts per group, and demographics (age, gender, experience).
- Every rating for items FS1–FS5, PE1–PE4, US1–US5, RE1–RE4, SP1–SP4 and CP1–CP4, so the weighted mean and SD can be computed for each item and each characteristic.
- The means split by IT experts and clinical users (Table 37).
- Common themes from the open-ended Section D answers, for the discussion paragraphs.

### Screening time and consistency (SOP 5)

This is Section 4.4, Tables 38–39. Nothing has been collected yet.

- Timed screenings, manual versus with Toothwise: number of patients, mean time and SD.
- Agreement with the dentist's findings, manual versus Toothwise: percentage agreement or Cohen's kappa, and missed findings.

### KNN against real cases

- The number of dentist-confirmed tiers and the KNN accuracy on them. Run `python -m app.ml.evaluate_knn` after the clinic has confirmed some screenings.

## Inconsistencies to fix in other chapters

- **SOP 4 in Chapter 1** lists the six characteristics as "security, privacy, usability, reliability, performance efficiency, and data protection". The survey instrument actually uses Functional Suitability, Performance Efficiency, Usability, Reliability, Security & Privacy, and Compatibility & Portability, and Chapter 4 follows the instrument. Update the SOP 4 wording to match.
- **The old `ToothWise_Chapters_4_and_5.docx` contains invented results.** Examples: 94.3% ensemble sensitivity, a 4.68 survey mean, a 65.6% reduction in screening time, and kappa 0.91. None of these come from real data, and they contradict the real test-split mAP@50 of 48–54%. Do not submit that file. The same invented "Table 15" is referenced at the end of `ToothWise_ISO25010_Evaluation_Tool_and_Responses.docx` (Part II).
- **`backend/models_weights/README.md`** still describes the old 8-class label set. The trained weights use 5 classes.
- **Chapter 3, page 52** says the technical specification "is presented in Chapter IV". Chapter IV is now Results and Discussion, and the specifications are in sections 3.6–3.7.
