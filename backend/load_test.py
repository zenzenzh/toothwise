"""
Load test: simulate real traffic against the Toothwise patient portal.

    # 1. 100 patients register, sign in and browse their own results
    python load_test.py --mode patients --users 100 --concurrency 10

    # 2. a dentist records screenings (this is the AI-inference path)
    python load_test.py --mode screening --screenings 20 \
        --dentist-email x@y.com --dentist-password secret

Two populations, because the app has two:

  * patients are READ-ONLY. POST /api/patients/{id}/screening requires a
    dentist token (screenings.py: Depends(get_current_dentist)), and
    patientScreeningsAPI only exposes mine/get/imageObjectUrl. A patient
    cannot upload a photo, so "100 users uploading" is not a thing this app
    can do.
  * dentists do the uploads, and each one runs YOLO twice on CPU. That is the
    expensive path and it is what --mode screening measures.

Uses only requests + stdlib. No locust/k6 needed for one endpoint mix.

Writes real rows to the database. Reset afterwards with reset_test_data.py.
"""
import argparse
import io
import random
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parent
DEFAULT_BASE = "http://localhost:8000"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
PASSWORD = "LoadTest!2026"          # noqa: S105 - throwaway accounts only


class Result:
    __slots__ = ("stage", "ms", "status", "error", "body", "throttled")

    def __init__(self, stage, ms, status, error=None, body=None, throttled=0):
        self.stage, self.ms, self.status = stage, ms, status
        self.error, self.body, self.throttled = error, body, throttled


def timed(fn, stage: str, retries: int = 0) -> Result:
    """One request. On 429 honour Retry-After (the app rate-limits auth to
    5/minute per IP) and retry, so the run measures the system instead of
    dying at the first throttle. The 429s are counted and reported - the
    throttling is itself the finding."""
    t0 = time.perf_counter()
    throttled = 0
    for attempt in range(retries + 1):
        try:
            r = fn()
        except requests.RequestException as e:
            return Result(stage, (time.perf_counter() - t0) * 1000, -1,
                          str(e)[:120], throttled=throttled)
        except Exception as e:                   # noqa: BLE001
            return Result(stage, (time.perf_counter() - t0) * 1000, -1,
                          f"{type(e).__name__}: {str(e)[:120]}", throttled=throttled)
        if r.status_code == 429 and attempt < retries:
            throttled += 1
            wait = float(r.headers.get("Retry-After") or min(2 ** attempt, 15))
            time.sleep(wait)
            continue
        body = None
        try:
            body = r.json()
        except ValueError:
            pass
        return Result(stage, (time.perf_counter() - t0) * 1000, r.status_code,
                      body=body, throttled=throttled)
    raise AssertionError("unreachable")


def one_patient(idx: int, base: str, timeout: int, run_id: str,
                retries: int) -> list:
    """register -> login -> browse own results. No upload: patients can't."""
    s = requests.Session()
    # NOT @example.test / .example / .invalid - the app's EmailStr rejects
    # special-use TLDs (422), which is correct hygiene but blocks load testing.
    # run_id keeps re-runs from colliding on the unique email constraint.
    email = f"lt{run_id}{idx:04d}@toothwise-loadtest.com"
    out = []

    reg = timed(lambda: s.post(f"{base}/api/auth/patient/register", json={
        "first_name": f"Load{idx:04d}", "last_name": "Tester",
        "email": email, "password": PASSWORD,
    }, timeout=timeout), "register", retries=retries)
    out.append(reg)
    if not (200 <= reg.status < 300):
        return out

    login = timed(lambda: s.post(f"{base}/api/auth/patient/login", json={
        "email": email, "password": PASSWORD}, timeout=timeout), "login",
        retries=retries)
    out.append(login)
    if not (200 <= login.status < 300):
        return out
    tok = (login.body or {}).get("access_token")
    if not tok:
        out.append(Result("parse", 0, -1, "login returned no access_token"))
        return out
    s.headers["Authorization"] = f"Bearer {tok}"

    mine = timed(lambda: s.get(f"{base}/api/screenings/mine", timeout=timeout),
                 "browse")
    out.append(mine)
    if (200 <= mine.status < 300) and isinstance(mine.body, list) and mine.body:
        sid = mine.body[0].get("id")
        if sid:
            out.append(timed(
                lambda: s.get(f"{base}/api/screenings/self/{sid}", timeout=timeout),
                "detail"))
    return out


def one_screening(idx: int, base: str, images: list, timeout: int,
                  token: str, patients: list) -> list:
    """Dentist-side: record one screening for one patient. Runs YOLO twice."""
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    pid = patients[idx % len(patients)]
    img = images[idx % len(images)]
    up = timed(lambda: s.post(f"{base}/api/patients/{pid}/screening",
                              files={"file": (img.name, img.read_bytes(),
                                              "image/jpeg")},
                              timeout=timeout), "screening")
    out = [up]
    if 200 <= up.status < 300:
        try:
            sid = up.body.get("id")
        except AttributeError:
            sid = None
        if sid:
            out.append(timed(lambda: s.get(f"{base}/api/screenings/{sid}",
                                           timeout=timeout), "fetch"))
    return out


def pct(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    k = max(0, min(len(v) - 1, int(round(p / 100 * (len(v) - 1)))))
    return v[k]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("patients", "screening"),
                    default="patients")
    ap.add_argument("--users", type=int, default=100,
                    help="patients to simulate (--mode patients)")
    ap.add_argument("--screenings", type=int, default=20,
                    help="screenings to record (--mode screening)")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--retries", type=int, default=8,
                    help="retries on 429 (auth is capped at 5/min per IP)")
    ap.add_argument("--dentist-email")
    ap.add_argument("--dentist-password")
    ap.add_argument("--images", default=str(BACKEND / "uploads" / "screenings"))
    args = ap.parse_args()

    lock = threading.Lock()
    results: list = []
    t_start = time.perf_counter()
    done = 0
    run_id = time.strftime("%m%d%H%M")

    if args.mode == "patients":
        total = args.users
        print(f"base        : {args.base}")
        print(f"mode        : {total} patients register -> login -> browse")
        print(f"concurrency : {args.concurrency}   timeout: {args.timeout}s\n")

        def work(i):
            nonlocal done
            for r in one_patient(i, args.base, args.timeout, run_id,
                                 args.retries):
                with lock:
                    results.append(r)
            with lock:
                done += 1
                if done % 10 == 0 or done == total:
                    el = time.perf_counter() - t_start
                    print(f"  {done}/{total} patients  {el:6.1f}s  "
                          f"{done/el:.2f}/s", flush=True)
    else:
        img_dir = Path(args.images)
        images = sorted(p for p in img_dir.rglob("*")
                        if p.suffix.lower() in IMG_EXT)
        if not images:
            print(f"ERROR: no images in {img_dir}  pass --images <dir>")
            return 1
        if not (args.dentist_email and args.dentist_password):
            print("ERROR: --mode screening needs --dentist-email and "
                  "--dentist-password (screening creation is dentist-only)")
            return 1

        s = requests.Session()
        r = s.post(f"{args.base}/api/auth/login",
                   json={"email": args.dentist_email,
                         "password": args.dentist_password},
                   timeout=30)
        if r.status_code != 200:
            print(f"ERROR: dentist login failed {r.status_code}: "
                  f"{r.text[:200]}")
            return 1
        token = r.json()["access_token"]

        pr = s.get(f"{args.base}/api/patients",
                   headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if pr.status_code != 200:
            print(f"ERROR: listing patients failed {pr.status_code}: "
                  f"{pr.text[:200]}")
            return 1
        patients = [p["id"] for p in pr.json()]
        if not patients:
            print("ERROR: no patients exist. Run --mode patients first.")
            return 1

        total = args.screenings
        print(f"base        : {args.base}")
        print(f"mode        : {total} screenings as {args.dentist_email}")
        print(f"patients    : {len(patients)}   source imgs: {len(images)}")
        print(f"concurrency : {args.concurrency}   timeout: {args.timeout}s\n")

        def work(i):
            nonlocal done
            for r in one_screening(i, args.base, images, args.timeout,
                                   token, patients):
                with lock:
                    results.append(r)
            with lock:
                done += 1
                if done % 2 == 0 or done == total:
                    el = time.perf_counter() - t_start
                    print(f"  {done}/{total} screenings  {el:6.1f}s  "
                          f"{done/el:.2f}/s", flush=True)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(work, range(1, total + 1)))
    wall = time.perf_counter() - t_start

    by_stage: dict = {}
    for r in results:
        by_stage.setdefault(r.stage, []).append(r)

    total_429 = sum(r.throttled for r in results)
    print("\n" + "=" * 84)
    print(f"wall clock {wall:.1f}s   throughput {total/wall:.2f} ops/s "
          f"({total/wall*60:.0f}/min)")
    if total_429:
        print(f"429 rate-limit hits: {total_429} "
              f"(auth is capped at 5/minute per client IP)")
    print("=" * 84)
    print(f"{'stage':<12}{'n':>5}{'ok':>6}{'fail':>6}"
          f"{'p50':>9}{'p95':>9}{'max':>9}   errors")
    for stage, rs in by_stage.items():
        ms = [r.ms for r in rs]
        ok = [r for r in rs if 200 <= r.status < 300]
        bad = [r for r in rs if not (200 <= r.status < 300)]
        errs = {}
        for r in bad:
            errs[f"{r.status} {r.error or ''}".strip()[:52]] = \
                errs.get(f"{r.status} {r.error or ''}".strip()[:52], 0) + 1
        print(f"{stage:<12}{len(rs):>5}{len(ok):>6}{len(bad):>6}"
              f"{statistics.median(ms):>8.0f}m{pct(ms,95):>8.0f}m{max(ms):>8.0f}m")
        for e, n in sorted(errs.items(), key=lambda kv: -kv[1])[:3]:
            print(f"{'':<12}{'':<5}{'':<6}{'':<6}{'':<9}{'':<9}{'':<9}   "
                  f"{n}x {e}")

    scr = by_stage.get("screening", [])
    if scr:
        good = [r for r in scr if 200 <= r.status < 300]
        if good:
            rate = len(good) / wall * 60
            print(f"\nscreening p95 {pct([r.ms for r in good],95)/1000:.1f}s"
                  f" -> sustained {rate:.1f} screenings/min "
                  f"({rate/60*60:.0f}/hour)")
    return 0


if __name__ == "__main__":
    sys.exit(main())