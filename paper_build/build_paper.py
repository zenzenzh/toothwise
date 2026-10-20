"""Build ToothWise Chapters 1-4 as a Word document and a print-ready PDF.

    python paper_build/build_paper.py

Reads  paper_build/content.txt          (text of the paper, simple markup below)
       paper_build/old_text.txt         (paragraphs of the earlier PDF, pulled in by "=")
       paper_build/figures/*.png        (diagrams, charts and screenshots)
       paper_build/assets/letterhead.png
Writes ToothWise_Chapters_1-4_updated.docx
       ToothWise_Chapters_1-4_updated.pdf  (LibreOffice export of the .docx)

The table of contents is filled in a second pass: the document is exported
once, the page of every heading is read back from the PDF, and the contents
pages are rewritten with those numbers before the final export.

Markup (one block per line):
  #CH CHAPTER I | INTRODUCTION     chapter title on a new page
  ## Heading / ### Heading         section headings (###+ also goes in the contents)
  P text / PN text                 paragraph with / without first-line indent
  = start of an old paragraph      copy that paragraph from old_text.txt
  ~ old >>> new                    replace text in the previous paragraph
  - text / 1. text                 bullet / numbered item
  TABLE key | Title  W 1.2,3 ...   table; rows "| a | b |", first row is the header,
  ENDTABLE  NOTE text              ...closed by ENDTABLE, optional note line after
  FIG key | file | width_in | Title | description
  REF text  PAGEBREAK  TITLEPAGE  TOC
  Inline: **bold**, *italic*, [TBD ...] (highlighted), {fig:key} {tab:key}
"""
from __future__ import annotations

import copy
import re
import subprocess
import sys
from pathlib import Path

import pymupdf
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTENT = HERE / "content.txt"
OLD = HERE / "old_text.txt"
FIGS = HERE / "figures"
LETTERHEAD = HERE / "assets" / "letterhead.png"
NAME = "ToothWise_Chapters_1-4_updated"
FONT = "Times New Roman"
BODY_W = 6.04          # inches between the frame lines


# ------------------------------------------------------------------ parsing
def load_old():
    paras = []
    for line in OLD.read_text(encoding="utf-8").splitlines():
        if line.startswith(("P ", "PN ")):
            text = line.split(" ", 1)[1]
            # captions that the PDF text extraction glued onto the paragraph before a table
            text = re.sub(r"\s*\*\*Table \d+\*\* \*[^*]+\*\s*$", "", text)
            paras.append(text)
    return paras


def parse(text):
    old = load_old()
    blocks, table = [], None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        if table is not None:
            if line.startswith("W "):
                table["widths"] = [float(x) for x in line[2:].split(",")]
            elif line.startswith("|"):
                table["rows"].append([c.strip() for c in line.strip().strip("|").split("|")])
            elif line == "ENDTABLE":
                blocks.append(table)
                table = None
            else:
                raise ValueError(f"bad table line: {line}")
            continue
        tag, _, rest = line.partition(" ")
        if tag in ("=", "=+"):
            hits = [p for p in old if p.startswith(rest)]
            if len(hits) != 1:
                raise ValueError(f"{len(hits)} old paragraphs start with: {rest!r}")
            if tag == "=+":
                blocks[-1]["text"] += " " + hits[0]
            else:
                blocks.append({"kind": "P", "text": hits[0]})
        elif tag == "~":
            a, b = rest.split(" >>> ")
            if a not in blocks[-1]["text"]:
                raise ValueError(f"substitution not found: {a!r}")
            blocks[-1]["text"] = blocks[-1]["text"].replace(a, b)
        elif tag == "TABLE":
            key, title = [s.strip() for s in rest.split("|", 1)]
            table = {"kind": "TABLE", "key": key, "title": title, "rows": [], "widths": None}
        elif tag == "NOTE":
            blocks[-1]["note"] = rest
        elif tag == "FIGPAIR":
            pair = []
            for half in rest.split("||"):
                parts = [s.strip() for s in half.split("|")]
                pair.append({"key": parts[0], "file": parts[1], "width": float(parts[2]),
                             "title": parts[3], "desc": parts[4] if len(parts) > 4 else ""})
            blocks.append({"kind": "FIGPAIR", "figs": pair})
        elif tag == "FIG":
            parts = [s.strip() for s in rest.split("|")]
            key, file, width, title = parts[:4]
            blocks.append({"kind": "FIG", "key": key, "file": file, "width": float(width),
                           "title": title, "desc": parts[4] if len(parts) > 4 else ""})
        elif tag == "#CH":
            a, b = [s.strip() for s in rest.split("|")]
            blocks.append({"kind": "CH", "num": a, "title": b})
        elif tag in ("##", "###", "###+"):
            blocks.append({"kind": tag, "text": rest})
        elif tag in ("P", "PN", "REF", "-"):
            blocks.append({"kind": tag, "text": rest})
        elif re.fullmatch(r"\d+\.", tag):
            blocks.append({"kind": "NUM", "num": tag, "text": rest})
        elif tag in ("PAGEBREAK", "TITLEPAGE", "TOC"):
            blocks.append({"kind": tag})
        else:
            raise ValueError(f"unknown line: {line}")
    numbers, n_fig, n_tab = {}, 0, 0
    for b in blocks:
        if b["kind"] == "FIG":
            n_fig += 1
            numbers["fig:" + b["key"]] = b["n"] = n_fig
        elif b["kind"] == "FIGPAIR":
            for f in b["figs"]:
                n_fig += 1
                numbers["fig:" + f["key"]] = f["n"] = n_fig
        elif b["kind"] == "TABLE":
            n_tab += 1
            numbers["tab:" + b["key"]] = b["n"] = n_tab

    def resolve(s):
        return re.sub(r"\{((?:fig|tab):[\w-]+)\}", lambda m: str(numbers[m.group(1)]), s)

    for b in blocks:
        for k in ("text", "title", "desc", "note"):
            if k in b:
                b[k] = resolve(b[k])
        if b["kind"] == "TABLE":
            b["rows"] = [[resolve(c) for c in r] for r in b["rows"]]
        if b["kind"] == "FIGPAIR":
            for f in b["figs"]:
                f["title"], f["desc"] = resolve(f["title"]), resolve(f["desc"])
    return blocks


# --------------------------------------------------------------- docx tools
INLINE = re.compile(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*[^*\s][^*]*?\*|\[TBD[^\]]*\])")


def add_runs(par, text, size=None, bold=False, italic=False):
    for tok in INLINE.split(text):
        if not tok:
            continue
        b, i, hi = bold, italic, False
        if tok.startswith("***") and tok.endswith("***") and len(tok) > 6:
            tok, b, i = tok[3:-3], True, True
        elif tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            tok, b = tok[2:-2], True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            tok, i = tok[1:-1], True
        elif tok.startswith("[TBD"):
            b, hi = True, True
        r = par.add_run(tok)
        r.bold, r.italic = (b or None), (i or None)
        if size:
            r.font.size = Pt(size)
        if hi:
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return par


def fmt(par, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.5, before=0, after=6, line=1.5,
        keep_next=False, left=0.0, hanging=0.0):
    pf = par.paragraph_format
    par.alignment = align
    pf.first_line_indent = Inches(-hanging if hanging else indent)
    pf.left_indent = Inches(left)
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = line
    pf.keep_with_next = keep_next
    pf.widow_control = True
    return par


def shade(cell, color):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{color}"/>'))


def set_cell_margins(table, top=40, bottom=40, left=80, right=80):
    tblPr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for side, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    tblPr.append(m)


def anchor_behind(run, path, width_in, height_in):
    """Insert a picture anchored at the page origin, behind the text."""
    run.add_picture(str(path), width=Inches(width_in), height=Inches(height_in))
    inline = run._r.find(".//" + qn("wp:inline"))
    graphic = inline.find(qn("a:graphic"))
    ext = inline.find(qn("wp:extent"))
    anchor = parse_xml(
        f'<wp:anchor {nsdecls("wp", "a", "pic", "r")} distT="0" distB="0" distL="0" distR="0" simplePos="0" '
        f'relativeHeight="0" behindDoc="1" locked="1" layoutInCell="1" allowOverlap="1">'
        f'<wp:simplePos x="0" y="0"/>'
        f'<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        f'<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{ext.get("cx")}" cy="{ext.get("cy")}"/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
        f'<wp:docPr id="900" name="Letterhead"/><wp:cNvGraphicFramePr/></wp:anchor>')
    anchor.append(copy.deepcopy(graphic))
    inline.getparent().replace(inline, anchor)


def page_field(par):
    r = par.add_run()
    for kind, txt in (("begin", None), (None, "PAGE"), ("separate", None), (None, "4"), ("end", None)):
        if kind:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), kind)
            r._r.append(e)
        elif txt == "PAGE":
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = " PAGE "
            r._r.append(e)
        else:
            e = OxmlElement("w:t")
            e.text = txt
            r._r.append(e)


def setup_section(sec):
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin, sec.right_margin = Inches(1.5), Inches(0.96)
    sec.top_margin, sec.bottom_margin = Inches(1.68), Inches(1.16)
    sec.header_distance, sec.footer_distance = Inches(0.3), Inches(0.62)


# ------------------------------------------------------------------ writing
def write(blocks, toc_pages=None):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    for name in ("Heading 1", "Heading 2", "Heading 3"):
        h = doc.styles[name]
        h.font.name, h.font.size, h.font.bold, h.font.italic = FONT, Pt(12), True, False
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.element.rPr.rFonts.set(qn("w:asciiTheme"), "") if False else None
        rf = h.element.rPr.rFonts
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(a)) is not None:
                del rf.attrib[qn(a)]
        rf.set(qn("w:ascii"), FONT); rf.set(qn("w:hAnsi"), FONT)

    sec = doc.sections[0]
    setup_section(sec)
    hp = sec.header.paragraphs[0]
    anchor_behind(hp.add_run(), LETTERHEAD, 8.5, 11)

    toc_entries = []
    first_chapter = True
    for b in blocks:
        k = b["kind"]
        if k == "TITLEPAGE":
            title_page(doc)
        elif k == "TOC":
            write_toc(doc, blocks, toc_pages)
        elif k == "PAGEBREAK":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif k == "CH":
            if first_chapter:
                new = doc.add_section(WD_SECTION.NEW_PAGE)
                setup_section(new)
                new.footer.is_linked_to_previous = False
                fp = new.footer.paragraphs[0]
                fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                page_field(fp)
                first_chapter = False
                par = doc.add_paragraph(style="Heading 1")
            else:
                par = doc.add_paragraph(style="Heading 1")
                par.paragraph_format.page_break_before = True
            fmt(par, WD_ALIGN_PARAGRAPH.CENTER, 0, 0, 12, 1.5, keep_next=True)
            r = par.add_run(b["num"])
            if b["title"]:
                r.add_break(); par.add_run(b["title"])
        elif k in ("##", "###", "###+"):
            par = doc.add_paragraph(style="Heading 2" if k == "##" else "Heading 3")
            fmt(par, WD_ALIGN_PARAGRAPH.LEFT, 0, 10 if k == "##" else 6, 4, 1.5, keep_next=True)
            add_runs(par, b["text"])
        elif k in ("P", "PN"):
            fmt(add_runs(doc.add_paragraph(), b["text"]), indent=0.5 if k == "P" else 0)
        elif k == "-":
            par = fmt(doc.add_paragraph(), left=0.6, hanging=0.25, after=4)
            par.paragraph_format.tab_stops.add_tab_stop(Inches(0.6))
            add_runs(par, "•\t" + b["text"])
        elif k == "NUM":
            par = fmt(doc.add_paragraph(), left=0.6, hanging=0.3, after=4)
            par.paragraph_format.tab_stops.add_tab_stop(Inches(0.6))
            add_runs(par, b["num"] + "\t" + b["text"])
        elif k == "REF":
            add_runs(fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, left=0.5, hanging=0.5, after=6), b["text"])
        elif k in ("FIG", "FIGPAIR") and b.get("page_break"):
            brk = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, 0, 0, 0, 1.0)
            brk.paragraph_format.page_break_before = True
            brk.paragraph_format.line_spacing = Pt(1)
            brk.add_run().font.size = Pt(1)
        if k == "FIG":
            par = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, 0, 8, 4, 1.0, keep_next=True)
            par.add_run().add_picture(str(FIGS / b["file"]), width=Inches(b["width"]))
            cap = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER if not b["desc"] else WD_ALIGN_PARAGRAPH.JUSTIFY,
                      0, 2, 10, 1.15)
            add_runs(cap, f"**Figure {b['n']} {b['title']}.**" + (f" *{b['desc']}*" if b["desc"] else ""))
        elif k == "TABLE":
            write_table(doc, b)
        elif k == "FIGPAIR":
            t = doc.add_table(rows=2, cols=2)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            t.autofit = False
            for j, f in enumerate(b["figs"]):
                for i in range(2):
                    t.cell(i, j).width = Inches(BODY_W / 2)
                par = fmt(t.cell(0, j).paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER, 0, 6, 4, 1.0, keep_next=True)
                par.add_run().add_picture(str(FIGS / f["file"]), width=Inches(f["width"]))
                cap = fmt(t.cell(1, j).paragraphs[0], WD_ALIGN_PARAGRAPH.JUSTIFY, 0, 2, 6, 1.15)
                add_runs(cap, f"**Figure {f['n']} {f['title']}.**" + (f" *{f['desc']}*" if f["desc"] else ""), size=11)
            for gc in t._tbl.tblGrid.findall(qn("w:gridCol")):
                gc.set(qn("w:w"), str(int(BODY_W / 2 * 1440)))
            t._tbl.tblPr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))
            for row in t.rows:
                row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            spacer = fmt(doc.add_paragraph(), after=4, line=1.0)
            spacer.paragraph_format.line_spacing = Pt(1)       # must not spill onto a page of its own
            spacer.add_run().font.size = Pt(1)
    return doc


def title_page(doc):
    def line(text, bold=False, before=0, size=12):
        par = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, 0, before, 0, 1.5)
        add_runs(par, text, size=size, bold=bold)
    line("**Toothwise: A YOLO-Based Multi-Condition Dental Screening System with KNN-Based "
         "Recommendation for CodiSmile Dental Clinic**", before=0)
    line("A Capstone Project Presented to the College of", before=18)
    line("Computing Studies")
    line("Universidad de Manila")
    line("In Partial Fulfillment", before=18)
    line("of the Requirements for the Course")
    line("**CAPSTONE 2**")
    for i, n in enumerate(["Brayan Axel L. Tubillas", "Keith Ashly V. Sales", "Reizen S. Arreola",
                           "Robin C. Ponce", "Rizelle Carla N. Magpantay"]):
        line(n, before=60 if i == 0 else 0)
    line("**Prof. Francis Arlando L. Atienza**", before=60)
    line("Professor")
    line("September 2026", before=54)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def toc_items(blocks):
    items = []
    for b in blocks:
        if b["kind"] == "CH" and not b["title"]:
            items.append((1, b["num"].title(), b["num"], "CH"))
        elif b["kind"] == "CH":
            items.append((0, f"{b['num']}: {b['title']}", b["num"], "CH"))
        elif b["kind"] == "##":
            items.append((1, b["text"], b["text"], "H"))
        elif b["kind"] == "###+":
            items.append((2, b["text"].rstrip(":"), b["text"], "H"))
    return items


def write_toc(doc, blocks, pages):
    par = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, 0, 0, 8, 1.15)
    add_runs(par, "**TABLE OF CONTENTS**")
    tab = Inches(BODY_W - 0.02)
    for i, (lvl, text, _, _) in enumerate(toc_items(blocks)):
        par = doc.add_paragraph()
        fmt(par, WD_ALIGN_PARAGRAPH.LEFT, 0, 9 if lvl == 0 and i else 0, 3, 1.15, left=[0, 0.15, 0.5][lvl])
        par.paragraph_format.tab_stops.add_tab_stop(tab, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        num = str(pages[i]) if pages else "0"
        if lvl == 0:
            add_runs(par, f"**{text}**")
        else:
            add_runs(par, f"{text}\t{num}")
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def write_table(doc, b):
    cap = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, 0, 8, 4, 1.15, keep_next=True)
    add_runs(cap, f"**Table {b['n']} {b['title']}**")
    rows = b["rows"]
    ncol = len(rows[0])
    t = doc.add_table(rows=len(rows), cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_cell_margins(t)
    widths = b["widths"] or [BODY_W / ncol] * ncol
    scale = BODY_W / sum(widths) if sum(widths) > BODY_W else 1
    t.autofit = False
    tblPr = t._tbl.tblPr
    tw = int(sum(widths) * scale * 1440)
    tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{tw}" w:type="dxa"/>'))
    tblPr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))
    for gc, wdt in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(wdt * scale * 1440)))
    size = 11 if ncol <= 4 else 10
    for i, row in enumerate(rows):
        tr = t.rows[i]._tr
        trPr = tr.get_or_add_trPr()
        if i == 0:
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for j in range(ncol):
            cell = t.cell(i, j)
            cell.width = Inches(widths[j] * scale)
            txt = row[j] if j < len(row) else ""
            par = cell.paragraphs[0]
            fmt(par, WD_ALIGN_PARAGRAPH.LEFT, 0, 0, 0, 1.0)
            for k, piece in enumerate(txt.split("<br>")):
                if k:
                    par = fmt(cell.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, 0, 0, 0, 1.0)
                add_runs(par, piece, size=size, bold=(i == 0))
            if i == 0:
                shade(cell, "D9D9D9")
            if i < len(rows) - 1 or True:
                pass
    # keep each table with its caption: mark all but the last row keep-with-next
    for cell in t.rows[0].cells:          # caption + header row + first data row stay together
        for par in cell.paragraphs:
            par.paragraph_format.keep_with_next = True
    after = fmt(doc.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, 0, 2, 8, 1.0)
    if b.get("note"):
        add_runs(after, f"*{b['note']}*", size=10)
    else:
        after.paragraph_format.space_after = Pt(2)


# ------------------------------------------------------------------ export
def to_pdf(docx: Path) -> Path:
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                   check=True, capture_output=True)
    return docx.with_suffix(".pdf")


def norm(s):
    return re.sub(r"\s+", " ", s.replace("­", "")).strip()


def find_pages(pdf: Path, blocks):
    d = pymupdf.open(pdf)
    texts = [[norm(l) for l in d[i].get_text().splitlines()] for i in range(len(d))]
    pages, start = [], 3
    for lvl, text, key, kind in toc_items(blocks):
        key_n = norm(re.sub(r"\*", "", key))
        for i in range(start, len(texts)):
            lines = texts[i]
            hit = key_n in lines if kind == "CH" else any(l.startswith(key_n[:45]) for l in lines)
            if hit:
                pages.append(i + 1)
                start = i
                break
        else:
            raise ValueError(f"heading not found in PDF: {text}")
    return pages


def main():
    blocks = parse(CONTENT.read_text(encoding="utf-8"))
    layout = HERE / "layout.json"            # written by layout_pass.py
    if layout.exists():
        import json
        from layout_pass import apply
        blocks = apply(blocks, json.loads(layout.read_text(encoding="utf-8")))
    out = ROOT / f"{NAME}.docx"
    write(blocks).save(out)
    pages = find_pages(to_pdf(out), blocks)
    write(blocks, pages).save(out)
    pdf = to_pdf(out)
    again = find_pages(pdf, blocks)
    assert again == pages, f"contents page numbers moved: {pages} -> {again}"
    print(f"Wrote {out.name} and {pdf.name}: {len(pymupdf.open(pdf))} pages")


if __name__ == "__main__":
    main()
