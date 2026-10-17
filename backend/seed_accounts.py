"""
One-time bootstrap for initial CodiSmile staff accounts.

No credentials are stored in this source file. Set the environment variables
below before running from the backend directory:

  SEED_ADMIN_EMAIL      -> dentist / administrator account (full access)
  SEED_ADMIN_PASSWORD
  SEED_ADMIN_NAME
  SEED_ADMIN_LICENSE

Optional extra accounts can be supplied with these prefixes:

  DENTIST1_* / DENTIST2_*        -> additional dentists (role: dentist)
  RECEPTION1_* / RECEPTION2_*    -> receptionists (role: receptionist)
  ASSISTANT1_* / ASSISTANT2_*    -> dental assistants (role: assistant)

Each uses the same _NAME / _EMAIL / _PASSWORD (_LICENSE for dentists) keys.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app import models
from app.security import hash_password
from app.utils.names import split_name


def account_from_env(prefix: str, role, require_license: bool = False):
    full_name = os.getenv(f"{prefix}_NAME", "").strip()
    email = os.getenv(f"{prefix}_EMAIL", "").strip().lower()
    password = os.getenv(f"{prefix}_PASSWORD", "")
    license_no = os.getenv(f"{prefix}_LICENSE", "").strip()
    if not full_name and not email and not password and not license_no:
        return None
    required = [full_name, email, password]
    if require_license:
        required.append(license_no)
    if not all(required):
        raise SystemExit(f"Incomplete {prefix}_* environment variables.")
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "role": role,
        "license_no": license_no or None,
    }


def main():
    Base.metadata.create_all(bind=engine)

    accounts = []
    # The dentist is the clinic administrator (full access).
    admin = account_from_env("SEED_ADMIN", models.DentistRole.dentist, require_license=True)
    if admin:
        accounts.append(admin)
    for prefix in ("DENTIST1", "DENTIST2"):
        account = account_from_env(prefix, models.DentistRole.dentist)
        if account:
            accounts.append(account)
    for prefix in ("RECEPTION1", "RECEPTION2"):
        account = account_from_env(prefix, models.DentistRole.receptionist)
        if account:
            accounts.append(account)
    for prefix in ("ASSISTANT1", "ASSISTANT2"):
        account = account_from_env(prefix, models.DentistRole.assistant)
        if account:
            accounts.append(account)

    if not accounts:
        raise SystemExit("No seed accounts configured. Set SEED_ADMIN_* environment variables first.")

    db = SessionLocal()
    try:
        created, skipped = [], []
        for acc in accounts:
            exists = db.query(models.Dentist).filter(models.Dentist.email == acc["email"]).first()
            if exists:
                skipped.append(acc["email"])
                continue
            first_name, middle_name, last_name = split_name(acc["full_name"])
            dentist = models.Dentist(
                full_name=acc["full_name"],
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=acc["email"],
                hashed_password=hash_password(acc["password"]),
                role=acc["role"],
                license_no=acc["license_no"],
                is_active=True,
            )
            db.add(dentist)
            created.append(acc["email"])
        db.commit()
        print(f"Created: {len(created)} | Skipped existing: {len(skipped)}")
        for email in created:
            print(f"  created: {email}")
        for email in skipped:
            print(f"  skipped: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
