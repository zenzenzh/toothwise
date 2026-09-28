from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

path = r"C:\Users\zenn\toothwise\ToothWise_Final_Paper_Ch1-4_Revised_SOP_Objectives.docx"
doc = Document(path)
pi = ti = 0
for child in doc._element.body.iterchildren():
    if isinstance(child, CT_P):
        paragraph = Paragraph(child, doc)
        text = paragraph.text.strip()
        if text and pi >= 410:
            print(f"P{pi}: {text[:500]}")
        pi += 1
    elif isinstance(child, CT_Tbl):
        table = Table(child, doc)
        header = [cell.text.replace("\n", " / ")[:100] for cell in table.rows[0].cells]
        print(f"TABLE{ti}: {len(table.rows)}x{len(table.columns)} {header}")
        ti += 1
