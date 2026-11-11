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
    w(f"| Patient respondents | {nPT} | {nPT / N:.1%} |")
    w(f"| IT practitioners | {nIT} | {nIT / N:.1%} |")
    w(f"| Total | {N} | 100.0% |")
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
      f"Form.")
    w("### 4.3.2 Research Instrument")
    w(f"P Two instruments were used. The IT Expert Evaluation Form asks for the evaluator's profile, then has {len(IT_ITEMS)} statements, five "
      f"for each of the six quality characteristics named in the fourth problem, and three open-ended questions "
      f"on the system's technical strengths, the problems found, and recommended improvements. The user survey "
      f"has {len(feat_items)} statements on the three main features, {len(by_sec[MANUAL]) + len(by_sec[CONSIST])} "
      f"statements on the current manual process and on screening consistency and time (supporting information "
      f"for the fifth problem), a "
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
    for sec, prob in ((MANUAL, "Problem 1 (current process)"), (CONSIST, "Problem 5 (supporting)")):
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
        "Usability": " The experts suggested fewer clicks and less scrolling, less white space, and a layout for "
                     "all screen sizes (Appendices C and D).",
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
      f"describe the judgment of a small group. Second, the ratings show what the evaluators "
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

    # Sentences placed into the hand-maintained Section 4.4, Chapter V, and abstract.
    finding4 = (f"4. **Acceptability (Problem 4).** The {n_itx} IT experts rated the six ISO/IEC 25010 quality "
                f"characteristics with an overall mean of {f2(q_mean)} (Highly Acceptable): every characteristic "
                f"received 4.00 except Security ({f2(itS['Security']['wm'])}), where one expert chose Agree for two "
                f"statements. The three feature sections, rated by all {N} user respondents, obtained an overall mean "
                f"of {f2(feat_mean)} (Highly Acceptable).")
    conclusion5 = (f"5. Toothwise is highly acceptable to its evaluators on all six quality characteristics and on its "
                   f"main features (overall means of {f2(q_mean)} and {f2(feat_mean)} on a four-point scale). Because "
                   f"the quality characteristics were rated by {n_itx} IT experts, this conclusion should be confirmed "
                   f"with a larger group of IT experts, dentists, and clinic staff.")
    rec_simplify = ("Simplify pages that present much information at once, reduce the clicks and scrolling needed to "
                    "finish a task, reduce unneeded white space, make the layout adapt to all screen sizes and aspect "
                    "ratios, and make less-used features easier to find, as the IT experts and user respondents "
                    "suggested. In the longer term, billing and inventory modules can be added, as one IT expert noted.")
    abstract_eval = (f"The system was evaluated through two online forms answered on a four-point scale. The six "
                     f"ISO/IEC 25010 quality characteristics (security, privacy, usability, reliability, performance "
                     f"efficiency, and data protection), rated by {n_itx} IT experts, obtained an overall weighted mean "
                     f"of {f2(q_mean)}, and the system's detection, results, and prevention-plan features, rated by {N} "
                     f"user respondents ({nPT} patient respondents and {nIT} IT practitioners), obtained "
                     f"{f2(feat_mean)}; both are interpreted as Highly Acceptable.")

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
        f"P This section describes how the acceptability of Toothwise was evaluated (the fourth problem of the "
        f"study, with supporting information for the fifth): who the respondents were, the instrument they answered, how the data were gathered, and "
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

    # Appendices: A letter, B image-level results (hand-maintained), C feedback, D IT expert results.
    app = []
    app.append("#APP APPENDIX A | Letter of Approval from CodiSmile Dental Clinic")
    app.append("FIG letter1 | appendix_letter_1.png | 5.4 | Letter Requesting Approval to Conduct the Study (page 1 of 2)")
    app.append("FIG letter2 | appendix_letter_2.png | 5.4 | Letter Requesting Approval to Conduct the Study (page 2 of 2)")
    app.append("#APP APPENDIX C | Evaluator Feedback and Panel Consultation")
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

    app.append("#APP APPENDIX D | IT Expert Evaluation Results")
    app.append("P The table gives, for every statement of the IT Expert Evaluation Form, how many of the IT experts "
               "chose each rating and the weighted mean (WM); the statements are listed in Tables {tab:se} to "
               "{tab:dp}. The figures show the response summary from Google Forms, with the evaluators' names "
               "blurred, followed by the experts' written comments.")
    app.append("TABLE freqit | Frequency Distribution of the IT Experts' Ratings")
    app.append("W 0.6,0.8,0.65,0.75,0.75,0.8,0.55")
    app.append("| Code | Strongly Agree (4) | Agree (3) | Disagree (2) | Strongly Disagree (1) | N | WM |")
    for c, (_, xs) in IT_ITEMS.items():
        app.append(f"| {c} | {xs.count(4)} | {xs.count(3)} | {xs.count(2)} | {xs.count(1)} | {len(xs)} | "
                   f"{f2(st.mean(xs))} |")
    app.append("ENDTABLE")
    app.append("FIGPAIR res_prof | results_it_profile.png | 2.95 | IT Expert Form Results — Evaluator Profile | "
               "|| res_q1 | results_it_quality_1.png | 2.95 | IT Expert Form Results — Security, Privacy, and Usability | ")
    app.append("FIGPAIR res_q2 | results_it_quality_2.png | 2.95 | IT Expert Form Results — Reliability, Performance "
               "Efficiency, and Data Protection | || res_com | results_it_comments.png | 2.95 | IT Expert Form "
               "Results — Comments and Recommendations | ")
    app.append("PN **Comments and recommendations, as written**")
    for q, ans in IT_COMMENTS.items():
        app.append(f"PN *{q}*")
        for k, v in enumerate(ans, 1):
            app.append(f"- IT expert {k}: “{v}”")

    text = CONTENT.read_text(encoding="utf-8")
    # Section 4.4, Chapter V, the abstract, and Appendix D are maintained by hand in content.txt; only
    # the survey-dependent sentences in them are replaced here.
    a = text.index("The system was evaluated through")
    b = text.index("Highly Acceptable.", a) + len("Highly Acceptable.")
    text = text[:a] + abstract_eval + text[b:]
    hand = [
        (r"The \d+ respondents who rated the quality characteristics gave Performance Efficiency a mean of [\d.]+ "
         r"and Reliability [\d.]+, both Highly Acceptable \(Section 4.3\)\.",
         f"The {n_itx} IT experts rated Performance Efficiency {f2(itS['Performance Efficiency']['wm'])} and "
         f"Reliability {f2(itS['Reliability']['wm'])}, both Highly Acceptable (Section 4.3)."),
        (r"Respondents rated Performance Efficiency [\d.]+ and Reliability [\d.]+ \(Highly Acceptable\)\.",
         f"The IT experts rated Performance Efficiency {f2(itS['Performance Efficiency']['wm'])} and Reliability "
         f"{f2(itS['Reliability']['wm'])} (Highly Acceptable)."),
        (r"(?m)^4\. \*\*Acceptability \(Problem 4\)\.\*\*.*$", finding4),
        (r"(?m)^5\. Toothwise is highly acceptable to its evaluators.*$", conclusion5),
        (r"(?m)^5\. Simplify pages that present much information at once.*$",
         "5. " + rec_simplify),
    ]
    for pat, rep in hand:
        text, k = re.subn(pat, lambda m: rep, text)
        assert k == 1, pat
    # Chapter III evaluation procedure
    a = text.index("## 3.10 Evaluation Procedure")
    b = text.index("## 3.11 Full Current System Screenshots")
    text = text[:a] + "## 3.10 Evaluation Procedure\n" + "\n".join(ch3) + "\n\n" + text[b:]
    # Section 4.3 (Section 4.4 onward is kept)
    a = text.index("## 4.3 Software Quality Evaluation")
    b = text.index("## 4.4 ")
    text = text[:a] + "\n".join(L) + "\n\n" + text[b:]
    # appendices: generated A-C, hand-maintained D (image-level results), generated E onward
    a = text.find("#APP ")
    d0 = re.search(r"#APP APPENDIX [A-Z] \| Detailed Image-Level", text).start()
    d1 = text.find("#APP ", d0 + 5)
    app_d = text[d0:d1 if d1 > 0 else len(text)].rstrip("\n").split("\n")
    app_d[0] = re.sub(r"APPENDIX [A-Z] \|", "APPENDIX B |", app_d[0])
    text = re.sub(r"\bAppendix D\b", "Appendix B", text)     # references to the image-level appendix
    k = app.index(next(x for x in app if x.startswith("#APP APPENDIX C |")))
    app = app[:k] + app_d + app[k:]
    text = text[:a].rstrip("\n") + "\n\n" + "\n".join(app) + "\n"
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
