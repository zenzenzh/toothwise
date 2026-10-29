"""Capture the system screenshots used in Section 3.10 of the paper.

Needs the backend on :8000 (log-only e-mail mode, so the password-reset link
is written to its log) and the React dev server on :3000, seeded with demo
data. Screens are taken in light mode at 2x for clear printing.

    python paper_build/capture_screens.py OUT_DIR BACKEND_LOG [UPLOAD_SAMPLE]
"""
import json
import re
import sys

import httpx
from playwright.sync_api import sync_playwright

OUT, BACKEND_LOG = sys.argv[1], sys.argv[2]
APP, API = "http://localhost:3000", "http://localhost:8000/api"
STAFF = {"email": "admin@codismile.com", "password": "CodiSmile@2026"}
PATIENT = {"email": "liza.garcia@gmail.com", "password": "Patient@2026"}
SAMPLE = sys.argv[3] if len(sys.argv) > 3 else "frontend/public/codismile/services/cosmetic-whitening.jpg"


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light")
    pg = ctx.new_page()

    def shot(name, url=None, wait=1500, full=False):
        if url:
            pg.goto(APP + url, wait_until="networkidle")
        pg.wait_for_timeout(wait)
        pg.screenshot(path=f"{OUT}/{name}.png", full_page=full)
        print("saved", name)

    pg.goto(APP + "/", wait_until="networkidle")
    pg.evaluate("() => localStorage.setItem('tw_theme', 'light')")
    shot("landing", "/", 2500)

    # Staff sign-in with "Remember me" ticked, then forgot / reset password.
    pg.goto(APP + "/login", wait_until="networkidle")
    pg.fill("#login-email", STAFF["email"])
    pg.fill("input[type=password]", STAFF["password"])
    pg.get_by_label("Remember me on this device").check()
    shot("login")
    # Forgot password: no email; the user confirms details on file and sets a new password.
    pg.get_by_text("Forgot password?").click()
    pg.wait_for_load_state("networkidle")
    pg.fill("input[type=email]", STAFF["email"])
    pg.locator("input:not([type=email]):not([type=password]):not([type=checkbox])").first.fill("PRC-0123456")
    for el in pg.locator("input[type=password]").all():
        el.fill("NewStaff@2026pass")
    shot("forgot_staff", None, 800, full=True)
    pg.goto(APP + "/forgot-password?type=patient", wait_until="networkidle")
    pg.fill("input[type=email]", PATIENT["email"])
    pg.locator("input[type=date]").first.fill("1995-02-15")
    pg.fill("input[type=tel]", "09451234560")
    for el in pg.locator("input[type=password]").all():
        el.fill("NewPatient@2026")
    shot("forgot_patient", None, 800, full=True)

    # Staff workspace ("remember me" session lives in localStorage).
    t = httpx.post(API + "/auth/login", json={**STAFF, "remember_me": True}).json()
    pg.evaluate("([tok, d]) => { localStorage.setItem('tw_token', tok); localStorage.setItem('tw_dentist', d); }",
                [t["access_token"], json.dumps(t["dentist"])])
    shot("dashboard", "/dashboard", 2500)
    shot("patients", "/dashboard/patients")
    shot("patient_detail", "/dashboard/patients/1", 2500)
    shot("screening_upload", "/dashboard/patients/2/screening")
    pg.set_input_files("input[type=file]", SAMPLE)
    shot("screening_preview", None, 1500)
    shot("screening_result_full", "/dashboard/screenings/2", 3000, full=True)
    shot("staff", "/dashboard/dentists")
    shot("audit", "/dashboard/audit-log")
    pg.get_by_role("button", name=re.compile("Change password")).first.click()
    shot("change_password", None, 800)
    pg.keyboard.press("Escape")

    # Patient portal.
    pg.evaluate("() => { localStorage.removeItem('tw_token'); localStorage.removeItem('tw_dentist'); }")
    pg.goto(APP + "/patient-portal", wait_until="networkidle")
    pg.wait_for_timeout(800)
    shot("portal_login")
    pg.get_by_role("button", name=re.compile("^Sign up$")).first.click()
    shot("portal_register", None, 1000)
    pt = httpx.post(API + "/auth/patient/login", json={**PATIENT, "remember_me": True}).json()
    pg.evaluate("([tok, d]) => { localStorage.setItem('tw_patient_token', tok); localStorage.setItem('tw_patient', d); }",
                [pt["access_token"], json.dumps(pt.get("patient", {}))])
    shot("portal_home", "/patient-portal", 3000, full=True)
    pg.get_by_text("View details").first.click()
    shot("portal_screening", None, 2500)

    pdf = httpx.get(API + "/screenings/2/report/pdf", headers={"Authorization": "Bearer " + t["access_token"]})
    open(f"{OUT}/report.pdf", "wb").write(pdf.content)
    b.close()
