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


# IT Expert Evaluation Form (separate Google Form), from its response summary: rating counts per
# statement for the 2 IT experts. Names are not recorded here.
IT_SECTIONS = [("Security", "SE"), ("Privacy", "PR"), ("Usability", "US"), ("Reliability", "RE"),
               ("Performance Efficiency", "PE"), ("Data Protection", "DP")]
IT_ITEMS = {
    'SE1': ("Only authorized users can log in and access the system's functions.", [4, 3]),
    'SE2': ('Each role (Dentist, Receptionist, Dental Assistant, Patient) can only access the features permitted for that role.', [4, 3]),
    'SE3': ('Passwords and login sessions are handled securely.', [4, 4]),
    'SE4': ('Sensitive staff actions are recorded in the audit log for administrative review.', [4, 4]),
    'SE5': ('Login, registration, and password-reset requests are limited against repeated attempts, and a failed password reset does not reveal whether an account exists.', [4, 4]),
    'PR1': ('Screening images are not publicly exposed and can only be viewed by authorized users.', [4, 4]),
    'PR2': ('Patients can only view their own records through the patient portal.', [4, 4]),
    'PR3': ('The system handles personal and health information in line with the Data Privacy Act of 2012.', [4, 4]),
    'PR4': ('Users must read and agree to the Data Privacy Notice before they can use the system.', [4, 4]),
    'PR5': ('The AI assistant answers general dental and clinic questions without reading or revealing patient records.', [4, 4]),
    'US1': ('The system is easy to learn and use, even for first-time users.', [4, 4]),
    'US2': ('Navigation between the dashboard, patient records, and screening pages is clear and logical.', [4, 4]),
    'US3': ('Labels, buttons, and messages are easy to understand.', [4, 4]),
    'US4': ('The layout and design of the interface are visually pleasing and organized.', [4, 4]),
    'US5': ('The system works well in both desktop and mobile web browsers.', [4, 4]),
    'RE1': ('The system runs consistently without unexpected crashes or failures.', [4, 4]),
    'RE2': ('When an error occurs, the system shows a clear message and recovers without losing data.', [4, 4]),
    'RE3': ('The system produces consistent results when the same image is screened again.', [4, 4]),
    'RE4': ('Screening photos and records remain available after the server restarts.', [4, 4]),
    'RE5': ('After the server wakes from an idle period, the system works normally without errors.', [4, 4]),
    'PE1': ('The system analyzes an uploaded image and displays the results within an acceptable time.', [4, 4]),
    'PE2': ('Pages and patient records load quickly.', [4, 4]),
    'PE3': ('The system remains responsive while performing AI detection.', [4, 4]),
    'PE4': ('Photos in common formats (JPEG, PNG, WebP, HEIC) of up to 15 MB are uploaded and processed without errors.', [4, 4]),
    'PE5': ('The model-comparison view clearly reports the processing time of YOLOv8 and YOLOv12 for each screening.', [4, 4]),
    'DP1': ('Patient, screening, and detection records are stored accurately and completely.', [4, 4]),
    'DP2': ('Related records (patients, screenings, findings, recommendations, notes) remain consistent with one another.', [4, 4]),
    'DP3': ('The system prevents invalid or incomplete data from being saved.', [4, 4]),
    'DP4': ('The generated PDF screening report matches the stored screening record.', [4, 4]),
    'DP5': ('The system protects data against loss through database backups and stored copies of screening photos.', [4, 4]),
}
IT_PROFILE = {"field": {"Software / Web Development": 2},
              "years": {"1–3 years": 1, "4–6 years": 1},
              "positions": ["Senior AI Engineer", "IT"]}
IT_COMMENTS = {
    "What are the strengths of Toothwise from a technical point of view?": [
        "Innovative",
        "Biggest strength is that, it puts everything a dental clinic needs in one place. Patient records, dental "
        "history, and appointments are all stored in one system instead of on paper, so information is easier to "
        "find and less likely to get lost. Patients can book online, which helps the clinic avoid double bookings "
        "and manage its schedule better. Each user only sees what they need, so patient data stays protected. The "
        "system is also simple enough that even non-tech savy people can use it without much training."],
    "What problems, bugs, or security concerns did you encounter?": ["none that I know of", "none"],
    "What improvements or additional features would you recommend?": [
        "UI/UX, less click less scroll",
        "Since it’s web-based, it has a solid foundation for adding features like billing or inventory."],
}

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
    # Software quality: the 2 IT experts (IT Expert Evaluation Form). Features: the user survey.
    itS = {}
    for name, code in IT_SECTIONS:
        its = [(c, *IT_ITEMS[c]) for c in IT_ITEMS if c.startswith(code)]
        allv = [x for _, _, xs in its for x in xs]
        itS[name] = {"items": its, "wm": st.mean(st.mean(xs) for _, _, xs in its), "sd": st.pstdev(allv),
                     "neg": sum(1 for x in allv if x <= 2)}
    n_itx = len(next(iter(IT_ITEMS.values()))[1])
    q_all = [x for _, xs in IT_ITEMS.values() for x in xs]
    q_mean = st.mean(v["wm"] for v in itS.values())
    q_sd = st.pstdev(q_all)
    q_rank = sorted(itS, key=lambda k: -itS[k]["wm"])
    q_agree = sorted(c for c, (_, xs) in IT_ITEMS.items() if min(xs) < 4)

    w("## 4.3 Software Quality Evaluation Based on ISO/IEC 25010")
    w(f"P This section answers the fourth problem: how acceptable is Toothwise? Two groups evaluated the "
      f"system. Two IT experts rated its software quality on the six ISO/IEC 25010 characteristics using "
      f"the IT Expert Evaluation Form, and {N} user respondents rated its main features using the user survey "
      f"from {first} to {last}. Both forms were answered online (Google Forms) after the respondents agreed to "
      f"take part. None of the respondents was a patient of CodiSmile Dental Clinic, and no clinic records were "
      f"used.")
    w("### 4.3.1 Respondents")
    w(f"P The two IT experts both specialize in software and web development; one has 1 to 3 years and the "
      f"other 4 to 6 years of experience in IT, and they work as a senior AI engineer and an IT practitioner "
      f"(Table {{tab:itprof}}). The {N} user respondents were {nPT} patient respondents, who tried the system "
      f"from a patient's point of view, and {nIT} IT practitioners (Table {{tab:resp}}). Not every part of the "
      f"user survey was meant for every respondent, so the parts were answered by different numbers of people "
      f"(Table {{tab:sectn}}).")
    w("TABLE itprof | Profile of the IT Expert Evaluators")
    w("W 2.2,2.6,1.0")
    w("| Profile item | Category | Frequency |")
    for k, v in IT_PROFILE["field"].items():
        w(f"| Field of specialization | {k} | {v} |")
    for k, v in IT_PROFILE["years"].items():
        w(f"| Years of experience in IT | {k} | {v} |")
    for k in IT_PROFILE["positions"]:
        w(f"| Current position | {k} | 1 |")
    w("ENDTABLE")
    w(f"NOTE N = {n_itx}.")
    w("TABLE resp | Distribution of User Respondents")
    w("W 2.8,1.4,1.4")
    w("| Respondent group | Frequency | Percentage |")
    w(f"| Patient respondents | {nPT} | {nPT / N:.2%} |")
    w(f"| IT practitioners | {nIT} | {nIT / N:.2%} |")
    w(f"| Total | {N} | 100.00% |")
    w("ENDTABLE")
    w("TABLE sectn | User Respondents per Survey Part")
    w("W 2.75,1.25,1.25,0.75")
    w("| Survey part | Patient respondents | IT practitioners | Total |")
    for sec in FEATURE + [MANUAL, CONSIST] + ISO:
        p = S[sec]["pt"]["n"] if S[sec]["pt"] else 0
        i = S[sec]["it"]["n"] if S[sec]["it"] else 0
        tag = " (Part B3)" if sec in ISO else ""
        w(f"| {label(sec)}{tag} | {p} | {i} | {p + i} |")
    w("ENDTABLE")
    w(f"P All {N} user respondents rated the three main features. The user survey also had a software quality "
      f"part (Part B3) meant for dentists, clinic staff, and IT practitioners. No dentist or clinic staff member "
      f"took part, so it was answered by {n_iso} respondents ({it_iso} IT practitioners and {pt_iso} patient "
      f"respondents), with an overall mean of {f2(iso_mean)} (Strongly Agree). Because these respondents were "
      f"not all IT experts, the software quality results in this section come from the IT Expert Evaluation "
      f"Form; the Part B3 answers are listed in Appendices B and F. The two parts on the manual screening "
      f"process and on screening consistency and time were answered by {n_man} respondents (Section 4.4).")
    w("### 4.3.2 Research Instrument")
    w(f"P Two instruments were used; both are reproduced in Appendix A and shown as online forms in Appendix E. "
      f"The IT Expert Evaluation Form asks for the evaluator's profile, then has {len(IT_ITEMS)} statements, five "
      f"for each of the six quality characteristics named in the fourth problem, and three open-ended questions "
      f"on the system's technical strengths, the problems found, and recommended improvements. The user survey "
      f"has {len(feat_items)} statements on the three main features, {len(by_sec[MANUAL]) + len(by_sec[CONSIST])} "
      f"statements on the current manual process and on screening consistency and time (the fifth problem), a "
      f"software quality part for clinic staff and IT practitioners, and three open-ended questions on what "
      f"respondents liked, the difficulties they met, and the improvements they suggest (Table {{tab:chars}}).")
    w("TABLE chars | Sections of the Evaluation Instruments")
    w("W 2.6,0.9,0.6,1.9")
    w("| Instrument and section | Item codes | Items | Problem addressed |")
    for name, code in IT_SECTIONS:
        k = len(itS[name]["items"])
        w(f"| IT Expert Form — {name} | {code}1–{code}{k} | {k} | Problem 4 (quality characteristic) |")
    for sec, prob in zip(FEATURE, ("Problems 1 and 4", "Problems 2 and 4", "Problems 3 and 4")):
        k = len(by_sec[sec])
        w(f"| User Survey — {sec} | {CODES[sec]}1–{CODES[sec]}{k} | {k} | {prob} |")
    for sec, prob in ((MANUAL, "Problem 1 (current process)"), (CONSIST, "Problem 5")):
        k = len(by_sec[sec])
        w(f"| User Survey — {sec} | {CODES[sec]}1–{CODES[sec]}{k} | {k} | {prob} |")
    k = sum(len(by_sec[s]) for s in ISO)
    w(f"| User Survey — Software Quality (Part B3) | SE1–DP3 | {k} | Problem 4 (supplementary) |")
    w(f"| Total |  | {len(IT_ITEMS) + len(items)} |  |")
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
    w(f"P Tables {{tab:se}} to {{tab:dp}} show how the {n_itx} IT experts rated the six quality "
      f"characteristics. In each table, SA and A are the number of experts who chose Strongly Agree (4) and "
      f"Agree (3), WM is the average rating, and SD shows how much the two ratings differed (0 means both "
      f"experts gave the same rating).")
    keys = {"Security": "se", "Privacy": "pr", "Usability": "us", "Reliability": "re",
            "Performance Efficiency": "pe", "Data Protection": "dp"}
    extra = {
        "Security": " No security concern was reported in the written comments.",
        "Usability": " In their comments, one expert recommended “less click less scroll”, and in the Messenger "
                     "conversation (Appendix D) one found some white space uncomfortable and suggested a layout "
                     "that adapts to all screen sizes; these are included in the recommendations.",
        "Reliability": " This includes RE5, on the system working normally after the free server wakes from an idle "
                       "period, a limitation noted in Chapter I.",
    }
    for name, code in IT_SECTIONS:
        v = itS[name]
        w(f"TABLE {keys[name]} | Evaluation Results for {name}")
        w("W 0.5,3.35,0.45,0.45,0.55,0.5,1.2")
        w("| Code | Statement | SA | A | WM | SD | Verbal interpretation |")
        for c, stmt, xs in v["items"]:
            w(f"| {c} | {stmt} | {xs.count(4)} | {xs.count(3)} | {f2(st.mean(xs))} | {f2(st.pstdev(xs))} | "
              f"{verbal(st.mean(xs))} |")
        w(f"|  | {name} — mean |  |  | {f2(v['wm'])} | {f2(v['sd'])} | {verbal(v['wm'])} |")
        w("ENDTABLE")
        w(f"NOTE N = {n_itx} IT experts. SA = Strongly Agree; A = Agree; WM = weighted mean; SD = standard deviation. "
          f"No statement was rated Disagree or Strongly Disagree.")
        txt = (f"P {name} received an average rating of {f2(v['wm'])} out of 4 (SD {f2(v['sd'])}), which means "
               f"{verbal(v['wm'])}. ")
        if all(min(xs) == 4 for _, _, xs in v["items"]):
            txt += f"Both IT experts chose Strongly Agree for all {len(v['items'])} statements."
        else:
            ag = [c for c, _, xs in v["items"] if min(xs) < 4]
            txt += (f"One expert chose Agree for {' and '.join(ag)}, on who can sign in and what each role may open, "
                    f"so these two statements averaged {f2(3.5)}, still Strongly Agree; every other statement was "
                    f"rated Strongly Agree by both experts.")
        w(txt + extra.get(name, ""))
    w("### 4.3.6 Evaluation Results for the System Features")
    w(f"P Tables {{tab:ad}} to {{tab:pp}} show the results for the system's three main features, rated by all "
      f"{N} user respondents.")
    note_f = f"N = {N} ({nPT} patient respondents, {nIT} IT practitioners). WM = weighted mean; SD = standard deviation."
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
        fx = {
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
        w(txt + fx[sec])
    w("### 4.3.7 Summary of the Evaluation")
    w("TABLE iso | Summary of Evaluation Results")
    w("W 2.7,1.5,0.7,0.6,1.3")
    w("| Section | Rated by | WM | SD | Interpretation |")
    for name, _ in IT_SECTIONS:
        v = itS[name]
        w(f"| {name} | {n_itx} IT experts | {f2(v['wm'])} | {f2(v['sd'])} | {accept(v['wm'])} |")
    w(f"| Quality characteristics (mean of six) | {n_itx} IT experts | {f2(q_mean)} | {f2(q_sd)} | {accept(q_mean)} |")
    for sec in FEATURE:
        a = S[sec]["all"]
        w(f"| {sec} | {N} user respondents | {f2(a['wm'])} | {f2(a['sd'])} | {accept(a['wm'])} |")
    w(f"| System features (mean of three) | {N} user respondents | {f2(feat_mean)} | {f2(feat_sd)} | {accept(feat_mean)} |")
    w("ENDTABLE")
    w(f"P All nine sections were rated Strongly Agree, so Toothwise is Highly Acceptable to its evaluators. The "
      f"IT experts rated the six quality characteristics {f2(q_mean)} out of 4: {len(IT_ITEMS) * n_itx - len(q_agree)} "
      f"of their {len(IT_ITEMS) * n_itx} ratings were Strongly Agree and the other {len(q_agree)} were Agree, both "
      f"on Security. The user respondents rated the three features {f2(feat_mean)}, and only {neg_feat} of their "
      f"{len(featx):,} answers were Disagree or Strongly Disagree.")
    w(f"P Two cautions apply. First, the software quality results come from {n_itx} IT experts, so they "
      f"describe the judgment of a small group; the {n_iso} user respondents who answered the quality part of "
      f"the user survey gave a similar result ({f2(iso_mean)}). Second, the ratings show what the evaluators "
      f"thought of the system; they should be read together with the measured results in Sections 4.1 and 4.2.")
    w("P In their written comments, the IT experts described the system as innovative and praised that it keeps "
      "the clinic's records in one place, shows each user only what they need, and is simple enough to use "
      "without much training. Neither reported a problem, bug, or security concern. They recommended fewer clicks "
      "and less scrolling, and noted that the web-based design is a good base for features such as billing and "
      "inventory.")
    w("P The user respondents most often praised how easy the system is to use, its clear design, and its "
      "simple explanations. The problems they mentioned were slow loading the first time, pages with too much "
      "information at once, some features being hard to find, and wrong results from blurry photographs. Their "
      "suggestions were reminders for brushing and check-ups, more dental tips and short videos, an easier "
      "search, more conditions to detect with better accuracy, and an extra security step for staff accounts.")

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
    w(f"4. **Acceptability (Problem 4).** The {n_itx} IT experts rated the six ISO/IEC 25010 quality "
      f"characteristics with an overall mean of {f2(q_mean)} (Highly Acceptable): every characteristic received "
      f"4.00 except Security ({f2(itS['Security']['wm'])}), where one expert chose Agree for two statements. The "
      f"three feature sections, rated by all {N} user respondents, obtained an overall mean of {f2(feat_mean)} "
      f"(Highly Acceptable). Technically, the web application scored 100 in Lighthouse accessibility and best "
      f"practices on all audited pages and passed all 119 automated backend tests.")
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
      f"features (overall means of {f2(q_mean)} and {f2(feat_mean)} on a four-point scale). Because the quality "
      f"characteristics were rated by {n_itx} IT experts, this conclusion should be confirmed with a larger "
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
    w("4. Simplify pages that present much information at once, reduce the clicks and scrolling needed to finish a "
      "task, reduce unneeded white space, make the layout adapt to all screen sizes and aspect ratios, and make "
      "less-used features easier to find, as the IT experts and user respondents suggested. In the longer term, "
      "billing and inventory modules can be added, as one IT expert noted.")
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
        f"P Two evaluation forms were prepared in Google Forms and answered online: the IT Expert Evaluation "
        f"Form, on the six ISO/IEC 25010 quality characteristics, and the user survey, on the system's main "
        f"features. Participation was voluntary: each form opened with a statement explaining the purpose of "
        f"the study and the handling of the data, and only respondents who agreed to it could continue. The IT "
        f"experts were sent a video demonstration of Toothwise, the deployed system's address with test "
        f"accounts, and the form link. In the user survey, each respondent first stated their group and then "
        f"answered only the parts meant for that group. The user survey was answered from {first} to {last} "
        f"with {N} complete submissions, and the IT Expert Evaluation Form by {n_itx} IT experts.",
        f"P The study used purposive sampling, a non-probability technique in which respondents are chosen "
        f"because they fit the purpose of the study (Etikan et al., 2016). Two groups were sampled. IT experts "
        f"had to work in information technology and were personally invited by the researchers, because the "
        f"software quality evaluation calls for technical knowledge; two took part. User respondents had to be "
        f"able to judge the system from a user's point of view, as a dental patient or as an IT practitioner, "
        f"and had to agree to the consent statement. A minimum of 50 user respondents was set, and {N} took part "
        f"({nPT} patient respondents and {nIT} IT practitioners). Because the respondents were not randomly "
        f"selected, the results describe the respondents of this study and are not generalized to all patients "
        f"or all IT practitioners. Tables {{tab:itprof}}, {{tab:resp}}, and {{tab:sectn}} show the respondents.",
    ] + method + [
        "### 3.10.5 Ethical Considerations",
        "P All respondents gave their informed consent before answering. The user survey asked for the "
        "respondent's name and the IT Expert Evaluation Form asked for it as an optional field; names are not reported anywhere in this paper, and results are presented only as "
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
        f"all 119 automated backend tests passed. The system was evaluated through two online forms "
        f"answered on a four-point scale. The six ISO/IEC 25010 quality characteristics (security, privacy, "
        f"usability, reliability, performance efficiency, and data protection), rated by {n_itx} IT experts, "
        f"obtained an overall weighted mean of {f2(q_mean)}, and the system's detection, results, and "
        f"prevention-plan features, rated by {N} user respondents ({nPT} patient respondents and {nIT} IT "
        f"practitioners), obtained {f2(feat_mean)}; both are interpreted as Highly Acceptable. The study concludes that Toothwise "
        f"is an acceptable screening and documentation aid that supports, but does not replace, the dentist's "
        f"diagnosis, and recommends more training data for weak classes such as plaque, the use of an intraoral camera for clearer images, a larger evaluation with "
        f"dentists and clinic staff, and a controlled comparison of screening time and consistency.",
        "PN ***Keywords:*** dental screening, YOLOv8, YOLOv12, ensemble object detection, K-Nearest Neighbors, "
        "prevention plan, ISO/IEC 25010",
        "PAGEBREAK",
    ]

    # Appendices
    app = ["#APP APPENDIX A | Evaluation Instruments",
           f"P Both instruments were answered online through Google Forms (Appendix E). Each statement was rated on "
           f"a four-point scale: Strongly Agree (4), Agree (3), Disagree (2), and Strongly Disagree (1).",
           "PN **IT Expert Evaluation Form: Software Quality Evaluation Based on ISO/IEC 25010**",
           "PN *Part I. Evaluator Profile*",
           "- Name (optional); current position or job title; field of specialization; years of experience in IT; "
           "how the system was evaluated (used the deployed system, watched a demonstration, or both)."]
    for name, code in IT_SECTIONS:
        app.append(f"PN *Part II. {name}*")
        for c, (stmt, _) in IT_ITEMS.items():
            if c.startswith(code):
                app.append(f"- {c}. {stmt}")
    app.append("PN *Part III. Comments and Recommendations*")
    for q in IT_COMMENTS:
        app.append(f"- {q}")
    app.append("PN **User Survey: Toothwise Survey Questionnaire**")
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
    app.append("P The tables list, for every statement of both instruments, how many respondents chose each rating, the number of "
               "respondents who answered it (N), and the weighted mean (WM). Respondent names are not included.")
    app.append("TABLE freqit | Frequency Distribution — IT Expert Evaluation Form")
    app.append("W 0.6,0.8,0.65,0.75,0.75,0.8,0.55")
    app.append("| Code | Strongly Agree (4) | Agree (3) | Disagree (2) | Strongly Disagree (1) | N | WM |")
    for c, (_, xs) in IT_ITEMS.items():
        app.append(f"| {c} | {xs.count(4)} | {xs.count(3)} | {xs.count(2)} | {xs.count(1)} | {len(xs)} | "
                   f"{f2(st.mean(xs))} |")
    app.append("ENDTABLE")
    app.append("TABLE freq | Frequency Distribution — User Survey")
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
    app.append("#APP APPENDIX D | Evaluator Feedback and Panel Consultation")
    app.append("P The IT experts received a video demonstration of Toothwise and the evaluation form through Facebook "
               "Messenger and gave their feedback in the same conversations; their names and photos are blurred. "
               "Messages in Filipino are summarized in English in the captions.")
    app.append("FIGPAIR app_it1a | appendix_it1_a.jpg | 2.6 | IT Expert 1 — Demonstration and Form Sent | "
               "The researchers sent the demonstration video and the IT Expert Evaluation Form link. "
               "|| app_it1b | appendix_it1_b.jpg | 2.6 | IT Expert 1 — Feedback | "
               "After submitting the form, the expert found the system good and innovative and noted that the "
               "code base could also have been shared for review.")
    app.append("FIGPAIR app_it2a | appendix_it2_a.jpg | 2.95 | IT Expert 2 — Form Submitted | "
               "The expert submitted the form and offered the comments as suggestions for improvement and "
               "further advancement. "
               "|| app_it2b | appendix_it2_b.jpg | 2.95 | IT Expert 2 — Feedback | "
               "The expert liked the concept of a website with AI detection, found some white space "
               "uncomfortable, suggested a layout responsive to all aspect ratios, and asked if it opens on a phone.")
    app.append("FIGPAIR app_pan1 | appendix_panel_a.jpg | 2.95 | Panel Consultation — Request for Review | "
               "The researchers sent the revised paper to a panel member for checking of the statement of the problem. "
               "|| app_pan2 | appendix_panel_b.jpg | 2.95 | Panel Consultation — Approval | "
               "The panel member found the statement of the problem acceptable, noted that the model metrics were "
               "corrected and that the panel's advice to test on more datasets was followed, and saw no problem.")

    # Appendix E: the online forms, captured page by page without answers.
    app.append("#APP APPENDIX E | Online Evaluation Forms")
    app.append("P The evaluation forms were prepared in Google Forms. The figures show every page of each form as "
               "a respondent sees it, without answers; the main survey shows each part to the respondent groups "
               "named at the top of the part.")
    for key, title, n in (("main", "Toothwise Survey Questionnaire", 8),
                          ("it", "Toothwise IT Expert Evaluation Form", 6)):
        for a in range(1, n + 1, 2):
            app.append(f"FIGPAIR form_{key}_{a} | form_{key}_{a}.jpg | 2.95 | {title} ({a} of {n}) | "
                       f"|| form_{key}_{a+1} | form_{key}_{a+1}.jpg | 2.95 | {title} ({a+1} of {n}) | ")

    # Appendix F: every respondent's ratings (no names).
    rid = {id(r): f"R{i:03d}" for i, r in enumerate(data, 1)}
    typ = lambda r: "IT" if str(r[role]).startswith("IT") else "P"
    def resp_table(key, title, secs):
        its = [it for it in items if it["section"] in secs]
        rows = [r for r in data if any(score(r[it["col"]]) is not None for it in its)]
        app.append(f"TABLE {key} | {title} (n = {len(rows)})")
        app.append("W " + ",".join(["0.55", "0.4"] + ["0.36"] * len(its)))
        app.append("| " + " | ".join(["Resp.", "Type"] + [it["code"] for it in its]) + " |")
        for r in rows:
            vals = [str(score(r[it["col"]]) or "–") for it in its]
            app.append("| " + " | ".join([rid[id(r)], typ(r)] + vals) + " |")
        app.append("ENDTABLE")
    app.append("#APP APPENDIX F | Individual Responses")
    app.append("P The tables list the user survey responses. Each row is one respondent, numbered in the order the "
               f"responses were received (R001 to R{len(data):03d}); names are not shown. Type: P = patient "
               "respondent, IT = IT practitioner. Ratings: 4 = Strongly Agree, 3 = Agree, 2 = Disagree, 1 = "
               "Strongly Disagree. Item codes are those of the user survey in Appendix A. The ratings of the two "
               "IT experts on the IT Expert Evaluation Form are given per statement in Appendix B.")
    resp_table("indA", "Individual Ratings — System Features", FEATURE)
    resp_table("indB1", "Individual Ratings — Part B3: Security, Privacy, and Usability", ISO[:3])
    resp_table("indB2", "Individual Ratings — Part B3: Reliability, Performance Efficiency, and Data Protection", ISO[3:])
    resp_table("indC", "Individual Ratings — Current Process and Screening Consistency", [MANUAL, CONSIST])

    # Appendix G: open-ended answers, verbatim.
    junk = {"", "-", ".", "none", "n/a", "na", "nothing", "wala", "no", "n.a.", "none so far", "not applicable"}
    app.append("#APP APPENDIX G | Respondents' Comments and Suggestions")
    app.append("P The answers to the three open-ended questions are reproduced as written, without corrections; "
               "blank answers and answers such as \"none\" are omitted.")
    app.append("PN **IT Expert Evaluation Form**")
    for q, ans in IT_COMMENTS.items():
        app.append(f"PN *{q}*")
        for k, v in enumerate(ans, 1):
            app.append(f"- IT expert {k}: “{v}”")
    app.append("PN **User Survey**")
    for c in range(len(head)):
        h = str(head[c] or "")
        if not h.startswith(("What did you like", "What problems", "What improvements")):
            continue
        app.append(f"PN **{h}**")
        for r in data:
            v = re.sub(r"\s+", " ", str(r[c] or "")).strip()
            if v.lower() not in junk:
                v = v.replace("*", "∗").replace("|", "/")
                app.append(f"- {rid[id(r)]} ({typ(r)}): “{v}”")

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
