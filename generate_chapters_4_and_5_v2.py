"""
Build ToothWise_Chapters_4_and_5_v2.docx (Chapter IV Results and Discussion,
Chapter V Summary, Conclusions and Recommendations).

Every model number is read from chapter4_figures/training_metrics.json, which
extract_training_metrics.py pulls out of the trained checkpoints. Numbers that
do not exist yet (the ISO/IEC 25010 survey, per-class and ensemble accuracy,
the screening-time trial) are written as "[TBD - ...]" and highlighted yellow
so they cannot be mistaken for results.

House rules (same as generate_chapters_and_survey.py): Book Antiqua 12 pt,
margins 1.5 in left/top and 1.0 in right/bottom, third person, no contractions.

Run order:
    backend\\venv\\Scripts\\python.exe extract_training_metrics.py
    python generate_chapters_4_and_5_v2.py
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "chapter4_figures"
# --paper: Chapter IV only, typeset to match the Chapters 1-3 paper (Times New
# Roman 12, black headings, plain grid tables, body area that fits inside the
# UDM letterhead frame) for build_chapters_1_4_pdf.py to merge into the PDF.
PAPER = "--paper" in sys.argv
OUT = ROOT / ("ToothWise_Chapter_4_paper.docx" if PAPER else "ToothWise_Chapters_4_and_5_v2.docx")

BODY_FONT = "Times New Roman" if PAPER else "Book Antiqua"
HEAD_FONT = "Times New Roman" if PAPER else "Tahoma"
ACCENT = RGBColor(0, 0, 0) if PAPER else RGBColor(0x5C, 0x2D, 0x4E)
TBD_RE = re.compile(r"(\[TBD[^\]]*\])")

M = json.loads((FIG / "training_metrics.json").read_text(encoding="utf-8"))
V8, V12 = M["YOLOv8"]["final"], M["YOLOv12"]["final"]

# Test-split evaluation (extract_training_metrics.py <eval_out>): one
# prediction pass over the 2,930 test images, scored with the Ultralytics
# matching rule for YOLOv8, YOLOv12 and the backend's fused ensemble, plus
# confusion matrices at confidence 0.25 and IoU 0.45.
EV = json.loads((FIG / "eval_results.json").read_text(encoding="utf-8"))
SH = EV["shared"]
OFF8, OFF12 = SH["YOLOv8"], SH["YOLOv12"]
# Images containing each class in the rebuilt test split (counted from its labels).
TEST_IMAGES_PER_CLASS = [39, 1190, 297, 147, 558]
CLASS_NAMES = ["Healthy tooth", "Cavity", "Gum inflammation", "Plaque", "Tartar"]


def by_class(d, key):
    """Per-class value of a metric list, indexed by class id (None if the class had no labels)."""
    vals = dict(zip(d["class_index"], d[key]))
    return [vals.get(c) for c in range(5)]


def f1(p_, r_):
    return 2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0.0


def detection_counts(cm):
    """Counts from a confusion matrix laid out as matrix[predicted, true], index 5 = background."""
    m = [row[:] for row in cm]
    tp = [m[c][c] for c in range(5)]
    wrong = sum(m[r][c] for r in range(5) for c in range(5) if r != c)
    fp = sum(m[r][5] for r in range(5))
    fn = sum(m[5][c] for c in range(5))
    total_tp = sum(tp)
    per_class = []
    for c in range(5):
        pred_c = sum(m[c][x] for x in range(6))
        true_c = sum(m[r][c] for r in range(6))
        denom = pred_c + true_c - m[c][c]
        per_class.append(m[c][c] / denom if denom else None)
    return {"tp": total_tp, "wrong": wrong, "fp": fp, "fn": fn,
            "accuracy": total_tp / (total_tp + wrong + fp + fn), "per_class": per_class}


ACC = {k: detection_counts(SH[k]["confusion_matrix"]) for k in ("YOLOv8", "YOLOv12", "Ensemble")}

# Measured on the development laptop on 2026-10-18 by timing YOLO.predict() on
# the four images in backend/uploads/screenings after one warm-up pass.
CPU_BENCH = {  # 4 clinic images x 5 runs, CPU only, imgsz 640, conf 0.25
    "machine": "Intel Core i7-13620H, 16 GB RAM, CPU only (PyTorch 2.14 CPU, Ultralytics 8.4.116)",
    "YOLOv8": (215.9, 8.9, 203.7),     # mean wall ms, SD, model forward ms
    "YOLOv12": (206.5, 7.6, 198.9),
    "both": (506.8, 138.7),
}
KNN = {  # python -m app.ml.evaluate_knn, 2,000 unseen synthetic cases, seed 999
    "accuracy": 0.9275, "f1_weighted": 0.9251,
    "per_tier": [("LOW", 0.9835, 0.9630, 0.9731, 864),
                 ("MEDIUM", 0.9018, 0.9547, 0.9275, 971),
                 ("HIGH", 0.7619, 0.5818, 0.6598, 165)],
    "confusion": [[832, 32, 0], [14, 927, 30], [0, 69, 96]],
}

TABLE_NO = [11]   # Chapters I-III end at Table 11
FIGURE_NO = [18]  # and at Figure 18
# Table/figure numbers by key. The document is built twice: the first pass
# records where each captioned item lands, the second uses those numbers in
# the text that refers to them.
REF: dict[str, int] = {}


def R(key):
    return str(REF.get(key, "?"))


def pct(x):
    return f"{x * 100:.2f}%"


# ── document helpers ────────────────────────────────────────────────────────
def _force_font(style, font_name):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(attr), font_name)
    # Theme font attributes win over explicit ones, so drop them.
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(attr), None)


def configure(doc):
    s = doc.sections[0]
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.left_margin, s.right_margin = Inches(1.5), Inches(1.0)
    s.top_margin, s.bottom_margin = Inches(1.5), Inches(1.0)
    if PAPER:  # body box of the letterhead pages: x 108-543 pt, y 121-710 pt
        s.right_margin = Pt(612 - 543)
        s.top_margin, s.bottom_margin = Pt(121), Pt(792 - 710)
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.5
    _force_font(normal, BODY_FONT)
    sizes = {"Heading 1": 12, "Heading 2": 12, "Heading 3": 12} if PAPER else         {"Heading 1": 16, "Heading 2": 14, "Heading 3": 12.5}
    for name, size in sizes.items():
        font = HEAD_FONT if name == "Heading 1" else BODY_FONT
        st = doc.styles[name]
        st.font.name, st.font.size, st.font.bold = font, Pt(size), True
        st.font.color.rgb = ACCENT
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(6)
        if PAPER:
            st.font.italic = False
            if name == "Heading 1":
                st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _force_font(st, font)


def add_page_numbers(doc):
    para = doc.sections[0].footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


def add_runs(para, text, bold=False, italic=False, size=None):
    """Add text to a paragraph, highlighting every [TBD ...] placeholder."""
    for part in TBD_RE.split(text):
        if not part:
            continue
        run = para.add_run(part)
        run.bold, run.italic = bold, italic
        if size:
            run.font.size = Pt(size)
        if TBD_RE.fullmatch(part):
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run.bold = True
    return para


def h(doc, text, level=1):
    return doc.add_heading(text, level=level)


def p(doc, text="", bold=False, italic=False, align=None, size=None):
    para = doc.add_paragraph()
    if align is not None:
        para.alignment = align
    elif text:
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if PAPER and not bold:
            para.paragraph_format.first_line_indent = Inches(0.5)
    return add_runs(para, text, bold, italic, size)


def bullet(doc, text):
    return add_runs(doc.add_paragraph(style="List Bullet"), text)


LIST_NO = [0]


def restart_numbering():
    LIST_NO[0] = 0


def numbered(doc, text):
    """Typed numbers with a hanging indent, so each list restarts at 1."""
    LIST_NO[0] += 1
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para.paragraph_format.left_indent = Inches(0.35)
    para.paragraph_format.first_line_indent = Inches(-0.35)
    para.add_run(f"{LIST_NO[0]}.\t")
    return add_runs(para, text)


def caption(doc, kind, title, key=None):
    counter = TABLE_NO if kind == "Table" else FIGURE_NO
    counter[0] += 1
    if key:
        REF[key] = counter[0]
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER if kind == "Figure" else WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.keep_with_next = kind == "Table"
    r = para.add_run(f"{kind} {counter[0]} ")
    r.bold = True
    add_runs(para, title, italic=True)
    return counter[0]


def table(doc, title, key, headers, rows, widths=None, note=None):
    n = caption(doc, "Table", title, key)
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, head in enumerate(headers):
        add_runs(t.cell(0, j).paragraphs[0], head)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            add_runs(t.cell(i + 1, j).paragraphs[0], str(val))
    for i, row in enumerate(t.rows):
        if PAPER:
            row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            if i == 0:
                row._tr.get_or_add_trPr().append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
            for j, cell in enumerate(row.cells):
                if widths and j < len(widths):
                    cell.width = Inches(widths[j])
                for para in cell.paragraphs:
                    para.paragraph_format.line_spacing = 1.15
                    para.paragraph_format.space_after = Pt(2)
                    para.paragraph_format.first_line_indent = None
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in para.runs:
                        run.font.size = Pt(11)
                        run.font.name = BODY_FONT
                        if i == 0:
                            run.bold = True
                            run.font.highlight_color = None
            continue
        row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        if i == 0:
            row._tr.get_or_add_trPr().append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for j, cell in enumerate(row.cells):
            if widths and j < len(widths):
                cell.width = Inches(widths[j])
            tcPr = cell._tc.get_or_add_tcPr()
            if i == 0:
                tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="5C2D4E"/>'))
            for para in cell.paragraphs:
                para.paragraph_format.line_spacing = 1.0
                para.paragraph_format.space_after = Pt(2)
                for run in para.runs:
                    run.font.size = Pt(10)
                    run.font.name = BODY_FONT
                    if i == 0:
                        run.bold = True
                        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        run.font.highlight_color = None
                if i == 0:
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if note:
        p(doc, note, italic=True, size=10, align=WD_ALIGN_PARAGRAPH.LEFT)
    else:
        p(doc, "")
    return n


def figure(doc, path, title, width=6.0, key=None):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.keep_with_next = True
    para.add_run().add_picture(str(path), width=Inches(width))
    return caption(doc, "Figure", title, key)


# ── Chapter IV ──────────────────────────────────────────────────────────────
def chapter_4(doc):
    h(doc, "CHAPTER IV", 1)
    h(doc, "RESULTS AND DISCUSSION", 1)
    p(doc, "This chapter presents the results obtained from the development, training, testing, and "
           "evaluation of Toothwise. The results are organized according to the Statement of the Problem "
           "and the Specific Objectives in Chapter I: the results of the trained detection models (Specific "
           "Objective 1), the specialization and technical results of the implemented system (Specific "
           "Objectives 2 and 3), the software quality evaluation based on ISO/IEC 25010 (Specific Objective "
           "4), and the comparison of screening consistency and screening time against the manual process "
           "(Specific Objective 5). Values marked [TBD] are placeholders for data that had not yet been "
           "collected when this chapter was drafted; they are not results.")

    dataset_section(doc)
    model_results_section(doc)
    technical_section(doc)
    survey_section(doc)
    consistency_section(doc)


def dataset_section(doc):
    h(doc, "4.1 Results of the Trained Datasets", 2)
    p(doc, "This section answers the first problem of the study by reporting how accurately the trained "
           "models detect tartar, plaque, cavity, gum inflammation, and healthy tooth on still intraoral "
           "photographs, and how YOLOv8 and YOLOv12 compare in precision, recall, mAP, and inference speed.")

    h(doc, "4.1.1 Dataset Preparation", 3)
    p(doc, "Four publicly available, annotated dental image datasets exported in YOLOv8 format were merged into "
           "a single training corpus. Because each source used a different class list, every source class was "
           "remapped to one of the five Toothwise classes or dropped when it fell outside the scope of the "
           "study (for example, missing teeth, malalignment, spacing, ulcers, and hypodontia). Segmentation "
           "polygons in the source labels were converted into bounding boxes so that all annotations share "
           f"the same detection format. Table {R('src')} presents the class mapping applied to each source.")
    table(doc, "Source Datasets and Class Remapping to the Toothwise Taxonomy", "src",
          ["Source dataset (export)", "Original classes", "Mapped to Toothwise class", "Dropped classes"],
          [["dadad12 (v3)", "calculus, cavities, maligned, missing, plaque, spacing, stains",
            "calculus → tartar; cavities → cavity; plaque → plaque", "maligned, missing, spacing, stains"],
           ["DenPal (v8)", "Caries, Missing Tooth, Tartar",
            "Caries → cavity; Tartar → tartar", "Missing Tooth"],
           ["oral-diseases (v2)", "calculus, caries, gingivitis, hypodontia, tooth_discolation, ulcer",
            "calculus → tartar; caries → cavity; gingivitis → gum_inflammation",
            "hypodontia, tooth_discolation, ulcer"],
           ["Teeth 2 (v1)", "Caries, Cavity, Healthy",
            "Caries → cavity; Cavity → cavity; Healthy → healthy_tooth", "None"]],
          [1.2, 1.7, 2.0, 1.1],
          note="Source: class lists and remap printed by the YOLOv12 training notebook "
               "(train_dental_yolov12_5class_2.ipynb).")

    p(doc, "After merging, the dataset was divided into training, validation, and test splits, as shown in "
           f"Table {R('split')}. Images that contained only dropped classes were kept as background (negative) images, "
           "which teach the models not to raise false detections on unremarkable regions.")
    table(doc, "Merged Dataset Split", "split",
          ["Split", "Images", "Background images (no target label)", "Share of images"],
          [["Training", "40,271", "10,791", "83.0%"],
           ["Validation", "5,299", "2,833", "10.9%"],
           ["Test", "2,930", "1,067", "6.0%"],
           ["Total", "48,500", "14,691", "100.0%"]],
          [1.3, 1.1, 2.4, 1.2],
          note="Label rows written during the merge: 86,028 bounding boxes and 7,457 polygons converted to "
               "boxes (93,485 in total). Test background count taken from the rebuilt test split.")
    tc = EV["shared"]["targets_per_class"]
    imgs = TEST_IMAGES_PER_CLASS
    p(doc, f"Table {R('inst')} presents the number of labeled findings per class in the held-out test split, "
           "which was used for the per-class evaluation in Section 4.1.4. The classes are clearly unbalanced, "
           f"ranging from {min(tc):,} labeled {CLASS_NAMES[tc.index(min(tc))].lower()} instances to {max(tc):,} "
           f"{CLASS_NAMES[tc.index(max(tc))].lower()} instances.")
    table(doc, "Labeled Instances per Class (Test Split, 2,930 Images)", "inst",
          ["Class", "Images containing the class", "Labeled instances", "Share of instances"],
          [[CLASS_NAMES[c], f"{int(imgs[c]):,}" if imgs else "—", f"{tc[c]:,}", f"{tc[c] / sum(tc) * 100:.1f}%"]
           for c in range(5)] + [["Total", "—", f"{sum(tc):,}", "100.0%"]],
          [2.0, 1.8, 1.4, 1.2],
          note="Counted from the rebuilt test split (same source order, class remap, and polygon-to-box "
               "conversion as the training notebook).")

    h(doc, "4.1.2 Training Configuration", 3)
    a8, a12 = M["YOLOv8"]["train_args"], M["YOLOv12"]["train_args"]
    p(doc, "Both models were trained with the Ultralytics framework on Google Colab using an NVIDIA Tesla T4 GPU, "
           "with identical hyperparameters and the same merged dataset so that the comparison is fair. Training "
           f"was resumed from the last saved checkpoint whenever a Colab session disconnected. Table {R('config')} "
           "summarizes the configuration, which was read directly from the saved model checkpoints.")
    table(doc, "Training Configuration of the Two Detection Models", "config",
          ["Parameter", "YOLOv8", "YOLOv12"],
          [["Model scale", "YOLOv8m (medium; depth 0.67, width 0.75)", "YOLOv12m (medium)"],
           ["Trainable parameters", f"{M['YOLOv8']['parameters']:,}", f"{M['YOLOv12']['parameters']:,}"],
           ["Pretrained starting weights", "Yes (COCO)", "Yes (COCO)"],
           ["Classes", "5", "5"],
           ["Epochs", str(a8["epochs"]), str(a12["epochs"])],
           ["Image size", f"{a8['imgsz']} × {a8['imgsz']} px", f"{a12['imgsz']} × {a12['imgsz']} px"],
           ["Batch size", str(a8["batch"]), str(a12["batch"])],
           ["Optimizer", "auto (selected by Ultralytics)", "auto (MuSGD, lr 0.01, momentum 0.9)"],
           ["Early-stopping patience", f"{a8['patience']} epochs", f"{a12['patience']} epochs"],
           ["Random seed", str(a8["seed"]), str(a12["seed"])],
           ["Ultralytics version", M["YOLOv8"]["ultralytics_version"], M["YOLOv12"]["ultralytics_version"]],
           ["Training hardware", "Google Colab, NVIDIA Tesla T4 (15 GB)", "Google Colab, NVIDIA Tesla T4 (15 GB)"],
           ["Checkpoint date (UTC)", M["YOLOv8"]["trained_utc"][:10], M["YOLOv12"]["trained_utc"][:10]]],
          [2.0, 2.0, 2.0])


def model_results_section(doc):
    h(doc, "4.1.3 Overall Detection Performance of YOLOv8 and YOLOv12", 3)
    p(doc, "The models were evaluated with the standard object-detection metrics. Precision is the share of "
           "predicted boxes that are correct, and recall is the share of actual findings that the model "
           "detected. The F1-score is the harmonic mean of precision and recall. mAP@50 is the mean average "
           "precision across the five classes when a predicted box must overlap the labeled box by at least "
           "50% (IoU 0.50), and mAP@50-95 averages this over stricter overlaps from 0.50 to 0.95. Detection "
           "accuracy, which is not a single built-in metric for object detection, is reported separately in "
           "Section 4.1.5.")
    p(doc, f"Table {R('overall')} presents the overall results on two splits: the validation split (5,299 "
           "images), which was scored automatically at the end of training, and the held-out test split (2,930 "
           "images), which neither model saw during training and which is the primary basis for the comparison.")
    rows = []
    for key, label in (("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score"),
                       ("map50", "mAP@50"), ("map50_95", "mAP@50-95")):
        if key == "f1":
            t8, t12 = f1(OFF8["precision"], OFF8["recall"]), f1(OFF12["precision"], OFF12["recall"])
        else:
            t8, t12 = OFF8[key], OFF12[key]
        rows.append([label, pct(V8[key]), pct(V12[key]), pct(t8), pct(t12)])
    table(doc, "Overall Detection Performance of YOLOv8 and YOLOv12", "overall",
          ["Metric", "YOLOv8 (validation)", "YOLOv12 (validation)", "YOLOv8 (test)", "YOLOv12 (test)"],
          rows, [1.3, 1.25, 1.25, 1.25, 1.25],
          note="Validation: train_metrics stored in the checkpoints (epoch 60). Test: one prediction pass over "
               "the held-out test split (confidence 0.001, NMS IoU 0.70, image size 640), scored with the "
               "Ultralytics matching rule.")

    figure(doc, FIG / "fig_training_curves.png",
           "mAP@50 and mAP@50-95 per Training Epoch for YOLOv8 and YOLOv12", key="fig_curves")
    figure(doc, FIG / "fig_final_metrics.png", "Final Validation Metrics of YOLOv8 and YOLOv12", key="fig_final")

    best_t = "YOLOv8" if OFF8["map50"] >= OFF12["map50"] else "YOLOv12"
    bt, ot = (OFF8, OFF12) if best_t == "YOLOv8" else (OFF12, OFF8)
    p(doc, f"On the validation split, YOLOv8 obtained a slightly higher score than YOLOv12 on every overall "
           f"metric, with an mAP@50 of {pct(V8['map50'])} against {pct(V12['map50'])}. On the held-out test "
           f"split, {best_t} obtained the higher mAP@50 ({pct(bt['map50'])} against {pct(ot['map50'])}) "
           f"and mAP@50-95 ({pct(bt['map50_95'])} against {pct(ot['map50_95'])}). Test precision was "
           f"{pct(OFF8['precision'])} for YOLOv8 and {pct(OFF12['precision'])} for YOLOv12, and test recall was "
           f"{pct(OFF8['recall'])} and {pct(OFF12['recall'])}, respectively. YOLOv12 reached its results with "
           f"about 24% fewer parameters ({M['YOLOv12']['parameters'] / 1e6:.2f} million against "
           f"{M['YOLOv8']['parameters'] / 1e6:.2f} million).")
    p(doc, f"Figure {R('fig_curves')} shows that both models improved quickly during the first ten epochs and "
           "then levelled off: after roughly epoch 25, validation mAP@50 rose by only about two percentage points "
           "for either model. Additional epochs alone are therefore unlikely to produce large gains; further "
           "improvement depends more on the training data than on longer training.")

    h(doc, "4.1.4 Per-Class Detection Results", 3)
    p(doc, f"Tables {R('perclass_v8')} and {R('perclass_v12')} present the precision, recall, F1-score, mAP@50, "
           f"and mAP@50-95 of each class on the test split, and Figure {R('fig_perclass')} compares the per-class "
           "mAP@50 of the two models and the fused ensemble.")
    tc = SH["targets_per_class"]
    for name, d, key in (("YOLOv8", OFF8, "perclass_v8"), ("YOLOv12", OFF12, "perclass_v12")):
        P, Rr, A50, A = (by_class(d, k) for k in ("p", "r", "ap50", "ap50_95"))
        rows = []
        for c in range(5):
            if P[c] is None:
                rows.append([CLASS_NAMES[c], f"{tc[c]:,}", "—", "—", "—", "—", "—"])
            else:
                rows.append([CLASS_NAMES[c], f"{tc[c]:,}", pct(P[c]), pct(Rr[c]), pct(f1(P[c], Rr[c])),
                             pct(A50[c]), pct(A[c])])
        rows.append(["All classes", f"{sum(tc):,}", pct(d["precision"]), pct(d["recall"]),
                     pct(f1(d["precision"], d["recall"])), pct(d["map50"]), pct(d["map50_95"])])
        table(doc, f"Per-Class Detection Performance of {name} (Test Split)", key,
              ["Class", "Instances", "Precision", "Recall", "F1-score", "mAP@50", "mAP@50-95"],
              rows, [1.5, 0.8, 0.85, 0.8, 0.85, 0.8, 0.9],
              note="Source: test-split evaluation pass, scored with the Ultralytics matching rule.")
    figure(doc, FIG / "fig_perclass_map50.png", "Per-Class mAP@50 on the Test Split", key="fig_perclass")
    per_class_discussion(doc)

    h(doc, "4.1.5 Detection Accuracy and Confusion Matrix", 3)
    p(doc, "Object detection does not have a single built-in accuracy measure, because a model can be wrong "
           "in three ways: it can label a finding with the wrong class, raise a box where there is no finding "
           "(false alarm), or miss a finding entirely. This study therefore defines detection accuracy as the "
           "number of correctly located and correctly labeled findings divided by the total of correct, "
           "wrongly labeled, false-alarm, and missed findings. The counts were taken from the confusion matrix "
           "at the confidence threshold used by the deployed system (0.25) and an IoU of 0.45. Tables "
           f"{R('accuracy')} and {R('accuracy_class')} present the result, and Figure {R('fig_cm')} shows the "
           "confusion matrices.")
    rows = []
    for k in ("YOLOv8", "YOLOv12", "Ensemble"):
        a = ACC[k]
        rows.append([k if k != "Ensemble" else "Fused ensemble", f"{int(a['tp']):,}", f"{int(a['wrong']):,}",
                     f"{int(a['fp']):,}", f"{int(a['fn']):,}", pct(a["accuracy"])])
    table(doc, "Detection Accuracy on the Test Split (Confidence 0.25, IoU 0.45)", "accuracy",
          ["Model", "Correct", "Wrong class", "False alarms", "Missed", "Detection accuracy"],
          rows, [1.5, 0.9, 0.9, 1.0, 0.9, 1.2],
          note="Detection accuracy = Correct / (Correct + Wrong class + False alarms + Missed).")
    rows = []
    for c in range(5):
        vals = [ACC[k]["per_class"][c] for k in ("YOLOv8", "YOLOv12", "Ensemble")]
        rows.append([CLASS_NAMES[c]] + [pct(v) if v is not None else "—" for v in vals])
    table(doc, "Detection Accuracy per Class on the Test Split", "accuracy_class",
          ["Class", "YOLOv8", "YOLOv12", "Fused ensemble"], rows, [2.0, 1.3, 1.3, 1.5],
          note="Per class: correct detections of the class divided by all detections and labels of that "
               "class (correct + wrong + false alarms + missed).")
    figure(doc, FIG / "fig_confusion_matrices.png",
           "Confusion Matrices on the Test Split (Columns Normalized by True Class)", key="fig_cm", width=6.3)
    accuracy_discussion(doc)

    h(doc, "4.1.6 Inference Speed", 3)
    b = CPU_BENCH
    p(doc, "Inference speed was measured on the deployment-class workstation without a GPU, which reflects "
           "the clinic setting described in Chapter III. Each model processed four clinic screening images "
           f"five times at 640 × 640 pixels after a warm-up pass. Table {R('speed')} reports the mean time per image.")
    table(doc, "Inference Time per Image on CPU", "speed",
          ["Configuration", "Mean time per image", "Standard deviation", "Model forward pass only"],
          [["YOLOv8", f"{b['YOLOv8'][0]:.1f} ms", f"{b['YOLOv8'][1]:.1f} ms", f"{b['YOLOv8'][2]:.1f} ms"],
           ["YOLOv12", f"{b['YOLOv12'][0]:.1f} ms", f"{b['YOLOv12'][1]:.1f} ms", f"{b['YOLOv12'][2]:.1f} ms"],
           ["Both models (ensemble, run in sequence)", f"{b['both'][0]:.1f} ms", f"{b['both'][1]:.1f} ms", "—"]],
          [2.3, 1.4, 1.3, 1.4],
          note=f"Machine: {b['machine']}; n = 20 timed predictions per configuration.")
    p(doc, "Both models analyzed a photograph in about one fifth of a second, with YOLOv12 about 4% faster "
           "than YOLOv8 on the same hardware. Running both models for the ensemble took about half a second "
           "per image. This is well within an interactive response time for a screening workflow, in which "
           "the dentist uploads a photograph and reviews the results on the same screen.")

    h(doc, "4.1.7 Ensemble Fusion", 3)
    p(doc, "In the deployed system, both models analyze each image and their outputs are combined into a "
           "single clinical detection set. Boxes from both models are grouped when they share a label and "
           "overlap with an IoU of at least 0.50; each group is merged into one box whose coordinates are the "
           "confidence-weighted average of its members (weighted box fusion). A finding confirmed by both models "
           "receives a confidence increase of 0.08, capped at 0.98, because agreement between two independently "
           "trained models is stronger evidence than either model alone.")
    p(doc, "To measure the effect of fusion, the test split was passed once through both models, and the "
           "YOLOv8 output, the YOLOv12 output, and the fused output were scored with the same matching code. "
           f"Table {R('ensemble')} presents the result.")
    rows = []
    for key, label in (("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score"),
                       ("map50", "mAP@50"), ("map50_95", "mAP@50-95")):
        vals = []
        for k in ("YOLOv8", "YOLOv12", "Ensemble"):
            d = SH[k]
            vals.append(f1(d["precision"], d["recall"]) if key == "f1" else d[key])
        rows.append([label] + [pct(v) for v in vals])
    for c in range(5):
        vals = [by_class(SH[k], "ap50")[c] for k in ("YOLOv8", "YOLOv12", "Ensemble")]
        rows.append([f"mAP@50 – {CLASS_NAMES[c].lower()}"] + [pct(v) if v is not None else "—" for v in vals])
    table(doc, "YOLOv8, YOLOv12, and the Fused Ensemble on the Test Split", "ensemble",
          ["Metric", "YOLOv8", "YOLOv12", "Fused ensemble"], rows, [2.4, 1.2, 1.2, 1.4],
          note="Same prediction pass as Tables "
               f"{R('overall')} to {R('perclass_v12')}; the single-model columns repeat those results.")
    ensemble_discussion(doc)

    h(doc, "4.1.8 Summary of the Model Comparison", 3)
    model_summary(doc)


def class_rank():
    """Classes ordered from best to worst by the mean test mAP@50 of the two models."""
    a8, a12 = by_class(OFF8, "ap50"), by_class(OFF12, "ap50")
    have = [c for c in range(5) if a8[c] is not None and a12[c] is not None]
    return sorted(have, key=lambda c: -(a8[c] + a12[c]) / 2), a8, a12


def ens_vs_best():
    best = max(("YOLOv8", "YOLOv12"), key=lambda k: SH[k]["map50"])
    return best, SH["Ensemble"]["map50"] - SH[best]["map50"]


def per_class_discussion(doc):
    order, a8, a12 = class_rank()
    tc = SH["targets_per_class"]
    best, worst = order[0], order[-1]
    p(doc, f"Performance differed strongly between classes. Both models detected "
           f"{CLASS_NAMES[best].lower()} best (mAP@50 of {pct(a8[best])} for YOLOv8 and {pct(a12[best])} for "
           f"YOLOv12) and {CLASS_NAMES[worst].lower()} worst ({pct(a8[worst])} and {pct(a12[worst])}). In "
           f"descending order of mean mAP@50, the classes ranked as follows: "
           + ", ".join(CLASS_NAMES[c].lower() for c in order) + ".")
    p(doc, "The per-class results show that the moderate overall scores are driven mainly by the weaker "
           "classes rather than by uniformly weak detection. Classes with distinct, well-bounded visual "
           "features are detected far more reliably than classes that appear as thin, low-contrast films or "
           "diffuse discoloration along the gum line, whose boundaries are hard to annotate consistently and "
           "therefore hard to match at an IoU of 0.50. Class frequency also matters: the test split contains "
           f"{tc[worst]:,} {CLASS_NAMES[worst].lower()} instances against {max(tc):,} "
           f"{CLASS_NAMES[tc.index(max(tc))].lower()} instances, and each class comes from only some of the "
           "four source datasets, so the models may partly learn the photographic style of a source rather "
           "than the condition itself. These are the same difficulties that the first problem of the study "
           "identifies in visual-only screening.")


def accuracy_discussion(doc):
    a8, a12, ae = ACC["YOLOv8"], ACC["YOLOv12"], ACC["Ensemble"]
    best = max(ACC, key=lambda k: ACC[k]["accuracy"])
    kinds = {"missed findings": a8["fn"] + a12["fn"], "false alarms": a8["fp"] + a12["fp"],
             "wrong-class detections": a8["wrong"] + a12["wrong"]}
    main_err = max(kinds, key=kinds.get)
    # Most frequent class-to-class confusion across both single models.
    pair, pair_n = None, 0
    for r in range(5):
        for c in range(5):
            if r != c:
                n = SH["YOLOv8"]["confusion_matrix"][r][c] + SH["YOLOv12"]["confusion_matrix"][r][c]
                if n > pair_n:
                    pair, pair_n = (r, c), n
    name = {"YOLOv8": "YOLOv8", "YOLOv12": "YOLOv12", "Ensemble": "the fused ensemble"}
    p(doc, f"At the deployed confidence threshold, YOLOv8 reached a detection accuracy of {pct(a8['accuracy'])}, "
           f"YOLOv12 {pct(a12['accuracy'])}, and the fused ensemble {pct(ae['accuracy'])}; the highest was "
           f"obtained by {name[best]}. For both single models, the most common error type was {main_err}. "
           "Wrong-class detections were comparatively rare, which means that when a model does locate a "
           "finding it usually names the condition correctly; most errors come from findings that are not "
           "detected at all or from boxes raised on unremarkable areas."
           + (f" The most frequent confusion between two conditions was a true "
              f"{CLASS_NAMES[pair[1]].lower()} labeled as {CLASS_NAMES[pair[0]].lower()}."
              if pair else ""))
    p(doc, "For a screening support tool, missed findings are the more serious error because a false alarm is "
           "reviewed and dismissed by the dentist, whereas a missed finding may not be examined. This supports "
           "keeping the dentist's visual examination as the reference and presenting the detections as "
           "suggestions.")


def ensemble_discussion(doc):
    best, gain = ens_vs_best()
    e = SH["Ensemble"]
    b = SH[best]
    p(doc, f"The fused ensemble obtained an mAP@50 of {pct(e['map50'])}, against {pct(b['map50'])} for the "
           f"better single model ({best}) in the same evaluation, a difference of {gain * 100:+.2f} percentage "
           f"points. Its recall was {pct(e['recall'])} against {pct(b['recall'])}, and its precision "
           f"{pct(e['precision'])} against {pct(b['precision'])}.")
    if gain > 0.005:
        p(doc, "Fusion therefore improved on both single models: findings that one model misses are often "
               "detected by the other, and agreement between the two raises the confidence of the findings "
               "that both models report. This result supports the design decision to run both models in the "
               "deployed system rather than choosing one.")
    elif gain >= -0.005:
        p(doc, "Fusion therefore performed on par with the better single model. Its main value in the deployed "
               "system is that agreement between two independently trained models marks the findings that are "
               "most likely to be real, which the dentist sees as a higher confidence.")
    else:
        p(doc, "Fusion therefore did not improve on the better single model at the current fusion settings. "
               "Because the fused confidence is boosted when both models agree, false alarms that both models "
               "share are also promoted. The fusion threshold and confidence boost should be tuned on the "
               "validation split before the ensemble is relied upon, as recommended in Chapter V.")


def model_summary(doc):
    best_t = "YOLOv8" if OFF8["map50"] >= OFF12["map50"] else "YOLOv12"
    order, _, _ = class_rank()
    b = CPU_BENCH
    p(doc, f"In answer to the first problem, both models learned to detect the five target classes. On the "
           f"held-out test split, {best_t} obtained the higher mAP@50 (YOLOv8 {pct(OFF8['map50'])}, YOLOv12 "
           f"{pct(OFF12['map50'])}), while YOLOv12 was lighter and slightly faster (about {b['YOLOv12'][0]:.0f} ms "
           f"against {b['YOLOv8'][0]:.0f} ms per image on CPU). The difference between the two models is small "
           f"compared with the difference between classes: {CLASS_NAMES[order[0]].lower()} was detected "
           f"reliably, while {CLASS_NAMES[order[-1]].lower()} remained difficult for both. The fused ensemble "
           f"reached an mAP@50 of {pct(SH['Ensemble']['map50'])} and a detection accuracy of "
           f"{pct(ACC['Ensemble']['accuracy'])}. These results support the delimitation in Chapter I that "
           "Toothwise is a screening support tool and not a diagnostic replacement: detections are presented "
           "to the dentist as suggestions, and the dentist confirms or corrects the findings and the risk tier.")


def technical_section(doc):
    h(doc, "4.2 Specialization and Technical Results", 2)
    p(doc, "This section presents the technical results of the implemented system: the detection pipeline, "
           "the risk scoring engine, the KNN recommendation feature, the results interface and patient records, "
           "role-based access, the patient-facing chatbot, and the measured quality of the web application.")

    h(doc, "4.2.1 AI Detection Pipeline", 3)
    p(doc, "The FastAPI backend loads both trained checkpoints when the server starts and exposes the "
           "screening workflow through authenticated REST endpoints. For each uploaded intraoral photograph the "
           "pipeline (1) validates the file type and size (maximum 15 MB), (2) runs YOLOv8 and YOLOv12, "
           "(3) fuses their detections as described in Section 4.1.6, (4) computes a risk score and risk tier, "
           "(5) generates a prevention plan, and (6) stores the image, every detection with its bounding box and "
           "confidence, the risk result, and the plan in the patient's record. The response includes the fused "
           "detections and the raw output of each model.")

    h(doc, "4.2.2 Risk Scoring Engine", 3)
    p(doc, "The risk score is rule-based so that every score can be explained to the patient and audited by "
           "the dentist. Each non-healthy detection contributes its class severity multiplied by its "
           "confidence; the score is the highest such value plus 6 points for every additional finding (up to 5 "
           f"additional findings), capped at 100. Table {R('risk')} lists the severity weights and the tier thresholds.")
    table(doc, "Risk Scoring Weights and Tier Thresholds", "risk",
          ["Class", "Severity weight", "Highest possible score from one finding"],
          [["Healthy tooth", "0", "0 (no risk contribution)"],
           ["Plaque", "25", "25 (LOW)"],
           ["Tartar", "35", "35 (MEDIUM)"],
           ["Gum inflammation", "45", "45 (MEDIUM)"],
           ["Cavity", "70", "70 (HIGH)"]],
          [2.0, 1.5, 2.5],
          note="Tiers: LOW 0–34, MEDIUM 35–69, HIGH 70–100. Source: backend/app/ml/labels.py "
               "(SEVERITY_WEIGHT) and backend/app/ml/risk_engine.py.")

    h(doc, "4.2.3 KNN-Based Recommendation Feature", 3)
    p(doc, "A K-Nearest Neighbors classifier (K = 5, distance-weighted) assigns each screening to a LOW, "
           "MEDIUM, or HIGH tier from its detection profile, and the prevention plan is composed from that tier "
           "and the specific conditions found. The classifier was first trained on synthetic reference cases "
           "generated from the clinical scoring rule. Every tier that a dentist confirms or corrects in the "
           "system is stored as a real labeled case and added to the reference data on retraining.")
    p(doc, f"Table {R('knn')} presents the result of the evaluation script on 2,000 synthetic cases that were not used "
           "in training. Because these cases follow the same rule as the training cases, the result measures "
           "how faithfully the classifier reproduces the rule, not its clinical accuracy.")
    rows = [[t, pct(pr), pct(rc), pct(f1), f"{n:,}"] for t, pr, rc, f1, n in KNN["per_tier"]]
    rows.append(["Overall (weighted)", "—", "—", pct(KNN["f1_weighted"]), "2,000"])
    table(doc, "KNN Tier Classification on Unseen Synthetic Cases", "knn",
          ["Risk tier", "Precision", "Recall", "F1-score", "Cases"], rows,
          [1.6, 1.1, 1.1, 1.1, 1.0],
          note=f"Overall accuracy: {pct(KNN['accuracy'])}. Source: python -m app.ml.evaluate_knn.")
    c = KNN["confusion"]
    p(doc, f"The classifier agreed with the rule on {pct(KNN['accuracy'])} of the unseen cases. Most errors "
           f"occurred at tier boundaries; the weakest tier was HIGH, where {c[2][1]} of {sum(c[2])} cases were "
           f"classified as MEDIUM (recall {pct(KNN['per_tier'][2][2])}). No LOW case was classified as HIGH and "
           f"no HIGH case as LOW. Because a missed HIGH tier is the most consequential error, the dentist's "
           f"confirmation step remains part of the workflow. The accuracy of the classifier against "
           f"dentist-confirmed tiers is [TBD – number of dentist-confirmed cases and accuracy; none were "
           f"recorded when this chapter was drafted].")

    h(doc, "4.2.4 Results Interface and Patient Records", 3)
    p(doc, "In answer to the second problem, every screening is saved as a standardized visual record: the "
           "original photograph, color-coded bounding boxes with the condition label and confidence, a "
           "plain-language description of each condition, the risk score and tier, the prevention plan, and the "
           "dentist's clinical notes. The patient record lists all screenings in chronological order with a "
           "risk trend chart, so findings can be compared across visits. Each screening can be exported as a "
           "PDF report. Patients can register for the self-service portal and view their own screening history, "
           "findings, and prevention plans, but no other patient's data.")

    h(doc, "4.2.5 Role-Based Web Application", 3)
    p(doc, "The staff side of the system enforces three roles. The dentist acts as administrator and can "
           "manage staff accounts and view the audit log; the receptionist manages patient registration and "
           "records; and the dental assistant performs screenings. Patients use a separate login scope. Access "
           "is enforced by the backend on every request, not only by hiding menu items. Passwords are hashed "
           "with bcrypt, sessions use JSON Web Tokens, login and chatbot requests are rate-limited, and "
           "sensitive staff actions are written to an append-only audit log.")
    p(doc, "The backend has an automated test suite of 84 test cases covering authentication, staff "
           "management, patients, screenings, labels, the risk engine, the recommender, and role permissions. "
           f"All 84 tests passed in the final run (Table {R('tests')}).")
    table(doc, "Automated Backend Test Results", "tests",
          ["Test module", "Area tested", "Test cases", "Result"],
          [["test_auth.py", "Staff and patient login, tokens", "11", "Passed"],
           ["test_dentists.py", "Staff account management", "14", "Passed"],
           ["test_patients.py", "Patient records", "10", "Passed"],
           ["test_screenings.py", "Screening workflow and storage", "9", "Passed"],
           ["test_labels.py", "Class list consistency", "11", "Passed"],
           ["test_risk_engine.py", "Risk score and tier", "9", "Passed"],
           ["test_recommender.py", "KNN tier and prevention plan", "9", "Passed"],
           ["test_roles.py", "Three-role access control", "11", "Passed"],
           ["Total", "", "84", "84 passed, 0 failed"]],
          [1.6, 2.4, 1.0, 1.4],
          note="Source: python -m pytest in backend/.")

    h(doc, "4.2.6 AI Chatbot", 3)
    p(doc, "The public website includes an AI assistant for general dental-care questions and questions about "
           "the clinic and the Toothwise service. It is powered by the Google Gemini API. Before a message is "
           "sent to the model, e-mail addresses, phone numbers, and record identifiers are removed, and any "
           "request for a personal record or screening result is answered with a referral to the secure "
           "patient portal instead of being forwarded. Requests are limited to 12 per minute per client.")

    h(doc, "4.2.7 Web Performance and Accessibility", 3)
    p(doc, "The production build of the frontend was audited with Google Lighthouse 12 on the public pages at a "
           f"mobile width (390 px, simulated slow 4G) and a desktop width (1440 px). Table {R('lighthouse')} presents the scores.")
    table(doc, "Lighthouse Audit Results", "lighthouse",
          ["Page", "Viewport", "Performance", "Accessibility", "Best practices", "Largest Contentful Paint"],
          [["Landing", "Desktop", "99", "100", "100", "0.8 s"],
           ["Landing", "Mobile", "83", "100", "100", "4.0 s"],
           ["Staff login", "Desktop", "100", "100", "100", "0.7 s"],
           ["Staff login", "Mobile", "92", "100", "100", "2.9 s"],
           ["Patient portal", "Desktop", "100", "100", "100", "0.7 s"],
           ["Patient portal", "Mobile", "91", "100", "100", "3.0 s"]],
          [1.3, 0.9, 1.0, 1.0, 1.0, 1.3],
          note="Cumulative Layout Shift was 0 on every page. Source: docs/frontend_polish_plan.md.")
    p(doc, "Accessibility and best practices scored 100 on every audited page, and performance ranged from 99 "
           "to 100 on desktop and from 83 to 92 on mobile. The lowest score, the landing page on mobile, is due "
           "to the hero photograph being discovered late in page loading. Splitting the application by route "
           "reduced the main JavaScript bundle from 231 KB to 95 KB (compressed). The signed-in staff pages, "
           "which Lighthouse cannot reach, were audited with axe-core 4.14 against WCAG 2.0 and 2.1 Level A and "
           "AA rules on all eight staff routes and five dialogs in both light and dark mode; the final audit "
           "found zero violations.")


def survey_section(doc):
    h(doc, "4.3 Software Quality Evaluation Based on ISO/IEC 25010", 2)
    p(doc, "This section answers the fourth problem of the study. [TBD – the evaluation survey is scheduled "
           "for administration; every number in this section is a placeholder to be replaced with the tallied "
           "responses.]")

    h(doc, "4.3.1 Respondents", 3)
    p(doc, "The evaluation targets 100 respondents in two groups: 30 IT experts (software developers, systems "
           "analysts, database administrators, and IT educators) and 70 clinical end users (licensed dentists, "
           f"dental assistants, receptionists, and patients of CodiSmile Dental Clinic). Table {R('resp')} presents the "
           "planned and actual distribution of respondents.")
    table(doc, "Distribution of Respondents", "resp",
          ["Respondent group", "Planned (n)", "Actual (n)", "Percentage"],
          [["IT experts", "30", "[TBD]", "[TBD]"],
           ["Licensed dentists", "10", "[TBD]", "[TBD]"],
           ["Dental assistants", "10", "[TBD]", "[TBD]"],
           ["Receptionists", "5", "[TBD]", "[TBD]"],
           ["Patients", "45", "[TBD]", "[TBD]"],
           ["Total", "100", "[TBD]", "100%"]],
          [2.4, 1.2, 1.2, 1.2])
    table(doc, "Demographic Profile of Respondents", "demo",
          ["Profile", "Category", "Frequency", "Percentage"],
          [["Age", "18–25 / 26–35 / 36–45 / 46–55 / 56 and above", "[TBD]", "[TBD]"],
           ["Gender", "Male / Female / Prefer not to say", "[TBD]", "[TBD]"],
           ["Experience with digital health or IT systems",
            "Less than 1 year / 1–3 years / 4–7 years / 8 years or more", "[TBD]", "[TBD]"]],
          [1.8, 2.6, 1.0, 1.0],
          note="Expand each row into one row per category when the responses are tallied.")

    h(doc, "4.3.2 Research Instrument", 3)
    p(doc, "The instrument (Appendix A) contains 26 statements grouped under six quality characteristics of the "
           f"ISO/IEC 25010 software product quality model, as listed in Table {R('iso')}. Respondents rate each statement "
           "after using the system.")
    table(doc, "ISO/IEC 25010 Characteristics Evaluated", "iso",
          ["Characteristic", "Item codes", "Items", "What is evaluated"],
          [["Functional Suitability", "FS1–FS5", "5", "Patient records, AI detection, risk scoring, KNN plan, PDF report"],
           ["Performance Efficiency", "PE1–PE4", "4", "Detection response time, page loading, resource use, concurrency"],
           ["Usability", "US1–US5", "5", "Layout, result presentation, screening workflow, patient portal, legibility"],
           ["Reliability", "RE1–RE4", "4", "Error handling, availability, data integrity, backups"],
           ["Security and Privacy", "SP1–SP4", "4", "Authentication and roles, password hashing, image protection, audit log"],
           ["Compatibility and Portability", "CP1–CP4", "4", "Browsers, screen sizes, cameras, deployment"],
           ["Total", "", "26", ""]],
          [1.8, 1.0, 0.6, 3.0])

    h(doc, "4.3.3 Rating Scale and Interpretation", 3)
    p(doc, "Each statement is rated on a five-point Likert scale. The weighted mean of each item and "
           f"characteristic is interpreted using the ranges in Table {R('likert')}.")
    table(doc, "Likert Scale and Verbal Interpretation", "likert",
          ["Scale", "Mean range", "Verbal interpretation", "Acceptability"],
          [["5", "4.21 – 5.00", "Strongly Agree", "Highly Acceptable"],
           ["4", "3.41 – 4.20", "Agree", "Acceptable"],
           ["3", "2.61 – 3.40", "Neutral", "Moderately Acceptable"],
           ["2", "1.81 – 2.60", "Disagree", "Slightly Acceptable"],
           ["1", "1.00 – 1.80", "Strongly Disagree", "Not Acceptable"]],
          [0.8, 1.4, 2.0, 2.0])

    h(doc, "4.3.4 Statistical Treatment", 3)
    p(doc, "The weighted mean of each item is computed as WM = Σ(f × x) / N, where f is the number of "
           "respondents who chose a rating, x is the rating (1 to 5), and N is the number of respondents. The "
           "mean of a characteristic is the average of its item means, and the overall mean is the average of "
           "the six characteristic means. The standard deviation is reported to show how much the respondents "
           "agreed with one another.")

    h(doc, "4.3.5 Evaluation Results per Characteristic", 3)
    items = {
        "Functional Suitability": [
            ("FS1", "The system accurately captures and maintains patient information and records."),
            ("FS2", "The AI detection module correctly identifies and localizes dental conditions."),
            ("FS3", "The risk score (0–100) and risk tier classification are appropriate to the findings."),
            ("FS4", "The KNN recommendation feature generates relevant, condition-specific prevention plans."),
            ("FS5", "The system generates complete PDF screening reports.")],
        "Performance Efficiency": [
            ("PE1", "The AI model returns detection results within an acceptable time."),
            ("PE2", "Pages, patient lists, and images load quickly."),
            ("PE3", "The system runs smoothly without using excessive computer resources."),
            ("PE4", "Concurrent requests and database transactions are handled reliably.")],
        "Usability": [
            ("US1", "The interface layout is well-structured, intuitive, and easy to navigate."),
            ("US2", "Detection results, color-coded labels, and risk badges are easy to understand."),
            ("US3", "The four-step screening workflow is easy to follow."),
            ("US4", "The patient portal is accessible and patient-friendly."),
            ("US5", "Contrast, typography, and light and dark themes make the text easy to read.")],
        "Reliability": [
            ("RE1", "The system handles invalid inputs and interruptions gracefully."),
            ("RE2", "The system remains available for continuous use."),
            ("RE3", "Data integrity is maintained across all records."),
            ("RE4", "Database backups run reliably to protect patient data.")],
        "Security and Privacy": [
            ("SP1", "Authentication uses secure tokens and role-based access."),
            ("SP2", "Passwords are stored using secure hashing."),
            ("SP3", "Patient photographs are protected from unauthorized access."),
            ("SP4", "An audit trail records sensitive administrative and clinical actions.")],
        "Compatibility and Portability": [
            ("CP1", "The application works consistently across mainstream browsers."),
            ("CP2", "The system adapts to desktop, laptop, and tablet screens."),
            ("CP3", "The system works with standard device cameras for image capture."),
            ("CP4", "The system can be deployed on standard clinic computers.")],
    }
    p(doc, f"Tables {R('char0')} to {R('char5')} present the weighted mean, standard deviation, and verbal interpretation of each "
           "statement, grouped by characteristic. The statements are abbreviated; the full wording is in "
           "Appendix A.")
    for char, its in items.items():
        rows = [[code, text, "[TBD]", "[TBD]", "[TBD]"] for code, text in its]
        rows.append(["", f"{char} — mean", "[TBD]", "[TBD]", "[TBD]"])
        table(doc, f"Evaluation Results for {char}", f"char{list(items).index(char)}",
              ["Code", "Statement", "WM", "SD", "Verbal interpretation"], rows,
              [0.6, 3.3, 0.6, 0.6, 1.4])
        p(doc, f"[TBD – one paragraph interpreting the {char} results: the highest- and lowest-rated "
               f"statements and what respondents' comments say about them.]")

    h(doc, "4.3.6 Summary of the ISO/IEC 25010 Evaluation", 3)
    rows = [[c, "[TBD]", "[TBD]", "[TBD]", "[TBD]", "[TBD]"] for c in items]
    rows.append(["Overall", "[TBD]", "[TBD]", "[TBD]", "[TBD]", "[TBD]"])
    table(doc, "Summary of ISO/IEC 25010 Evaluation Results", "isosum",
          ["Characteristic", "IT experts (WM)", "Clinical users (WM)", "Overall WM", "SD", "Interpretation"],
          rows, [1.8, 0.9, 0.9, 0.9, 0.6, 1.3])
    p(doc, "[TBD – discussion of the overall result: the overall weighted mean and its interpretation, the "
           "highest- and lowest-rated characteristics, any difference between IT experts and clinical users, "
           "and the main themes of the qualitative feedback in Section D of the instrument.]")


def consistency_section(doc):
    h(doc, "4.4 Screening Consistency and Screening Time", 2)
    p(doc, "This section answers the fifth problem of the study by comparing Toothwise-assisted screening with "
           "the current manual process, using the dentist's findings as the reference. [TBD – this comparison "
           "had not been conducted when this chapter was drafted.]")
    table(doc, "Screening Time: Manual Process versus Toothwise", "time",
          ["Measure", "Manual process", "With Toothwise", "Difference"],
          [["Number of screenings timed", "[TBD]", "[TBD]", "—"],
           ["Mean screening and documentation time per patient", "[TBD]", "[TBD]", "[TBD]"],
           ["Standard deviation", "[TBD]", "[TBD]", "—"],
           ["Statistical test (e.g., paired t-test) and p-value", "—", "—", "[TBD]"]],
          [2.6, 1.3, 1.3, 1.2])
    table(doc, "Screening Consistency against the Dentist's Findings", "consist",
          ["Measure", "Manual process", "With Toothwise"],
          [["Agreement with the dentist's findings (%)", "[TBD]", "[TBD]"],
           ["Cohen's kappa against the dentist's findings", "[TBD]", "[TBD]"],
           ["Findings missed (false negatives)", "[TBD]", "[TBD]"]],
          [3.0, 1.6, 1.6])
    p(doc, "[TBD – interpretation of the time and consistency results.]")


# ── Chapter V ───────────────────────────────────────────────────────────────
def chapter_5(doc):
    doc.add_page_break()
    h(doc, "CHAPTER V", 1)
    h(doc, "SUMMARY OF FINDINGS, CONCLUSIONS, AND RECOMMENDATIONS", 1)
    p(doc, "This chapter summarizes the findings of the study, states the conclusions drawn from them, and "
           "presents recommendations for CodiSmile Dental Clinic, for the further development of Toothwise, "
           "and for future researchers.")

    h(doc, "5.1 Summary of Findings", 2)
    p(doc, "The findings are summarized according to the five problems stated in Chapter I.")
    restart_numbering()
    order, a8, a12 = class_rank()
    best_c, worst_c = CLASS_NAMES[order[0]].lower(), CLASS_NAMES[order[-1]].lower()
    numbered(doc, f"Detection of the five classes (Problem 1). Two detection models were trained on 40,271 "
                  f"images merged from four public datasets and evaluated on a held-out test split of 2,930 "
                  f"images. On the test split, YOLOv8 obtained a precision of {pct(OFF8['precision'])}, a recall "
                  f"of {pct(OFF8['recall'])}, an mAP@50 of {pct(OFF8['map50'])}, and an mAP@50-95 of "
                  f"{pct(OFF8['map50_95'])}; YOLOv12 obtained {pct(OFF12['precision'])}, {pct(OFF12['recall'])}, "
                  f"{pct(OFF12['map50'])}, and {pct(OFF12['map50_95'])}, respectively, with 24% fewer parameters. "
                  f"The detection accuracy at the deployed threshold was {pct(ACC['YOLOv8']['accuracy'])} for "
                  f"YOLOv8, {pct(ACC['YOLOv12']['accuracy'])} for YOLOv12, and "
                  f"{pct(ACC['Ensemble']['accuracy'])} for the fused ensemble, whose mAP@50 was "
                  f"{pct(SH['Ensemble']['map50'])}. Across classes, {best_c} was detected best and {worst_c} "
                  f"worst. On CPU, the models analyzed an image in {CPU_BENCH['YOLOv8'][0]:.0f} ms and "
                  f"{CPU_BENCH['YOLOv12'][0]:.0f} ms, and both together in about {CPU_BENCH['both'][0]:.0f} ms.")
    numbered(doc, "Recording and access to findings (Problem 2). Every screening is stored as a standardized "
                  "visual record with the photograph, labeled bounding boxes, risk result, prevention plan, and "
                  "dentist's notes, viewable across visits by staff, exportable as a PDF, and viewable by the "
                  "patient through the self-service portal.")
    numbered(doc, f"Finding-specific preventive guidance (Problem 3). The rule-based risk engine and the KNN "
                  f"classifier (K = 5) produce a risk tier and a prevention plan for every screening. On 2,000 "
                  f"unseen synthetic cases the classifier reproduced the clinical rule with "
                  f"{pct(KNN['accuracy'])} accuracy; its weakest tier was HIGH (recall "
                  f"{pct(KNN['per_tier'][2][2])}).")
    numbered(doc, "Acceptability based on ISO/IEC 25010 (Problem 4). [TBD – overall weighted mean, "
                  "interpretation, and highest- and lowest-rated characteristics from the survey of 100 "
                  "respondents.] Technically, the web application scored 100 in Lighthouse accessibility and "
                  "best practices on all audited pages, had zero WCAG A/AA violations on the staff pages, and "
                  "passed all 84 automated backend tests.")
    numbered(doc, "Screening consistency and time (Problem 5). [TBD – mean screening time and agreement with "
                  "the dentist's findings, manual process versus Toothwise.]")

    h(doc, "5.2 Conclusions", 2)
    p(doc, "Based on the findings, the following conclusions are drawn.")
    restart_numbering()
    top = max(OFF8["map50"], OFF12["map50"])
    best, gain = ens_vs_best()
    numbered(doc, f"YOLO-based detection on ordinary intraoral photographs can locate and label tartar, plaque, "
                  f"cavity, gum inflammation, and healthy tooth, but with an mAP@50 of {pct(top)} at best on "
                  f"unseen images, and with large differences between classes ({best_c} reliable, {worst_c} "
                  f"weak), it is suitable as a screening aid that directs the dentist's attention, not as an "
                  f"independent diagnosis. This confirms the delimitation set in Chapter I.")
    numbered(doc, "The difference between YOLOv8 and YOLOv12 on this dataset is small compared with the "
                  "differences between classes, so the quality, balance, and consistency of the training data "
                  "matter more than the choice of architecture. "
                  + ("Combining both models improved detection over either model alone, which supports the "
                     "ensemble design." if gain > 0.005 else
                     "Combining both models performed on par with the better single model; the ensemble is "
                     "mainly useful for marking findings on which both models agree." if gain >= -0.005 else
                     "At its current settings, combining both models did not improve on the better single "
                     "model, so the fusion settings need tuning before the ensemble is relied upon."))
    numbered(doc, "Storing each screening as a standardized visual record and giving patients portal access "
                  "addresses the absence of comparable records across visits identified in the second problem.")
    numbered(doc, "Finding-specific prevention plans can be generated automatically for every screening without "
                  "adding to the dentist's workload, while the dentist's confirmation of the risk tier keeps the "
                  "guidance clinically supervised and gradually improves the KNN reference data.")
    numbered(doc, "[TBD – conclusion on acceptability, to be written after the survey: whether IT experts and "
                  "clinical users rated Toothwise as acceptable on the six ISO/IEC 25010 characteristics.]")
    numbered(doc, "[TBD – conclusion on screening consistency and screening time, to be written after the "
                  "comparison with the manual process.]")

    h(doc, "5.3 Recommendations", 2)
    p(doc, "In light of the findings and conclusions, the following are recommended.")
    p(doc, "For CodiSmile Dental Clinic", bold=True)
    bullet(doc, "Use Toothwise as a screening aid during intake and follow-up visits, with the dentist reviewing "
                "and confirming every finding and risk tier before it is shared with the patient.")
    bullet(doc, "Standardize image capture (camera, lighting, distance, and angle) so that clinic photographs "
                "resemble the training images as closely as possible.")
    bullet(doc, "Confirm or correct the risk tier on every screening so that the KNN feature learns from real "
                "clinic cases.")
    bullet(doc, "Encourage patients to register for the patient portal so they can follow their prevention plans "
                "between visits.")
    p(doc, "For the improvement of the detection models", bold=True)
    bullet(doc, "Collect and annotate photographs from CodiSmile Dental Clinic, with labels reviewed by the "
                "clinic's dentist, and fine-tune both models on them; this is expected to give the largest "
                "accuracy gain because the current models learned only from public datasets.")
    bullet(doc, "Review and harmonize annotations across the merged sources, in particular the healthy tooth and "
                "gum inflammation classes, which each come from a single source.")
    bullet(doc, "Balance the classes through targeted data collection or augmentation, guided by the per-class "
                f"results in Table {R('perclass_v8')}.")
    bullet(doc, "Evaluate both models and the fused ensemble on the held-out test split, and tune the confidence "
                "and IoU thresholds of the ensemble on the validation split.")
    bullet(doc, "Experiment with larger model variants, higher input resolution for small findings, and longer "
                "training only after the data improvements above, since validation accuracy had levelled off "
                "after about 25 epochs.")
    p(doc, "For the further development of the system", bold=True)
    bullet(doc, "Evaluate the KNN feature against dentist-confirmed tiers once enough real cases are recorded, "
                "and retrain it periodically on those cases.")
    bullet(doc, "Improve mobile loading of the public landing page (currently a Lighthouse performance score "
                "of 83 on mobile) by loading the hero image earlier.")
    bullet(doc, "Add appointment reminders and follow-up notifications in the patient portal, and consider "
                "integration with the clinic's appointment and billing processes, which were outside the scope "
                "of this study.")
    p(doc, "For future researchers", bold=True)
    bullet(doc, "Test the system in other clinics and with other camera devices to measure how well the results "
                "generalize.")
    bullet(doc, "Extend the classes to other conditions visible in photographs, such as discoloration or fractured "
                "teeth, with adequately annotated data.")
    bullet(doc, "Study long-term outcomes, such as whether patients who receive finding-specific prevention plans "
                "show fewer new cavities over time, which this study did not measure.")


def build():
    TABLE_NO[0], FIGURE_NO[0] = 11, 18
    restart_numbering()
    doc = Document()
    configure(doc)
    if not PAPER:  # the paper's letterhead pages carry their own page numbers
        add_page_numbers(doc)
    chapter_4(doc)
    if not PAPER:
        chapter_5(doc)
    return doc


def main():
    build()          # first pass: records where every table and figure lands
    doc = build()    # second pass: the text now cites the right numbers
    doc.save(OUT)
    print(f"Wrote {OUT.name}: tables 12-{TABLE_NO[0]}, figures 19-{FIGURE_NO[0]}")


if __name__ == "__main__":
    main()
