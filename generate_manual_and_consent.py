"""
Generates the ToothWise User Manual and Patient Consent Form .docx files,
matching the formatting of TOOTHWISE_CAPSTONE_DOCUMENTATION_FORMATTED.docx:
  Letter page; margins L 1.5in / R 1in / T 1.5in / B 1in;
  Normal = Book Antiqua 12pt; Heading 1 = Tahoma 22pt bold.

House rules from the paper's own style notes are enforced by a final check:
  no first person (we / i / you / our / us), no contractions.
Run:  .venv\\Scripts\\python.exe generate_manual_and_consent.py
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor

OUT_DIR = Path(__file__).resolve().parent
BODY_FONT = "Book Antiqua"
HEAD_FONT = "Tahoma"
ACCENT = RGBColor(0x5C, 0x2D, 0x4E)


# ---------------------------------------------------------------- format bits
def configure(doc):
    s = doc.sections[0]
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.left_margin, s.right_margin = Inches(1.5), Inches(1)
    s.top_margin, s.bottom_margin = Inches(1.5), Inches(1)

    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(6)
    _force_font(normal, BODY_FONT)

    spec = {"Heading 1": (HEAD_FONT, 22), "Heading 2": (BODY_FONT, 14),
            "Heading 3": (BODY_FONT, 12.5), "Heading 4": (BODY_FONT, 12)}
    for name, (font, size) in spec.items():
        st = doc.styles[name]
        st.font.name, st.font.size, st.font.bold = font, Pt(size), True
        st.font.color.rgb = ACCENT
        _force_font(st, font)


def _force_font(style, font_name):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(attr), font_name)


def add_page_numbers(doc):
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(fld)
    run._r.append(instr)
    run._r.append(end)


def add_toc(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = 'Right-click and choose "Update Field" to generate the table of contents.'
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, placeholder, end):
        run._r.append(el)


# ---------------------------------------------------------------- text helpers
def h(doc, text, level=1):
    doc.add_heading(text, level=level)


def p(doc, text="", bold=False, italic=False, align=None, size=None):
    para = doc.add_paragraph()
    if align is not None:
        para.alignment = align
    run = para.add_run(text)
    run.bold, run.italic = bold, italic
    if size:
        run.font.size = Pt(size)
    return para


def bullet(doc, text):
    doc.add_paragraph(text, style="List Bullet")


def numbered(doc, text):
    doc.add_paragraph(text, style="List Number")


def kv(doc, label, value):
    para = doc.add_paragraph()
    para.add_run(f"{label}: ").bold = True
    para.add_run(value)


def ref(doc, label):
    para = doc.add_paragraph()
    para.add_run(label + "  ").bold = True
    para.add_run("_" * 40)
    return para


def sign_line(doc, label, width=42):
    para = doc.add_paragraph()
    para.add_run(label + "  ").bold = True
    para.add_run("_" * width)


def cover(doc, title_lines, appendix):
    p(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER)
    for i, line in enumerate(title_lines):
        size = 16 if i == 0 else 13
        p(doc, line, bold=(i == 0), align=WD_ALIGN_PARAGRAPH.CENTER, size=size)
    doc.add_paragraph()
    p(doc, appendix, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=13)
    doc.add_page_break()


# ---------------------------------------------------------------- user manual
def build_manual():
    doc = Document()
    configure(doc)
    add_page_numbers(doc)

    cover(doc, [
        "TOOTHWISE",
        "Teeth Cavity Detection with Recommendation System Using YOLOv12",
        "for CodiSmile Dental Clinic",
        "USER MANUAL",
        "Version 1.0",
        "Prepared for: CodiSmile Dental Clinic",
        "Universidad de Manila",
    ], "Appendix D")

    p(doc, "Table of Contents", bold=True, size=14)
    add_toc(doc)
    doc.add_page_break()

    # 1
    h(doc, "1  Introduction")
    h(doc, "1.1  Purpose of This Manual", 2)
    p(doc, "This manual explains how to operate the ToothWise system, from signing in "
           "and registering a patient to running an AI-assisted dental screening and "
           "producing a clinical report. It is written for CodiSmile Dental Clinic staff "
           "and for patients who use the patient portal.")
    h(doc, "1.2  About ToothWise", 2)
    p(doc, "ToothWise is a web-based dental screening system that uses a YOLOv12 object "
           "detection model to identify common dental conditions from an intraoral "
           "photograph, computes a rule-based clinical risk score, and generates a "
           "prevention plan together with a downloadable PDF report. Detection results "
           "are intended to assist, not replace, an in-person examination by a licensed "
           "dentist.")
    h(doc, "1.3  Intended Users and Roles", 2)
    bullet(doc, "Clinic staff (dentist). Registers patients, runs screenings, reviews "
                "results, records notes, and downloads reports.")
    bullet(doc, "Administrator. Performs all staff functions and, in addition, manages "
                "staff accounts and reviews the audit trail.")
    bullet(doc, "Patient. Uses the patient portal to register, sign in, and review "
                "personal screening history and results.")
    h(doc, "1.4  System Requirements", 2)
    bullet(doc, "A modern web browser such as Google Chrome, Microsoft Edge, or Mozilla "
                "Firefox, updated to a recent version.")
    bullet(doc, "A stable internet connection to reach the hosted application.")
    bullet(doc, "An intraoral dental photograph in a common image format (JPG or PNG). "
                "The upload limit is 15 MB per image.")
    bullet(doc, "A screen resolution of at least 1024 x 768 pixels. The interface adapts "
                "to mobile screens, but a desktop or tablet is recommended for screening.")
    h(doc, "1.5  Glossary of Terms", 2)
    kv(doc, "Screening", "A single AI-assisted analysis of one dental image for one patient.")
    kv(doc, "Detection", "A single condition found in an image, reported with a label and "
                         "a confidence value.")
    kv(doc, "Risk score", "A clinical risk value from 0 to 100 derived from the findings.")
    kv(doc, "Risk level", "The category of the risk score, shown as LOW, MEDIUM, or HIGH.")
    kv(doc, "Fused detection", "The combined clinical result used across the application, "
                               "shown in reports and summaries.")

    # 2
    h(doc, "2  Getting Started")
    h(doc, "2.1  Accessing the System", 2)
    p(doc, "ToothWise is accessed through a web browser. Open the clinic-provided address "
           "in the browser. The landing page presents two entry points: Staff Sign-In for "
           "clinic personnel and a Patient Portal for patients. The landing page also "
           "lists the clinic services and contact details.")
    h(doc, "2.2  Staff Sign-In", 2)
    numbered(doc, "Open the landing page and choose Staff Sign-In.")
    numbered(doc, "Enter the registered staff email address and password.")
    numbered(doc, "Choose Sign In. A successful sign-in opens the workspace dashboard.")
    p(doc, "If the email address or password is incorrect, a message advises the user to "
           "check the credentials. Repeated failed attempts are rate-limited for security.")
    h(doc, "2.3  Patient Portal Sign-In", 2)
    p(doc, "Patients sign in through the Patient Portal using the email address and "
           "password created during registration. A new patient creates an account first; "
           "see Section 6.")
    h(doc, "2.4  Understanding the Workspace", 2)
    p(doc, "The workspace has a navigation sidebar on the left and a top bar. The sidebar "
           "contains Overview, Patients, and, for administrators, Staff and Audit trail. "
           "The bottom of the sidebar shows the signed-in staff member and the Sign Out "
           "control. A button collapses the sidebar to a narrow icon rail, which is useful "
           "on smaller screens.")
    p(doc, "The top bar contains the notification bell, the global patient search, and the "
           "theme toggle. Breadcrumbs below the top bar show the current location, for "
           "example Patients / Screening.")
    h(doc, "2.5  Light and Dark Mode", 2)
    p(doc, "Choose the moon or sun icon in the top bar to switch between light and dark "
           "mode. The selected theme is remembered on the device.")
    h(doc, "2.6  Signing Out", 2)
    p(doc, "Choose Sign Out at the bottom of the sidebar to end the session. The system "
           "returns to the sign-in page, and the saved pages are cleared so that clinical "
           "data is not left visible on a shared computer.")

    # 3
    h(doc, "3  Dashboard Overview")
    h(doc, "3.1  Summary Cards", 2)
    p(doc, "The Overview page opens with summary cards that show key clinic figures, "
           "including the total number of patients, screenings recorded today, and the "
           "number of high-risk cases that require attention.")
    h(doc, "3.2  Charts and Activity", 2)
    p(doc, "Below the cards, charts summarize screening activity and the distribution of "
           "findings over time. These views provide a quick picture of clinic workload and "
           "of recurring conditions.")
    h(doc, "3.3  Global Search", 2)
    p(doc, "Choose the search icon in the top bar and type a name, patient ID, email "
           "address, or contact number. Matching patient records appear as a list; "
           "selecting a result opens that patient record directly.")
    h(doc, "3.4  Notifications", 2)
    p(doc, "Choose the bell icon to view clinic activity, such as new high-risk cases or "
           "screenings recorded today. A dot on the bell indicates unread notifications.")
    h(doc, "3.5  Quick Actions", 2)
    p(doc, "Common tasks, such as opening the patient directory or starting a new "
           "screening, are reachable from the Overview page and from the Patients page.")

    # 4
    h(doc, "4  Patient Management")
    h(doc, "4.1  Viewing the Patient Directory", 2)
    p(doc, "Choose Patients in the sidebar to open the patient directory. The directory "
           "lists each patient with identifying details, the number of screenings on "
           "record, and the most recent risk level.")
    h(doc, "4.2  Registering a New Patient", 2)
    numbered(doc, "On the Patients page, choose the option to add a new patient.")
    numbered(doc, "Enter the patient first name, middle name, and last name.")
    numbered(doc, "Enter the age, gender, contact number, and email address.")
    numbered(doc, "Choose Save. The new patient appears in the directory and the action "
                  "is written to the audit trail.")
    h(doc, "4.3  Searching and Filtering Patients", 2)
    p(doc, "Use the search box on the Patients page, or the global search in the top bar, "
           "to find a patient by name, patient ID, email address, or contact number.")
    h(doc, "4.4  Opening a Patient Record", 2)
    p(doc, "Select a patient row to open the patient record. The record shows the patient "
           "details, the screening history, and a risk-trend chart that plots the risk "
           "score across screenings over time.")
    h(doc, "4.5  Editing a Patient Record", 2)
    p(doc, "Open the patient record and choose Edit. Update the required fields and choose "
           "Save. Changes to the name fields update the displayed full name automatically.")
    h(doc, "4.6  Deleting a Patient Record", 2)
    p(doc, "Open the patient record and choose Delete. A confirmation is required before "
           "the record is removed. Deleted records are recorded in the audit trail. "
           "Deletion is restricted because the action is permanent.")
    h(doc, "4.7  Appointment Confirmation Email", 2)
    p(doc, "When the clinic configures mail delivery, the system sends an appointment "
           "confirmation message to the patient. When mail delivery is not configured, "
           "the message is written to the application log instead, and no email is sent.")

    # 5
    h(doc, "5  Dental Screening Workflow")
    h(doc, "5.1  Starting a Screening", 2)
    p(doc, "A screening always belongs to one patient. Open the patient record, choose "
           "the option to start a new screening, or start one from the Patients page for "
           "the selected patient.")
    h(doc, "5.2  Step 1 - Uploading a Dental Image", 2)
    numbered(doc, "Accept the on-screen guidance on image quality and consent.")
    numbered(doc, "Choose the upload area, or drag and drop an intraoral photograph into "
                  "it.")
    numbered(doc, "Confirm that the uploaded image is correct.")
    p(doc, "Use a clear, well-lit, close-up photograph of the teeth. The maximum file size "
           "is 15 MB. Images in JPG or PNG format are supported.")
    h(doc, "5.3  Step 2 - Previewing and Confirming", 2)
    p(doc, "The uploaded image is displayed for review. Confirm the image, or replace it, "
           "before running detection. This step prevents analysis of the wrong photograph.")
    h(doc, "5.4  Step 3 - Running AI Detection", 2)
    p(doc, "Choose Run Detection. The system processes the image and then shows the "
           "results. Processing may take a few seconds. If AI detection is turned off by "
           "the clinic administrator, the system shows a message that screening is "
           "temporarily unavailable.")
    h(doc, "5.5  Reading the Results", 2)
    p(doc, "The results view shows the annotated image with labelled bounding boxes, the "
           "risk summary, a breakdown of findings, and the prevention plan.")
    bullet(doc, "The risk panel shows the risk level and the risk score, for example "
                "RISK LEVEL: HIGH - Score: 100/100.")
    bullet(doc, "The finding list shows each detected condition with its confidence "
                "percentage.")
    bullet(doc, "The annotated image shows each finding within a colour-coded box.")
    h(doc, "5.6  Understanding the Risk Score", 2)
    p(doc, "The risk score ranges from 0 to 100. It is derived from the most severe finding "
           "in the image, weighted by the confidence of the detection, with a small "
           "increase for each additional finding. The score is mapped to a risk level:")
    kv(doc, "LOW", "a score below 35.")
    kv(doc, "MEDIUM", "a score from 35 up to 69.")
    kv(doc, "HIGH", "a score of 70 or above.")
    p(doc, "A score of zero with the LOW level means that no concerning findings were "
           "detected on the image.")
    h(doc, "5.7  Detection Classes and Colour Legend", 2)
    p(doc, "The system recognizes five classes. Each class has a fixed colour used in the "
           "bounding-box overlay:")
    kv(doc, "Healthy tooth (green)", "no issue detected on the tooth.")
    kv(doc, "Plaque (amber)", "soft deposit requiring improved oral hygiene.")
    kv(doc, "Tartar (dark amber)", "hardened deposit requiring professional scaling.")
    kv(doc, "Gum inflammation (pink)", "inflamed gum tissue requiring assessment.")
    kv(doc, "Cavity (red)", "tooth decay requiring dental treatment.")
    h(doc, "5.8  Prevention Plan", 2)
    p(doc, "The system produces a prevention plan tailored to the detected findings. "
           "Recommendations of higher urgency are marked as URGENT at the start of the "
           "line. General oral-health guidance accompanies the finding-specific advice.")
    h(doc, "5.9  Adding Clinical Notes", 2)
    p(doc, "On the screening result, add clinical notes to record observations or "
           "follow-up actions. Notes are saved with the screening and are included in the "
           "PDF report. Each note is stamped with the date and time it was added.")
    h(doc, "5.10  Downloading the PDF Report", 2)
    p(doc, "Choose the download option to produce a PDF clinical report for the screening. "
           "The report contains the patient details, the screening date and identifier, "
           "the risk summary, the screening image, a table of detected findings with "
           "confidence values, the prevention plan, and any clinical notes. A disclaimer "
           "states that the report is generated by an AI-assisted tool and is not a "
           "substitute for an in-person examination.")
    h(doc, "5.11  Screening History and Risk Trend", 2)
    p(doc, "Every screening is saved to the patient record. The patient record lists all "
           "screenings in date order and displays a risk-trend chart, which helps the "
           "dentist observe whether the patient condition is improving or worsening over "
           "time.")

    # 6
    h(doc, "6  Patient Portal")
    h(doc, "6.1  Creating a Patient Account", 2)
    numbered(doc, "On the landing page, open the Patient Portal.")
    numbered(doc, "Choose the option to register a new account.")
    numbered(doc, "Enter the required personal details, an email address, and a password.")
    numbered(doc, "Submit the registration. The account is then ready for sign-in.")
    h(doc, "6.2  Signing In to the Portal", 2)
    p(doc, "Enter the registered email address and password, then choose Sign In. The "
           "portal shows the patient personal screening history.")
    h(doc, "6.3  Viewing Screening History", 2)
    p(doc, "The portal lists each screening with its date, risk level, and risk score, "
           "most recent first.")
    h(doc, "6.4  Viewing a Screening Result", 2)
    p(doc, "Select a screening to view its details, including the annotated image, the "
           "detected findings, and the prevention plan. Patients can review results at "
           "any time.")
    h(doc, "6.5  Using the AI Assistant", 2)
    p(doc, "An AI assistant is available from the chat button. The assistant answers "
           "general questions about oral health and about using the portal, and it does "
           "not replace professional dental advice.")

    # 7
    h(doc, "7  Administrative Functions")
    p(doc, "The functions in this section are available only to accounts with the "
           "administrator role.")
    h(doc, "7.1  Managing Staff Accounts", 2)
    p(doc, "Choose Staff in the sidebar to view clinic staff accounts. From this page, an "
           "administrator adds new staff, assigns the role, and updates or removes "
           "accounts. Every change is recorded in the audit trail.")
    h(doc, "7.2  Audit Trail", 2)
    p(doc, "Choose Audit trail in the sidebar to review a record of sensitive actions, "
           "including sign-ins, patient changes, staff changes, and screening activity. "
           "Each entry shows who performed the action, what was done, and when. The audit "
           "trail supports accountability and privacy compliance.")
    h(doc, "7.3  Roles and Permissions", 2)
    kv(doc, "Staff", "patient management and screenings.")
    kv(doc, "Administrator", "all staff functions, plus staff management and the audit "
                             "trail.")
    p(doc, "Restricted pages are hidden from accounts that do not hold the required role, "
           "and access is also enforced by the server.")

    # 8
    h(doc, "8  AI Assistant")
    h(doc, "8.1  What the Assistant Does", 2)
    p(doc, "The AI assistant is a chat helper that answers general questions about oral "
           "health and about using ToothWise. It is designed for guidance only and does "
           "not provide a diagnosis.")
    h(doc, "8.2  How to Use the Assistant", 2)
    numbered(doc, "Choose the chat button in the corner of the screen.")
    numbered(doc, "Type a question in the message box and send it.")
    numbered(doc, "Read the reply and continue the conversation as needed.")

    # 9
    h(doc, "9  Data Privacy and Security")
    h(doc, "9.1  Personal Data Protection", 2)
    p(doc, "ToothWise processes personal and health information. The system is operated in "
           "accordance with the Data Privacy Act of 2012 (Republic Act No. 10173) and its "
           "implementing rules. The clinic collects only the data required for screening "
           "and record keeping.")
    h(doc, "9.2  Access Control", 2)
    p(doc, "Access to patient data requires a valid sign-in. Passwords are stored in "
           "hashed form and are never displayed. Restricted functions require the "
           "appropriate role.")
    h(doc, "9.3  Records and Monitoring", 2)
    p(doc, "Sensitive actions are recorded in the audit trail, and clinical data is not "
           "stored in the browser cache, so that patient information is not left visible "
           "on a shared computer.")

    # 10
    h(doc, "10  Troubleshooting and Frequently Asked Questions")
    h(doc, "10.1  General Troubleshooting", 2)
    kv(doc, "The sign-in fails",
        "confirm the email address and password. After several failed attempts, the "
        "system briefly limits further attempts; wait a moment and try again.")
    kv(doc, "The screening shows that detection is unavailable",
        "AI detection has been turned off by the administrator. Contact the clinic "
        "administrator.")
    kv(doc, "The image does not upload",
        "confirm that the file is a JPG or PNG image and that it is no larger than 15 MB.")
    kv(doc, "The results do not appear",
        "wait a few seconds and try again. If the problem continues, confirm the internet "
        "connection.")
    kv(doc, "A page appears blank after signing in",
        "reload the page. Saved pages are cleared for privacy, so the session may need to "
        "be re-opened.")
    h(doc, "10.2  Frequently Asked Questions", 2)
    kv(doc, "Is ToothWise a replacement for a dentist?",
        "No. ToothWise assists screening. A licensed dentist confirms every result.")
    kv(doc, "Which image works best?",
        "A clear, well-lit, close-up intraoral photograph works best.")
    kv(doc, "Can a patient see the result immediately?",
        "Yes. A patient can review results through the patient portal after screening.")
    kv(doc, "Where is the report saved?",
        "The report is downloaded as a PDF file, and the screening is stored in the "
        "patient record.")
    kv(doc, "Who can delete a patient record?",
        "Clinic staff can delete a record, and every deletion is recorded in the audit "
        "trail.")

    # 11
    h(doc, "11  Support and Contact Information")
    p(doc, "For assistance with ToothWise, contact CodiSmile Dental Clinic:")
    kv(doc, "Clinic", "CodiSmile Dental Clinic")
    kv(doc, "Email", "support@codismile.com")
    kv(doc, "Support hours", "Monday to Friday, 9:00 AM to 5:00 PM")
    p(doc, "When reporting an issue, include the patient identifier or screening "
           "identifier, the page in use, and a short description of what happened.")

    out = OUT_DIR / "ToothWise_User_Manual.docx"
    doc.save(out)
    return out


# ---------------------------------------------------------------- consent form
def build_consent():
    doc = Document()
    configure(doc)
    add_page_numbers(doc)

    cover(doc, [
        "TOOTHWISE",
        "Teeth Cavity Detection with Recommendation System Using YOLOv12",
        "for CodiSmile Dental Clinic",
        "PATIENT CONSENT FORM",
        "AI-Assisted Dental Screening",
        "Version 1.0",
        "Universidad de Manila",
    ], "Appendix E")

    h(doc, "Patient Consent Form for AI-Assisted Dental Screening")
    p(doc, "This form records the informed consent of the patient for dental screening "
           "performed with the assistance of the ToothWise system at CodiSmile Dental "
           "Clinic. Please read this form carefully before signing.")

    h(doc, "1  Purpose of This Form", 2)
    p(doc, "The purpose of this form is to explain how ToothWise works, what information "
           "is collected, how the information is used and protected, and the rights of "
           "the patient, so that the patient can decide, freely and voluntarily, whether "
           "to provide consent.")

    h(doc, "2  Description of the ToothWise System", 2)
    p(doc, "ToothWise is a web-based dental screening system. It analyzes an intraoral "
           "photograph with an artificial intelligence model, reports any detected "
           "dental conditions, computes a clinical risk score, and produces a prevention "
           "plan and a screening report. The result supports, and does not replace, the "
           "judgment of a licensed dentist.")

    h(doc, "3  Nature of AI-Assisted Screening and Its Limitations", 2)
    p(doc, "The system provides an automated assessment based on an image. Artificial "
           "intelligence results may be incomplete or incorrect, and image quality "
           "affects accuracy. Every result is reviewed by a licensed dentist. A clinical "
           "examination remains necessary to confirm any finding and to decide on "
           "treatment.")

    h(doc, "4  Information Collected and Processed", 2)
    p(doc, "The following information is collected and processed for screening and record "
           "keeping:")
    bullet(doc, "Identifying information, such as name, age, and gender.")
    bullet(doc, "Contact information, such as contact number and email address.")
    bullet(doc, "The intraoral dental photograph submitted for screening.")
    bullet(doc, "The screening results, the risk score, and the prevention plan.")
    bullet(doc, "Clinical notes recorded by the dentist, if any.")

    h(doc, "5  Purpose of Processing", 2)
    p(doc, "The information is processed to perform the dental screening, to prepare the "
           "screening report, to maintain the patient dental record, and to support "
           "follow-up care. The information is not used for any other purpose without "
           "further consent.")

    h(doc, "6  Data Privacy", 2)
    p(doc, "The patient information is processed in accordance with the Data Privacy Act "
           "of 2012 (Republic Act No. 10173) and its implementing rules. The patient has "
           "the right to be informed, the right to access, the right to correct, the "
           "right to object, and the right to erasure of personal data, subject to legal "
           "and clinical retention requirements.")

    h(doc, "7  Storage, Retention, and Security", 2)
    p(doc, "Records are stored in the clinic system and are protected by access controls. "
           "Access requires a valid sign-in, passwords are stored in hashed form, and "
           "sensitive actions are recorded in an audit trail. Records are retained only "
           "for as long as required for clinical and legal purposes.")

    h(doc, "8  Access and Disclosure", 2)
    p(doc, "Patient information is accessed by authorized clinic staff for screening and "
           "care. Information is not disclosed to third parties except with the consent "
           "of the patient or when required by law.")

    h(doc, "9  Risks and Benefits", 2)
    p(doc, "Benefits: early detection of dental conditions, a documented screening "
           "record, and a prevention plan that supports timely care.")
    p(doc, "Risks: an automated result may be incomplete or incorrect; an image may be of "
           "low quality; and the processing of personal and health information carries "
           "an inherent privacy risk, which the clinic manages through the safeguards "
           "described above.")

    h(doc, "10  Voluntariness and Right to Withdraw", 2)
    p(doc, "Providing consent is voluntary. The patient may refuse or withdraw consent "
           "at any time, without penalty and without affecting the right to dental care. "
           "On withdrawal, the clinic stops further processing, and the patient may "
           "request deletion of the data, subject to legal and clinical retention "
           "requirements.")

    h(doc, "11  Clinical Disclaimer", 2)
    p(doc, "The ToothWise result is an AI-assisted screening outcome. It is not a "
           "diagnosis and is not a substitute for an in-person examination by a licensed "
           "dentist. The patient should consult a licensed dentist before making any "
           "treatment decision.")

    h(doc, "12  Consent Statement", 2)
    p(doc, "By signing below, the patient confirms the following:")
    bullet(doc, "The purpose of the AI-assisted screening and the nature of the ToothWise "
                "system have been explained, and the explanation is understood.")
    bullet(doc, "The information to be collected, and the purpose of processing, have "
                "been explained, and the explanation is understood.")
    bullet(doc, "The limitations of an AI-assisted result have been explained, and the "
                "explanation is understood.")
    bullet(doc, "Consent is given freely and voluntarily for dental screening with "
                "ToothWise and for the processing of the related personal information.")
    p(doc, "Patient response (check one):")
    p(doc, "[   ]  Consent is given.        [   ]  Consent is not given.")

    h(doc, "13  Patient Declaration and Signature", 2)
    sign_line(doc, "Patient name (printed)")
    sign_line(doc, "Patient date of birth")
    sign_line(doc, "Patient signature")
    sign_line(doc, "Date")
    sign_line(doc, "Patient identifier")

    h(doc, "14  Consent for a Minor or a Patient Unable to Consent", 2)
    p(doc, "If the patient is a minor or is unable to provide consent, the parent or legal "
           "guardian signs below. The relationship to the patient is stated.")
    sign_line(doc, "Parent or guardian name (printed)")
    sign_line(doc, "Relationship to patient")
    sign_line(doc, "Signature")
    sign_line(doc, "Date")

    h(doc, "15  Explanation Provided By (Clinic Staff)", 2)
    p(doc, "The undersigned clinic staff member confirms that this form was explained to "
           "the patient, or to the parent or guardian, before it was signed.")
    sign_line(doc, "Staff name (printed)")
    sign_line(doc, "Role or position")
    sign_line(doc, "Signature")
    sign_line(doc, "Date")

    h(doc, "16  Witness (Optional)", 2)
    sign_line(doc, "Witness name (printed)")
    sign_line(doc, "Signature")
    sign_line(doc, "Date")

    h(doc, "17  Contact and Data Protection Officer", 2)
    p(doc, "Questions about this form, or about personal data, may be directed to the "
           "clinic:")
    kv(doc, "Clinic", "CodiSmile Dental Clinic")
    kv(doc, "Email", "support@codismile.com")
    kv(doc, "Contact number", "____________________")

    out = OUT_DIR / "ToothWise_Patient_Consent_Form.docx"
    doc.save(out)
    return out


# ---------------------------------------------------------------- verification
FORBIDDEN = re.compile(r"\b(we|our|ours|i|you|your|yours|us)\b", re.IGNORECASE)
CONTRACTION = re.compile(r"\b\w+'(t|s|re|ve|ll|d|m)\b", re.IGNORECASE)


def check(path):
    doc = Document(path)
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    bad = []
    for text in paras:
        # Skip the intentional TOC field placeholder and checkbox glyphs.
        if "Update Field" in text:
            continue
        if FORBIDDEN.search(text):
            bad.append(("first-person", text))
        if CONTRACTION.search(text):
            bad.append(("contraction", text))
    return len(paras), bad


def main():
    manual = build_manual()
    consent = build_consent()
    for path in (manual, consent):
        count, bad = check(path)
        print(f"{path.name}: {count} paragraphs, {path.stat().st_size} bytes")
        assert count > 40, "document looks empty"
        for kind, text in bad:
            print(f"  WARN [{kind}] {text[:90]}")


if __name__ == "__main__":
    main()
