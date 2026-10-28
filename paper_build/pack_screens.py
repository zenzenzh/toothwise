"""Size the Section 3.10 screenshots so that every page they occupy is full.

    python paper_build/pack_screens.py      # after layout_pass.py; updates layout.json

The screenshots follow one another with no text in between, so moving text
cannot fill the gaps. Instead this measures, from a built PDF, the space each
caption takes and the space left on the first page, then splits the
screenshots into consecutive page groups and picks one scale per page so the
images fill it (dynamic programming over the groupings, within each image's
minimum and maximum width). The widths are written to layout.json.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pymupdf
from PIL import Image

import build_paper as bp
from layout_pass import BODY_BOT, BODY_TOP, LAYOUT, apply, caption_line

SAFETY = 6            # pt kept free at the bottom of each page
PAGE_H = BODY_BOT - BODY_TOP


def limits(f):
    """(min, max) width in inches for one screenshot or one half of a pair."""
    w, h = Image.open(bp.FIGS / f["file"]).size
    r = h / w
    if r > 1.0:                        # tall: portrait pages and the full results page
        if f.get("cols") == 3:
            return 1.7, 1.95
        return (2.2, 2.95) if f.get("pair") else ((3.4, 4.8) if "result" in f["file"] else (2.8, 3.6))
    return 4.0, 6.0


def main():
    layout = json.loads(LAYOUT.read_text(encoding="utf-8")) if LAYOUT.exists() else {"move": {}, "width": {}}
    base = bp.parse(bp.CONTENT.read_text(encoding="utf-8"))
    blocks = apply(base, layout)
    idx = [i for i, b in enumerate(blocks)
           if (b["kind"] == "FIG" and b["key"].startswith("s_")) or b["kind"] == "FIGPAIR"]
    out = bp.ROOT / f"{bp.NAME}.docx"
    bp.write(blocks).save(out)
    doc = pymupdf.open(bp.to_pdf(out))

    items = []                         # one per block: ratio h/w at width 1, fixed height, limits
    first_top = None
    for i in idx:
        b = blocks[i]
        figs = [dict(f, pair=True, cols=len(b["figs"])) for f in b["figs"]] if b["kind"] == "FIGPAIR" else [b]
        n = figs[0]["n"]
        page, y0, y1 = caption_line(doc, f"Figure {n} ")
        imgs = [im["bbox"] for im in doc[page].get_image_info()
                if im["bbox"][3] <= y0 + 3 and im["bbox"][2] - im["bbox"][0] < 500]
        img_top = min(r[1] for r in imgs)
        img_bot = max(r[3] for r in imgs)
        if first_top is None:
            prev_bottom = None
            # where would the first screenshot start: right after the 3.10 intro text
            for blk in doc[page - 1].get_text("dict")["blocks"] if img_top < BODY_TOP + 14 else []:
                if BODY_TOP - 9 < blk["bbox"][1] < BODY_BOT:
                    prev_bottom = max(prev_bottom or 0, blk["bbox"][3])
            first_top = (prev_bottom + 12) if prev_bottom else img_top - 8
        if b["kind"] == "FIGPAIR":
            caps = [caption_line(doc, f"Figure {f['n']} ") for f in b["figs"]]
            cap_bot = max(c[2] for c in caps)
        else:
            cap_bot = y1
        fixed = (cap_bot - img_bot) + 12      # caption plus the space before the next image (measured)
        lims = [limits(f) for f in figs]
        ratios = [Image.open(bp.FIGS / f["file"]).size[1] / Image.open(bp.FIGS / f["file"]).size[0] for f in figs]
        items.append({"block": i, "figs": figs, "fixed": fixed, "ratios": ratios, "lims": lims})

    banned = set()                     # groupings that overflowed in a real build even at minimum size

    def group_cost(a, b, avail):
        """Best scale for items a..b-1 on one page with `avail` pt: (leftover, scale) or None."""
        if (a, b) in banned:
            return None
        fixed = sum(it["fixed"] for it in items[a:b])
        hmax = sum(max(r * lim[1] for r, lim in zip(it["ratios"], it["lims"])) * 72 for it in items[a:b])
        smin = max(lim[0] / lim[1] for it in items[a:b] for lim in it["lims"])
        room = avail - SAFETY - fixed
        if room <= 0:
            return None
        s = min(1.0, room / hmax)
        if s < smin:
            return None
        return room - s * hmax, s

    first_avail = BODY_BOT - first_top
    n = len(items)

    def plan():
        @lru_cache(None)
        def best(a, first):
            if a == n:
                return 0.0, ()
            avail = first_avail if first else PAGE_H
            out = None
            for b in range(a + 1, n + 1):
                g = group_cost(a, b, avail)
                if g is None:
                    continue
                leftover, s = g
                cost = (0 if b == n else leftover) + 40 * (1 - s)     # fill pages; prefer large images
                rest = best(b, False)
                if out is None or cost + rest[0] < out[0]:
                    out = (cost + rest[0], ((a, b, s),) + rest[1])
            if first:                                              # or leave the intro page and start fresh
                rest = best(a, False)
                alt = (rest[0] + first_avail, rest[1], True)
                if out is None or alt[0] < out[0]:
                    return alt
            return (out[0], out[1], False) if out else (1e9, (), False)
        return best(0, True)

    def store(groups, scales, fresh_first):
        widths = dict(layout.get("width", {}))
        breaks = []
        for g, (a, b, _) in enumerate(groups):
            if g > 0 or fresh_first:
                breaks.append(items[a]["figs"][0]["key"])
            for it in items[a:b]:
                for f, lim in zip(it["figs"], it["lims"]):
                    widths[f["key"]] = round(lim[1] * scales[g], 2)
        layout["width"], layout["break"] = widths, breaks
        LAYOUT.write_text(json.dumps(layout, indent=1, ensure_ascii=False), encoding="utf-8")

    def overflowing(groups):
        bp.write(apply(base, layout)).save(out)
        doc = pymupdf.open(bp.to_pdf(out))
        bad = []
        for g, (a, b, _) in enumerate(groups):
            p1 = caption_line(doc, f"Figure {items[a]['figs'][0]['n']} ")[0]
            p2 = caption_line(doc, f"Figure {items[b - 1]['figs'][-1]['n']} ")[0]
            if p1 != p2:
                bad.append(g)
        return bad

    for rnd in range(14):
        _, groups, fresh_first = plan()
        scales = [s for _, _, s in groups]
        replan = False
        for _ in range(4):
            store(groups, scales, fresh_first)
            bad = overflowing(groups)
            print(f"round {rnd}: groups {[(a, b) for a, b, _ in groups]} overflowing {bad}")
            if not bad:
                break
            for g in bad:
                a, b, _ = groups[g]
                floor = max(lim[0] / lim[1] for it in items[a:b] for lim in it["lims"])
                if scales[g] <= floor + 1e-6:
                    banned.add((a, b))
                    replan = True
                scales[g] = max(floor, scales[g] - 0.05)
            if replan:
                break
        if not replan and not bad:
            break
        if not replan:                      # still overflowing after shrinking: ban and re-plan
            for g in bad:
                banned.add(groups[g][:2])
    for (a, b, _), sc in zip(groups, scales):
        print(f"page: {[items[k]['figs'][0]['key'] for k in range(a, b)]} scale {sc:.2f}")
    print("wrote", LAYOUT.name)


if __name__ == "__main__":
    main()
