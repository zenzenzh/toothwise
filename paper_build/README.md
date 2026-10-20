# Building the Chapters 1-4 paper

`ToothWise_Chapters_1-4_updated.docx` and `.pdf` (repo root) are generated from this folder.

| File | Role |
|---|---|
| `content.txt` | The paper text in a small markup (see the docstring of `build_paper.py`). Edit this to change the paper. |
| `old_text.txt` | Paragraphs extracted from the earlier `ToothWise_Chapters_1-4_corrected.pdf`; `content.txt` pulls unchanged ones in with `=`. |
| `figures/` | Every figure, as opaque RGB PNGs sized for print. |
| `assets/letterhead.png` | The UDM header, logos and frame lines placed behind every page. |
| `build_paper.py` | Builds the .docx with python-docx, exports the PDF with LibreOffice, then fills in the table of contents from the PDF. |
| `make_diagrams.py` | Redraws the Chapter III diagrams (use case, ERD, DFDs, Gantt, Agile cycle). |
| `make_charts.py` | Re-plots the Chapter IV charts from `chapter4_figures/*.json`. |
| `layout_pass.py` | Removes white space: finds figures/tables pushed to the next page and moves the following text up (or shrinks screenshots/charts slightly). Writes `layout.json`. |
| `pack_screens.py` | Sizes the Section 3.10 screenshots so each page they use is full; adds to `layout.json`. |
| `layout.json` | Result of the two passes above; `build_paper.py` applies it on every build. |
| `REFERENCES_CHECK.md` | What was verified, fixed, replaced, or added in the reference list, with sources. |
| `capture_screens.py` | Takes the Section 3.10 screenshots from a running, seeded instance (backend :8000, frontend :3000). |

```bash
pip install python-docx pymupdf playwright matplotlib   # plus LibreOffice (soffice) on PATH
python paper_build/make_diagrams.py paper_build/figures
python paper_build/make_charts.py paper_build/figures
python paper_build/layout_pass.py     # after editing content.txt (about 10 min)
python paper_build/pack_screens.py
python paper_build/build_paper.py
```

Times New Roman is set in the .docx; on a machine without it LibreOffice substitutes the
metric-compatible Liberation Serif, so line breaks and page numbers stay the same.
