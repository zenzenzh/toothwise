import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app import models

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def hash_password(password: str) -> str:
    # Pydantic's PASSWORD_MAX_LENGTH=72 (schemas.py) already rejects
    # anything longer than bcrypt's 72-byte limit at the API boundary, with
    # a clear validation error the user actually sees. The [:72] slice
    # below is a defensive backstop only - for pure-ASCII passwords 72
    # chars == 72 bytes so it should never actually trigger; it exists so
    # a caller that bypasses the schema layer (e.g. a script, a future
    # endpoint) still can't crash bcrypt on oversized/multi-byte input
    # rather than silently accepting a password that then behaves
    # differently than what the user believes they set.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


def create_access_token(
    subject: str, scope: str = "dentist", expires_minutes: Optional[int] = None
) -> str:
    """
    scope distinguishes a staff (dentist/admin) token from a patient-portal
    token, so a patient account can never be used to call staff-only
    endpoints and vice versa, even if emails were ever to collide across
    the two tables.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire, "scope": scope}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_dentist(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.Dentist:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        # Tokens issued before the scope claim existed have no "scope" key
        # at all - treat those as staff tokens too so already-logged-in
        # dentists aren't kicked out by this change.
        if email is None or payload.get("scope") not in (None, "dentist"):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    dentist = db.query(models.Dentist).filter(models.Dentist.email == email).first()
    if dentist is None or not dentist.is_active:
        raise credentials_exception
    return dentist


def get_current_patient(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.Patient:
    """Auth dependency for the patient self-service portal (screening history, profile)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None or payload.get("scope") != "patient":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    patient = db.query(models.Patient).filter(models.Patient.email == email).first()
    if patient is None or not patient.is_active:
        raise credentials_exception
    return patient


def require_admin(current: models.Dentist = Depends(get_current_dentist)) -> models.Dentist:
    if current.role != models.DentistRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action",
        )
    return current
