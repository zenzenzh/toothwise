"""
Generates a one-page(ish) PDF clinical report for a screening: patient
info, risk summary, the intraoral photo, a table of detected findings,
the prevention plan, and any clinical notes on record.

Uses reportlab's Platypus layer (flowables) rather than raw Canvas
drawing, since the report has a variable amount of content (findings,
notes) that needs to reflow/paginate cleanly - see /mnt/skills/public/pdf
for the general guidance this follows.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
)

from app.config import get_settings

settings = get_settings()

_RISK_COLORS = {
    "HIGH": colors.HexColor("#C4505A"),
    "MEDIUM": colors.HexColor("#D4850A"),
    "LOW": colors.HexColor("#2D7A52"),
}


def generate_screening_report_pdf(screening) -> str:
    """
    screening: a loaded models.Screening ORM instance (with .patient,
    .detections, .recommendations, .notes relationships accessible).
    Returns the path to a generated temp PDF file.
    """
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#5C2D4E"),
    )
    heading_style = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], textColor=colors.HexColor("#5C2D4E"),
        spaceBefore=14, spaceAfter=6,
    )
    body_style = styles["BodyText"]

    story = []
    patient = screening.patient

    story.append(Paragraph("Toothwise Screening Report", title_style))
    story.append(Paragraph("CodiSmile Dental Clinic", body_style))
    story.append(Spacer(1, 0.2 * inch))

    info_rows = [
        ["Patient", patient.full_name if patient else "-"],
        ["Age / Gender", f"{patient.age if patient and patient.age is not None else '-'} / {patient.gender.value if patient and patient.gender else '-'}"],
        ["Screening Date", screening.created_at.strftime("%B %d, %Y %I:%M %p")],
        ["Screening ID", f"#{screening.id}"],
    ]
    info_table = Table(info_rows, colWidths=[1.6 * inch, 4.5 * inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.15 * inch))

    risk_color = _RISK_COLORS.get(screening.risk_level.value, colors.grey)
    finding_count = len([d for d in screening.detections if d.detection_set == "fused"])
    risk_table = Table(
        [[f"RISK LEVEL: {screening.risk_level.value}",
          f"{finding_count} finding{'s' if finding_count != 1 else ''}"]],
        colWidths=[3 * inch, 3 * inch],
    )
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 0.2 * inch))

    # Intraoral photo, if it's still on disk.
    image_full_path = Path(settings.UPLOAD_DIR) / screening.image_path
    if image_full_path.exists():
        story.append(Paragraph("Screening Image", heading_style))
        try:
            img = RLImage(str(image_full_path), width=4 * inch, height=3 * inch, kind="proportional")
            story.append(img)
        except Exception:
            story.append(Paragraph("(image could not be embedded)", body_style))
        story.append(Spacer(1, 0.1 * inch))

    # Findings table - only the fused/clinical detection set, same rule
    # used everywhere else in the app (dashboard, patient screening list).
    fused = [d for d in screening.detections if d.detection_set == "fused"]
    story.append(Paragraph("Detected Findings", heading_style))
    if fused:
        rows = [["Finding", "Confidence"]] + [
            [d.label.replace("_", " ").title(), f"{d.confidence * 100:.0f}%"]
            for d in sorted(fused, key=lambda d: d.confidence, reverse=True)
        ]
        findings_table = Table(rows, colWidths=[4 * inch, 1.5 * inch])
        findings_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7EEF2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EAD8E2")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(findings_table)
    else:
        story.append(Paragraph("No concerning findings detected.", body_style))
    story.append(Spacer(1, 0.15 * inch))

    # Prevention plan.
    story.append(Paragraph("Prevention Plan", heading_style))
    for rec in sorted(screening.recommendations, key=lambda r: r.order_index):
        prefix = "URGENT - " if rec.priority > 0 else "- "
        story.append(Paragraph(prefix + rec.text, body_style))
    story.append(Spacer(1, 0.15 * inch))

    # Clinical notes, if any.
    if screening.notes:
        story.append(Paragraph("Clinical Notes", heading_style))
        for note in sorted(screening.notes, key=lambda n: n.created_at):
            when = note.created_at.strftime("%b %d, %Y %I:%M %p")
            story.append(Paragraph(f"<b>{when}</b> - {note.body}", body_style))

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "This report is generated by an AI-assisted screening tool and is "
        "not a substitute for an in-person clinical examination.",
        ParagraphStyle("Disclaimer", parent=body_style, fontSize=8, textColor=colors.grey),
    ))

    tmp_dir = Path(tempfile.gettempdir()) / "toothwise_reports"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_path = tmp_dir / f"screening_{screening.id}_report.pdf"

    doc = SimpleDocTemplate(str(out_path), pagesize=letter,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    doc.build(story)
    return str(out_path)
