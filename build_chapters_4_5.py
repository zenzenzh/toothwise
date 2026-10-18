from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.section import WD_SECTION

OUT = 'ToothWise_Chapters_4_and_5_Revised.docx'

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.85)
sec.bottom_margin = Inches(0.8)
sec.left_margin = Inches(0.9)
sec.right_margin = Inches(0.9)

styles = doc.styles
styles['Normal'].font.name = 'Times New Roman'
styles['Normal']._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman')
styles['Normal']._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman')
styles['Normal'].font.size = Pt(11)
styles['Normal'].paragraph_format.line_spacing = 1.5
styles['Normal'].paragraph_format.space_after = Pt(6)
for name, size in [('Title', 15), ('Heading 1', 13), ('Heading 2', 11.5)]:
    st = styles[name]
    st.font.name = 'Times New Roman'
    st._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman')
    st._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0, 0, 0)

def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)

def borders(cell):
    tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.first_child_found_in('w:tcBorders')
    if b is None: b = OxmlElement('w:tcBorders'); tcPr.append(b)
    for edge in ('top','left','bottom','right','insideH','insideV'):
        tag = qn('w:' + edge); el = b.find(tag)
        if el is None: el = OxmlElement('w:' + edge); b.append(el)
        el.set(qn('w:val'),'single'); el.set(qn('w:sz'),'6'); el.set(qn('w:color'),'D9D9D9')

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    for i, h in enumerate(headers):
        c=t.rows[0].cells[i]; c.text=h; shade(c,'1F4E79'); borders(c)
        for r in c.paragraphs[0].runs: r.font.bold=True; r.font.color.rgb=RGBColor(255,255,255); r.font.size=Pt(9)
        c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for ri,row in enumerate(rows):
        cells=t.add_row().cells
        for i,val in enumerate(row):
            cells[i].text=str(val); borders(cells[i]); cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if ri%2==1: shade(cells[i],'F3F7FA')
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after=Pt(2); p.paragraph_format.space_before=Pt(2)
                for r in p.runs: r.font.size=Pt(9)
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(2)
    return t

def p(text='', boldlead=None):
    par=doc.add_paragraph()
    par.paragraph_format.first_line_indent=Inches(.25)
    if boldlead and text.startswith(boldlead):
        r=par.add_run(boldlead); r.bold=True
        par.add_run(text[len(boldlead):])
    else: par.add_run(text)
    return par

def heading(text, level=1):
    h=doc.add_paragraph(style=f'Heading {level}')
    h.add_run(text)
    h.paragraph_format.space_before=Pt(14 if level==1 else 10)
    h.paragraph_format.space_after=Pt(5)
    return h

def bullet(text):
    x=doc.add_paragraph(style='List Bullet'); x.add_run(text); return x

# Cover
title=doc.add_paragraph(style='Title'); title.alignment=WD_ALIGN_PARAGRAPH.CENTER
title.add_run('TOOTHWISE')
sub=doc.add_paragraph(); sub.alignment=WD_ALIGN_PARAGRAPH.CENTER
sub.add_run('A YOLO Based Multi Condition Dental Screening System with KNN Based Recommendation for CodiSmile Dental Clinic').bold=True
doc.add_paragraph().paragraph_format.space_after=Pt(12)
for line in ['CHAPTER IV AND CHAPTER V', 'Results Discussion Summary Conclusions and Recommendations', 'Capstone Project Documentation']:
    q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER; q.add_run(line)
doc.add_page_break()

heading('CHAPTER IV', 1)
heading('RESULTS AND DISCUSSION', 1)
p('This chapter presents the verified technical results of the ToothWise prototype as of the current development stage. It reports results that can be reproduced from the available source code, model files, and evaluation harnesses. The ISO/IEC 25010 user evaluation is intentionally reported as pending because the planned 100 respondents have not yet completed the survey. Accordingly, this chapter does not claim user-acceptability scores, clinical accuracy, consultation-time reduction, or patient outcomes that have not been measured.')

heading('4.1 Scope of the Reported Results', 2)
p('The system combines a dual YOLO image-screening pipeline, an auditable risk-scoring module, a K-Nearest Neighbors (KNN) recommendation component, authenticated patient and dentist workflows, and a web-based interface. The project directory contains trained YOLOv8 and YOLOv12 weight files with saved validation metrics. The retained metrics support a model-to-model comparison, but the test images, annotation files, confusion matrices, and per-class results are not available in the project directory. Therefore, the results are reported as saved validation performance rather than as an independent clinical diagnostic-accuracy study.')
table(['Evidence source', 'Verified result', 'Interpretation'], [
 ['YOLO model assets', 'yolov8_dental.pt and yolov12_dental.pt are present.', 'The system can be configured for real-model inference.'],
 ['Supported labels', '5 configured labels: healthy tooth, cavity, gum inflammation, plaque, and tartar.', 'The class order matches both trained checkpoints and the application label map.'],
 ['KNN evaluation harness', 'Synthetic holdout and clinician-confirmed case evaluation are implemented.', 'The recommendation tier can be checked separately from image detection.'],
 ['ISO/IEC 25010 instrument', 'A survey instrument and response template are prepared.', 'Acceptability results remain pending until 100 completed responses are collected.'],
], [1.35, 2.35, 2.65])

heading('4.2 Trained Image Detection Models and Dataset Readiness', 2)
p('The image-analysis component uses two object-detection checkpoints: YOLOv8 and YOLOv12. Both models are intended to process the same intraoral image. Their detections are then compared and fused by label and intersection-over-union (IoU). When matching boxes from both models overlap at or above the configured threshold, the system produces an ensemble output. This architecture allows the application to preserve the separate outputs while presenting a single fused result to the screening workflow.')
table(['Model artifact', 'File size', 'Configured role', 'Reported metric status'], [
 ['YOLOv8 dental checkpoint', '52,040,210 bytes', 'First detector in the ensemble', 'Precision 53.96%; recall 49.73%; mAP50 46.83%; mAP50-95 26.80%'],
 ['YOLOv12 dental checkpoint', '39,817,646 bytes', 'Second detector in the ensemble', 'Precision 49.43%; recall 49.05%; mAP50 45.02%; mAP50-95 25.87%'],
 ['Ensemble fusion', 'Software implementation', 'Fuses same-label overlapping boxes; configured IoU threshold is 0.50', 'Requires evaluation against labeled held-out images'],
], [1.55, 1.2, 2.45, 2.05])
p('Both checkpoints were trained for 60 epochs at an image size of 640 using the same five-class dataset configuration. YOLOv8 achieved the stronger saved validation values across all four aggregate metrics: it exceeded YOLOv12 by 4.53 percentage points in precision, 0.67 in recall, 1.81 in mAP50, and 0.93 in mAP50-95. These saved values demonstrate comparative performance on the validation split used during training. They do not establish clinical generalizability or replace professional judgment. A valid clinical-performance claim still requires an independent patient-disjoint labeled test set.')

heading('4.3 Comparison of the Saved Validation Results', 2)
p('The model checkpoints retain the aggregate validation results produced during training. Table 2 compares the two models. Precision reflects the proportion of predicted boxes that are correct, recall reflects the proportion of labeled boxes detected, mAP50 measures average precision at an IoU threshold of 0.50, and mAP50-95 evaluates detection quality across stricter IoU thresholds from 0.50 to 0.95.')
table(['Model', 'Precision', 'Recall', 'mAP50', 'mAP50-95'], [
 ['YOLOv8', '53.96%', '49.73%', '46.83%', '26.80%'],
 ['YOLOv12', '49.43%', '49.05%', '45.02%', '25.87%'],
], [1.3, 1.3, 1.25, 1.25, 1.4])
p('YOLOv8 is the stronger individual checkpoint under the retained validation results. The advantage is modest in recall, mAP50, and mAP50-95, but it is consistent across all reported aggregate measures. The retained files do not include the validation image count, class distribution, per-class average precision, or confusion matrix. A fresh independent evaluation should therefore be completed on a patient-disjoint held-out test set before making a clinical accuracy claim or selecting a permanent deployment threshold.')

heading('4.4 Risk Scoring and Recommendation Results', 2)
p('ToothWise converts detected findings into a transparent risk score. Healthy-only findings produce a low-risk score of zero. For non-healthy findings, the highest confidence-weighted severity is used as the base score. A small capped increment is added for additional findings. The final score is limited to 100 and is categorized as LOW (0 to 34), MEDIUM (35 to 69), or HIGH (70 to 100). This deterministic rule makes the reason for each tier inspectable during testing and clinical review.')
table(['Risk-tier component', 'Verified implementation behavior'], [
 ['Severity calculation', 'Uses the confidence-weighted severity of the most serious non-healthy detection.'],
 ['Multiple findings', 'Adds a capped six-point increment for each additional concerning finding.'],
 ['Risk thresholds', 'LOW: 0-34; MEDIUM: 35-69; HIGH: 70-100.'],
 ['Recommendation output', 'Prioritizes urgent advice for high risk, then condition-specific and general oral-health guidance.'],
], [2.1, 4.6])

heading('4.5 KNN Recommendation Evaluation', 2)
p('The KNN recommender was evaluated with its built-in synthetic holdout procedure. The holdout contains 2,000 deterministically generated feature vectors created with a different random seed from the training bootstrap. The measured accuracy was 0.9275 (92.75%), while the weighted F1 score was 0.9251 (92.51%). These results show that the KNN model largely reproduces the risk-tier pattern represented in the generated data.')
p('This result must be interpreted narrowly. Because the bootstrap and holdout data are generated from the same rule-based severity framework, the metric demonstrates internal consistency rather than clinical effectiveness. At the time of evaluation, the clinician-confirmed case journal contained zero real labeled cases. Therefore, no claim can be made that the recommender accurately predicts risk tiers in a real patient population.')
table(['Evaluation measure', 'Observed result', 'Appropriate interpretation'], [
 ['Synthetic holdout size', '2,000 cases', 'A reproducible software-level evaluation set'],
 ['Accuracy', '0.9275 or 92.75%', 'Agreement with the generated tier pattern'],
 ['Weighted F1 score', '0.9251 or 92.51%', 'Balanced synthetic classification performance'],
 ['Real clinician-confirmed cases', '0 cases', 'Clinical validation has not started'],
], [1.75, 1.5, 3.45])

heading('4.6 Functional Verification of the System', 2)
p('The backend test suite contains 73 collected automated tests covering authentication, role and token scoping, dentist and patient records, screening creation and retrieval, label normalization, risk scoring, KNN recommendation behaviors, and selected security conditions. The suite provides useful regression coverage for the system functions that can be tested without a live clinical study. It should be run in the deployment environment before final demonstration, with the final pass/fail summary recorded in the manuscript.')
table(['Area covered', 'Examples of verified behaviors'], [
 ['Authentication and access control', 'Login, incorrect credentials, token requirements, and separation of dentist and patient access.'],
 ['Record management', 'Create, retrieve, update, search, and delete patient and dentist records.'],
 ['Screening workflow', 'Create and retrieve screenings, store detections and recommendations, and add clinical notes.'],
 ['Decision logic', 'Risk boundaries, score cap, label aliases, recommendation ordering, and tier confirmation.'],
], [1.8, 4.9])

heading('4.7 ISO IEC 25010 Survey Status', 2)
p('The planned ISO/IEC 25010 evaluation will use 100 respondents and a five-point Likert-scale instrument. Until the questionnaires are completed and encoded, weighted means, standard deviations, verbal interpretations, and an overall acceptability rating cannot be reported. Stating a survey result before data collection would undermine the validity of the study.')
p('When the survey is completed, the analysis should report the respondent profile; the number of valid responses; the mean and standard deviation for each quality characteristic; the overall weighted mean; the interpretation scale; and selected qualitative comments. The results should distinguish software quality perceptions from clinical diagnostic effectiveness, which requires a separate validated clinical dataset.')

heading('4.8 Discussion', 2)
p('The present evidence supports the conclusion that ToothWise is an implemented, testable prototype with trained image-model artifacts, an auditable risk engine, and a KNN-supported recommendation workflow. The saved validation results show that YOLOv8 is the stronger individual model on the available aggregate measures, while YOLOv12 provides a second independent detection output for the deployed ensemble. The KNN synthetic holdout result is useful for verifying recommendation-pipeline consistency. Neither result substitutes for an independent clinical validation study.')
p('This distinction is important for responsible deployment. ToothWise should be presented as a clinical decision-support and screening system. A licensed dentist remains responsible for assessment, diagnosis, and treatment decisions. The next phase of the study should supply the missing empirical evidence: a locked, labeled detection test set; clinician-confirmed recommendation outcomes; and the 100-user quality survey.')

doc.add_page_break()
heading('CHAPTER V', 1)
heading('SUMMARY CONCLUSIONS AND RECOMMENDATIONS', 1)

heading('5.1 Summary of Findings', 2)
p('The development of ToothWise produced a web-based multi-condition dental screening prototype for CodiSmile Dental Clinic. The system integrates two trained YOLO checkpoint files, an ensemble-fusion process, a deterministic risk engine, a KNN-based recommendation component, authenticated portals, and data-management functions for patient screening records.')
p('The five configured screening labels are healthy tooth, cavity, gum inflammation, plaque, and tartar. The class order in the trained YOLOv8 and YOLOv12 checkpoints matches the application label map. The project has the technical capability to run real model inference when the trained checkpoint paths and runtime environment are configured. The saved validation results favor YOLOv8: precision 53.96%, recall 49.73%, mAP50 46.83%, and mAP50-95 26.80%, compared with YOLOv12 at 49.43%, 49.05%, 45.02%, and 25.87%, respectively. These figures are not independent clinical test results.')
p('The KNN recommendation component achieved 92.75% accuracy and 92.51% weighted F1 on a 2,000-case synthetic holdout. Since the data were generated from the same rule-based framework used in the prototype, these figures show internal consistency only. No clinician-confirmed cases were available at the time of evaluation. The backend also contains 73 collected automated tests covering important functional and access-control behaviors.')
p('The ISO/IEC 25010 evaluation instrument is prepared, but the planned 100-user survey has not yet been conducted. Consequently, this study does not report a weighted mean, acceptability rating, or stakeholder satisfaction result.')

heading('5.2 Conclusions', 2)
p('Based on the verified development evidence, ToothWise has achieved its prototype implementation objective. It provides an end-to-end workflow for storing screening information, processing multi-condition detections, assigning an understandable risk tier, and generating prevention guidance. Its rule-based scoring logic and automated tests make key software decisions inspectable and repeatable.')
p('The current evidence is not sufficient to conclude that ToothWise has a particular clinical diagnostic accuracy, improves consultation time, or is highly acceptable to users. Those conclusions require measured evidence from a held-out annotated dataset, clinician review, workflow timing, and the completed ISO/IEC 25010 survey. The system should therefore be framed as a decision-support prototype rather than an autonomous diagnostic tool.')
p('The synthetic KNN result indicates that the recommendation pipeline consistently maps generated detection features into risk tiers. Its clinical usefulness remains to be established through clinician-confirmed outcomes. The saved YOLO validation metrics support YOLOv8 as the stronger individual model, while an independent patient-disjoint test set remains necessary for a final clinical performance claim.')

heading('5.3 Recommendations', 2)
heading('5.3.1 Complete the Model Evaluation', 2)
bullet('Freeze a patient-disjoint, labeled test set and record its image count and class distribution.')
bullet('Run the trained YOLOv8, YOLOv12, and fused ensemble on that test set, then report precision, recall, mAP50, mAP50-95, per-class average precision, and a confusion matrix.')
bullet('Have a licensed dentist review a sample of false positives and false negatives to identify annotation ambiguity and clinically important failure modes.')

heading('5.3.2 Conduct the 100 User ISO IEC 25010 Survey', 2)
bullet('Collect the 100 responses before assigning any acceptability rating.')
bullet('Encode the results accurately, remove duplicate or incomplete entries according to a documented rule, and report the valid response count.')
bullet('Compute the weighted mean and standard deviation for each quality characteristic and present the interpretation scale used by the study.')

heading('5.3.3 Validate in a Controlled Clinical Workflow', 2)
bullet('Use ToothWise alongside, not in place of, professional dental assessment during a supervised pilot.')
bullet('Record real clinician-confirmed risk tiers so the KNN evaluator can measure performance on non-synthetic cases.')
bullet('Measure workflow time prospectively using defined start and end points if time-efficiency is a research objective.')

heading('5.3.4 Improve Dataset Governance and Generalizability', 2)
bullet('Document data provenance, consent, de-identification, image quality criteria, annotation protocol, and annotator agreement.')
bullet('Expand the dataset across varied lighting, cameras, age groups, dental conditions, and clinic settings while monitoring class imbalance.')
bullet('Retain training logs, data configuration files, metrics, and confusion matrices with the final model weights for reproducibility.')

heading('5.3.5 Maintain Safety and Privacy Controls', 2)
bullet('Keep the dentist in the clinical decision loop and display that screening outputs are decision support, not final diagnoses.')
bullet('Use strong credentials, role-based authorization, audit logs, encrypted deployment configuration, and controlled access to patient images.')
bullet('Perform regression testing after model, dependency, or workflow changes before deployment.')

heading('5.4 Proposed Next Steps for the Manuscript', 2)
p('After the survey and model evaluation are completed, Chapter IV should be updated by replacing the pending-result fields with measured values and adding the final survey tables, model-metric tables, and interpretations. Chapter V should then be revised so its conclusions correspond only to the completed evidence. This sequence will keep the manuscript defensible during oral presentation and avoid overstating the capabilities of the prototype.')

# Footer page number field
for section in doc.sections:
    footer = section.footer
    par = footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run=par.add_run('ToothWise Chapters IV and V | Page ')
    fldChar1=OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'),'begin')
    instrText=OxmlElement('w:instrText'); instrText.set(qn('xml:space'),'preserve'); instrText.text=' PAGE '
    fldChar2=OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'),'end')
    run._r.append(fldChar1); run._r.append(instrText); run._r.append(fldChar2)

doc.core_properties.title = 'ToothWise Chapters IV and V'
doc.core_properties.subject = 'Results discussion summary conclusions and recommendations'
doc.core_properties.author = 'ToothWise Capstone Project'
doc.save(OUT)
print(OUT)
