"""Self-check for reset_test_data.py: seed one row per wipe table, wipe, verify
all zero + dentists kept, then restore from the backup and verify counts match.

    python test_reset_roundtrip.py

Creates its own throwaway patient, so it is safe to run on a live DB. It wipes
whatever patient-side data exists, so do not run it against data you care about.
"""
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import reset_test_data as R  # noqa: E402

ENGINE = R.connect()


def counts():
    wipe, _ = R.table_names(ENGINE)
    return R.counts(ENGINE, wipe)


def seed():
    """One patient + screening + detection + recommendation + audit log."""
    with ENGINE.begin() as con:
        pid = con.execute(sa.text("""
            INSERT INTO patients (full_name, first_name, last_name, email,
                                  hashed_password, birthdate)
            VALUES ('Reset Probe', 'Reset', 'Probe',
                    'reset-probe@toothwise-test.local', 'x', '1990-01-01')
            RETURNING id""")).scalar()
        sid = con.execute(sa.text("""
            INSERT INTO screenings (patient_id, image_path, image_width,
                                    image_height)
            VALUES (:p, 'probe.jpg', 100, 100) RETURNING id"""),
            {"p": pid}).scalar()
        con.execute(sa.text("""
            INSERT INTO detections (screening_id, label, confidence,
                                    x1, y1, x2, y2)
            VALUES (:s, 'cavity', 0.9, 1, 1, 10, 10)"""), {"s": sid})
        con.execute(sa.text("""
            INSERT INTO recommendations (screening_id, text, priority,
                                        order_index)
            VALUES (:s, 'probe', 1, 0)"""), {"s": sid})
        con.execute(sa.text("""
            INSERT INTO appointments (patient_id, dentist_id, scheduled_at,
                                     status)
            VALUES (:p, NULL, now(), 'scheduled')"""), {"p": pid})
        con.execute(sa.text("""
            INSERT INTO clinical_notes (screening_id, body)
            VALUES (:s, 'probe')"""), {"s": sid})
        did = con.execute(sa.text("SELECT id FROM dentists LIMIT 1")).scalar()
        con.execute(sa.text("""
            INSERT INTO audit_logs (actor_dentist_id, actor_email, action,
                                   entity_type)
            VALUES (:d, 'reset-probe@toothwise-test.local', 'reset.probe',
                    'screening')"""), {"d": did})
    return pid


def run(*args):
    return subprocess.run([sys.executable, str(BACKEND / "reset_test_data.py"),
                           *args], capture_output=True, text=True, cwd=BACKEND)


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
    return ok


def main():
    passed = True
    seed()
    before = counts()
    print("seeded:", {k: v for k, v in before.items() if k in R.WIPE})
    passed &= check("seeded rows present",
                    all(before[t] > 0 for t in R.WIPE if t in before),
                    str({t: before[t] for t in R.WIPE if t in before}))

    r = run("--yes")
    assert r.returncode == 0, r.stderr
    after = counts()
    passed &= check("every wipe table is 0",
                    all(after[t] == 0 for t in R.WIPE if t in after),
                    str({t: after[t] for t in R.WIPE if t in after}))
    passed &= check("dentists kept", after["dentists"] == before["dentists"],
                    f"{after['dentists']}")

    path = sorted((BACKEND / "backups").glob("reset_*.json"))[-1]
    r = run("--restore", str(path))
    assert r.returncode == 0, r.stderr
    back = counts()
    passed &= check("restore returns row counts",
                    all(back[t] == before[t] for t in R.WIPE if t in back),
                    str({t: back[t] for t in R.WIPE if t in back}))

    # leave the DB as we found it
    r = run("--yes")
    final = counts()
    passed &= check("final state clean",
                    all(final[t] == 0 for t in R.WIPE if t in final)
                    and final["dentists"] == before["dentists"])
    path.unlink(missing_ok=True)

    print(f"\n{'ALL PASS' if passed else 'FAILURES ABOVE'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())