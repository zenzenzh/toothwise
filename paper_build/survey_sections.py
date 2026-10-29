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
    import datetime as _dt
    _d = sorted(_dt.date.fromisoformat(str(r[0])[:10]) for r in data)
    first = f"{_d[0]:%B} {_d[0].day}"
    last = (f"{_d[-1].day}, {_d[-1].year}" if _d[0].month == _d[-1].month else f"{_d[-1]:%B} {_d[-1].day}, {_d[-1].year}")

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
    w(f"P This section answers the fourth problem: how acceptable is Toothwise to the people who used it? "
      f"{N} respondents answered the online questionnaire (Google Forms) from {first} to {last}, after agreeing "
      f"to take part. None of them was a patient of CodiSmile Dental Clinic, and no clinic records were used.")
    w("### 4.3.1 Respondents")
    w(f"P The respondents were in two groups (Table {{tab:resp}}): {nPT} patient respondents, who tried the "
      f"system from a patient's point of view, and {nIT} IT experts. Different parts of the questionnaire were "
      f"meant for different groups, so not every section was answered by the same number of people (Table "
      f"{{tab:sectn}}).")
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
    w(f"P All {N} respondents rated the system's three main features: AI detection and risk classification, "
      f"the results and patient records, and the prevention plan. The six ISO/IEC 25010 quality sections (Part "
      f"B3) were meant only for dentists, clinic staff, and IT experts, as the form's instructions say, because "
      f"they ask about staff-side features that patients never see, such as user roles, the staff audit log, and "
      f"how records stay consistent. All {it_iso} IT experts answered them. No dentist or clinic staff member "
      f"took part, so the only other answers came from {pt_iso} patient respondents who answered the part "
      f"anyway, for a total of {n_iso}. The two sections on the manual screening process and on screening "
      f"consistency and time were answered by {n_man} respondents. Of the respondents who gave their work "
      f"experience, "
      + ", ".join(f"{v} reported {k.lower()}" for k, v in exp.most_common()) + ".")
    w("### 4.3.2 Research Instrument")
    w(f"P The instrument has eleven sections with {len(items)} statements, listed in Table {{tab:chars}} and reproduced in full in Appendix A, plus "
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
    w(f"P Tables {{tab:se}} to {{tab:dp}} show the results for the six quality characteristics, rated by "
      f"{n_iso} respondents. In each table, WM is the average rating (4 = Strongly Agree, 1 = Strongly "
      f"Disagree), and SD shows how much the answers varied: a small SD means the respondents mostly agreed "
      f"with one another.")
    note_iso = f"N = {n_iso} ({it_iso} IT experts, {pt_iso} patient respondents). WM = weighted mean; SD = standard deviation."
    keys = {"1. Security": "se", "2. Privacy": "pr", "3. Usability": "us", "4. Reliability": "re",
            "5. Performance Efficiency": "pe", "6. Data Protection": "dp"}
    for sec in ISO:
        item_table(sec, keys[sec], f"Evaluation Results for {label(sec)}", note_iso)
        hi, lo = hilo(sec)
        a = S[sec]
        txt = (f"P {label(sec)} received an average rating of {f2(a['all']['wm'])} out of 4 (SD "
               f"{f2(a['all']['sd'])}), which means {verbal(a['all']['wm'])}. ")
        if abs(hi["all"]["wm"] - lo["all"]["wm"]) < 0.005:
            txt += "Every statement in this section received the same average. "
        else:
            txt += (f"The best-rated statement was {hi['code']}, “{hi['stmt'].rstrip('.')}” "
                    f"({f2(hi['all']['wm'])}). The lowest was {lo['code']}, “{lo['stmt'].rstrip('.')}” "
                    f"({f2(lo['all']['wm'])}), which is still Strongly Agree. ")
        if a["it"] and a["pt"]:
            txt += (f"IT experts gave lower ratings than patient respondents "
                    f"({f2(a['it']['wm'])} against {f2(a['pt']['wm'])}). "
                    if a["it"]["wm"] < a["pt"]["wm"] - 0.05 else
                    f"IT experts and patient respondents gave about the same ratings "
                    f"({f2(a['it']['wm'])} and {f2(a['pt']['wm'])}). ")
        neg = sum(1 for it in by_sec[sec] for x in it["all"]["xs"] if x <= 2)
        txt += ("Nobody disagreed with any statement in this section." if neg == 0 else
                f"Only {neg} of the answers in this section were Disagree or Strongly Disagree.")
        extra = {
            "4. Reliability": " IT experts also rated RE1 lowest. In the written comments, two respondents mentioned "
                              "slow first loading and bugs that had to be fixed; one reason is that the free server "
                              "used for the study goes to sleep after 15 minutes without use and takes time to "
                              "wake up (Chapter I, Limitations).",
            "1. Security": " One respondent suggested an extra security step for staff accounts, which is included in "
                           "the recommendations.",
            "3. Usability": " In the written comments, ease of use and the look of the interface were praised most, "
                            "while a few respondents found some pages too long or some features hard to find.",
        }
        w(txt + extra.get(sec, ""))
    w("### 4.3.6 Evaluation Results for the System Features")
    w(f"P Tables {{tab:ad}} to {{tab:pp}} show the results for the system's three main features, rated by all "
      f"{N} respondents.")
    note_f = f"N = {N} ({nIT} IT experts, {nPT} patient respondents). WM = weighted mean; SD = standard deviation."
    for sec, key in zip(FEATURE, ("ad", "ri", "pp")):
        item_table(sec, key, f"Evaluation Results for {sec}", note_f)
        hi, lo = hilo(sec)
        a = S[sec]
        neg = sum(1 for it in by_sec[sec] for x in it["all"]["xs"] if x <= 2)
        total = sum(len(it["all"]["xs"]) for it in by_sec[sec])
        txt = (f"P {sec} received an average rating of {f2(a['all']['wm'])} out of 4 (SD {f2(a['all']['sd'])}), "
               f"which means {verbal(a['all']['wm'])}. The best-rated statement was {hi['code']}, "
               f"“{hi['stmt'].rstrip('.')}” ({f2(hi['all']['wm'])}), and the lowest was {lo['code']}, "
               f"“{lo['stmt'].rstrip('.')}” ({f2(lo['all']['wm'])}). Only {neg} of the {total} answers in this "
               f"section were Disagree or Strongly Disagree. ")
        extra = {
            FEATURE[0]: "Note that this rating shows how accurate the detection seemed to the respondents, not "
                        "how accurate it measured: the measured accuracy in Section 4.1 is moderate, and plaque "
                        "is often missed. One respondent wrote that results may be wrong when the photograph is "
                        "blurry and should still be checked by a dentist, which is how the system is meant to "
                        "be used.",
            FEATURE[1]: "In their written comments, respondents especially liked the plain-language "
                        "explanations and how clearly the results are shown.",
            FEATURE[2]: "This was the best-rated of the three features. Respondents wrote that the tips were "
                        "clear and reminded them to care for their teeth, and several asked for more dental "
                        "tips, check-up reminders, and short videos.",
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
    w(f"P All nine sections were rated Strongly Agree, so Toothwise is Highly Acceptable to its respondents. "
      f"The six quality characteristics averaged {f2(iso_mean)} out of 4, and the three features "
      f"{f2(feat_mean)}. Among the quality characteristics, {label(iso_rank[0])} was rated highest "
      f"({f2(S[iso_rank[0]]['all']['wm'])}) and {label(iso_rank[-1])} lowest "
      f"({f2(S[iso_rank[-1]]['all']['wm'])}). IT experts gave lower ratings than patient respondents in every "
      f"section, but still Strongly Agree; this is expected, because IT experts judge the system against "
      f"technical standards. Disagreement was rare: {neg_iso} of {len(allx)} quality answers and "
      f"{neg_feat} of {len(featx)} feature answers were Disagree or Strongly Disagree.")
    w(f"P Two cautions apply. First, only {n_iso} of the {N} respondents rated the six quality "
      f"characteristics, and only {nIT} were IT experts, so these ratings come from a small group. This is "
      f"because that part was meant for dentists, clinic staff, and IT experts, and no dentists or clinic staff "
      f"took part. Second, the ratings show what the respondents thought of the system; they should be read "
      f"together with the measured results in Sections 4.1 and 4.2.")
    w("P In the written comments, respondents most often praised how easy the system is to use, its clear "
      "design, and its simple explanations. The problems they mentioned were slow loading the first time, pages "
      "with too much information at once, some features being hard to find, and wrong results from blurry "
      "photographs. Their suggestions were reminders for brushing and check-ups, more dental tips and short "
      "videos, an easier search, more conditions to detect with better accuracy, and an extra security step for "
      "staff accounts.")

    # ---------------------------------------------------------------- 4.4
    w("## 4.4 Screening Consistency and Screening Time")
    w(f"P This section answers the fifth problem: does Toothwise make screening more consistent and faster? "
      f"The original plan was to time the same patients' screenings with and without Toothwise and compare both "
      f"with the dentist's findings, but this could not be done because the study did not involve the clinic's "
      f"patients. Instead, this section uses the respondents' ratings of the current manual process and of "
      f"Toothwise (Tables {{tab:ms}} and {{tab:sc}}), together with the measured processing time in Section "
      f"4.1.6.")
    note_m = (f"N = {n_man}. These two sections were answered by only {n_man} respondents, so the results are "
              f"shown for completeness and should not be generalized.")
    item_table(MANUAL, "ms", "Respondents' Assessment of the Current Manual Screening Process", note_m)
    item_table(CONSIST, "sc", "Respondents' Assessment of Screening Consistency and Time with Toothwise", note_m)
    m, c = S[MANUAL]["all"], S[CONSIST]["all"]
    ms_lo = min(by_sec[MANUAL], key=lambda i: i["all"]["wm"])
    w(f"P The {n_man} respondents agreed that checking teeth by eye alone has the problems described in the "
      f"first problem (average {f2(m['wm'])}): results can differ from one examination to the next, lighting "
      f"and angle affect what can be seen, and a tool for consistent early screening would be useful. The only "
      f"statement they disagreed with was {ms_lo['code']}, “{ms_lo['stmt'].rstrip('.')}” "
      f"({f2(ms_lo['all']['wm'])}). They also agreed that Toothwise makes results more consistent, saves time in "
      f"completing and recording a screening, and agrees with the dentist's own findings (average "
      f"{f2(c['wm'])}), and they would recommend that the clinic keep using it.")
    w(f"P Because only {n_man} respondents answered these sections and no screening was timed, these results "
      f"show a likely direction, not a measured effect. What was measured is the processing time: the live "
      f"system finishes a screening with both models in about 3 to 4 seconds (Section 4.1.6), and it records "
      f"every finding, the risk result, and the prevention plan automatically, so the screening no longer has "
      f"to be written up by hand.")

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
      f"Lighthouse accessibility and best practices on all audited pages and passed all 119 automated backend "
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
    w("4. Train the detection models on more and larger datasets. The current models learned from four public "
      "datasets in which plaque appears in only one source, which explains much of the weak plaque result. "
      "More public datasets, consented and dentist-annotated clinic photographs, and a more balanced number "
      "of examples per condition should raise accuracy.")
    w("5. Add an oral diagnosis form to the system: a digital examination form in which the dentist records "
      "the clinical findings for each tooth (for example, on a tooth chart), the final diagnosis, and the "
      "treatment plan, next to the AI detections. The recorded diagnoses could then be compared with the "
      "detections to measure accuracy in real use and supply labeled cases for retraining.")
    w("6. Extend the system to detect more classes. The source datasets already contain conditions that this "
      "study left out, such as missing teeth, malalignment, spacing, tooth stains and "
      "discoloration, oral ulcers, and hypodontia, and orthodontic braces could be added as their own class "
      "instead of being filtered out. Each new class needs enough annotated examples, a risk weight, and its "
      "own advice.")
    w("7. Use an intraoral camera to capture the images for detection. Smartphone photographs vary in "
      "lighting and angle and cannot clearly show the back teeth; an intraoral camera gives close, well-lit, "
      "and consistent views of each tooth. Future researchers could connect one to the screening page and "
      "retrain the models on its images.")

    # The instrument, scale and statistical treatment belong to the method (Chapter III).
    i0 = L.index("### 4.3.2 Research Instrument")
    i1 = L.index("### 4.3.5 Evaluation Results per Quality Characteristic")
    method = L[i0:i1]
    del L[i0:i1]
    for old, new in (("### 4.3.5 ", "### 4.3.2 "), ("### 4.3.6 ", "### 4.3.3 "), ("### 4.3.7 ", "### 4.3.4 ")):
        L = [new + x[len(old):] if x.startswith(old) else x for x in L]
    method = [x.replace("### 4.3.2 ", "### 3.10.2 ").replace("### 4.3.3 ", "### 3.10.3 ")
               .replace("### 4.3.4 ", "### 3.10.4 ") for x in method]
    parts = {MANUAL: "Part A", CONSIST: "Part A"}
    ch3 = [
        f"P This section describes how the acceptability of Toothwise was evaluated (the fourth and fifth problems "
        f"of the study): who the respondents were, the instrument they answered, how the data were gathered, and "
        f"how the responses were treated. The results are presented in Sections 4.3 and 4.4.",
        "### 3.10.1 Respondents and Data Gathering",
        f"P The evaluation questionnaire was prepared in Google Forms and shared online. Participation was "
        f"voluntary: the form opened with a statement explaining the purpose of the study and the handling of the "
        f"data, and only respondents who agreed to it could continue. Each respondent first stated their group, "
        f"either patient respondent (a member of the public evaluating the system from a patient's point of view) "
        f"or IT expert (IT practitioner), and then answered the parts of the questionnaire intended for them. The "
        f"software quality part (ISO/IEC 25010) was written for dentists, clinic staff, and IT experts, while the "
        f"parts on the system's features were written for all respondents. Responses were collected from "
        f"{first} to {last}, and {N} complete submissions were received.",
    ] + method + [
        "### 3.10.5 Ethical Considerations",
        "P All respondents gave their informed consent before answering. The questionnaire asked for a name only "
        "as an optional field; names are not reported anywhere in this paper, and results are presented only as "
        "group statistics. No patient records or photographs from CodiSmile Dental Clinic were collected for the "
        "evaluation, and all data were handled in accordance with the Data Privacy Act of 2012 (Republic Act No. "
        "10173). The screening images shown in this paper are demonstration images.",
    ]

    abstract = [
        "FRONTH ABSTRACT",
        f"PN Dental screening at CodiSmile Dental Clinic relies on visual inspection, which makes early tartar, "
        f"plaque, cavity, and gum inflammation hard to detect consistently, leaves no standardized visual record, "
        f"and gives patients little finding-specific guidance. This study developed Toothwise, a web-based "
        f"screening support system that detects these four conditions and healthy tooth in still intraoral "
        f"photographs with a fused YOLOv8 and YOLOv12 ensemble, computes a 0–100 risk score and a low, medium, "
        f"or high risk tier, and generates a personalized prevention plan with a K-Nearest Neighbors (KNN) "
        f"classifier. The system was developed with an Agile methodology using React, FastAPI, and PostgreSQL, "
        f"and deployed on cloud hosting. On a held-out test set of 2,930 images, YOLOv8 reached an mAP@50 of "
        f"51.91% and YOLOv12 48.11%, and the fused ensemble 54.24%; cavity was detected best and plaque worst. "
        f"The KNN classifier reproduced the clinical risk rule with 92.75% accuracy on 2,000 unseen cases, and "
        f"all 119 automated backend tests passed. The system was evaluated through an online questionnaire "
        f"answered by {N} respondents ({nPT} patient respondents and {nIT} IT experts) on a four-point scale. The "
        f"six ISO/IEC 25010 quality characteristics (security, privacy, usability, reliability, performance "
        f"efficiency, and data protection), rated by {n_iso} respondents, obtained an overall weighted mean of "
        f"{f2(iso_mean)}, and the system's detection, results, and prevention-plan features, rated by all {N}, "
        f"obtained {f2(feat_mean)}; both are interpreted as Highly Acceptable. The study concludes that Toothwise "
        f"is an acceptable screening and documentation aid that supports, but does not replace, the dentist's "
        f"diagnosis, and recommends more training data for weak classes such as plaque, the use of an intraoral camera for clearer images, a larger evaluation with "
        f"dentists and clinic staff, and a controlled comparison of screening time and consistency.",
        "PN ***Keywords:*** dental screening, YOLOv8, YOLOv12, ensemble object detection, K-Nearest Neighbors, "
        "prevention plan, ISO/IEC 25010",
        "PAGEBREAK",
    ]

    # Appendices
    app = ["#APP APPENDIX A | Evaluation Questionnaire",
           f"P The questionnaire was answered online through Google Forms. Each statement was rated on a four-point "
           f"scale: Strongly Agree (4), Agree (3), Disagree (2), and Strongly Disagree (1)."]
    part_of = lambda sec: ("Part A. Current Process and Expected Effect" if sec in (MANUAL, CONSIST) else
                           "Part B3. Software Quality Evaluation (ISO/IEC 25010) — for dentists, clinic staff, and IT experts"
                           if sec in ISO else "Part B. System Features — for all respondents")
    last_part = None
    for sec, its in by_sec.items():
        if part_of(sec) != last_part:
            last_part = part_of(sec)
            app.append(f"PN **{last_part}**")
        app.append(f"PN *{label(sec)}*")
        for it in its:
            app.append(f"- {it['code']}. {it['stmt']}")
    app.append("PN **Part C. Open-ended Questions**")
    for q in ("What did you like most about Toothwise?", "What problems or difficulties did you encounter while "
              "using Toothwise?", "What improvements or additional features would you suggest?"):
        app.append(f"- {q}")
    app.append("#APP APPENDIX B | Frequency Distribution of Responses")
    app.append("P The table lists, for every statement, how many respondents chose each rating, the number of "
               "respondents who answered it (N), and the weighted mean (WM). Respondent names are not included.")
    app.append("TABLE freq | Frequency Distribution of Responses per Statement")
    app.append("W 0.6,0.8,0.65,0.75,0.75,0.8,0.55,0.6")
    app.append("| Code | Strongly Agree (4) | Agree (3) | Disagree (2) | Strongly Disagree (1) | N | WM | Section |")
    for it in items:
        xs = it["all"]["xs"]
        app.append(f"| {it['code']} | {xs.count(4)} | {xs.count(3)} | {xs.count(2)} | {xs.count(1)} | {len(xs)} | "
                   f"{f2(it['all']['wm'])} | {CODES[it['section']]} |")
    app.append("ENDTABLE")
    app.append("NOTE Section codes: " + "; ".join(f"{CODES[s]} = {label(s)}" for s in by_sec) + ".")
    app.append("#APP APPENDIX C | Letter of Approval from CodiSmile Dental Clinic")
    app.append("FIG letter1 | appendix_letter_1.png | 5.4 | Letter Requesting Approval to Conduct the Study (page 1 of 2)")
    app.append("FIG letter2 | appendix_letter_2.png | 5.4 | Letter Requesting Approval to Conduct the Study (page 2 of 2)")

    text = CONTENT.read_text(encoding="utf-8")
    # abstract: between TITLEPAGE and TOC
    a = text.index("TITLEPAGE") + len("TITLEPAGE")
    b = text.index("\nTOC")
    text = text[:a] + "\n" + "\n".join(abstract) + text[b:]
    # Chapter III evaluation procedure
    a = text.index("## 3.10 Evaluation Procedure")
    b = text.index("## 3.11 Full Current System Screenshots")
    text = text[:a] + "## 3.10 Evaluation Procedure\n" + "\n".join(ch3) + "\n\n" + text[b:]
    # 4.3 to Chapter V
    a = text.index("## 4.3 Software Quality Evaluation")
    b = text.index("#CH REFERENCES")
    text = text[:a] + "\n".join(L) + "\n\n" + text[b:]
    # appendices at the end
    a = text.find("#APP ")
    text = (text if a < 0 else text[:a]).rstrip("\n") + "\n\n" + "\n".join(app) + "\n"
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
