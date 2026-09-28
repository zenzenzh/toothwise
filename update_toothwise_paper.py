from copy import deepcopy
from io import BytesIO
from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Inches, Pt
from docx.oxml.text.paragraph import CT_P
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\zenn\toothwise")
SOURCE = ROOT / "ToothWise_Final_Paper_Ch1-4_Revised_SOP_Objectives.docx"
OUTPUT = ROOT / "ToothWise_Final_Paper_Ch1-4_Updated_Methodology.docx"
USECASE_PNG = ROOT / "toothwise_use_case.png"
DFD_PNG = ROOT / "toothwise_dfd_level0.png"
AGILE_PNG = ROOT / "toothwise_agile_development.png"

INK = "#000000"
BLUE = "#000000"
PALE = "#FFFFFF"
MINT = "#FFFFFF"
GRAY = "#333333"
WHITE = "#FFFFFF"


def font(size, bold=False):
    path = r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def centered_text(draw, box, text, fnt, fill=INK, max_width=None, gap=8):
    x1, y1, x2, y2 = box
    max_width = max_width or (x2 - x1 - 28)
    lines = []
    for source_line in text.splitlines() or [text]:
        lines.extend(wrap(draw, source_line, fnt, max_width) if source_line else [""])
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for line, h in zip(lines, heights):
        w = draw.textbbox((0, 0), line, font=fnt)[2]
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=fnt, fill=fill)
        y += h + gap


def rounded(draw, box, fill, outline=BLUE, radius=22, width=4):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def actor(draw, center, label):
    x, y = center
    draw.ellipse((x - 30, y - 92, x + 30, y - 32), fill=WHITE, outline=INK, width=5)
    draw.line((x, y - 32, x, y + 55), fill=INK, width=5)
    draw.line((x - 50, y - 2, x + 50, y - 2), fill=INK, width=5)
    draw.line((x, y + 55, x - 42, y + 115), fill=INK, width=5)
    draw.line((x, y + 55, x + 42, y + 115), fill=INK, width=5)
    centered_text(draw, (x - 190, y + 120, x + 190, y + 205), label, font(46, True), INK)


def arrow(draw, points, fill=BLUE, width=4, head=15):
    draw.line(points, fill=fill, width=width, joint="curve")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - 0.45), y2 - head * math.sin(a - 0.45))
    p2 = (x2 - head * math.cos(a + 0.45), y2 - head * math.sin(a + 0.45))
    draw.polygon([(x2, y2), p1, p2], fill=fill)


def create_use_case(path):
    """UML use-case diagram: actors outside, system boundary inside, plain associations."""
    im = Image.new("RGB", (2700, 1320), WHITE)
    d = ImageDraw.Draw(im)
    d.text((110, 35), "TOOTHWISE USE CASE DIAGRAM", font=font(64, True), fill=INK)
    boundary = (420, 150, 2280, 1230)
    d.rectangle(boundary, outline=INK, width=6)
    centered_text(d, (450, 160, 2250, 225), "ToothWise Dental Screening and Patient Portal", font(46, True), INK)

    cases = [
        (850, 270, 1510, 355, "Log in and authenticate", "staff"),
        (850, 415, 1510, 500, "Manage patient records", "staff"),
        (850, 560, 1510, 645, "Capture or upload image", "staff"),
        (850, 705, 1510, 790, "Run AI screening", "staff"),
        (850, 850, 1510, 935, "Review findings and risk", "staff"),
        (850, 995, 1510, 1080, "Add clinical note and generate report", "staff"),
        (500, 390, 800, 475, "Manage staff accounts", "admin"),
        (500, 540, 800, 625, "Review audit log", "admin"),
        (1600, 830, 2200, 915, "View own screening history", "patient"),
        (1600, 980, 2200, 1065, "Ask screening assistant", "patient"),
    ]
    for x1, y1, x2, y2, label, _role in cases:
        d.ellipse((x1, y1, x2, y2), fill=WHITE, outline=INK, width=4)
        centered_text(d, (x1, y1, x2, y2), label, font(30, True), INK, max_width=x2-x1-36)

    # Administrator specializes the dentist actor and inherits its shared use cases.
    admin, dentist, patient = (205, 300), (205, 800), (2500, 940)
    actor(d, admin, "Administrator")
    actor(d, dentist, "Dentist")
    actor(d, patient, "Patient")
    # UML generalization uses an open triangle pointed toward the parent actor.
    d.line((285, 300, 390, 300), fill=INK, width=4)
    d.line((390, 300, 390, 650), fill=INK, width=4)
    d.line((390, 650, 205, 650), fill=INK, width=4)
    d.line((180, 650, 205, 700), fill=INK, width=4)
    d.line((230, 650, 205, 700), fill=INK, width=4)
    d.line((180, 650, 230, 650), fill=INK, width=4)
    for target in [(850, 312), (850, 457), (850, 602), (850, 747), (850, 892), (850, 1037)]:
        d.line((285, dentist[1], *target), fill=INK, width=3)
    for target in [(500, 432), (500, 582)]:
        d.line((285, admin[1], *target), fill=INK, width=3)
    for target in [(2200, 872), (2200, 1022)]:
        d.line((patient[0] - 75, patient[1], *target), fill=INK, width=3)
    im.save(path, dpi=(220, 220))


def entity(draw, box, title, subtitle=""):
    # Gane and Sarson external entity: a double-bordered rectangle.
    draw.rectangle(box, fill=WHITE, outline=INK, width=5)
    x1, y1, x2, y2 = box
    draw.rectangle((x1 + 12, y1 + 12, x2 - 12, y2 - 12), outline=INK, width=3)
    centered_text(draw, (x1 + 12, y1 + 10, x2 - 12, y1 + 85), title, font(43, True), INK)
    if subtitle:
        centered_text(draw, (x1 + 10, y1 + 88, x2 - 10, y2 - 10), subtitle, font(32), GRAY)


def create_dfd(path):
    im = Image.new("RGB", (2400, 1450), WHITE)
    d = ImageDraw.Draw(im)
    d.text((110, 50), "TOOTHWISE LEVEL 0 DATA FLOW DIAGRAM", font=font(64, True), fill=INK)
    d.text((110, 130), "Context view: all information passes through the system process", font=font(40), fill=GRAY)

    # One context process receives and returns all system data flows.
    process = (850, 410, 1560, 1000)
    d.rounded_rectangle(process, radius=26, fill=PALE, outline=INK, width=7)
    d.rectangle((850, 410, 1560, 510), fill=INK)
    centered_text(d, (860, 415, 1550, 505), "0.0  ToothWise System", font(52, True), WHITE)
    centered_text(d, (910, 545, 1500, 940), "Patient and staff records\nIntraoral image processing\nDetection and risk results\nPrevention plan and reports\nAudit and access controls", font(42), INK, gap=22)

    admin = (100, 240, 580, 450)
    dentist = (100, 940, 580, 1170)
    patient = (1810, 640, 2290, 870)
    entity(d, admin, "System Administrator", "staff access and oversight")
    entity(d, dentist, "Dentist / Clinical Staff", "clinical screening workflow")
    entity(d, patient, "Patient", "self-service portal")

    # Paired flows enter and leave each external entity without crossing one another.
    arrow(d, [(580, 325), (850, 455)], fill="#8B6B3E", head=18)
    centered_text(d, (590, 225, 840, 300), "Staff credentials and\nmanagement requests", font(30, True), INK)
    arrow(d, [(850, 540), (580, 420)], fill="#8B6B3E", head=18)
    centered_text(d, (590, 460, 830, 535), "Access decisions and\naudit information", font(30, True), INK)
    arrow(d, [(580, 1020), (850, 845)], head=18)
    centered_text(d, (590, 930, 840, 1010), "Patient details, images,\nand clinical notes", font(30, True), INK)
    arrow(d, [(850, 920), (580, 1120)], head=18)
    centered_text(d, (590, 1160, 840, 1240), "Findings, risk, and\nrecommendations", font(30, True), INK)

    # Right-side patient portal exchanges.
    arrow(d, [(1560, 700), (1810, 700)], fill=BLUE, head=20)
    centered_text(d, (1570, 560, 1800, 675), "Registration and portal\nrequests", font(30, True), INK)
    arrow(d, [(1810, 815), (1560, 815)], fill=BLUE, head=20)
    centered_text(d, (1570, 850, 1800, 965), "Personal results and\nprevention guidance", font(30, True), INK)

    # Legend and boundary note.
    d.line((150, 1350, 2250, 1350), fill="#D6E0E5", width=2)
    d.text((155, 1370), "External entity", font=font(32), fill=GRAY)
    d.rectangle((110, 1374, 140, 1404), fill=PALE, outline=INK, width=2)
    d.text((530, 1370), "Process 0.0", font=font(32), fill=GRAY)
    d.rounded_rectangle((485, 1374, 515, 1404), radius=5, fill=PALE, outline=INK, width=2)
    d.text((1020, 1370), "Labeled arrows show named data exchanges", font=font(32), fill=GRAY)
    im.save(path, dpi=(220, 220))


def create_agile(path):
    """A simple, readable iteration cycle for the project development method."""
    im = Image.new("RGB", (2600, 1320), WHITE)
    d = ImageDraw.Draw(im)
    d.text((110, 40), "AGILE DEVELOPMENT METHODOLOGY", font=font(64, True), fill=INK)
    d.text((110, 120), "Each iteration produces a tested improvement for the next review cycle", font=font(36), fill=GRAY)
    center = (1300, 710)
    d.ellipse((1040, 500, 1560, 920), fill=WHITE, outline=INK, width=6)
    centered_text(d, (1080, 550, 1520, 870), "ITERATION\nDeliver a working\nToothWise increment", font(43, True), INK, gap=16)
    stages = [
        ((1100, 220, 1500, 350), "Plan"),
        ((1750, 380, 2150, 510), "Design"),
        ((1770, 850, 2170, 980), "Develop"),
        ((1100, 1050, 1500, 1180), "Test"),
        ((440, 850, 840, 980), "Review"),
        ((430, 380, 830, 510), "Refine"),
    ]
    anchors = []
    for box, label in stages:
        rounded(d, box, WHITE, INK, radius=22, width=5)
        centered_text(d, box, label, font(42, True), INK)
        x1, y1, x2, y2 = box
        anchors.append(((x1+x2)//2, (y1+y2)//2))
    # Route arrows between the outer edges, never through a stage box.
    links = [
        ((1500, 285), (1750, 445)),
        ((1950, 510), (1970, 850)),
        ((1770, 915), (1500, 1115)),
        ((1100, 1115), (840, 915)),
        ((440, 850), (430, 510)),
        ((830, 445), (1100, 285)),
    ]
    for p1, p2 in links:
        arrow(d, [p1, p2], fill=INK, width=5, head=20)
    d.text((820, 1225), "Feedback informs the next iteration", font=font(34), fill=GRAY)
    im.save(path, dpi=(220, 220))


def set_text(paragraph, text):
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def find_paragraph(doc, exact=None, starts=None):
    for p in doc.paragraphs:
        if exact is not None and p.text.strip() == exact:
            return p
        if starts is not None and p.text.strip().startswith(starts):
            return p
    raise ValueError(f"Paragraph not found: {exact or starts}")


def format_numbered(p):
    p.paragraph_format.left_indent = Inches(0)
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.5
    if p.runs:
        for r in p.runs:
            r.text = re.sub(r"[ \t\u00a0]+", " ", r.text).strip() if r is p.runs[0] else r.text


def replace_picture(paragraph, png, width=6.35):
    paragraph.clear()
    paragraph.alignment = 1
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.add_run().add_picture(str(png), width=Inches(width))


def remove_section_including_tables(doc, heading_starts, next_heading_starts):
    """Remove every body element in a numbered subsection, including its tables."""
    body = doc._element.body
    children = list(body.iterchildren())
    start = next(i for i, el in enumerate(children)
                 if isinstance(el, CT_P) and Paragraph(el, doc).text.strip().startswith(heading_starts))
    end = next(i for i, el in enumerate(children[start + 1:], start + 1)
               if isinstance(el, CT_P) and Paragraph(el, doc).text.strip().startswith(next_heading_starts))
    for el in children[start:end]:
        body.remove(el)


def set_cell_black_only(cell):
    """Make a table cell monochrome: white fill, black text, and black borders."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), "FFFFFF")
    shading.set(qn("w:color"), "000000")
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge = tc_borders.find(qn(f"w:{edge_name}"))
        if edge is None:
            edge = OxmlElement(f"w:{edge_name}")
            tc_borders.append(edge)
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "6")
        edge.set(qn("w:color"), "000000")
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.color.rgb = None
            r_pr = run._r.get_or_add_rPr()
            color = r_pr.find(qn("w:color"))
            if color is None:
                color = OxmlElement("w:color")
                r_pr.append(color)
            color.set(qn("w:val"), "000000")


def make_tables_black_only(tables):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                set_cell_black_only(cell)


def normalize_document_spacing(doc):
    """Apply 1.5 line spacing and consistent first line indents across the paper."""
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        fmt = p.paragraph_format
        fmt.line_spacing = 1.5
        if text.startswith(("Figure ", "Table ")):
            fmt.space_before = Pt(6)
            fmt.space_after = Pt(6)
            fmt.left_indent = Inches(0)
            fmt.first_line_indent = Inches(0)
            fmt.keep_with_next = text.startswith("Figure ")
        elif re.match(r"^(?:CHAPTER\s+[IVX]+|\d+(?:\.\d+){0,3}\s+)", text):
            fmt.space_before = Pt(12)
            fmt.space_after = Pt(6)
            fmt.keep_with_next = True
            fmt.left_indent = Inches(0)
            fmt.first_line_indent = Inches(0)
        else:
            fmt.space_before = Pt(0)
            fmt.space_after = Pt(6)
            if p.style.name.startswith("Heading"):
                fmt.left_indent = Inches(0)
                fmt.first_line_indent = Inches(0)
            elif "List of " not in text and "\t" not in text:
                ppr = p._p.pPr
                if ppr is None or ppr.numPr is None:
                    fmt.left_indent = Inches(0)
                    fmt.first_line_indent = Inches(0.5)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.5
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.left_indent = Inches(0)
                    p.paragraph_format.first_line_indent = Inches(0)


def rebuild_manual_list(doc, heading_text, end_heading, entries, column_heading):
    paragraphs = doc.paragraphs
    heading = next(p for p in paragraphs if p.text.strip() == heading_text)
    end = next(p for p in paragraphs if p.text.strip() == end_heading)
    start_i, end_i = paragraphs.index(heading), paragraphs.index(end)
    section = paragraphs[start_i + 1:end_i]
    header = next((p for p in section if p.text.strip() == column_heading), None)
    template = next((p for p in section if p is not header and p.text.strip()), None)
    if template is None:
        template = header or heading
    if header is None:
        header = section[0]
        set_text(header, column_heading)
    for p in list(section):
        if p is not header:
            p._element.getparent().remove(p._element)
    anchor = header
    for entry in entries:
        new_el = deepcopy(template._p)
        new_p = Paragraph(new_el, anchor._parent)
        set_text(new_p, entry)
        anchor._p.addnext(new_el)
        anchor = new_p


def main():
    create_use_case(USECASE_PNG)
    create_dfd(DFD_PNG)
    create_agile(AGILE_PNG)
    doc = Document(SOURCE)

    # Remove the full 1.3.1 ISO subsection and its operationalization table.
    remove_section_including_tables(doc, "1.3.1 ISO/IEC 25010", "1.4 Scope and Limitation")

    # Standardize paragraph spacing and remove accidental tabs/multiple spaces in both lists.
    for p in doc.paragraphs:
        s = p.text.strip()
        if re.match(r"^[1-5]\.\s", s):
            set_text(p, re.sub(r"^([1-5]\.)\s+", r"\1 ", re.sub(r"[ \t\u00a0]+", " ", s)))
            format_numbered(p)
    # Keep numbered questions/objectives visually consistent with the list's normal style.
    for idx in list(range(233, 238)) + list(range(253, 258)):
        if idx < len(doc.paragraphs):
            format_numbered(doc.paragraphs[idx])

    # Replace the diagrams using their captions, rather than fragile paragraph indices.
    agile_caption = find_paragraph(doc, exact="Figure 1 Agile Development Methodology")
    replace_picture(Paragraph(agile_caption._p.getprevious(), doc), AGILE_PNG, width=6.15)
    use_case_caption = find_paragraph(doc, exact="Figure 2 Use Case Diagram")
    replace_picture(Paragraph(use_case_caption._p.getprevious(), doc), USECASE_PNG)
    dfd_caption = find_paragraph(doc, starts="Figure 4 Toothwise Level 0 Data Flow Diagram")
    replace_picture(Paragraph(dfd_caption._p.getprevious(), doc), DFD_PNG)

    # Update the context DFD dictionary to agree with the actual portal and clinic workflows.
    data_rows = [
        ("Staff credentials and sign-in request", "Dentist / Administrator", "ToothWise System (0.0)", "Staff email and password submitted for authentication and role-scoped access."),
        ("Staff management and audit queries", "System Administrator", "ToothWise System (0.0)", "Staff account create, update, or deactivation requests and audit-log queries."),
        ("Patient profile and screening request", "Dentist / Clinical Staff", "ToothWise System (0.0)", "Patient demographic details and request to start or review a screening."),
        ("Intraoral image", "Dentist / Intraoral Camera", "ToothWise System (0.0)", "Captured camera frame or uploaded intraoral image for analysis."),
        ("Detection and risk results", "ToothWise System (0.0)", "Dentist / Clinical Staff", "Detected labels, bounding boxes, confidence values, model timings, and screening risk level."),
        ("Clinical note and tier confirmation", "Dentist / Clinical Staff", "ToothWise System (0.0)", "Dentist-authored screening note or confirmation of the AI risk tier."),
        ("Screening report", "ToothWise System (0.0)", "Dentist / Clinical Staff", "Authenticated PDF report containing the screening image, findings, risk level, recommendations, and notes."),
        ("Audit trail and service status", "ToothWise System (0.0)", "System Administrator", "Recorded sign-in and sensitive record actions, plus service and database health status."),
        ("Patient registration and portal request", "Patient", "ToothWise System (0.0)", "Self-registration or login, own-history request, and question submitted to the screening assistant."),
        ("Patient screening history and guidance", "ToothWise System (0.0)", "Patient", "The patient's own screening findings and recommendations, history, and assistant response."),
    ]
    for row, values in zip(doc.tables[5].rows[1:], data_rows):
        for cell, value in zip(row.cells, values):
            cell.text = value

    # The Chapter 3 tables are intentionally monochrome for the final paper.
    make_tables_black_only(doc.tables[:23])

    # Renumber every Chapter 3 table, preserving the Chapter 1 and 2 tables.
    # Document table indices 1..23 are the Chapter 3 sources/requirements/spec tables.
    for table_index in range(1, 24):
        old_num = table_index
        new_num = table_index
        # Captions are paragraphs, updated separately below. Table content is retained.
    caption_map = {
        "Table 1 Sources of Requirements and Technical Data": "Table 3.1 Sources of Requirements and Technical Data",
        "Table 2 Roles and Responsibilities of the Development Team": "Table 3.2 Roles and Responsibilities of the Development Team",
        "Table 3 Functional Requirements": "Table 3.3 Functional Requirements",
        "Table 4 Non-Functional Requirements": "Table 3.4 Non-Functional Requirements",
        "Table 6 Development Phase Activities": "Table 3.8 Development Phase Activities",
        "Table 7 Agile Iteration Summary": "Table 3.9 Agile Iteration Summary",
        "Table 3.8 Toothwise Comprehensive System Test Cases and Verification Results": "Table 3.10 Toothwise Comprehensive System Test Cases and Verification Results",
        "Table 3.9 ISO/IEC 25010 Software Quality Evaluation Results (Summary)": "Table 3.11 ISO/IEC 25010 Software Quality Evaluation Results (Summary)",
        "Table 4.1. Software Development Requirements": "Table 3.12 Software Development Requirements",
        "Table 4.2. Implementation Software Requirements": "Table 3.13 Implementation Software Requirements",
        "Table 4.3. Hardware Development Requirements": "Table 3.14 Hardware Development Requirements",
        "Table 4.4. Implementation Hardware Requirements": "Table 3.15 Implementation Hardware Requirements",
        "Table 4.5. dentists table": "Table 3.16 dentists table",
        "Table 4.6. patients table": "Table 3.17 patients table",
        "Table 4.7. screening table": "Table 3.18 screening table",
        "Table 4.8. detection table": "Table 3.19 detection table",
        "Table 4.9. recommendations table": "Table 3.20 recommendations table",
        "Table 4.10. clinical_notes table": "Table 3.21 clinical_notes table",
        "Table 4.11. audit_logs table": "Table 3.22 audit_logs table",
        "Table 4.12. Implementation / Deployment Procedure": "Table 3.23 Implementation / Deployment Procedure",
    }
    for p in doc.paragraphs:
        s = p.text.strip()
        if s in caption_map:
            set_text(p, caption_map[s])

    # Move the complete former Chapter IV technical-specification block directly after Chapter III.
    body = doc._element.body
    paragraphs_by_text = {p.text.strip(): p for p in doc.paragraphs if p.text.strip()}
    ch4 = paragraphs_by_text["CHAPTER IV"]._p
    ch5 = paragraphs_by_text["CHAPTER V"]._p
    ref_heading = paragraphs_by_text["REFERENCES"]._p
    children = list(body.iterchildren())
    start_i, end_i = children.index(ch4), children.index(ch5)
    block = children[start_i:end_i]
    for element in block:
        body.remove(element)
    insertion_point = paragraphs_by_text["REFERENCES"]._p
    ref_index = list(body.iterchildren()).index(insertion_point)
    for offset, element in enumerate(block):
        body.insert(ref_index + offset, element)

    # The moved heading is now a Chapter 3 subsection; avoid a duplicate title line.
    moved_paragraphs = [Paragraph(el, doc) for el in block if isinstance(el, CT_P)]
    for p in moved_paragraphs:
        s = p.text.strip()
        if s == "CHAPTER IV":
            set_text(p, "3.9 Technical Specifications")
        elif s == "TECHNICAL SPECIFICATIONS":
            set_text(p, "")
        elif s.startswith("4.1 Software Specifications"):
            set_text(p, "3.9.1 Software Specifications")
        elif s.startswith("4.2 Hardware Specifications"):
            set_text(p, "3.9.2 Hardware Specifications")
        elif s.startswith("4.3 System Architecture"):
            set_text(p, "3.9.3 System Architecture")
        elif s.startswith("4.4 Database Technical Specifications"):
            set_text(p, "3.9.4 Database Technical Specifications")
        elif s.startswith("4.5.1 Model Evaluation Procedure"):
            set_text(p, "3.9.5.1 Model Evaluation Procedure")
        elif s.startswith("4.5 AI/ML Technical Specifications"):
            set_text(p, "3.9.5 AI/ML Technical Specifications")
        elif s.startswith("4.6 Risk Assessment Technical Specifications"):
            set_text(p, "3.9.6 Risk Assessment Technical Specifications")
        elif s.startswith("4.7 Recommendation Engine Technical Specifications"):
            set_text(p, "3.9.7 Recommendation Engine Technical Specifications")
        elif s.startswith("4.8 Security Technical Specifications"):
            set_text(p, "3.9.8 Security Technical Specifications")
        elif s.startswith("4.9 Network and Deployment Specifications"):
            set_text(p, "3.9.9 Network and Deployment Specifications")
        elif s.startswith("Table 4."):
            set_text(p, re.sub(r"Table 4\.(\d+)", lambda m: f"Table 3.{int(m.group(1)) + 11}", s))
        elif s.startswith("Figure 1 Three-Tier Toothwise System Architecture"):
            set_text(p, "Figure 19 Three-Tier ToothWise System Architecture")
        elif s.startswith("Figure 2 Toothwise Screening Process Flow"):
            set_text(p, "Figure 20 ToothWise Screening Process Flow")
        elif s.startswith("Figure 4.1"):
            set_text(p, s.replace("Figure 4.1", "Figure 19"))
        elif s.startswith("Figure 4.2"):
            set_text(p, s.replace("Figure 4.2", "Figure 20"))
        elif s.startswith("Table 4.1") or s.startswith("Table 4.2") or s.startswith("Table 4.3") or s.startswith("Table 4.4") or s.startswith("Table 4.5") or s.startswith("Table 4.6") or s.startswith("Table 4.7") or s.startswith("Table 4.8") or s.startswith("Table 4.9"):
            # Caption titles are handled by the explicit map.
            pass

    # Update references elsewhere in Chapter 3 that pointed into old Chapter IV.
    replacements = {
        "Section 4.4": "Section 3.9.4",
        "Chapter IV": "Chapter III",
        "Section 4.8": "Section 3.9.8",
        "Section 4.5": "Section 3.9.5",
        "Section 4.6": "Section 3.9.6",
        "Table 4.1": "Table 3.12",
        "Table 4.2": "Table 3.13",
        "Table 4.3": "Table 3.14",
        "Table 4.4": "Table 3.15",
        "Table 4.5": "Table 3.16",
        "Table 4.6": "Table 3.17",
        "Table 4.7": "Table 3.18",
        "Table 4.8": "Table 3.19",
        "Table 4.9": "Table 3.20",
        "Table 4.10": "Table 3.21",
        "Table 4.11": "Table 3.22",
        "Table 4.12": "Table 3.23",
        "Figure 4.1": "Figure 19",
        "Figure 4.2": "Figure 20",
        "Figure 3.3": "Figure 3",
        "Table 3.8 presents the test cases": "Table 3.10 presents the test cases",
        "Table 3.9 presents the statistical summary": "Table 3.11 presents the statistical summary",
    }
    for p in doc.paragraphs:
        text = p.text
        updated = text
        for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            updated = updated.replace(old, new)
        if p in moved_paragraphs:
            updated = updated.replace("Tables 4.5 to 4.11", "Tables 3.16 to 3.22")
            updated = updated.replace("This chapter presents the current technical specifications", "This section presents the current technical specifications")
            updated = updated.replace("Toothwise", "ToothWise")
            updated = updated.replace(" � ", " - ")
            if updated.startswith("�  "):
                updated = updated[3:]
        if updated != text:
            set_text(p, updated)

    # Rebuild the manually typed Chapter 3 outline so its labels match the revised body.
    outline_changes = {
        "   `\t\tChapter 3   Methodology": "Chapter 3 Methodology",
        "\tDevelopment Methodology": "3.1 Development Methodology",
        "\tProject Planning": "3.2 Project Planning",
        "\tRoles and Responsibilities of the Development Team": "3.3 Roles and Responsibilities of the Development Team",
        "\tRequirements Analysis": "3.4 Requirements Analysis",
        "\tSystem Design (Use Case, ERD, DFD, Gantt Chart)": "3.5 System Design (Use Case, ERD, DFD, Gantt Chart)",
        "\tSystem Development": "3.6 System Development",
        "\tSystem Testing": "3.7 System Testing",
        "\tFull Current System Screenshots": "3.8 Full Current System Screenshots",
        "Chapter 4   Technical Specifications": "3.9 Technical Specifications",
        "Chapter 3   Methodology": "3.9 Technical Specifications",
        "\tSoftware Specifications": "3.9.1 Software Specifications",
        "\tHardware Specifications": "3.9.2 Hardware Specifications",
        "\tSystem Architecture": "3.9.3 System Architecture",
        "\tDatabase Technical Specifications": "3.9.4 Database Technical Specifications",
        "\tAI/ML Technical Specifications": "3.9.5 AI/ML Technical Specifications",
        "\tRisk Assessment Technical Specifications": "3.9.6 Risk Assessment Technical Specifications",
        "\tRecommendation Engine Technical Specifications": "3.9.7 Recommendation Engine Technical Specifications",
        "\tSecurity Technical Specifications": "3.9.8 Security Technical Specifications",
        "\tNetwork and Deployment Specifications": "3.9.9 Network and Deployment Specifications",
    }
    for p in doc.paragraphs:
        if p.text in outline_changes:
            set_text(p, outline_changes[p.text])

    # Expand Chapter III's introduction to reflect the added technical sections.
    for p in doc.paragraphs:
        if p.text.startswith("This chapter presents the methodology used in the development"):
            set_text(p, "This chapter presents the methodology used to develop ToothWise for CodiSmile Dental Clinic. It describes the Agile development process, project planning, team responsibilities, requirements analysis, system design, development, and testing. It also documents the system's software and hardware requirements, architecture, database, AI and machine-learning components, risk and recommendation engines, security controls, and deployment specifications.")

    # Remove stale Chapter IV references and update every affected table/figure cross-reference.
    for p in doc.paragraphs:
        value = p.text
        for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            value = value.replace(old, new)
        value = value.replace("Tables 4.5 to 4.11", "Tables 3.16 to 3.22")
        if value.startswith("�  "):
            value = value[3:]
        value = value.replace("Toothwise", "ToothWise")
        if value != p.text:
            set_text(p, value)

    # Keep the diagram explanations accurate and use unhyphenated wording.
    for p in doc.paragraphs:
        value = p.text.strip()
        if value.startswith("Figure 2 presents the use case diagram"):
            set_text(p, "Figure 2 presents the ToothWise use case diagram. The dentist actor is associated with the clinic screening functions. The administrator actor specializes the dentist role and therefore inherits those functions, in addition to managing staff accounts and reviewing audit records. The patient actor can view personal screening history and ask the screening assistant.")
        elif value.startswith("Figure 4 presents the Level 0 (context) Data Flow Diagram"):
            set_text(p, "Figure 4 presents the Level 0 context Data Flow Diagram for ToothWise. It shows the system as one process and identifies the information exchanged with the system administrator, dentist or clinical staff, and patient. Each labeled arrow represents information entering or leaving the system. The data flow dictionary in Table 3.6 describes these exchanges.")
        elif value.startswith("As illustrated in Figure 4, the Level 0 Context Data Flow Diagram"):
            set_text(p, "Figure 4 shows the boundary of the ToothWise system as Process 0.0 and its primary information exchanges with the dentist or clinical staff, system administrator, and patient. The system receives patient details, intraoral images, clinical notes, staff requests, and patient portal requests. It returns screening findings, risk results, recommendations, reports, access decisions, and audit information. Table 3.6 lists the data flows and their contents.")
        elif value.startswith("The cycle in Figure 1 was applied repeatedly"):
            set_text(p, "The cycle in Figure 1 was repeated across the project iterations. Planning and requirements analysis identified the clinic workflow features. System design translated requirements into frontend routes, API endpoints, and database structures. Development implemented the React, FastAPI, and machine learning components. Testing checked system behavior, and review compared results with requirements. Refinement addressed issues before the next iteration.")

    # Match objectives 2 to the implemented YOLOv8/YOLOv12 ensemble and fusion flow.
    objective_and_problem_updates = {
        "2. How can the YOLOv12 object-detection model be integrated into ToothWise to identify and localize dental caries and other trained oral findings from intraoral images through labeled bounding boxes and confidence scores?":
        "2. How can ToothWise integrate the YOLOv8 and YOLOv12 object-detection models to identify and localize trained oral findings in intraoral images, retain each model's results, and present fused clinical findings with bounding boxes and confidence scores?",
        "2. To integrate a YOLOv12 object-detection model that identifies and localizes dental caries and other trained oral findings from intraoral images using bounding boxes and confidence scores.":
        "2. To integrate the YOLOv8 and YOLOv12 object-detection models to identify and localize trained oral findings in intraoral images, retain their individual results, and present fused clinical findings with bounding boxes and confidence scores.",
    }
    for p in doc.paragraphs:
        if p.text in objective_and_problem_updates:
            set_text(p, objective_and_problem_updates[p.text])
            format_numbered(p)
    for p in doc.paragraphs:
        if re.match(r"^[1-5]\. To ", p.text.strip()):
            # These objective paragraphs already contain their visible numbers;
            # remove inherited Word list numbering to prevent doubled markers.
            ppr = p._p.pPr
            if ppr is not None and ppr.numPr is not None:
                ppr.remove(ppr.numPr)
            format_numbered(p)

    specific_heading = None
    objective_index = next((i for i, p in enumerate(doc.paragraphs)
                            if p.text.strip().startswith("1.3 Objective of the Study")), None)
    if objective_index is not None:
        specific_heading = next((p for p in doc.paragraphs[objective_index + 1:]
                                 if p.text.strip() == "Specific Objectives"), None)
    if specific_heading is not None:
        specific_heading.paragraph_format.page_break_before = True
        specific_heading.paragraph_format.keep_with_next = True

    # Remove obsolete empty paragraphs and an explicit page break retained from
    # the former Chapter IV opening; 3.9 now follows the Chapter III material.
    tech_intro = find_paragraph(doc, starts="This chapter presents the current technical specifications")
    set_text(tech_intro, tech_intro.text.replace("This chapter presents", "This section presents").replace("Toothwise", "ToothWise"))
    # The former Chapter IV opening retained several empty lines and a manual
    # page break. Remove those so the new Chapter III subsection flows normally.
    previous = tech_intro._p.getprevious()
    while previous is not None and not Paragraph(previous, doc).text.strip():
        parent = previous.getparent()
        parent.remove(previous)
        previous = tech_intro._p.getprevious()
    technical_heading = Paragraph(previous, doc)
    if technical_heading.text.strip() != "3.9 Technical Specifications":
        raise ValueError("Could not locate the Chapter 3.9 heading before its introduction")
    previous = technical_heading._p.getprevious()
    while previous is not None and not Paragraph(previous, doc).text.strip():
        parent = previous.getparent()
        parent.remove(previous)
        previous = technical_heading._p.getprevious()

    # Format the transferred subsection headings consistently with the existing
    # Chapter III section headings, clearing the former Chapter IV title indents.
    paragraph_list = doc.paragraphs
    tech_start_index = next(i for i, p in enumerate(paragraph_list) if p._p is technical_heading._p)
    for p in paragraph_list[tech_start_index:]:
        if p.text.strip() == "REFERENCES":
            break
        text = p.text.strip()
        if re.match(r"^3\.9(?:\.\d+){0,3} ", text):
            p.paragraph_format.left_indent = Inches(0)
            p.paragraph_format.first_line_indent = Inches(0)
            p.paragraph_format.space_before = Pt(10 if text == "3.9 Technical Specifications" else 7)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.keep_with_next = True
            p.alignment = 0
            if p.runs:
                p.runs[0].font.name = "Book Antiqua"
                p.runs[0].font.size = Pt(12)
                p.runs[0].bold = True

    normalize_document_spacing(doc)

    # Keep the use-case image and its caption on one page.
    use_case_caption = find_paragraph(doc, exact="Figure 2 Use Case Diagram")
    preceding = Paragraph(use_case_caption._p.getprevious(), doc)
    preceding.paragraph_format.keep_with_next = True

    # Update the static table/figure lists so their labels agree with Chapter 3.
    table_entries = [
        "3.1    Sources of Requirements and Technical Data",
        "3.2    Roles and Responsibilities of the Development Team",
        "3.3    Functional Requirements",
        "3.4    Non-Functional Requirements",
        "3.5    ToothWise Database Fact Table",
        "3.6    Data Flow Dictionary for Level 0 Context Diagram",
        "3.7    Capstone Project Work Breakdown Structure and Timeline",
        "3.8    Development Phase Activities",
        "3.9    Agile Iteration Summary",
        "3.10   ToothWise Comprehensive System Test Cases and Results",
        "3.11   ISO/IEC 25010 Software Quality Evaluation Results",
        "3.12   Software Development Requirements",
        "3.13   Implementation Software Requirements",
        "3.14   Hardware Development Requirements",
        "3.15   Implementation Hardware Requirements",
        "3.16   dentists table",
        "3.17   patients table",
        "3.18   screenings table",
        "3.19   detections table",
        "3.20   recommendations table",
        "3.21   clinical_notes table",
        "3.22   audit_logs table",
        "3.23   Implementation / Deployment Procedure",
    ]
    figure_entries = [
        "1    Agile Development Methodology",
        "2    ToothWise Use Case Diagram",
        "3    Entity Relationship Diagram",
        "4    ToothWise Level 0 Data Flow Diagram",
        "5    ToothWise Level 1 Data Flow Diagram",
        "6    Capstone 1 and Capstone 2 Gantt Chart",
        "7    Public Landing Page",
        "8    Staff Login Page",
        "9    Dashboard",
        "10   Patient List",
        "11   Patient Details",
        "12   New Screening (Capture / Upload)",
        "13   Screening Results",
        "14   Staff Management (Admin)",
        "15   Audit Log (Admin)",
        "16   Patient Portal Login",
        "17   Patient Portal Registration",
        "18   Patient Portal Screening History",
        "19   Three-Tier ToothWise System Architecture",
        "20   ToothWise Screening Process Flow",
    ]
    rebuild_manual_list(doc, "List of Tables", "List of Figures", table_entries,
                        "Table No.    Table Title")
    rebuild_manual_list(doc, "List of Figures", "\\List of Appendices", figure_entries,
                        "Figure No.    Figure Title")
    # Fix numbered table lists that were still carrying the old specification chapter.
    for p in doc.paragraphs:
        s = p.text.strip()
        if s.startswith("4.") and ("Software" in s or "Hardware" in s or "System Architecture" in s or "Technical Specifications" in s or "Deployment" in s):
            set_text(p, s.replace("4.", "3.9.", 1))
        elif s.startswith("4.") and "Table" in s:
            set_text(p, re.sub(r"^4\.(\d+)", lambda m: f"3.{int(m.group(1)) + 11}", s))

    # Keep image positions/captions together and update in-chapter figure numbers.
    for p in doc.paragraphs:
        s = p.text.strip()
        if s.startswith("Figure 2 Use Case Diagram"):
            set_text(p, "Figure 2 ToothWise Use Case Diagram")
        elif s.startswith("Figure 4 ToothWise Level 0 Data Flow Diagram"):
            set_text(p, "Figure 4 ToothWise Level 0 Data Flow Diagram (Context Diagram)")
        if s.startswith("Figure 4 Toothwise Level 0"):
            set_text(p, "Figure 4 ToothWise Level 0 Data Flow Diagram (Context Diagram)")

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
