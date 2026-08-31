r"""
Toothwise — automated database backup

Runs `pg_dump` against your Toothwise database and writes a timestamped,
compressed backup file, pruning old backups beyond a retention count.
Closes the ISO/IEC 25010 Reliability gap ("Add auto-backup system") noted
in your ISO compliance doc.

Requirements: PostgreSQL's `pg_dump` must be on PATH (it ships with the
PostgreSQL server/client install - same install you already used for
`psql`).

Usage (manual run):
    python backup_db.py

Reads connection details from backend/.env (same DATABASE_URL the app
uses) so there's only one place to configure the database - no separate
credentials to keep in sync.

--- Scheduling on Windows (Task Scheduler) ---
1. Open Task Scheduler -> Create Basic Task.
2. Trigger: Daily, pick a time (e.g. 2:00 AM).
3. Action: "Start a program".
   Program/script:   C:\Users\zenn\toothwise\backend\.venv\Scripts\python.exe
   Add arguments:    backup_db.py
   Start in:         C:\Users\zenn\toothwise\database
4. Finish. Test it once with "Run" in Task Scheduler before trusting it
   unattended.

Backups land in database/backups/ by default - back that folder up
somewhere off this machine too (cloud drive, USB) since a local-only
backup doesn't protect against the machine itself failing.
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# How many backups to keep. Older ones beyond this count are deleted after
# each successful run. 14 daily backups = 2 weeks of history.
RETENTION_COUNT = 14

BACKUP_DIR = Path(__file__).parent / "backups"


def _load_database_url() -> str:
    # Prefer an explicit env var (e.g. set by Task Scheduler / CI) over the
    # backend's .env file, but fall back to reading .env directly so this
    # script works standalone without needing python-dotenv installed.
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if not env_path.exists():
        print(f"ERROR: could not find {env_path} and DATABASE_URL is not set.")
        sys.exit(1)

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()

    print(f"ERROR: DATABASE_URL not found in {env_path}.")
    sys.exit(1)


def _parse_database_url(url: str) -> dict:
    # Accepts postgresql+psycopg://user:pass@host:port/dbname (what the
    # app uses) - psycopg's driver suffix is stripped since pg_dump
    # doesn't understand it.
    cleaned = re.sub(r"^postgresql\+\w+://", "postgresql://", url)
    parsed = urlparse(cleaned)
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
    }


def run_backup():
    db = _parse_database_url(_load_database_url())
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = BACKUP_DIR / f"toothwise_{db['dbname']}_{timestamp}.dump"

    env = os.environ.copy()
    if db["password"]:
        env["PGPASSWORD"] = db["password"]

    cmd = [
        "pg_dump",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-F", "c",  # custom format: compressed, restorable with pg_restore
        "-f", str(out_file),
        db["dbname"],
    ]

    print(f"Backing up '{db['dbname']}' to {out_file} ...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        print("BACKUP FAILED:")
        print(result.stderr)
        sys.exit(1)

    size_kb = out_file.stat().st_size / 1024
    print(f"Backup complete: {out_file.name} ({size_kb:.1f} KB)")

    _prune_old_backups()


def _prune_old_backups():
    backups = sorted(
        BACKUP_DIR.glob("toothwise_*.dump"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[RETENTION_COUNT:]:
        print(f"Pruning old backup: {old.name}")
        old.unlink()


if __name__ == "__main__":
    run_backup()
