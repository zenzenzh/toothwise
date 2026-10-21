from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log_action
from app.config import get_settings
from app.database import get_db
from app.notifications import send_email
from app.rate_limit import limiter
from app.security import (
    verify_password, hash_password, create_access_token,
    get_current_staff, get_current_patient,
    create_password_reset_token, read_password_reset_token, reset_token_matches,
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


# ---------- Forgot / reset / change password ----------
FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent. "
    "Check your inbox and spam folder."
)


def _entity(account_type: str) -> str:
    return "dentist" if account_type == "staff" else "patient"


def _send_reset_link(email: str, full_name: str, account_type: str, hashed_password: str):
    """Emails a reset link. Returns the link only when it could not be
    emailed outside production (so the flow can be demoed locally)."""
    token = create_password_reset_token(email, account_type, hashed_password)
    query = urlencode({"token": token, "type": account_type})
    url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?{query}"
    body = (
        f"Hi {full_name},\n\n"
        f"We received a request to reset your {settings.CLINIC_NAME} ToothWise password.\n"
        f"Open this link to choose a new password. It works once and expires in "
        f"{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes:\n\n{url}\n\n"
        "If you didn't ask for this, ignore this email. Your password won't change.\n"
    )
    sent = send_email(email, "Reset your ToothWise password", body)
    if not sent and settings.ENV != "production":
        return url
    return None


def _forgot_password(account, account_type: str, email: str, db: Session):
    dev_url = None
    if account is not None and account.is_active and account.hashed_password:
        dev_url = _send_reset_link(email, account.full_name, account_type, account.hashed_password)
        log_action(
            db, None, f"{account_type}.password_reset.requested",
            _entity(account_type), account.id, actor_label=email,
        )
        db.commit()
    # Same answer whether or not the account exists, so this endpoint can't
    # be used to find out which emails are registered.
    return schemas.ForgotPasswordResponse(message=FORGOT_PASSWORD_MESSAGE, dev_reset_url=dev_url)


def _reset_password(model, account_type: str, payload: schemas.ResetPasswordRequest, db: Session):
    invalid = HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "This reset link is invalid or has expired. Please request a new one.",
    )
    data = read_password_reset_token(payload.token, account_type)
    if data is None:
        raise invalid
    account = db.query(model).filter(model.email == data["sub"]).first()
    if (
        account is None or not account.is_active or not account.hashed_password
        or not reset_token_matches(data, account.hashed_password)
    ):
        raise invalid
    account.hashed_password = hash_password(payload.new_password)
    log_action(
        db, account if account_type == "staff" else None,
        f"{account_type}.password_reset.completed",
        _entity(account_type), account.id, actor_label=account.email,
    )
    db.commit()
    return schemas.MessageResponse(message="Your password has been reset. You can now sign in.")


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


@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
@limiter.limit("3/minute")
def staff_forgot_password(request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    staff = db.query(models.Dentist).filter(models.Dentist.email == payload.email).first()
    return _forgot_password(staff, "staff", payload.email, db)


@router.post("/reset-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def staff_reset_password(request: Request, payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    return _reset_password(models.Dentist, "staff", payload, db)


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


@router.post("/patient/forgot-password", response_model=schemas.ForgotPasswordResponse)
@limiter.limit("3/minute")
def patient_forgot_password(request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.email == payload.email).first()
    return _forgot_password(patient, "patient", payload.email, db)


@router.post("/patient/reset-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def patient_reset_password(request: Request, payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    return _reset_password(models.Patient, "patient", payload, db)


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
