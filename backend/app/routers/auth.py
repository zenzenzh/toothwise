import hmac
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log_action
from app.config import get_settings
from app.database import get_db
from app.rate_limit import limiter
from app.security import (
    verify_password, hash_password, create_access_token,
    get_current_staff, get_current_patient,
)
from app.utils.names import combine_name

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _login_token(email: str, scope: str, remember_me: bool) -> str:
    """Remembered devices get a long-lived token; otherwise the default."""
    minutes = settings.REMEMBER_ME_EXPIRE_DAYS * 24 * 60 if remember_me else None
    return create_access_token(subject=email, scope=scope, expires_minutes=minutes)


@router.post("/login", response_model=schemas.Token)
@limiter.limit("5/minute")
def login(request: Request, payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    dentist = db.query(models.Dentist).filter(
        models.Dentist.email == payload.email
    ).first()

    if not dentist or not verify_password(payload.password, dentist.hashed_password):
        # Failed attempts are logged without linking to a dentist row (we
        # don't know which account, if any, was actually targeted) but do
        # keep the attempted email for security review.
        log_action(db, None, "login.failed", details=payload.email)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not dentist.is_active:
        log_action(db, dentist, "login.rejected_inactive", "dentist", dentist.id)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    log_action(db, dentist, "login.success", "dentist", dentist.id)
    db.commit()

    token = _login_token(dentist.email, "staff", payload.remember_me)
    return schemas.Token(access_token=token, dentist=dentist)


@router.get("/me", response_model=schemas.DentistOut)
def me(current: models.Dentist = Depends(get_current_staff)):
    return current


# ---------- Patient portal (self-service registration/login) ----------
@router.post("/patient/register", response_model=schemas.PatientToken, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def patient_register(request: Request, payload: schemas.PatientRegister, db: Session = Depends(get_db)):
    existing = db.query(models.Patient).filter(models.Patient.email == payload.email).first()
    if existing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "An account with this email already exists. Try logging in instead.",
        )

    patient = models.Patient(
        full_name=combine_name(payload.first_name, payload.middle_name, payload.last_name),
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        contact_number=payload.contact_number,
        birthdate=payload.birthdate,
        gender=payload.gender,
        address=payload.address,
    )
    db.add(patient)
    db.flush()
    log_action(
        db, None, "patient.self_register", "patient", patient.id,
        details=payload.email, actor_label=payload.email,
    )
    db.commit()
    db.refresh(patient)

    token = create_access_token(subject=patient.email, scope="patient")
    return schemas.PatientToken(access_token=token, patient=patient)


@router.post("/patient/login", response_model=schemas.PatientToken)
@limiter.limit("5/minute")
def patient_login(request: Request, payload: schemas.PatientLoginRequest, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.email == payload.email).first()

    if not patient or not patient.hashed_password or not verify_password(payload.password, patient.hashed_password):
        log_action(db, None, "patient.login.failed", details=payload.email, actor_label=payload.email)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not patient.is_active:
        log_action(db, None, "patient.login.rejected_inactive", "patient", patient.id, actor_label=payload.email)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    log_action(db, None, "patient.login.success", "patient", patient.id, actor_label=payload.email)
    db.commit()

    token = _login_token(patient.email, "patient", payload.remember_me)
    return schemas.PatientToken(access_token=token, patient=patient)


@router.get("/patient/me", response_model=schemas.PatientOut)
def patient_me(current: models.Patient = Depends(get_current_patient)):
    return current


# ---------- Forgot / change password ----------
# Forgot password works without email: the user proves who they are with
# details already stored on their account, then sets a new password right
# away. Every failure returns the same message, so these endpoints can't be
# used to find out which emails exist or which detail was wrong.
RESET_FAILED_MESSAGE = "The details you entered do not match our records."
RESET_DONE_MESSAGE = "Your password has been changed. You can now sign in."


def _entity(account_type: str) -> str:
    return "dentist" if account_type == "staff" else "patient"


def _phone_key(value: Optional[str]) -> str:
    """Last 10 digits, so 09171234567, +639171234567 and 0917-123-4567 match."""
    return re.sub(r"\D", "", value or "")[-10:]


def _same(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(a, b)


def _finish_reset(account, account_type: str, verified: bool, email: str, new_password: str, db: Session):
    if not verified:
        log_action(db, None, f"{account_type}.password_reset.failed", details=email, actor_label=email)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_FAILED_MESSAGE)
    account.hashed_password = hash_password(new_password)
    log_action(
        db, account if account_type == "staff" else None,
        f"{account_type}.password_reset.completed",
        _entity(account_type), account.id, actor_label=email,
    )
    db.commit()
    return schemas.MessageResponse(message=RESET_DONE_MESSAGE)


def _change_password(account, actor, account_type: str, payload: schemas.ChangePasswordRequest, db: Session):
    if not account.hashed_password or not verify_password(payload.current_password, account.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect.")
    if verify_password(payload.new_password, account.hashed_password):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Choose a new password that is different from your current one.",
        )
    account.hashed_password = hash_password(payload.new_password)
    log_action(
        db, actor, f"{account_type}.password_changed",
        _entity(account_type), account.id, actor_label=account.email,
    )
    db.commit()
    return schemas.MessageResponse(message="Your password has been changed.")


@router.post("/forgot-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def staff_forgot_password(request: Request, payload: schemas.StaffForgotPassword, db: Session = Depends(get_db)):
    """Staff reset: email + the PRC license number on file. Staff without a
    license number ask the dentist/administrator to reset it for them."""
    staff = db.query(models.Dentist).filter(models.Dentist.email == payload.email).first()
    verified = (
        staff is not None and staff.is_active
        and _same((staff.license_no or "").strip().upper(), payload.license_no.strip().upper())
    )
    return _finish_reset(staff, "staff", verified, payload.email, payload.new_password, db)


@router.post("/change-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def staff_change_password(
    request: Request,
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(get_current_staff),
):
    staff = db.get(models.Dentist, current.id)
    return _change_password(staff, staff, "staff", payload, db)


@router.post("/patient/forgot-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def patient_forgot_password(request: Request, payload: schemas.PatientForgotPassword, db: Session = Depends(get_db)):
    """Patient reset: email + the birthdate and mobile number on the account."""
    patient = db.query(models.Patient).filter(models.Patient.email == payload.email).first()
    verified = (
        patient is not None and patient.is_active
        and bool(patient.hashed_password)  # only portal accounts have a password
        and patient.birthdate == payload.birthdate
        and _same(_phone_key(patient.contact_number), _phone_key(payload.contact_number))
    )
    return _finish_reset(patient, "patient", verified, payload.email, payload.new_password, db)


@router.post("/patient/change-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def patient_change_password(
    request: Request,
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: models.Patient = Depends(get_current_patient),
):
    patient = db.get(models.Patient, current.id)
    return _change_password(patient, None, "patient", payload, db)
