"""Remove white space left by figures and tables that did not fit on a page.

    python paper_build/layout_pass.py          # search, then write layout.json
    python paper_build/build_paper.py          # builds using layout.json

Word and LibreOffice push a figure that does not fit to the next page and
leave the rest of the page blank. This pass does what a typesetter would:
it builds the paper, finds every figure or table that was pushed to the top
of a page while the page before it ends early, and then either

  * moves the following paragraph (with its heading) above the figure, so the
    text fills the gap and the figure follows on the next page, or
  * for screenshots and charts only, shrinks the image just enough to fit
    (never below MIN_WIDTH, so text in diagrams stays legible in print).

A change is kept only if the total white space in the paper goes down. The
result is stored in layout.json as "move this float N blocks later" and
"print this figure at W inches", which build_paper.py applies on every build.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pymupdf

import build_paper as bp

LAYOUT = Path(__file__).with_name("layout.json")
BODY_TOP, BODY_BOT = 121, 712          # body area of the letterhead pages, in pt
GAP_MIN = 0.35 * 72                    # gaps smaller than this are ignored
MOVABLE = {"P", "PN", "-", "NUM", "###", "###+", "TABLE"}
HEADINGS = {"###", "###+"}


def min_width(b):
    """Smallest width a float may be printed at, or None if it must not shrink."""
    if b["kind"] == "FIGPAIR":
        return 2.3 if len(b["figs"]) == 2 else 1.7
    if b["kind"] != "FIG":
        return None
    if b["key"].startswith("s_"):
        return 3.4 if b["width"] < 4 else 4.2       # portrait / landscape screenshots
    if b["key"] in ("curves", "final", "perclass", "cm"):
        return 5.0                                  # charts
    if b["key"] in ("usecase", "erd", "dfd1a", "dfd1b", "gantt"):
        return 5.4                                  # keeps diagram text at 8 pt or more in print
    return None                                     # other diagrams keep their size


def content_bottom(page):
    ys = []
    for blk in page.get_text("dict")["blocks"]:
        x0, y0, x1, y1 = blk["bbox"]
        if BODY_TOP - 9 < y0 < BODY_BOT + 3 and 100 < x0 < 550:
            ys.append(y1)
    for im in page.get_image_info():
        r = im["bbox"]
        if r[1] > BODY_TOP - 9 and r[3] < BODY_BOT + 4 and r[2] - r[0] < 500:
            ys.append(r[3])
    for dr in page.get_drawings():
        r = dr["rect"]
        if BODY_TOP - 6 < r.y0 < BODY_BOT + 3 and 105 < r.x0 < 545 and r.width < 450:
            ys.append(r.y1)
    return max(ys) if ys else BODY_TOP


def chapter_starts(doc):
    starts = set()
    for i, p in enumerate(doc):
        lines = [bp.norm(l) for l in p.get_text().splitlines()]
        if any(l.startswith("CHAPTER ") and len(l) < 14 for l in lines[:4]) or "REFERENCES" in lines[:3]:
            starts.add(i)
    return starts


def caption_line(doc, label):
    """(page index, y0, y1) of the bold caption line that starts with label."""
    for i, p in enumerate(doc):
        for blk in p.get_text("dict")["blocks"]:
            for line in blk.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                if spans and spans[0]["flags"] & 16 and "".join(s["text"] for s in spans).startswith(label):
                    return i, line["bbox"][1], blk["bbox"][3]
    return None


def measure(blocks):
    doc_path = bp.ROOT / f"{bp.NAME}.docx"
    bp.write(blocks).save(doc_path)
    doc = pymupdf.open(bp.to_pdf(doc_path))
    starts = chapter_starts(doc)
    gaps = {}
    for i in range(3, len(doc) - 1):
        if i + 1 in starts:
            continue
        g = BODY_BOT - content_bottom(doc[i])
        if g > GAP_MIN:
            gaps[i] = g
    pushed = []
    for k, b in enumerate(blocks):
        if b["kind"] not in ("FIG", "FIGPAIR", "TABLE"):
            continue
        n = b["figs"][0]["n"] if b["kind"] == "FIGPAIR" else b["n"]
        label = f"Table {n} " if b["kind"] == "TABLE" else f"Figure {n} "
        hit = caption_line(doc, label)
        if not hit:
            continue
        page, y0, y1 = hit
        if b["kind"] == "TABLE":
            top, img_h = y0, None
        else:
            imgs = [im["bbox"] for im in doc[page].get_image_info()
                    if im["bbox"][3] <= y0 + 3 and im["bbox"][2] - im["bbox"][0] < 500]
            if not imgs:
                continue
            top = min(r[1] for r in imgs)
            img_h = max(r[3] for r in imgs) - top
        if top < BODY_TOP + 14 and page - 1 in gaps and page not in starts:
            pushed.append({"index": k, "gap": gaps[page - 1], "height": y1 - top, "img_h": img_h})
    return sum(gaps.values()), pushed, len(doc)


def apply(blocks, layout):
    """Apply widths and moves from a layout dict to a parsed block list."""
    blocks = copy.deepcopy(blocks)
    for b in blocks:
        if b["kind"] == "FIG" and b["key"] in layout.get("width", {}):
            b["width"] = layout["width"][b["key"]]
        if b["kind"] == "FIGPAIR":
            for f in b["figs"]:
                if f["key"] in layout.get("width", {}):
                    f["width"] = layout["width"][f["key"]]
    for b in blocks:
        if float_key(b) in layout.get("break", []):
            b["page_break"] = True
    for key, steps in layout.get("move", {}).items():
        k = next(i for i, b in enumerate(blocks) if float_key(b) == key)
        blk = blocks.pop(k)
        blocks.insert(k + steps, blk)
    return blocks


def float_key(b):
    if b["kind"] == "FIGPAIR":
        return b["figs"][0]["key"]
    return b.get("key")


def try_shrink(blocks, p, layout):
    b = blocks[p["index"]]
    floor = min_width(b)
    if floor is None or not p["img_h"]:
        return None
    need = p["height"] - p["gap"] + 4
    scale = (p["img_h"] - need) / p["img_h"]
    if scale <= 0:
        return None
    widths = dict(layout.get("width", {}))
    figs = b["figs"] if b["kind"] == "FIGPAIR" else [b]
    for f in figs:
        w = round(f["width"] * scale - 0.02, 2)
        if w < floor:
            return None
        widths[f["key"]] = w
    return {**layout, "width": widths}


def try_move(blocks, p, layout):
    k = p["index"]
    b = blocks[k]
    steps = 0
    j = k + 1
    while j < len(blocks) and blocks[j]["kind"] in HEADINGS:      # a heading travels with its text
        j += 1
        steps += 1
    if j >= len(blocks) or blocks[j]["kind"] not in MOVABLE:
        return None
    if b["kind"] == "TABLE" and blocks[j]["kind"] == "TABLE":
        return None                                               # keep table numbers in order
    steps += 1
    moves = dict(layout.get("move", {}))
    moves[float_key(b)] = moves.get(float_key(b), 0) + steps
    return {**layout, "move": moves}


def main():
    base = bp.parse(bp.CONTENT.read_text(encoding="utf-8"))
    layout = {"move": {}, "width": {}}
    score, pushed, pages = measure(apply(base, layout))
    print(f"start: {score / 72:.1f} in of white space, {pages} pages")
    frozen = set()
    for _ in range(60):
        cand = [p for p in pushed if float_key(apply(base, layout)[p["index"]]) not in frozen]
        if not cand:
            break
        p = cand[0]
        blocks = apply(base, layout)
        key = float_key(blocks[p["index"]])
        best = None
        for attempt in (try_shrink, try_move):
            trial = attempt(blocks, p, layout)
            if trial is None:
                continue
            s, pu, pg = measure(apply(base, trial))
            if s < score - 8 and (best is None or s < best[0]):
                best = (s, pu, pg, trial, attempt.__name__)
        if best:
            score, pushed, pages, layout, how = best
            print(f"  {key}: {how} -> {score / 72:.1f} in, {pages} pages")
        else:
            frozen.add(key)
            print(f"  {key}: no improvement")
    LAYOUT.write_text(json.dumps(layout, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"done: {score / 72:.1f} in of white space; wrote {LAYOUT.name}")


if __name__ == "__main__":
    main()
