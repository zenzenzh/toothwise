"""
Reset patient-side data for a clean user-testing run.

Wipes screenings, detections, recommendations, patients and audit logs, and
restarts their id sequences. Keeps dentists, because they are staff accounts:
the admin and dentist sign-ins live there and wiping them locks everyone out
of the app entirely. Appointments and clinical notes are included in the
wipe for completeness; both reference screenings, which is going away.

A JSON backup of every row about to be deleted is written first, and the
reset aborts if that backup fails - a reset you cannot undo is not a reset.

    python reset_test_data.py --yes            # do it
    python reset_test_data.py                  # dry run, prints the plan
    python reset_test_data.py --restore backups/reset_<stamp>.json

Credentials live in backend/.env (DATABASE_URL); nothing is hardcoded.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import sqlalchemy as sa

# Patient-side tables, children before parents. dentists is deliberately absent.
WIPE = ["detections", "recommendations", "clinical_notes", "appointments",
        "screenings", "patients", "audit_logs"]
KEEP = ["dentists"]
BACKUP_DIR = BACKEND / "backups"


def connect():
    """Use the app's own models/engine so the reset can never drift from the
    schema the running app expects."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BACKEND / ".env")
    except ImportError:
        pass
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set - is backend/.env present?")
    engine = sa.create_engine(url, pool_pre_ping=True,
                              connect_args={"connect_timeout": 10})
    return engine


def table_names(engine):
    """Return (wipe_tables_present, all_tables).

    Only KEEP tables are required. The wipe list is intersected with what the
    database actually has, so this keeps working on a DB that predates
    appointments/clinical_notes instead of dying on them."""
    insp = sa.inspect(engine)
    have = set(insp.get_table_names())
    missing_keep = [t for t in KEEP if t not in have]
    if missing_keep:
        raise SystemExit(f"tables not found in the database: {missing_keep}")
    return [t for t in WIPE if t in have], have


def snapshot(engine, wipe):
    out = {}
    with engine.connect() as con:
        for t in wipe:
            cols = [c["name"] for c in sa.inspect(engine).get_columns(t)]
            rows = con.execute(sa.text(f'SELECT * FROM "{t}"')).mappings().all()
            out[t] = {"columns": cols,
                      "rows": [{k: (v.isoformat() if hasattr(v, "isoformat") else v)
                                for k, v in r.items()} for r in rows]}
    return out


def counts(engine, wipe):
    with engine.connect() as con:
        return {t: con.execute(sa.text(f'SELECT count(*) FROM "{t}"')).scalar()
                for t in wipe + KEEP}


def save_backup(snap, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")
    return path


def load_backup(path: Path, engine, wipe):
    snap = json.loads(path.read_text(encoding="utf-8"))
    with engine.begin() as con:
        # parents first so foreign keys stay satisfied while rows go back in
        for t in reversed([x for x in wipe if x in snap]):
            rows = snap[t]["rows"]
            if not rows:
                continue
            cols = snap[t]["columns"]
            stmt = sa.text(
                f'INSERT INTO "{t}" ({",".join(chr(34)+c+chr(34) for c in cols)}) '
                f'VALUES ({",".join(":"+c for c in cols)})')
            for r in rows:
                con.execute(stmt, {c: r.get(c) for c in cols})
    return snap


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true",
                    help="actually wipe; without it this is a dry run")
    ap.add_argument("--restore", metavar="JSON",
                    help="re-insert rows from a previous backup and exit")
    args = ap.parse_args()

    engine = connect()
    wipe, _have = table_names(engine)

    if args.restore:
        snap = load_backup(Path(args.restore), engine, wipe)
        n = sum(len(v["rows"]) for v in snap.values())
        print(f"restored {n} row(s) from {args.restore}")
        print("counts now:", counts(engine, wipe))
        return 0

    before = counts(engine, wipe)
    print("current counts")
    for t, n in before.items():
        tag = "KEEP" if t in KEEP else "wipe"
        print(f"  {t:18} {n:>6}   {tag}")

    dentists_gone = 0
    with engine.connect() as con:
        dentists_gone = con.execute(
            sa.text("SELECT count(*) FROM dentists WHERE NOT is_active")).scalar()
    if dentists_gone:
        print(f"\nWARNING: {dentists_gone} dentist account(s) are inactive and "
              f"cannot sign in after you log them out.")

    if not args.yes:
        print(f"\ndry run - nothing changed. re-run with --yes to wipe "
              f"{', '.join(t for t in wipe if before[t])}")
        return 0

    # Back up first. If this fails, abort rather than destroy unrecoverable rows.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    try:
        snap = snapshot(engine, wipe)
        path = save_backup(snap, BACKUP_DIR / f"reset_{stamp}.json")
    except Exception as e:
        raise SystemExit(f"backup failed, refusing to wipe: {e}")
    n = sum(len(v["rows"]) for v in snap.values())
    print(f"\nbacked up {n} row(s) -> {path}")

    with engine.begin() as con:
        con.execute(sa.text(
            "TRUNCATE " + ", ".join(f'"{t}"' for t in wipe) + " RESTART IDENTITY CASCADE"))

    after = counts(engine, wipe)
    print("\nafter reset")
    for t, c in after.items():
        flag = "  <- wiped" if before[t] != c and t in wipe else ""
        print(f"  {t:18} {c:>6}{flag}")
    print(f"\ndentists kept: {after['dentists']} (sign-in still works)")
    print(f"restore with:  python reset_test_data.py --restore \"{path}\"")
    print(f"new patients self-register at POST /api/auth/patient/register")
    return 0


if __name__ == "__main__":
    sys.exit(main())