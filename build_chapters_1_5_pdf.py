"""Insert Chapters IV and V into the Chapters 1-3 paper PDF, then make a
small copy of it.

Reads  ToothWise_Chapters_1-3_Updated.pdf   (left untouched)
       ToothWise_Chapters_4_5_paper.docx    (python generate_chapters_4_and_5_v2.py --paper --with-ch5)
Writes ToothWise_Chapters_1-5.pdf
       ToothWise_Chapters_1-5_compressed.pdf

The page work is the same as build_chapters_1_4_pdf.py (letterhead pages,
split page 60, renumbered References). Because Chapters IV and V add ten
contents lines, the second contents page is redrawn with even spacing.

The compressed copy is lossless: every page's content streams are
recompressed and identical objects are merged (the full PDF repeats the same
letterhead stream on every page). verify() then checks page count, page size,
text, images and fonts page by page against the full PDF.

Needs PyMuPDF, pypdf and Microsoft Word:  pip install pymupdf pypdf
    python build_chapters_1_5_pdf.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf
from pypdf import PdfReader, PdfWriter

from build_chapters_1_4_pdf import CH4_TOC, ROOT, main as build

DOCX = ROOT / "ToothWise_Chapters_4_5_paper.docx"
PDF = ROOT / "ToothWise_Chapters_4_5_paper.pdf"
DST = ROOT / "ToothWise_Chapters_1-5.pdf"
SMALL = ROOT / "ToothWise_Chapters_1-5_compressed.pdf"

CH5_TOC = [
    ("CHAPTER V: SUMMARY OF FINDINGS, CONCLUSIONS, AND RECOMMENDATIONS", "CHAPTER V", True, 124.8),
    ("5.1 Summary of Findings", "5.1 Summary of Findings", False, 129.4),
    ("5.2 Conclusions", "5.2 Conclusions", False, 129.4),
    ("5.3 Recommendations", "5.3 Recommendations", False, 129.4),
]


def compress(src: Path, dst: Path):
    writer = PdfWriter(clone_from=PdfReader(src))
    for page in writer.pages:
        page.compress_content_streams(level=9)
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    with open(dst, "wb") as fh:
        writer.write(fh)


def fingerprint(page):
    images = sorted(hashlib.sha1(page.parent.extract_image(img[0])["image"]).hexdigest()
                    for img in page.get_images(full=True))
    fonts = sorted({f[3] for f in page.get_fonts(full=True)})
    return (tuple(page.mediabox), page.get_text(), tuple(images), tuple(fonts))


def verify(full: Path, small: Path):
    a, b = pymupdf.open(full), pymupdf.open(small)
    assert len(a) == len(b), f"page count {len(a)} != {len(b)}"
    bad = [i + 1 for i in range(len(a)) if fingerprint(a[i]) != fingerprint(b[i])]
    assert not bad, f"pages differ: {bad}"
    return len(a)


def main():
    info = build(docx=DOCX, pdf=PDF, dst=DST, toc_entries=CH4_TOC + CH5_TOC, label="Chapters IV-V")
    ch5_first = info["heading_pages"]["CHAPTER V"]
    print(f"Chapter IV: pages {info['first']}-{ch5_first - 1}; "
          f"Chapter V: pages {ch5_first}-{info['refs'] - 1}; References from page {info['refs']}")
    compress(DST, SMALL)
    n = verify(DST, SMALL)
    mb = lambda p: p.stat().st_size / 1e6
    print(f"{DST.name}: {mb(DST):.1f} MB; {SMALL.name}: {mb(SMALL):.1f} MB; "
          f"all {n} pages match (size, text, images, fonts)")


if __name__ == "__main__":
    main()
