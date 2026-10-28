"""Write Sections 4.3-4.4 and Chapter V of content.txt from the survey responses.

    python paper_build/survey_sections.py RESPONSES.xlsx

Reads the Google Forms export (one row per respondent), computes the weighted
mean and standard deviation of every statement on the 4-point scale, and
replaces everything in content.txt from "## 4.3" up to "#CH REFERENCES"
with the result tables, their interpretation, and Chapter V. Respondent
names are never written to the paper. Also writes paper_build/survey_stats.json.
"""
from __future__ import annotations

import collections
import json
import re
import statistics as st
import sys
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content.txt"

ISO = ["1. Security", "2. Privacy", "3. Usability", "4. Reliability", "5. Performance Efficiency",
       "6. Data Protection"]
FEATURE = ["AI Detection and Risk Classification", "Results Interface and Patient Records",
           "KNN-Based Personalized Prevention Plan"]
MANUAL, CONSIST = "Current Manual Screening Process", "Screening Consistency and Time"
CODES = {"1. Security": "SE", "2. Privacy": "PR", "3. Usability": "US", "4. Reliability": "RE",
         "5. Performance Efficiency": "PE", "6. Data Protection": "DP",
         FEATURE[0]: "AD", FEATURE[1]: "RI", FEATURE[2]: "PP", MANUAL: "MS", CONSIST: "SC"}


def label(sec):
    return re.sub(r"^\d+\.\s*", "", sec)


def score(v):
    m = re.search(r"\((\d)\)", str(v or ""))
    return int(m.group(1)) if m else None


def verbal(m):
    return "Strongly Agree" if m >= 3.26 else "Agree" if m >= 2.51 else "Disagree" if m >= 1.76 else "Strongly Disagree"


def accept(m):
    return ("Highly Acceptable" if m >= 3.26 else "Acceptable" if m >= 2.51 else
            "Slightly Acceptable" if m >= 1.76 else "Not Acceptable")


def f2(x):
    return f"{x:.2f}"


def load(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    head, data = rows[0], [tuple(r) + (None,) * (len(rows[0]) - len(r)) for r in rows[1:] if any(r)]
    items = []
    for i, h in enumerate(head):
        m = re.match(r"(.+?) \[(\d+)\.\s*(.+)\]$", str(h or ""))
        if m:
            items.append({"col": i, "section": m.group(1), "no": int(m.group(2)), "stmt": m.group(3)})
    return head, data, items


def stats(rows, col):
    xs = [s for s in (score(r[col]) for r in rows) if s is not None]
    if not xs:
        return None
    return {"n": len(xs), "wm": st.mean(xs), "sd": st.pstdev(xs), "xs": xs}


def section_stats(rows, items):
    xs = [s for it in items for s in (score(r[it["col"]]) for r in rows) if s is not None]
    means = [stats(rows, it["col"])["wm"] for it in items if stats(rows, it["col"])]
    resp = {i for it in items for i, r in enumerate(rows) if score(r[it["col"]]) is not None}
    return {"wm": st.mean(means), "sd": st.pstdev(xs), "n": len(resp)} if means else None


def main(path):
    head, data, items = load(path)
    role = head.index("Patient") if "Patient" in head else 3
    IT = [r for r in data if str(r[role]).startswith("IT")]
    PT = [r for r in data if str(r[role]) == "Patient"]
    by_sec = collections.OrderedDict()
    for it in items:
        by_sec.setdefault(it["section"], []).append(it)
    for it in items:
        it["code"] = f"{CODES[it['section']]}{it['no']}"
        it["all"] = stats(data, it["col"])
    S = {s: {"all": section_stats(data, its), "it": section_stats(IT, its), "pt": section_stats(PT, its)}
         for s, its in by_sec.items()}
    n_iso = S[ISO[0]]["all"]["n"]
    n_feat = S[FEATURE[0]]["all"]["n"]
    n_man = S[MANUAL]["all"]["n"]
    it_iso = S[ISO[0]]["it"]["n"] if S[ISO[0]]["it"] else 0
    pt_iso = S[ISO[0]]["pt"]["n"] if S[ISO[0]]["pt"] else 0
    exp = collections.Counter(r[4] for r in data if r[4])
    N, nIT, nPT = len(data), len(IT), len(PT)
    iso_mean = st.mean(S[s]["all"]["wm"] for s in ISO)
    feat_mean = st.mean(S[s]["all"]["wm"] for s in FEATURE)
    allx = [s for it in items if it["section"] in ISO for s in it["all"]["xs"]]
    featx = [s for it in items if it["section"] in FEATURE for s in it["all"]["xs"]]
    iso_sd, feat_sd = st.pstdev(allx), st.pstdev(featx)
    neg_feat = sum(1 for x in featx if x <= 2)
    neg_iso = sum(1 for x in allx if x <= 2)
    iso_rank = sorted(ISO, key=lambda s: -S[s]["all"]["wm"])
    feat_items = [it for it in items if it["section"] in FEATURE]
    iso_items = [it for it in items if it["section"] in ISO]
    hi_f = max(feat_items, key=lambda i: i["all"]["wm"])
    lo_f = min(feat_items, key=lambda i: i["all"]["wm"])
    lo_i = min(iso_items, key=lambda i: i["all"]["wm"])
    hi_i = max(iso_items, key=lambda i: i["all"]["wm"])
    first = min(str(r[0])[:10] for r in data)
    last = max(str(r[0])[:10] for r in data)

    L = []
    w = L.append

    def item_table(sec, key, title, n_note):
        its = by_sec[sec]
        w(f"TABLE {key} | {title}")
        w("W 0.55,3.25,0.6,0.6,1.3")
        w("| Code | Statement | WM | SD | Verbal interpretation |")
        for it in its:
            a = it["all"]
            w(f"| {it['code']} | {it['stmt']} | {f2(a['wm'])} | {f2(a['sd'])} | {verbal(a['wm'])} |")
        a = S[sec]["all"]
        w(f"|  | {label(sec)} — mean | {f2(a['wm'])} | {f2(a['sd'])} | {verbal(a['wm'])} |")
        w("ENDTABLE")
        w(f"NOTE {n_note}")

    def hilo(sec):
        its = sorted(by_sec[sec], key=lambda i: -i["all"]["wm"])
        return its[0], its[-1]

    # ---------------------------------------------------------------- 4.3
    w("## 4.3 Software Quality Evaluation Based on ISO/IEC 25010")
    w(f"P This section answers the fourth problem of the study. The evaluation questionnaire was answered online "
      f"through Google Forms between {first} and {last} by {N} respondents who gave their informed consent. "
      f"None of the respondents was a patient of CodiSmile Dental Clinic, and no clinic records were used.")
    w("### 4.3.1 Respondents")
    w(f"P The respondents fall into two groups: {nPT} patient respondents, who evaluated the system from a "
      f"patient's point of view after using it, and {nIT} IT experts (IT practitioners). Table {{tab:resp}} "
      f"presents their distribution. The questionnaire's parts were written for different respondent groups, "
      f"so the number of respondents differs per section, as shown in Table {{tab:sectn}}.")
    w("TABLE resp | Distribution of Respondents")
    w("W 2.8,1.4,1.4")
    w("| Respondent group | Frequency | Percentage |")
    w(f"| Patient respondents | {nPT} | {nPT / N:.2%} |")
    w(f"| IT experts / IT practitioners | {nIT} | {nIT / N:.2%} |")
    w(f"| Total | {N} | 100.00% |")
    w("ENDTABLE")
    w("TABLE sectn | Respondents per Questionnaire Section")
    w("W 3.2,0.9,0.95,0.95")
    w("| Questionnaire section | Patient respondents | IT experts | Total |")
    for sec in [MANUAL, CONSIST] + ISO + FEATURE:
        p = S[sec]["pt"]["n"] if S[sec]["pt"] else 0
        i = S[sec]["it"]["n"] if S[sec]["it"] else 0
        w(f"| {label(sec)} | {p} | {i} | {p + i} |")
    w("ENDTABLE")
    w(f"P All {N} respondents answered the three sections on the system's features (AI detection and risk "
      f"classification, the results interface and patient records, and the prevention plan). The six ISO/IEC "
      f"25010 quality sections (Part B3 of the instrument) were written for dentists, clinic staff, and IT "
      f"experts, as the instructions of that part state, because many of their statements concern staff-side "
      f"and technical features that a patient using the portal does not see, such as role-based access, the "
      f"staff audit log, and data consistency between related records. All {it_iso} IT experts answered them; "
      f"since no dentist or clinic staff member took part, the only other answers came from {pt_iso} patient "
      f"respondents who completed the part although it was not meant for them, for a total of {n_iso}. The "
      f"two sections on the manual screening process and on screening consistency and time "
      f"by {n_man}. Of the respondents who gave their experience in their current field, "
      + ", ".join(f"{v} reported {k.lower()}" for k, v in exp.most_common()) + ".")
    w("### 4.3.2 Research Instrument")
    w(f"P The instrument has eleven sections with {len(items)} statements, listed in Table {{tab:chars}}, plus "
      f"three open-ended questions on what respondents liked, the difficulties they met, and the improvements "
      f"they suggest. Six sections follow the quality characteristics named in the fourth problem of the study, "
      f"three evaluate the system's main features, and two concern the current manual screening process and "
      f"Toothwise's effect on screening consistency and time (the fifth problem).")
    w("TABLE chars | Sections of the Evaluation Instrument")
    w("W 2.6,0.9,0.6,1.9")
    w("| Section | Item codes | Items | Problem addressed |")
    for sec in ISO:
        k = len(by_sec[sec])
        w(f"| {label(sec)} | {CODES[sec]}1–{CODES[sec]}{k} | {k} | Problem 4 (quality characteristic) |")
    for sec, prob in zip(FEATURE, ("Problems 1 and 4", "Problems 2 and 4", "Problems 3 and 4")):
        k = len(by_sec[sec])
        w(f"| {sec} | {CODES[sec]}1–{CODES[sec]}{k} | {k} | {prob} |")
    for sec, prob in ((MANUAL, "Problem 1 (current process)"), (CONSIST, "Problem 5")):
        k = len(by_sec[sec])
        w(f"| {sec} | {CODES[sec]}1–{CODES[sec]}{k} | {k} | {prob} |")
    w(f"| Total |  | {len(items)} |  |")
    w("ENDTABLE")
    w("### 4.3.3 Rating Scale and Interpretation")
    w(f"P Each statement is rated on a four-point Likert scale with no neutral option, so every respondent "
      f"states either agreement or disagreement. The weighted mean of each statement and section is interpreted "
      f"using the ranges in Table {{tab:likert}}, which divide the 1-to-4 range into four equal intervals of 0.75.")
    w("TABLE likert | Four-Point Likert Scale and Verbal Interpretation")
    w("W 0.8,1.4,1.9,1.9")
    w("| Scale | Mean range | Verbal interpretation | Acceptability |")
    w("| 4 | 3.26 – 4.00 | Strongly Agree | Highly Acceptable |")
    w("| 3 | 2.51 – 3.25 | Agree | Acceptable |")
    w("| 2 | 1.76 – 2.50 | Disagree | Slightly Acceptable |")
    w("| 1 | 1.00 – 1.75 | Strongly Disagree | Not Acceptable |")
    w("ENDTABLE")
    w("### 4.3.4 Statistical Treatment")
    w("P The weighted mean of each statement is computed as WM = Σ(f × x) / N, where f is the number of "
      "respondents who chose a rating, x is the rating (1 to 4), and N is the number of respondents who answered "
      "the statement. The mean of a section is the average of its statement means, and the overall mean is the "
      "average of the section means. The standard deviation (SD) of the ratings shows how closely the "
      "respondents agreed with one another: the smaller the SD, the more uniform the ratings.")
    w("### 4.3.5 Evaluation Results per Quality Characteristic")
    w(f"P Tables {{tab:se}} to {{tab:dp}} present the results for the six quality characteristics, answered by "
      f"{n_iso} respondents.")
    note_iso = f"N = {n_iso} ({it_iso} IT experts, {pt_iso} patient respondents). WM = weighted mean; SD = standard deviation."
    keys = {"1. Security": "se", "2. Privacy": "pr", "3. Usability": "us", "4. Reliability": "re",
            "5. Performance Efficiency": "pe", "6. Data Protection": "dp"}
    for sec in ISO:
        item_table(sec, keys[sec], f"Evaluation Results for {label(sec)}", note_iso)
        hi, lo = hilo(sec)
        a = S[sec]
        txt = (f"P {label(sec)} obtained a mean of {f2(a['all']['wm'])} (SD {f2(a['all']['sd'])}), interpreted as "
               f"{verbal(a['all']['wm'])}. ")
        if abs(hi["all"]["wm"] - lo["all"]["wm"]) < 0.005:
            txt += "All statements in this section were rated equally. "
        else:
            txt += (f"The highest-rated statement was {hi['code']}, “{hi['stmt'].rstrip('.')}” "
                    f"({f2(hi['all']['wm'])}), and the lowest was {lo['code']}, “{lo['stmt'].rstrip('.')}” "
                    f"({f2(lo['all']['wm'])}), which was still rated Strongly Agree. ")
        if a["it"] and a["pt"]:
            txt += (f"The IT experts were more critical than the patient respondents "
                    f"({f2(a['it']['wm'])} against {f2(a['pt']['wm'])}). "
                    if a["it"]["wm"] < a["pt"]["wm"] - 0.05 else
                    f"The IT experts and the patient respondents gave similar ratings "
                    f"({f2(a['it']['wm'])} and {f2(a['pt']['wm'])}). ")
        neg = sum(1 for it in by_sec[sec] for x in it["all"]["xs"] if x <= 2)
        txt += ("No respondent disagreed with any statement in this section." if neg == 0 else
                f"Only {neg} of the ratings in this section were Disagree or Strongly Disagree.")
        extra = {
            "4. Reliability": " RE1 was also the statement the IT experts rated lowest. In the open-ended answers, "
                              "two respondents mentioned slow first loading and performance bugs that had to be "
                              "patched; the "
                              "free hosting tier used for the study sleeps after 15 minutes without requests "
                              "(Chapter I, Limitations).",
            "1. Security": " One respondent suggested an additional security measure for authorized personnel, "
                           "which is taken up in the recommendations.",
            "3. Usability": " In the open-ended answers, ease of use and the interface were the most often "
                            "mentioned strengths, while a few respondents found some pages long or some features "
                            "hard to find.",
        }
        w(txt + extra.get(sec, ""))
    w("### 4.3.6 Evaluation Results for the System Features")
    w(f"P Tables {{tab:ad}} to {{tab:pp}} present the results for the three sections on the system's main "
      f"features, answered by all {N} respondents.")
    note_f = f"N = {N} ({nIT} IT experts, {nPT} patient respondents). WM = weighted mean; SD = standard deviation."
    for sec, key in zip(FEATURE, ("ad", "ri", "pp")):
        item_table(sec, key, f"Evaluation Results for {sec}", note_f)
        hi, lo = hilo(sec)
        a = S[sec]
        neg = sum(1 for it in by_sec[sec] for x in it["all"]["xs"] if x <= 2)
        total = sum(len(it["all"]["xs"]) for it in by_sec[sec])
        txt = (f"P {sec} obtained a mean of {f2(a['all']['wm'])} (SD {f2(a['all']['sd'])}), interpreted as "
               f"{verbal(a['all']['wm'])}. The highest-rated statement was {hi['code']}, "
               f"“{hi['stmt'].rstrip('.')}” ({f2(hi['all']['wm'])}), and the lowest was {lo['code']}, "
               f"“{lo['stmt'].rstrip('.')}” ({f2(lo['all']['wm'])}). Only {neg} of the {total} ratings in this "
               f"section were Disagree or Strongly Disagree. ")
        extra = {
            FEATURE[0]: "Although the respondents rated detection highly, this is a perception measure taken "
                        "while using the system, not a measure of accuracy; the measured accuracy in Section "
                        "4.1 is moderate, and plaque in particular is often missed. One respondent noted that "
                        "results may be wrong when the photograph is blurry and should still be checked by a "
                        "dentist, which agrees with the design of the system.",
            FEATURE[1]: "Respondents singled out the plain-language descriptions and the clear presentation of "
                        "the results in their open-ended answers.",
            FEATURE[2]: "This was the highest-rated of the three feature sections. Respondents wrote that the "
                        "tips were clear and helped them remember to care for their teeth, and several asked "
                        "for more dental health tips, check-up reminders, and short videos.",
        }
        w(txt + extra[sec])
    w("### 4.3.7 Summary of the Evaluation")
    w("TABLE iso | Summary of Evaluation Results")
    w("W 2.3,0.85,0.95,0.75,0.55,1.1")
    w("| Section | IT experts (WM) | Patient respondents (WM) | Overall WM | SD | Interpretation |")
    for sec in ISO + FEATURE:
        a = S[sec]
        it = f2(a["it"]["wm"]) if a["it"] else "—"
        pt = f2(a["pt"]["wm"]) if a["pt"] else "—"
        w(f"| {label(sec)} | {it} | {pt} | {f2(a['all']['wm'])} | {f2(a['all']['sd'])} | {accept(a['all']['wm'])} |")
    w(f"| Quality characteristics (mean of six) |  |  | {f2(iso_mean)} | {f2(iso_sd)} | {accept(iso_mean)} |")
    w(f"| System features (mean of three) |  |  | {f2(feat_mean)} | {f2(feat_sd)} | {accept(feat_mean)} |")
    w("ENDTABLE")
    w(f"NOTE Quality characteristics: N = {n_iso}; system features: N = {N}.")
    w(f"P All nine sections were rated Strongly Agree and are therefore interpreted as Highly Acceptable. The "
      f"six quality characteristics obtained an overall mean of {f2(iso_mean)} and the three feature sections "
      f"{f2(feat_mean)}. Among the quality characteristics, {label(iso_rank[0])} was rated highest "
      f"({f2(S[iso_rank[0]]['all']['wm'])}) and {label(iso_rank[-1])} lowest "
      f"({f2(S[iso_rank[-1]]['all']['wm'])}). The IT experts rated every section lower than the patient "
      f"respondents, but still within Strongly Agree, which is expected of evaluators who judge the system "
      f"against technical standards. Disagreement was rare: {neg_iso} of {len(allx)} quality ratings and "
      f"{neg_feat} of {len(featx)} feature ratings were Disagree or Strongly Disagree.")
    w(f"P Two cautions apply. First, the six quality sections were answered by only {n_iso} of the {N} "
      f"respondents, and only {nIT} of the respondents were IT experts, so the quality ratings rest on a small "
      f"group. This follows from the design of the instrument, which directed the quality evaluation to dentists, "
      f"clinic staff, and IT experts, and from the absence of dentists and clinic staff among the respondents. "
      f"Second, the ratings express how the "
      f"respondents perceived the system, and are read together with the measured results in Sections 4.1 and "
      f"4.2. In the open-ended answers, the respondents most often praised the system's ease of use, clear "
      f"interface, and understandable explanations; the difficulties they reported were slow first loading, "
      f"pages with much information at once, some features being hard to find, and inaccurate results from "
      f"blurry photographs; and their suggestions were reminders for brushing and check-ups, more dental tips "
      f"and short videos, a faster and easier search, more detectable conditions with better accuracy, and an "
      f"additional security measure for authorized personnel.")

    # ---------------------------------------------------------------- 4.4
    w("## 4.4 Screening Consistency and Screening Time")
    w(f"P This section answers the fifth problem of the study. The planned controlled comparison, in which the "
      f"same patients would be screened and timed with and without Toothwise against the dentist's findings, "
      f"could not be carried out because the study did not involve the clinic's patients. The fifth problem is "
      f"therefore answered through the respondents' assessment of the current manual process and of "
      f"Toothwise's effect on screening consistency and time (Tables {{tab:ms}} and {{tab:sc}}), together with "
      f"the measured processing time in Section 4.1.6.")
    note_m = (f"N = {n_man}. These two sections were optional and were answered by only {n_man} respondents, so "
              f"the results are reported for completeness and are not generalized.")
    item_table(MANUAL, "ms", "Respondents' Assessment of the Current Manual Screening Process", note_m)
    item_table(CONSIST, "sc", "Respondents' Assessment of Screening Consistency and Time with Toothwise", note_m)
    m, c = S[MANUAL]["all"], S[CONSIST]["all"]
    ms_lo = min(by_sec[MANUAL], key=lambda i: i["all"]["wm"])
    w(f"P The {n_man} respondents agreed that the current visual-only process has the limitations identified "
      f"in the first problem (mean {f2(m['wm'])}): findings can differ between examinations, lighting and angle "
      f"affect what can be seen, and a tool that supports consistent early screening would be useful. The only "
      f"statement rated Disagree was {ms_lo['code']}, “{ms_lo['stmt'].rstrip('.')}” ({f2(ms_lo['all']['wm'])}). "
      f"They also agreed that Toothwise makes results more consistent, reduces the time needed to complete and "
      f"document a screening, and agrees with the dentist's own findings (mean {f2(c['wm'])}), and they would "
      f"recommend its continued use. Because only {n_man} respondents answered these sections and no screening "
      f"was timed, these results indicate a direction rather than a measured effect. The measured part of the "
      f"answer is the processing time: the deployed system completes a screening, with both models, in about 3 "
      f"to 4 seconds (Section 4.1.6), and it records every finding, the risk result, and the prevention plan "
      f"automatically, so the documentation of a screening no longer has to be written by hand.")

    # ---------------------------------------------------------------- Chapter V
    ad, ri, pp = (S[s]["all"]["wm"] for s in FEATURE)
    w("#CH CHAPTER V | SUMMARY OF FINDINGS, CONCLUSIONS, AND RECOMMENDATIONS")
    w("P This chapter summarizes the findings of the study, states the conclusions drawn from them, and presents "
      "recommendations for CodiSmile Dental Clinic, for the further development of Toothwise, and for future "
      "researchers.")
    w("## 5.1 Summary of Findings")
    w("P The findings are summarized according to the five problems stated in Chapter I.")
    w("1. **Detection of the five conditions (Problem 1).** YOLOv8 and YOLOv12 were trained on 40,271 images "
      "merged from four public datasets and tested on 2,930 unseen images. On the test split, YOLOv8 obtained a "
      "precision of 54.32%, a recall of 52.34%, and an mAP@50 of 51.91%; YOLOv12 obtained 52.94%, 50.06%, and "
      "48.11%, with about 24% fewer parameters and slightly faster inference (about 206 ms against 216 ms per "
      "image on CPU). Fusing the two models raised the mAP@50 to 54.24%. Healthy tooth and cavity were detected "
      "best, and plaque worst (mAP@50 below 10%). Detection accuracy at the deployed threshold was 43.77% for "
      f"YOLOv8, 41.85% for YOLOv12, and 43.02% for the ensemble. In the deployed system, a screening takes about "
      f"3 to 4 seconds, and metal brackets are filtered out so that they are not reported as cavities. The "
      f"respondents who evaluated the current manual process agreed that it has the limitations described in "
      f"the first problem (mean {f2(m['wm'])}).")
    w(f"2. **Recording and access to findings (Problem 2).** Every screening is saved as a standardized visual "
      f"record with the photograph, labeled bounding boxes, the risk result, the prevention plan, and the "
      f"dentist's notes; it can be compared across visits, exported as a PDF report, and viewed by the patient "
      f"through the self-service portal, which now also shows the latest results, a risk-over-time chart, and "
      f"the next check-up date. Respondents rated the results interface and patient records {f2(ri)}, Strongly "
      f"Agree.")
    w(f"3. **Finding-specific preventive guidance (Problem 3).** The rule-based risk engine and the KNN "
      f"classifier (K = 5) produce a risk tier and an ordered prevention plan for every screening. On 2,000 "
      f"unseen synthetic cases, the classifier reproduced the clinical rule with 92.75% accuracy; its weakest "
      f"tier was HIGH (recall 58.18%). Respondents rated the prevention plan {f2(pp)}, Strongly Agree, the "
      f"highest of the three feature sections.")
    w(f"4. **Acceptability (Problem 4).** On the six quality characteristics, answered by {n_iso} respondents, "
      f"the overall mean was {f2(iso_mean)} (Highly Acceptable), with {label(iso_rank[0])} highest "
      f"({f2(S[iso_rank[0]]['all']['wm'])}) and {label(iso_rank[-1])} lowest "
      f"({f2(S[iso_rank[-1]]['all']['wm'])}). The three feature sections, answered by all {N} respondents, "
      f"obtained an overall mean of {f2(feat_mean)} (Highly Acceptable). IT experts rated every section lower "
      f"than patient respondents, but still Strongly Agree. Technically, the web application scored 100 in "
      f"Lighthouse accessibility and best practices on all audited pages and passed all 117 automated backend "
      f"tests.")
    w(f"5. **Screening consistency and time (Problem 5).** A controlled, timed comparison against the dentist's "
      f"findings was not conducted. The {n_man} respondents who answered the related section agreed that "
      f"Toothwise makes screening more consistent and faster to document (mean {f2(c['wm'])}), and the "
      f"measured processing time of the deployed system is about 3 to 4 seconds per screening.")
    w("## 5.2 Conclusions")
    w("P Based on the findings, the following conclusions are drawn.")
    w("1. YOLO-based detection on ordinary intraoral photographs can locate and label tartar, plaque, cavity, gum "
      "inflammation, and healthy tooth, but with an mAP@50 of about 52% to 54% on unseen images and large "
      "differences between conditions, it is suitable as a screening aid that directs the dentist's attention, "
      "not as an independent diagnosis. This confirms the delimitation set in Chapter I.")
    w("2. The difference between YOLOv8 and YOLOv12 is small compared with the differences between conditions, "
      "so the quality, balance, and consistency of the training data matter more than the choice of "
      "architecture. Combining both models improved detection over either model alone, which supports the "
      "ensemble design.")
    w("3. Storing each screening as a standardized visual record, with patient portal access, addresses the "
      "absence of comparable records across visits identified in the second problem.")
    w("4. Finding-specific prevention plans can be generated automatically for every screening without adding to "
      "the dentist's work, and the respondents found them relevant and easy to follow.")
    w(f"5. Toothwise is highly acceptable to its evaluators on all six quality characteristics and on its main "
      f"features (overall means of {f2(iso_mean)} and {f2(feat_mean)} on a four-point scale). Because the "
      f"quality characteristics were intended for dentists, clinic staff, and IT experts and were rated by "
      f"{n_iso} respondents, of whom {it_iso} were IT experts, this conclusion should be confirmed with a larger "
      f"group of IT experts, dentists, and clinic staff.")
    w("6. Toothwise shortens the documentation of a screening, since results, risk, and the prevention plan are "
      "produced and recorded in seconds, and the respondents expect it to make screening more consistent. "
      "Whether it improves agreement with the dentist and shortens the whole screening in practice could not be "
      "established without a controlled comparison.")
    w("## 5.3 Recommendations")
    w("P In light of the findings and conclusions, the following are recommended.")
    w("PN **For CodiSmile Dental Clinic**")
    w("1. Use Toothwise as a screening and documentation aid, always with the dentist's review of the "
      "detections and confirmation of the risk tier, and take clear, well-lit photographs, since blurry images "
      "reduce accuracy.")
    w("2. Confirm or correct the risk tier of every screening so that the KNN classifier is retrained on real, "
      "dentist-labeled cases.")
    w("3. Move the system from the free hosting tier to a plan that does not sleep, so that the first page "
      "load is not delayed, before using it in daily operations.")
    w("PN **For the further development of Toothwise**")
    w("1. Improve detection of plaque and other weak classes by adding more and better-annotated photographs, "
      "including consented photographs from the clinic, and add a braces class instead of filtering brackets.")
    w("2. Add the features requested by respondents: reminders for brushing and check-ups, more dental health "
      "tips and short videos, a faster and simpler search, and lighter pages for slow Internet connections.")
    w("3. Add a second authentication factor for staff accounts, as one respondent suggested, and keep the "
      "audit and privacy controls aligned with the Data Privacy Act of 2012.")
    w("4. Simplify pages that present much information at once and make less-used features easier to find.")
    w("PN **For future researchers**")
    w("1. Conduct the controlled comparison planned for the fifth problem: time the same screenings with and "
      "without Toothwise and measure agreement with the dentist's findings (for example, with Cohen's kappa).")
    w("2. Repeat the ISO/IEC 25010 evaluation with a larger and more balanced group of IT experts, dentists, and "
      "clinic staff, the groups for which the quality evaluation was designed.")
    w("3. Validate the models on photographs from other clinics and devices, and compare them with newer "
      "detection architectures and with segmentation-based approaches.")

    text = CONTENT.read_text(encoding="utf-8")
    a = text.index("## 4.3 Software Quality Evaluation")
    b = text.index("#CH REFERENCES")
    text = text[:a] + "\n".join(L) + "\n\n" + text[b:]
    CONTENT.write_text(text, encoding="utf-8")
    out = {"N": N, "it": nIT, "patients": nPT, "n_iso": n_iso, "n_features": n_feat, "n_manual": n_man,
           "iso_mean": round(iso_mean, 2), "feature_mean": round(feat_mean, 2),
           "sections": {s: {k: (None if v is None else {kk: round(vv, 2) for kk, vv in v.items()})
                            for k, v in d.items()} for s, d in S.items()},
           "items": [{"code": it["code"], "stmt": it["stmt"], "n": it["all"]["n"], "wm": round(it["all"]["wm"], 2),
                      "sd": round(it["all"]["sd"], 2)} for it in items]}
    (HERE / "survey_stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"N={N} (IT {nIT}, patients {nPT}); quality mean {iso_mean:.2f} (n={n_iso}); features {feat_mean:.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
