"""Capture the system screenshots used in Section 3.10 of the paper.

Needs the backend on :8000 and the React dev server on :3000, seeded with
demo data. Screens are taken in light mode at 2x for clear printing.
    python paper_build/capture_screens.py OUT_DIR
"""
import sys, time, httpx
from playwright.sync_api import sync_playwright

OUT = sys.argv[1]
APP, API = "http://localhost:3000", "http://localhost:8000/api"

def staff_token():
    r = httpx.post(API + "/auth/login", json={"email": "admin@codismile.com", "password": "CodiSmile@2026"})
    return r.json()

def patient_token():
    r = httpx.post(API + "/auth/patient/login", json={"email": "liza.garcia@gmail.com", "password": "Patient@2026"})
    return r.json()

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light")
    pg = ctx.new_page()

    def shot(name, url=None, wait=1500, full=False, clip=None):
        if url:
            pg.goto(APP + url, wait_until="networkidle")
        pg.wait_for_timeout(wait)
        pg.screenshot(path=f"{OUT}/{name}.png", full_page=full, clip=clip)
        print("saved", name)

    shot("landing", "/", 2500)
    shot("login", "/login")
    shot("portal_login", "/patient-portal")

    t = staff_token()
    pg.evaluate("""([tok, d]) => { localStorage.setItem('tw_token', tok); localStorage.setItem('tw_dentist', d);
                   localStorage.setItem('tw_theme','light'); }""",
                [t["access_token"], __import__("json").dumps(t["dentist"])])
    shot("dashboard", "/dashboard", 2500)
    shot("patients", "/dashboard/patients")
    shot("patient_detail", "/dashboard/patients/1", 2500)
    shot("screening_upload", "/dashboard/patients/2/screening")
    pg.set_input_files("input[type=file]", "frontend/public/codismile/services-stock/braces.jpg")
    shot("screening_preview", None, 1500)
    shot("screening_result", "/dashboard/screenings/1", 3000)
    shot("screening_result_full", None, 500, full=True)
    shot("staff", "/dashboard/dentists")
    shot("audit", "/dashboard/audit-log")

    # patient portal
    pg.evaluate("() => { localStorage.removeItem('tw_token'); localStorage.removeItem('tw_dentist'); }")
    pg.goto(APP + "/patient-portal", wait_until="networkidle")
    for link in ("Sign up", "Create account", "Register"):
        loc = pg.get_by_text(link, exact=False)
        if loc.count():
            loc.first.click(); break
    shot("portal_register", None, 1200)
    pt = patient_token()
    pg.evaluate("""([tok, d]) => { localStorage.setItem('tw_patient_token', tok); localStorage.setItem('tw_patient', d); }""",
                [pt["access_token"], __import__("json").dumps(pt.get("patient", {}))])
    shot("portal_home", "/patient-portal", 2500)
    loc = pg.get_by_text("View details")
    if loc.count():
        loc.first.click()
        shot("portal_screening", None, 2500)
    pdf = httpx.get(API + "/screenings/1/report/pdf", headers={"Authorization": "Bearer " + t["access_token"]})
    open(f"{OUT}/report.pdf", "wb").write(pdf.content)
    b.close()
