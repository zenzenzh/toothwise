from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log_action
from app.database import get_db
from app.rate_limit import limiter
from app.security import (
    verify_password, hash_password, create_access_token,
    get_current_staff, get_current_patient,
)
from app.utils.names import combine_name

router = APIRouter(prefix="/auth", tags=["auth"])


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

    token = create_access_token(subject=dentist.email)
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

    token = create_access_token(subject=patient.email, scope="patient")
    return schemas.PatientToken(access_token=token, patient=patient)


@router.get("/patient/me", response_model=schemas.PatientOut)
def patient_me(current: models.Patient = Depends(get_current_patient)):
    return current
