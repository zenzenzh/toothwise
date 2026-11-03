"""Draw the Chapter III design diagrams for the paper as print-ready PNGs.

Every diagram is an SVG whose user units are PDF points at the width it is
printed (W units = 6.0 in on the page), so a font-size of 9 here prints at
about 9 pt. Lines are at least 0.9 pt and pure black so nothing fades on a
laser printer. Each SVG is rendered by Chromium at 5x (about 390 dpi).

    python paper_build/make_diagrams.py OUT_DIR
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

FONT = "Liberation Sans, Arial, Helvetica, sans-serif"
INK = "#000"
LW = 1.0          # default stroke width (pt)


# ---------------------------------------------------------------- primitives
def text(x, y, s, size=9, anchor="middle", weight="normal", style="normal", fill=INK):
    lines = s.split("\n")
    out = []
    lh = size * 1.18
    y0 = y - (len(lines) - 1) * lh / 2
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x:.1f}" y="{y0 + i * lh:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-style="{style}" fill="{fill}" dominant-baseline="central">'
            f"{escape(line)}</text>")
    return "".join(out)


def rect(x, y, w, h, rx=0, fill="#fff", sw=LW, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{INK}" stroke-width="{sw}"{d}/>')


def line(x1, y1, x2, y2, sw=LW, dash=None, arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-end="url(#arr)"' if arrow else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" '
            f'stroke-width="{sw}"{d}{m}/>')


def poly(points, sw=LW, dash=None, arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-end="url(#arr)"' if arrow else ""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="{sw}"{d}{m}/>'


DEFS = (
    '<defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" '
    'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#000"/></marker></defs>')


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}">{DEFS}<rect width="{w}" height="{h}" fill="#fff"/>{body}</svg>')


# ------------------------------------------------------------ 1. agile cycle
def agile():
    W, H = 470, 470
    steps = ["Planning", "Requirements\nAnalysis", "System\nDesign", "Development",
             "Testing", "Evaluation", "Refinement"]
    bw, bh, x = 150, 40, 120
    gap = (H - 20 - bh * len(steps)) / (len(steps) - 1)
    b = []
    ys = []
    for i, s in enumerate(steps):
        y = 10 + i * (bh + gap)
        ys.append(y)
        b.append(rect(x, y, bw, bh, rx=7, sw=1.3))
        b.append(text(x + bw / 2, y + bh / 2, s, size=12))
        if i:
            b.append(line(x + bw / 2, ys[i - 1] + bh, x + bw / 2, y, sw=1.2, arrow=True))
    xr = x + bw + 55
    b.append(poly([(x + bw, ys[-1] + bh / 2), (xr, ys[-1] + bh / 2), (xr, ys[0] + bh / 2),
                   (x + bw + 1, ys[0] + bh / 2)], sw=1.2, dash="5 3", arrow=True))
    b.append(text(xr + 8, H / 2, "next\niteration", size=12, anchor="start", style="italic"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------- 2. use case
def actor(x, y, name, above=False):
    b = [f'<circle cx="{x}" cy="{y}" r="7" fill="#fff" stroke="#000" stroke-width="1.1"/>',
         line(x, y + 7, x, y + 26, 1.1), line(x - 11, y + 14, x + 11, y + 14, 1.1),
         line(x, y + 26, x - 9, y + 40, 1.1), line(x, y + 26, x + 9, y + 40, 1.1),
         text(x, y - 22 if above else y + 52, name, size=9, weight="bold")]
    return "".join(b)


def ellipse(cx, cy, rx, ry, label, size=8.6):
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#fff" stroke="#000" stroke-width="1.1"/>'
            + text(cx, cy, label, size=size))


def use_case():
    W, H = 470, 560
    bx0, bx1 = 100, 398
    b = [rect(bx0, 8, bx1 - bx0, H - 16, sw=1.3), text((bx0 + bx1) / 2, 22, "ToothWise System", size=10.5, weight="bold")]
    L, rx = 182, 72            # left column
    R, rr = 342, 50            # right column
    ry = 17
    left = {
        "staff": (58, "Manage Staff\nAccounts"),
        "audit": (104, "Review Audit Trail"),
        "patients": (152, "Manage Patient\nRecords"),
        "delete": (204, "Delete Patient\nRecord"),
        "screen": (262, "Perform AI Dental\nScreening"),
        "review": (324, "Review Findings and\nRecommendations"),
        "tier": (384, "Confirm Risk Tier"),
        "note": (434, "Add Clinical Note"),
        "pdf": (486, "Generate PDF Report"),
    }
    right = {
        "auth": (128, "Authenticate\nUser"),
        "pw": (196, "Reset or Change\nPassword"),
        "upload": (262, "Upload Intraoral\nImage"),
        "history": (448, "View Own\nScreening History"),
        "ask": (510, "Ask AI Assistant"),
    }
    actors = {"rec": (40, 92), "den": (40, 262), "asst": (40, 420), "pat": (440, 448)}
    assoc = {
        "rec": ["patients"],
        "den": ["staff", "audit", "patients", "delete", "screen", "review", "tier", "note", "pdf"],
        "asst": ["patients", "screen", "review", "pdf"],
    }
    for a, ucs in assoc.items():
        x0, y0 = actors[a][0] + 10, actors[a][1] + 16
        for u in ucs:
            b.append(line(x0, y0, L - rx + 1, left[u][0], 0.9))
    px, py = actors["pat"][0] - 10, actors["pat"][1] + 16
    for u in ("history", "ask"):
        b.append(line(px, py, R + rr - 1, right[u][0], 0.9))

    def lab(x, y, s):
        b.append(f'<rect x="{x - 22}" y="{y - 5.5}" width="44" height="11" fill="#fff"/>')
        b.append(text(x, y, s, size=7.8))

    def dash(pts):
        b.append(poly(pts, 0.9, dash="4 2.5", arrow=True))

    # <<include>> Authenticate User (staff use cases)
    ax, ay = R - rr, right["auth"][0]
    for u, dy in (("staff", -8), ("audit", -3), ("patients", 3)):
        y = left[u][0]
        dash([(L + rx - 2, y - (6 if u == "staff" else 0)), (ax + 3, ay + dy)])
    dash([(L + rx - 14, left["screen"][0] - 13), (ax + 12, ay + 13)])
    lab(268, 104, "«include»")
    lab(268, 196, "«include»")
    # Reset or Change Password <<extend>> Authenticate User
    dash([(R, right["pw"][0] - ry), (R, ay + ry)])
    lab(R + 30, (right["pw"][0] + ay) / 2, "«extend»")
    # Perform screening <<include>> upload image
    dash([(L + rx, left["screen"][0]), (R - rr, right["upload"][0])])
    lab(266, 252, "«include»")
    # patient history <<include>> authenticate (routed down the right edge)
    hy = right["history"][0]
    dash([(R + 30, hy - 14), (R + 52, hy - 34), (R + 52, ay + 36), (R + 32, ay + 14)])
    lab(R + 30, (hy + ay) / 2 + 40, "«include»")
    # <<extend>>: arrow points at the extended use case
    dash([(L, left["delete"][0] - ry), (L, left["patients"][0] + ry)])
    lab(L + 34, (left["delete"][0] + left["patients"][0]) / 2, "«extend»")
    for u, xo in (("tier", 262), ("note", 272), ("pdf", 282)):
        y = left[u][0]
        sx = L + rx * (0.92 if u == "tier" else 0.8)
        dash([(L + rx - (2 if u == "tier" else 10), y - (0 if u == "tier" else 7)), (xo, y - 14 if u != "tier" else y),
              (xo, left["review"][0] + 4 + (xo - 262) / 2), (L + rx - 1, left["review"][0] + 3)])
    lab(304, 410, "«extend»")
    for k, (y, s) in left.items():
        b.append(ellipse(L, y, rx, ry, s))
    for k, (y, s) in right.items():
        b.append(ellipse(R, y, rr, ry, s, size=8.4))
    b.append(actor(*actors["rec"], "Receptionist"))
    b.append(actor(*actors["den"], "Dentist\n(Administrator)", above=True))
    b.append(actor(*actors["asst"], "Dental\nAssistant"))
    b.append(actor(*actors["pat"], "Patient"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- 3. ERD
TABLES = {
    "dentists": [("PK", "id", "SERIAL"), ("", "full_name", "VARCHAR(120)"), ("", "first_name", "VARCHAR(60)"),
                 ("", "middle_name", "VARCHAR(60)"), ("", "last_name", "VARCHAR(60)"),
                 ("UQ", "email", "VARCHAR(150)"), ("", "hashed_password", "VARCHAR(255)"),
                 ("", "role", "dentistrole"), ("", "license_no", "VARCHAR(60)"), ("", "is_active", "BOOLEAN"),
                 ("", "created_at", "TIMESTAMP")],
    "patients": [("PK", "id", "SERIAL"), ("", "full_name", "VARCHAR(120)"), ("", "first_name", "VARCHAR(60)"),
                 ("", "middle_name", "VARCHAR(60)"), ("", "last_name", "VARCHAR(60)"), ("", "birthdate", "DATE"),
                 ("", "gender", "gender"), ("", "contact_number", "VARCHAR(30)"), ("", "address", "VARCHAR(255)"),
                 ("UQ", "email", "VARCHAR(150)"), ("", "hashed_password", "VARCHAR(255)"),
                 ("", "is_active", "BOOLEAN"), ("", "created_at", "TIMESTAMP")],
    "screenings": [("PK", "id", "SERIAL"), ("FK", "patient_id", "INTEGER"), ("FK", "dentist_id", "INTEGER"),
                   ("", "image_path", "VARCHAR(255)"), ("", "image_width", "INTEGER"),
                   ("", "image_height", "INTEGER"), ("", "risk_level", "risklevel"), ("", "risk_score", "INTEGER"),
                   ("", "yolov8_ms", "FLOAT"), ("", "yolov12_ms", "FLOAT"), ("", "created_at", "TIMESTAMP")],
    "screening_images": [("PK,FK", "screening_id", "INTEGER"), ("", "data", "BYTEA"),
                         ("", "created_at", "TIMESTAMP")],
    "detections": [("PK", "id", "SERIAL"), ("FK", "screening_id", "INTEGER"), ("", "label", "VARCHAR(40)"),
                   ("", "confidence", "FLOAT"), ("", "x1", "FLOAT"), ("", "y1", "FLOAT"), ("", "x2", "FLOAT"),
                   ("", "y2", "FLOAT"), ("", "source_model", "VARCHAR(20)"), ("", "detection_set", "VARCHAR(20)")],
    "recommendations": [("PK", "id", "SERIAL"), ("FK", "screening_id", "INTEGER"), ("", "text", "TEXT"),
                        ("", "priority", "INTEGER"), ("", "order_index", "INTEGER")],
    "clinical_notes": [("PK", "id", "SERIAL"), ("FK", "screening_id", "INTEGER"), ("FK", "dentist_id", "INTEGER"),
                       ("", "body", "TEXT"), ("", "created_at", "TIMESTAMP")],
    "audit_logs": [("PK", "id", "SERIAL"), ("FK", "actor_dentist_id", "INTEGER"), ("", "actor_email", "VARCHAR(150)"),
                   ("", "action", "VARCHAR(60)"), ("", "entity_type", "VARCHAR(40)"), ("", "entity_id", "INTEGER"),
                   ("", "details", "TEXT"), ("", "created_at", "TIMESTAMPTZ")],
}
RH, HH = 11.6, 15.0     # row height, header height


def table_box(name, x, y, w):
    rows = TABLES[name]
    h = HH + RH * len(rows) + 3
    b = [rect(x, y, w, h, sw=1.1), f'<rect x="{x}" y="{y}" width="{w}" height="{HH}" fill="#d9d9d9" stroke="#000" stroke-width="1.1"/>',
         text(x + w / 2, y + HH / 2, name, size=9, weight="bold"), line(x + 24, y + HH, x + 24, y + h, 0.6)]
    for i, (k, col, typ) in enumerate(rows):
        cy = y + HH + 1.5 + RH * (i + 0.5)
        b.append(text(x + 12, cy, k, size=6.8 if "," in k else 7.8, weight="bold"))
        b.append(text(x + 28, cy, col, size=8.4, anchor="start", weight="bold" if k else "normal"))
        b.append(text(x + w - 4, cy, typ, size=8.0, anchor="end"))
    return "".join(b), h


def row_y(name, y, col):
    for i, (_, c, _) in enumerate(TABLES[name]):
        if c == col:
            return y + HH + 1.5 + RH * (i + 0.5)
    raise KeyError(col)


def end_mark(x, y, direction, kind):
    """Crow's-foot end marker at (x, y); direction is the unit vector pointing
    from the line into the table edge ('r','l','u','d')."""
    dx, dy = {"r": (1, 0), "l": (-1, 0), "d": (0, 1), "u": (0, -1)}[direction]
    px, py = -dy, dx            # perpendicular
    b = []
    if kind in ("one", "one_only"):
        for off in (5, 9):
            cx, cy = x - dx * off, y - dy * off
            b.append(line(cx - px * 5, cy - py * 5, cx + px * 5, cy + py * 5, 1.0))
    if kind == "zero_one":
        cx, cy = x - dx * 6, y - dy * 6
        b.append(line(cx - px * 5, cy - py * 5, cx + px * 5, cy + py * 5, 1.0))
        ox, oy = x - dx * 14, y - dy * 14
        b.append(f'<circle cx="{ox}" cy="{oy}" r="3.6" fill="#fff" stroke="#000" stroke-width="1"/>')
    if kind == "many":
        bx, by = x - dx * 10, y - dy * 10
        for s in (-1, 0, 1):
            b.append(line(bx, by, x + px * 5.5 * s, y + py * 5.5 * s, 1.0))
        ox, oy = x - dx * 15, y - dy * 15
        b.append(f'<circle cx="{ox}" cy="{oy}" r="3.6" fill="#fff" stroke="#000" stroke-width="1"/>')
    return "".join(b)


def erd():
    W, H = 470, 585
    w = 176
    xl, xr = 18, W - w - 2
    pos = {"dentists": (xl, 4), "clinical_notes": (xl, 0), "audit_logs": (xl, 0), "detections": (xl, 0),
           "patients": (xr, 4), "screenings": (xr, 0), "screening_images": (xr, 0), "recommendations": (xr, 0)}
    hs = {n: HH + RH * len(TABLES[n]) + 3 for n in TABLES}
    gaps = {"clinical_notes": 34, "audit_logs": 22, "detections": 30,
            "screenings": 34, "screening_images": 30, "recommendations": 22}
    order_l = ["dentists", "clinical_notes", "audit_logs", "detections"]
    order_r = ["patients", "screenings", "screening_images", "recommendations"]
    for order in (order_l, order_r):
        for prev, cur in zip(order, order[1:]):
            x, _ = pos[cur]
            pos[cur] = (x, pos[prev][1] + hs[prev] + gaps[cur])
    b = []
    P = lambda n: pos[n]
    gx0, gx1 = xl + w, xr          # the gap between the two columns

    def label(x, y, s):
        b.append(f'<rect x="{x - 25}" y="{y - 6}" width="50" height="12" fill="#fff"/>')
        b.append(text(x, y, s, size=8, style="italic"))

    # dentists 1 -- 0..* screenings  (performs)
    y1 = row_y("dentists", P("dentists")[1], "id")
    y2 = row_y("screenings", P("screenings")[1], "dentist_id")
    xm = gx0 + 40
    b.append(poly([(gx0, y1), (xm, y1), (xm, y2), (gx1, y2)]))
    b.append(end_mark(gx0, y1, "l", "zero_one")); b.append(end_mark(gx1, y2, "r", "many"))
    label(xm, (y1 + y2) / 2 - 40, "performs")
    # patients 1 -- 0..* screenings (undergoes): vertical, right column
    xp = xr + w - 40
    yb = P("patients")[1] + hs["patients"]
    yt = P("screenings")[1]
    b.append(line(xp, yb, xp, yt)); b.append(end_mark(xp, yb, "u", "one")); b.append(end_mark(xp, yt, "d", "many"))
    label(xp - 52, (yb + yt) / 2, "undergoes")
    # dentists 1 -- 0..* clinical_notes (authors): vertical, left column
    xd = xl + 40
    yb = P("dentists")[1] + hs["dentists"]
    yt = P("clinical_notes")[1]
    b.append(line(xd, yb, xd, yt)); b.append(end_mark(xd, yb, "u", "zero_one")); b.append(end_mark(xd, yt, "d", "many"))
    label(xd + 50, (yb + yt) / 2, "authors")
    # dentists 0..1 -- 0..* audit_logs (records): routed down the left margin
    y1 = row_y("dentists", P("dentists")[1], "id") + 4
    y2 = row_y("audit_logs", P("audit_logs")[1], "actor_dentist_id")
    b.append(poly([(xl, y1), (4, y1), (4, y2), (xl, y2)]))
    b.append(end_mark(xl, y1, "r", "zero_one")); b.append(end_mark(xl, y2, "r", "many"))
    b.append(f'<g transform="translate(9,{(y1 + y2) / 2 + 60}) rotate(-90)">'
             f'<rect x="-22" y="-6" width="44" height="12" fill="#fff"/>{text(0, 0, "records", size=8, style="italic")}</g>')
    # screenings 1 -- 0..* clinical_notes (has)
    sy = P("screenings")[1]
    y1 = row_y("screenings", sy, "id")
    y2 = row_y("clinical_notes", P("clinical_notes")[1], "screening_id")
    xm2 = gx0 + 60
    b.append(poly([(gx1, y1), (xm2, y1), (xm2, y2), (gx0, y2)]))
    b.append(end_mark(gx1, y1, "r", "one")); b.append(end_mark(gx0, y2, "l", "many"))
    label(xm2 + 14, y2 - 9, "has")
    # screenings 1 -- 0..* detections (contains)
    y1b = y1 + 4
    y2 = row_y("detections", P("detections")[1], "screening_id")
    xm3 = gx0 + 22
    b.append(poly([(gx1, y1b + 50), (xm3, y1b + 50), (xm3, y2), (gx0, y2)]))
    b.append(end_mark(gx1, y1b + 50, "r", "one")); b.append(end_mark(gx0, y2, "l", "many"))
    label(xm3, y2 - 70, "contains")
    # screenings 1 -- 0..1 screening_images (stores photo): vertical
    yb = sy + hs["screenings"]
    yt = P("screening_images")[1]
    b.append(line(xp, yb, xp, yt)); b.append(end_mark(xp, yb, "u", "one")); b.append(end_mark(xp, yt, "d", "zero_one"))
    label(xp - 56, (yb + yt) / 2, "stores photo")
    # screenings 1 -- 0..* recommendations (yields): routed via the gap
    y1c = yb - 12
    y2 = row_y("recommendations", P("recommendations")[1], "screening_id")
    xm4 = gx1 - 22
    b.append(poly([(gx1, y1c), (xm4, y1c), (xm4, y2), (gx1, y2)]))
    b.append(end_mark(gx1, y1c, "r", "one")); b.append(end_mark(gx1, y2, "r", "many"))
    label(xm4 - 26, (y1c + y2) / 2, "yields")

    for n, (x, y) in pos.items():
        s, _ = table_box(n, x, y, w)
        b.append(s)
    # legend under the right column
    ly = P("recommendations")[1] + hs["recommendations"] + 16
    lx = xr
    b.append(text(lx, ly, "Crow's foot notation", size=8.6, anchor="start", weight="bold"))
    for i, (kind, lab) in enumerate((("one", "exactly one"), ("zero_one", "zero or one"), ("many", "zero or many"))):
        yy = ly + 14 + i * 13
        b.append(line(lx, yy, lx + 34, yy)); b.append(end_mark(lx + 34, yy, "r", kind))
        b.append(text(lx + 42, yy, lab, size=8.4, anchor="start"))
    b.append(text(lx, ly + 58, "PK primary key · FK foreign key · UQ unique", size=8, anchor="start"))
    return svg(W, max(H, int(ly + 66)), "".join(b))


# ---------------------------------------------------------- 4/5. DFDs
EW, AW, PW = 80, 98, 88          # entity box, arrow lane, process box widths
FL = 9.4                          # flow-label line height


def entity(x, y, w, h, name):
    return (f'<rect x="{x + 3}" y="{y + 3}" width="{w}" height="{h}" fill="#000"/>'
            + rect(x, y, w, h, sw=1.1) + text(x + w / 2, y + h / 2, name, size=8.4, weight="bold"))


def store(x, y, w, h, sid, name):
    return (line(x, y, x + w, y, 1.1) + line(x, y + h, x + w, y + h, 1.1) + line(x, y, x, y + h, 1.1)
            + line(x + 24, y, x + 24, y + h, 1.1)
            + text(x + 12, y + h / 2, sid, size=8.4, weight="bold") + text(x + 29, y + h / 2, name, size=8.4, anchor="start"))


def flows_height(flows):
    return sum(FL * len(lbl.split("\n")) + 9 for lbl, _ in flows)


def side(items, x_box, x_lane0, x_lane1, top, box_w, left_side):
    """Lay out entities/stores on one side of a process; returns svg, bottom y."""
    b = []
    y = top
    for it in items:
        kind, name, flows = it[0], it[1], it[-1]
        fh = flows_height(flows)
        h = max(24, fh + 4)
        if kind == "E":
            b.append(entity(x_box, y, box_w, h, name))
        else:
            b.append(store(x_box, y, box_w, h, it[2], name))
        fy = y + (h - fh) / 2
        for lbl, into_process in flows:
            n = len(lbl.split("\n"))
            ty = fy + FL * n / 2 + 1
            ay = fy + FL * n + 4.5
            b.append(text((x_lane0 + x_lane1) / 2, ty, lbl, size=8))
            if left_side:
                a, c = (x_lane0, x_lane1) if into_process else (x_lane1, x_lane0)
            else:
                a, c = (x_lane1, x_lane0) if into_process else (x_lane0, x_lane1)
            b.append(line(a, ay, c, ay, 0.95, arrow=True))
            fy += FL * n + 9
        y += h + 8
    return "".join(b), y - 8


def band(top, pid, pname, left, right, W=470):
    x_e0 = 0
    x_l0, x_l1 = EW + 3, EW + AW
    x_p = EW + AW
    x_r0, x_r1 = x_p + PW, x_p + PW + AW - 3
    x_s = x_p + PW + AW
    sw = W - x_s - 3
    sl, yl = side(left, x_e0, x_l0, x_l1, top, EW, True)
    sr, yr = side(right, x_s, x_r0, x_r1, top, sw, False)
    bottom = max(yl, yr, top + 52)
    h = bottom - top
    p = (rect(x_p, top, PW, h, rx=8, sw=1.3) + line(x_p, top + 17, x_p + PW, top + 17, 1.1)
         + text(x_p + PW / 2, top + 9, pid, size=9, weight="bold")
         + text(x_p + PW / 2, top + 17 + (h - 17) / 2, pname, size=9))
    return sl + sr + p, bottom


def dfd_sheet(bands, note):
    W = 470
    b, y = [], 6
    for spec in bands:
        s, y = band(y, *spec)
        b.append(s)
        y += 22
    y -= 8
    b.append(entity(0, y, 30, 14, "")); b.append(text(40, y + 7, "External entity", size=8, anchor="start"))
    b.append(rect(120, y, 30, 14, rx=4)); b.append(text(156, y + 7, "Process", size=8, anchor="start"))
    b.append(store(205, y, 40, 14, "D#", "")); b.append(text(251, y + 7, "Data store", size=8, anchor="start"))
    b.append(line(310, y + 7, 345, y + 7, 0.95, arrow=True)); b.append(text(351, y + 7, "Data flow", size=8, anchor="start"))
    b.append(text(0, y + 28, note, size=8, anchor="start", style="italic"))
    return svg(W, int(y + 36), "".join(b))


REC, DEN, ASST, PAT = "RECEPTIONIST", "DENTIST\n(ADMINISTRATOR)", "DENTAL\nASSISTANT", "PATIENT"
NOTE = "Entities and data stores are repeated next to each process so that no data flows cross."


def dfd0():
    W = 470
    left = [("E", REC, [("staff credentials,\npatient registration data", True), ("access token,\npatient directory", False)]),
            ("E", DEN, [("staff credentials, patient\nrecord data, staff account\ndata, intraoral image,\nrisk-tier confirmation,\nclinical note, PDF report\nrequest, audit log query", True),
                        ("access token, patient records,\nstaff roster, detections and\nrisk result, screening review,\nPDF report, audit trail report", False)])]
    right = [("E", ASST, [("staff credentials, patient\nrecord data, intraoral\nimage, PDF report request", True),
                          ("access token, patient\nrecords, detections and\nrisk result, screening\nreview, PDF report", False)]),
             ("E", PAT, [("portal registration\nand login, screening\nhistory request, AI\nassistant question", True),
                         ("access token, screening\nhistory and prevention\nplan, AI assistant reply", False)])]
    global EW, AW, PW
    saved = EW, AW, PW
    EW, AW, PW = 84, 121, 80
    s, bottom = band(6, "0", "ToothWise\nAI-Assisted\nDental Screening\nand\nRecommendation\nSystem", left, right, W)
    EW, AW, PW = saved
    y = bottom + 14
    s += entity(0, y, 30, 14, "") + text(40, y + 7, "External entity", size=8, anchor="start")
    s += rect(130, y, 30, 14, rx=4) + text(166, y + 7, "Process", size=8, anchor="start")
    s += line(240, y + 7, 275, y + 7, 0.95, arrow=True) + text(281, y + 7, "Data flow", size=8, anchor="start")
    return svg(W, int(y + 22), s)


def dfd1_sheet1():
    return dfd_sheet([
        ("1.0", "Authenticate\nUsers",
         [("E", REC, [("credentials", True), ("access token", False)]),
          ("E", DEN, [("credentials", True), ("access token", False)]),
          ("E", ASST, [("credentials", True), ("access token", False)]),
          ("E", PAT, [("registration / login", True), ("access token", False)])],
         [("S", "Staff Accounts", "D1", [("staff account", True)]),
          ("S", "Patients", "D2", [("new portal account", False), ("patient account", True)]),
          ("S", "Audit Logs", "D7", [("login event", False)])]),
        ("2.0", "Manage\nPatient\nRecords",
         [("E", REC, [("registration data", True), ("patient directory", False)]),
          ("E", DEN, [("patient record data", True), ("patient records", False)]),
          ("E", ASST, [("patient record data", True), ("patient records", False)])],
         [("S", "Patients", "D2", [("new / updated record", False), ("patient record", True)]),
          ("S", "Audit Logs", "D7", [("record change event", False)])]),
        ("3.0", "Manage Staff\nAccounts",
         [("E", DEN, [("staff account data", True), ("staff roster", False)])],
         [("S", "Staff Accounts", "D1", [("staff account record", False), ("staff accounts", True)]),
          ("S", "Audit Logs", "D7", [("staff change event", False)])]),
        ("7.0", "Review Audit\nTrail",
         [("E", DEN, [("audit log query", True), ("audit trail report", False)])],
         [("S", "Audit Logs", "D7", [("audit log records", True)])]),
    ], NOTE)


def dfd1_sheet2():
    return dfd_sheet([
        ("4.0", "Perform AI\nDental\nScreening",
         [("E", DEN, [("intraoral image", True), ("detections,\nrisk result", False)]),
          ("E", ASST, [("intraoral image", True), ("detections,\nrisk result", False)])],
         [("S", "Patients", "D2", [("patient reference", True)]),
          ("S", "Screenings", "D3", [("screening record\nand photo", False)]),
          ("S", "Detections", "D4", [("detections", False)]),
          ("S", "Recommendations", "D5", [("KNN prevention plan", False)]),
          ("S", "Audit Logs", "D7", [("screening event", False)])]),
        ("5.0", "Review\nFindings and\nGenerate\nReport",
         [("E", DEN, [("tier confirmation,\nclinical note", True), ("PDF report request", True), ("review, PDF report", False)]),
          ("E", ASST, [("PDF report request", True), ("review, PDF report", False)])],
         [("S", "Patients", "D2", [("patient details", True)]),
          ("S", "Screenings", "D3", [("screening record", True), ("confirmed risk tier", False)]),
          ("S", "Detections", "D4", [("detections", True)]),
          ("S", "Recommendations", "D5", [("recommendations", True)]),
          ("S", "Clinical Notes", "D6", [("clinical note", False), ("clinical notes", True)]),
          ("S", "Audit Logs", "D7", [("review event", False)])]),
        ("6.0", "Serve Patient\nPortal and AI\nAssistant",
         [("E", PAT, [("history request", True), ("AI assistant question", True),
                      ("history, prevention\nplan", False), ("AI assistant reply", False)])],
         [("S", "Patients", "D2", [("patient profile", True)]),
          ("S", "Screenings", "D3", [("own screenings", True)]),
          ("S", "Recommendations", "D5", [("prevention plan", True)])]),
    ], NOTE)


# ---------------------------------------------------------------- 6. Gantt
def gantt():
    W = 470
    start = date(2026, 7, 12)
    day = lambda d: (d - start).days
    D = lambda m, d: date(2026, m, d)
    rows = [
        ("I", "Iteration 1: Core System Foundation", D(7, 12), D(7, 31)),
        ("T", "Requirements Analysis & Mapping", D(7, 12), D(7, 16)),
        ("T", "PostgreSQL Schema & ERD Setup", D(7, 14), D(7, 23)),
        ("T", "FastAPI Framework Setup", D(7, 18), D(7, 27)),
        ("T", "React UI Prototyping & Base Repo", D(7, 20), D(7, 31)),
        ("I", "Iteration 2: AI Screening", D(8, 1), D(8, 22)),
        ("T", "Dataset Processing & Annotation", D(8, 1), D(8, 10)),
        ("T", "YOLOv8 & YOLOv12 Model Training", D(8, 8), D(8, 18)),
        ("T", "Inference API Endpoint Development", D(8, 12), D(8, 20)),
        ("T", "Bounding Box UI Integration", D(8, 14), D(8, 22)),
        ("M", "Milestone: 30% of the system", D(8, 12), "Aug 12"),
        ("I", "Iteration 3: Recommendations & Workflow", D(8, 23), D(9, 13)),
        ("T", "KNN Recommendation Engine Logic", D(8, 23), D(9, 1)),
        ("T", "Role-Based Access Control & Routing", D(8, 27), D(9, 6)),
        ("T", "Patient History & Clinical Notes UI", D(8, 30), D(9, 8)),
        ("T", "Database Integration Testing", D(9, 4), D(9, 13)),
        ("I", "Iteration 4: Clinic Operations", D(9, 13), D(10, 2)),
        ("T", "Dashboard & Staff Management", D(9, 13), D(9, 22)),
        ("T", "Patient Self-Service Portal", D(9, 18), D(9, 27)),
        ("T", "Security Hardening & RBAC Auditing", D(9, 23), D(10, 1)),
        ("V", "60% Milestone Verification", D(9, 28), D(10, 2)),
        ("M", "Milestone: 60% of the system", D(10, 2), "Oct 2"),
        ("I", "Iteration 5: Testing, Hardening & Defense", D(10, 3), D(10, 30)),
        ("T", "ISO/IEC 25010 System Evaluation", D(10, 3), D(10, 13)),
        ("T", "Cloud Deployment & Performance Tuning", D(10, 9), D(10, 19)),
        ("T", "Final Manuscript Standardization", D(10, 14), D(10, 25)),
        ("T", "Final Defense Execution", D(10, 19), D(10, 30)),
        ("M", "Milestone: 100% of the system", D(10, 30), "Oct 30"),
    ]
    LX = 172                        # timeline starts here
    days = day(D(11, 1))
    px = (W - LX - 52) / days
    X = lambda d: LX + 18 + day(d) * px
    rh, top = 13.4, 20
    H = top + rh * len(rows) + 34
    b = [rect(0.5, 0.5, W - 1, top + rh * len(rows), fill="#fff", sw=1.0)]
    b.append(line(0.5, top, W - 0.5, top, 1.0))
    b.append(text(5, top / 2, "Iteration / task", size=8.6, anchor="start", weight="bold"))
    for i, r in enumerate(rows):
        if r[0] == "I":
            y = top + i * rh
            b.append(f'<rect x="1" y="{y:.1f}" width="{W - 2}" height="{rh:.1f}" fill="#e6e6e6"/>')
    d = D(7, 12)
    while d <= D(11, 1):
        x = X(d)
        b.append(line(x, top, x, top + rh * len(rows), 0.5, dash="2 2"))
        b.append(text(x, top / 2, d.strftime("%b %-d"), size=8))
        d += timedelta(days=14)
    b.append(line(LX, 0.5, LX, top + rh * len(rows), 1.0))
    for i, r in enumerate(rows):
        kind, name = r[0], r[1]
        y = top + i * rh
        cy = y + rh / 2
        b.append(text(5 if kind == "I" else 13, cy, name, size=8.2, anchor="start",
                      weight="bold" if kind in "IM" else "normal"))
        if kind == "I":
            b.append(f'<rect x="{X(r[2]):.1f}" y="{cy - 3:.1f}" width="{X(r[3]) - X(r[2]) + px:.1f}" height="6" fill="#000"/>')
        elif kind in "TV":
            fill = "#555" if kind == "V" else "#bdbdbd"
            b.append(rect(X(r[2]), cy - 4.5, X(r[3]) - X(r[2]) + px, 9, fill=fill, sw=0.9))
        else:
            x = X(r[2])
            b.append(f'<path d="M{x:.1f},{cy - 5.5:.1f} L{x + 5.5:.1f},{cy:.1f} L{x:.1f},{cy + 5.5:.1f} L{x - 5.5:.1f},{cy:.1f} z" fill="#000"/>')
            b.append(text(x + 9, cy, r[3], size=8, anchor="start"))
    ly = top + rh * len(rows) + 16
    b.append(rect(6, ly - 4.5, 22, 9, fill="#bdbdbd", sw=0.9)); b.append(text(33, ly, "Task", size=8.4, anchor="start"))
    b.append(rect(80, ly - 4.5, 22, 9, fill="#555", sw=0.9)); b.append(text(107, ly, "Milestone verification", size=8.4, anchor="start"))
    b.append(f'<rect x="215" y="{ly - 3}" width="26" height="6" fill="#000"/>'); b.append(text(246, ly, "Iteration span", size=8.4, anchor="start"))
    b.append(f'<path d="M335,{ly - 5.5} L340.5,{ly} L335,{ly + 5.5} L329.5,{ly} z" fill="#000"/>')
    b.append(text(346, ly, "System completion milestone", size=8.4, anchor="start"))
    return svg(W, int(H), "".join(b))


DIAGRAMS = {
    "fig_agile": agile, "fig_use_case": use_case, "fig_erd": erd, "fig_dfd0": dfd0,
    "fig_dfd1_sheet1": dfd1_sheet1, "fig_dfd1_sheet2": dfd1_sheet2, "fig_gantt": gantt,
}


def main(out: Path, only=None):
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = b.new_page(device_scale_factor=5)
        for name, fn in DIAGRAMS.items():
            if only and name not in only:
                continue
            s = fn()
            (out / f"{name}.svg").write_text(s, encoding="utf-8")
            page.set_content(f"<html><body style='margin:0;background:#fff'>{s}</body></html>")
            page.locator("svg").first.screenshot(path=str(out / f"{name}.png"), omit_background=False)
            print("drew", name)
        b.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:] or None)
