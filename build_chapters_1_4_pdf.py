"""Insert Chapter IV into the Chapters 1-3 paper PDF.

Reads  ToothWise_Chapters_1-3_Updated.pdf   (left untouched)
       ToothWise_Chapter_4_paper.docx       (python generate_chapters_4_and_5_v2.py --paper)
Writes ToothWise_Chapters_1-4.pdf

  * Chapter IV is converted to PDF with Microsoft Word, then each page is laid
    over a blank copy of the paper's letterhead page (UDM header, logos and
    border frame), so it looks like the rest of the paper.
  * Chapter III ends partway down page 60, where the References begin. That page
    is split: Chapter III keeps page 60, Chapter IV follows from page 61, and the
    References start on a fresh page after it.
  * The References pages are renumbered, and Chapter IV plus the new References
    page number are added to the table of contents.

Needs PyMuPDF and Microsoft Word:  pip install pymupdf
    python build_chapters_1_4_pdf.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "ToothWise_Chapters_1-3_Updated.pdf"
CH4_DOCX = ROOT / "ToothWise_Chapter_4_paper.docx"
CH4_PDF = ROOT / "ToothWise_Chapter_4_paper.pdf"
DST = ROOT / "ToothWise_Chapters_1-4.pdf"

FONTS = Path(r"C:\Windows\Fonts")
TIMES, TIMES_BOLD = str(FONTS / "times.ttf"), str(FONTS / "timesbd.ttf")

# Geometry of the letterhead pages, in PDF points (612 x 792).
BODY = pymupdf.Rect(100, 112, 546, 718)        # between the header rule and the footer rule
PAGE_NO = pymupdf.Rect(100, 725, 546, 760)     # page-number band below the footer rule
TEMPLATE_PAGE = 22                             # page 23: plain text, no figures
LAST_CH3_PAGE = 59                             # page 60: end of Chapter III + start of References
TOC_PAGE = 2                                   # page 3: second table-of-contents page

CH4_TOC = [  # (text, heading text to find in the inserted chapters, bold, indent)
    ("CHAPTER IV: RESULTS AND DISCUSSION", "CHAPTER IV", True, 124.8),
    ("4.1 Results of the Trained Datasets", "4.1 Results of the Trained Datasets", False, 129.4),
    ("4.2 Specialization and Technical Results", "4.2 Specialization and Technical Results", False, 129.4),
    ("4.3 Software Quality Evaluation Based on ISO/IEC 25010",
     "4.3 Software Quality Evaluation Based on ISO/IEC 25010", False, 129.4),
    ("4.4 Screening Consistency and Screening Time", "4.4 Screening Consistency and Screening Time",
     False, 129.4),
]


def docx_to_pdf(docx: Path, pdf: Path):
    script = (
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        f"$d = $w.Documents.Open('{docx}', $false, $true); "
        f"$d.SaveAs([ref]'{pdf}', [ref]17); $d.Close($false); $w.Quit()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def page_number_span(page):
    """The span holding the printed page number in the footer band."""
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip().isdigit() and pymupdf.Rect(span["bbox"]).intersects(PAGE_NO):
                    return span
    raise ValueError(f"no page number on page {page.number + 1}")


def blank(page, rects, line_art=pymupdf.PDF_REDACT_LINE_ART_NONE):
    for r in rects:
        page.add_redact_annot(r)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=line_art)


def put_number(page, n, ref_span):
    """Write page number n right-aligned where the original number sat."""
    page.insert_font(fontname="TNR", fontfile=TIMES)
    text = str(n)
    width = pymupdf.Font(fontfile=TIMES).text_length(text, ref_span["size"])
    right = ref_span["bbox"][0] + pymupdf.Font(fontfile=TIMES).text_length(
        ref_span["text"].rstrip(), ref_span["size"])
    page.insert_text((right - width, ref_span["origin"][1]), text,
                     fontname="TNR", fontsize=ref_span["size"])


def leader_line(page, y, x, text, number, bold, right=540.0, size=12.0):
    font = TIMES_BOLD if bold else TIMES
    name = "TNRB" if bold else "TNR"
    page.insert_font(fontname=name, fontfile=font)
    f = pymupdf.Font(fontfile=font)
    if number is None:
        page.insert_text((x, y), text, fontname=name, fontsize=size)
        return
    num_w = f.text_length(str(number), size)
    dot_w = pymupdf.Font(fontfile=TIMES).text_length(".", size)
    start = x + f.text_length(text + " ", size)
    dots = int((right - num_w - start) / dot_w)
    page.insert_text((x, y), text + " ", fontname=name, fontsize=size)
    page.insert_font(fontname="TNR", fontfile=TIMES)
    # Right-align the leader so it ends at the number; any slack goes after the title.
    page.insert_text((right - num_w - dots * dot_w, y), "." * dots, fontname="TNR", fontsize=size)
    page.insert_text((right - num_w, y), str(number), fontname="TNR", fontsize=size)


def rewrite_toc_page(page, new_entries, refs_no):
    """Redraw the whole second contents page with even spacing.

    Used when the inserted chapters add more lines than fit below the old
    References entry: the existing Chapter III lines are read back and written
    again together with the new ones, spaced to fill the page.
    """
    old = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            t = "".join(s["text"] for s in line["spans"]).replace(" ", " ").strip()
            if not t or "Universidad" in t or "References" in t or not pymupdf.Rect(line["bbox"]).intersects(BODY):
                continue
            title, _, num = t.rpartition(" ")
            title = title.rstrip(". ").strip()
            depth = title.split(" ")[0].count(".")
            old.append((title, int(num.strip(".")), False, 165.4 if depth >= 2 else 129.4))
    old.sort(key=lambda e: [int(x) for x in e[0].split(" ")[0].split(".")])
    blank(page, [BODY])
    rows = []
    for text, number, bold, x in old + new_entries + [("References", refs_no, False, 129.4)]:
        font = pymupdf.Font(fontfile=TIMES_BOLD if bold else TIMES)
        # Wrap a heading that would run past the frame onto a second line.
        if number is None and font.text_length(text, 12) > 540 - x:
            words = text.split(" ")
            cut = max(i for i in range(1, len(words))
                      if font.text_length(" ".join(words[:i]), 12) <= 540 - x)
            rows.append((" ".join(words[:cut]), None, bold, x))
            rows.append((" ".join(words[cut:]), None, bold, x))
            continue
        rows.append((text, number, bold, x))
    top, bottom = 131.0, 704.0                    # first and last baselines inside the frame
    pitch = min(34.5, (bottom - top) / (len(rows) - 1))
    y = top
    for text, number, bold, x in rows:
        leader_line(page, y, x, text, number, bold)
        y += pitch


def main(docx=CH4_DOCX, pdf=CH4_PDF, dst=DST, toc_entries=CH4_TOC, label="Chapter IV"):
    docx_to_pdf(docx, pdf)
    src = pymupdf.open(SRC)
    ch4 = pymupdf.open(pdf)
    n4 = len(ch4)
    ref_span = page_number_span(src[LAST_CH3_PAGE])

    # Blank letterhead: page 23 with its body text and page number removed.
    tpl = pymupdf.open()
    tpl.insert_pdf(src, from_page=TEMPLATE_PAGE, to_page=TEMPLATE_PAGE)
    blank(tpl[0], [BODY, PAGE_NO])

    # Where the References heading sits on page 60.
    refs_top = None
    for b in src[LAST_CH3_PAGE].get_text("dict")["blocks"]:
        t = "".join(s["text"] for l in b.get("lines", []) for s in l["spans"])
        if t.strip() == "REFERENCES":
            refs_top = b["bbox"][1] - 4
    assert refs_top, "REFERENCES heading not found on page 60"

    out = pymupdf.open()
    out.insert_pdf(src, from_page=0, to_page=LAST_CH3_PAGE)          # pages 1-60
    # Also drop line art inside the area (the REFERENCES underline); the frame
    # lines lie outside it.
    blank(out[LAST_CH3_PAGE], [pymupdf.Rect(BODY.x0, refs_top, BODY.x1, BODY.y1)],
          pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)

    first_ch4 = LAST_CH3_PAGE + 2                                     # printed number 61
    for k in range(n4):                                               # Chapter IV
        pg = out.new_page(width=612, height=792)
        pg.show_pdf_page(pg.rect, tpl, 0)
        pg.show_pdf_page(pg.rect, ch4, k)
        put_number(pg, first_ch4 + k, ref_span)

    refs_no = first_ch4 + n4                                          # References, first page
    pg = out.new_page(width=612, height=792)
    pg.show_pdf_page(pg.rect, tpl, 0)
    clip = pymupdf.Rect(BODY.x0, refs_top, BODY.x1, BODY.y1)
    dest = pymupdf.Rect(BODY.x0, 117, BODY.x1, 117 + clip.height)
    pg.show_pdf_page(dest, src, LAST_CH3_PAGE, clip=clip)
    put_number(pg, refs_no, ref_span)

    for i in range(LAST_CH3_PAGE + 1, len(src)):                      # rest of the References
        out.insert_pdf(src, from_page=i, to_page=i)
        pg = out[-1]
        span = page_number_span(pg)
        blank(pg, [pymupdf.Rect(span["bbox"]) + (-2, -2, 6, 2)])
        put_number(pg, refs_no + (i - LAST_CH3_PAGE), span)

    heading_pages = {}
    for k in range(n4):
        text = ch4[k].get_text()
        for _, find, _, _ in toc_entries:
            if find in text and find not in heading_pages:
                heading_pages[find] = first_ch4 + k
    if toc_entries is not CH4_TOC:
        entries = [(t, None if b else heading_pages[f], b, x) for t, f, b, x in toc_entries]
        rewrite_toc_page(out[TOC_PAGE], entries, refs_no)
        out.save(dst, garbage=3, deflate=True)
        print(f"Wrote {dst.name}: {len(out)} pages; {label} on pages {first_ch4}-{first_ch4 + n4 - 1}, "
              f"References from page {refs_no}")
        return {"pages": len(out), "first": first_ch4, "refs": refs_no, "heading_pages": heading_pages}

    # Table of contents: replace the old "References .... 60" line.
    toc = out[TOC_PAGE]
    old = None
    for b in toc.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            t = "".join(s["text"] for s in line["spans"])
            if "References" in t:
                old = line
    blank(toc, [pymupdf.Rect(old["bbox"]) + (-2, -1, 4, 1)])
    y = old["spans"][0]["origin"][1]
    pitch = 32.0  # a little tighter than the 34.5 pt above, so References stays inside the frame
    for text, find, bold, x in CH4_TOC:
        leader_line(toc, y, x, text, None if bold else heading_pages[find], bold)
        y += pitch
    leader_line(toc, y, 129.4, "References", refs_no, False)

    out.save(dst, garbage=3, deflate=True)
    print(f"Wrote {dst.name}: {len(out)} pages; {label} on pages {first_ch4}-{first_ch4 + n4 - 1}, "
          f"References from page {refs_no}")
    return {"pages": len(out), "first": first_ch4, "refs": refs_no, "heading_pages": heading_pages}


if __name__ == "__main__":
    main()
