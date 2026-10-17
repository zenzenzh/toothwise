from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import cast, func, String, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log_action
from app.database import get_db
from app.security import get_current_staff, require_clinical, require_dentist
from app.utils.names import combine_name

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[schemas.PatientListOut])
def list_patients(
    search: str | None = None,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(get_current_staff),
):
    query = db.query(models.Patient)
    if search:
        term = search.strip()
        # Search is intentionally limited to non-secret patient directory
        # fields. Password hashes are never included in the filter.
        query = query.filter(or_(
            models.Patient.full_name.ilike(f"%{term}%"),
            models.Patient.email.ilike(f"%{term}%"),
            models.Patient.contact_number.ilike(f"%{term}%"),
            cast(models.Patient.id, String).ilike(f"%{term}%"),
        ))
    patients = query.order_by(models.Patient.id).all()

    results = []
    for p in patients:
        last_screening = (
            db.query(models.Screening)
            .filter(models.Screening.patient_id == p.id)
            .order_by(models.Screening.created_at.desc())
            .first()
        )
        results.append(schemas.PatientListOut(
            **schemas.PatientOut.model_validate(p).model_dump(),
            screening_count=len(p.screenings),
            last_risk_level=last_screening.risk_level if last_screening else None,
        ))
    return results


@router.post("", response_model=schemas.PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(get_current_staff),
):
    data = payload.model_dump()
    data["full_name"] = combine_name(data["first_name"], data.get("middle_name"), data["last_name"])
    patient = models.Patient(**data)
    db.add(patient)
    db.flush()
    log_action(db, current, "patient.create", "patient", patient.id, patient.full_name)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=schemas.PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(get_current_staff),
):
    patient = db.query(models.Patient).get(patient_id)
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    return patient


@router.put("/{patient_id}", response_model=schemas.PatientOut)
def update_patient(
    patient_id: int,
    payload: schemas.PatientUpdate,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(get_current_staff),
):
    patient = db.query(models.Patient).get(patient_id)
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(patient, field, value)
    if {"first_name", "middle_name", "last_name"} & updates.keys():
        patient.full_name = combine_name(patient.first_name, patient.middle_name, patient.last_name)
    log_action(db, current, "patient.update", "patient", patient.id, patient.full_name)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(require_dentist),
):
    patient = db.query(models.Patient).get(patient_id)
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    log_action(db, current, "patient.delete", "patient", patient.id, patient.full_name)
    db.delete(patient)
    db.commit()


@router.get("/{patient_id}/screenings", response_model=list[schemas.ScreeningSummaryOut])
def list_patient_screenings(
    patient_id: int,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(require_clinical),
):
    patient = db.query(models.Patient).get(patient_id)
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")

    screenings = (
        db.query(models.Screening)
        .filter(models.Screening.patient_id == patient_id)
        .order_by(models.Screening.created_at.desc())
        .all()
    )
    out = []
    for s in screenings:
        # Only count the fused/clinical detection set here too - s.detections
        # includes the raw yolov8_raw/yolov12_raw rows kept for the
        # model-comparison view, which would inflate this count 2-3x.
        fused_count = sum(1 for d in s.detections if d.detection_set == "fused")
        out.append(schemas.ScreeningSummaryOut(
            id=s.id, created_at=s.created_at, risk_level=s.risk_level,
            risk_score=s.risk_score, detection_count=fused_count,
        ))
    return out


@router.get("/{patient_id}/risk-trend", response_model=list[schemas.RiskTrendPoint])
def get_patient_risk_trend(
    patient_id: int,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(require_clinical),
):
    """Chronological risk_score/risk_level per screening, oldest first -
    feeds the trend chart on the patient detail page."""
    patient = db.query(models.Patient).get(patient_id)
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")

    screenings = (
        db.query(models.Screening)
        .filter(models.Screening.patient_id == patient_id)
        .order_by(models.Screening.created_at.asc())
        .all()
    )
    return [
        schemas.RiskTrendPoint(
            screening_id=s.id, created_at=s.created_at,
            risk_score=s.risk_score, risk_level=s.risk_level,
        )
        for s in screenings
    ]
