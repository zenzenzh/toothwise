from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from docx import Document

ROOT = Path(r"C:\Users\zenn\toothwise\qa_word_render")
PAGES = ROOT / "pages"
pdf = ROOT / "ToothWise_Final_Paper_Ch1-4_Updated_Methodology.pdf"
reader = PdfReader(str(pdf))
print(f"PDF pages: {len(reader.pages)}")
needles = [
    "Problem Statement", "ToothWise Use Case", "Data Flow Diagram",
    "3.9 Technical Specifications", "3.9.1 Software Specifications",
    "3.9.4 Database Technical Specifications", "3.9.9 Network and Deployment",
]
for index, page in enumerate(reader.pages, 1):
    text = (page.extract_text() or "").replace("\n", " ")
    matches = [needle for needle in needles if needle in text]
    if matches:
        print(f"Page {index}: {', '.join(matches)}")

doc = Document(r"C:\Users\zenn\toothwise\ToothWise_Final_Paper_Ch1-4_Updated_Methodology.docx")
print(f"DOCX sections: {len(doc.sections)}")
for index, paragraph in enumerate(doc.paragraphs):
    if paragraph.text.startswith(("3.8 Full Current", "3.9 Technical", "Figure 2 ToothWise", "Figure 4 ToothWise")):
        props = paragraph._p.pPr
        print("LAYOUT", index, repr(paragraph.text),
              "pageBreakBefore", bool(props is not None and props.pageBreakBefore is not None),
              "sectionBreak", bool(props is not None and props.sectPr is not None),
              "breakRuns", paragraph._p.xpath('.//w:br/@w:type'),
              "drawingSize", [(x.cx, x.cy) for x in paragraph._p.xpath('.//wp:extent')])
for index, section in enumerate(doc.sections):
    print("SECTION", index, "start", section.start_type)

files = sorted(PAGES.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1]))
print(f"Rendered page images: {len(files)}")
font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
per_sheet = 12
cols, rows = 3, 4
thumb_w, thumb_h = 330, 430
for start in range(0, len(files), per_sheet):
    batch = files[start:start + per_sheet]
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 28)), "#D8E0E6")
    draw = ImageDraw.Draw(sheet)
    for offset, file in enumerate(batch):
        image = Image.open(file).convert("RGB")
        image.thumbnail((thumb_w - 16, thumb_h - 10))
        x = (offset % cols) * thumb_w + (thumb_w - image.width) // 2
        y = (offset // cols) * (thumb_h + 28) + 25
        sheet.paste(image, (x, y))
        draw.text(((offset % cols) * thumb_w + 10,
                   (offset // cols) * (thumb_h + 28) + 4),
                  f"Page {start + offset + 1}", fill="#18324A", font=font)
    sheet.save(ROOT / f"contact-{start // per_sheet + 1:02d}.jpg", quality=88)
    print(ROOT / f"contact-{start // per_sheet + 1:02d}.jpg")
