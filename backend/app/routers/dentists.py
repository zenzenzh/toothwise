from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log_action
from app.database import get_db
from app.security import hash_password, get_current_staff, require_dentist
from app.utils.names import combine_name

router = APIRouter(prefix="/dentists", tags=["dentists"])


@router.get("", response_model=list[schemas.DentistOut])
def list_dentists(
    search: str | None = None,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(require_dentist),
):
    query = db.query(models.Dentist)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (models.Dentist.full_name.ilike(like)) | (models.Dentist.email.ilike(like))
        )
    return query.order_by(models.Dentist.id).all()


@router.get("/{dentist_id}", response_model=schemas.DentistOut)
def get_dentist(
    dentist_id: int,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(require_dentist),
):
    dentist = db.query(models.Dentist).get(dentist_id)
    if not dentist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dentist not found.")
    return dentist


@router.post("", response_model=schemas.DentistOut, status_code=status.HTTP_201_CREATED)
def create_dentist(
    payload: schemas.DentistCreate,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(require_dentist),
):
    existing = db.query(models.Dentist).filter(
        models.Dentist.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered.")

    dentist = models.Dentist(
        full_name=combine_name(payload.first_name, payload.middle_name, payload.last_name),
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        license_no=payload.license_no,
    )
    db.add(dentist)
    db.flush()
    log_action(db, current, "dentist.create", "dentist", dentist.id, dentist.email)
    db.commit()
    db.refresh(dentist)
    return dentist


@router.put("/{dentist_id}", response_model=schemas.DentistOut)
def update_dentist(
    dentist_id: int,
    payload: schemas.DentistUpdate,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(get_current_staff),
):
    dentist = db.query(models.Dentist).get(dentist_id)
    if not dentist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dentist not found.")

    data = payload.model_dump(exclude_unset=True)

    if current.role != models.DentistRole.dentist:
        if current.id != dentist_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed.")
        if any(k in data for k in ("role", "email", "is_active")):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the dentist/administrator can modify role, email, or active status.")

    if "password" in data and data["password"]:
        dentist.hashed_password = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(dentist, field, value)
    if {"first_name", "middle_name", "last_name"} & data.keys():
        dentist.full_name = combine_name(dentist.first_name, dentist.middle_name, dentist.last_name)

    log_action(db, current, "dentist.update", "dentist", dentist.id, dentist.email)
    db.commit()
    db.refresh(dentist)
    return dentist


@router.put("/{dentist_id}/password", response_model=schemas.DentistOut)
def reset_password(
    dentist_id: int,
    payload: schemas.DentistPasswordReset,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(require_dentist),
):
    dentist = db.query(models.Dentist).get(dentist_id)
    if not dentist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dentist not found.")
    dentist.hashed_password = hash_password(payload.new_password)
    log_action(db, current, "dentist.password_reset", "dentist", dentist.id, dentist.email)
    db.commit()
    db.refresh(dentist)
    return dentist


@router.post("/{dentist_id}/deactivate", response_model=schemas.DentistOut)
def deactivate_dentist(
    dentist_id: int,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(require_dentist),
):
    dentist = db.query(models.Dentist).get(dentist_id)
    if not dentist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dentist not found.")
    dentist.is_active = not dentist.is_active
    action = "dentist.deactivate" if not dentist.is_active else "dentist.activate"
    log_action(db, current, action, "dentist", dentist.id, dentist.email)
    db.commit()
    db.refresh(dentist)
    return dentist


@router.delete("/{dentist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dentist(
    dentist_id: int,
    db: Session = Depends(get_db),
    current: models.Dentist = Depends(require_dentist),
):
    if current.id == dentist_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own account.")
    dentist = db.query(models.Dentist).get(dentist_id)
    if not dentist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dentist not found.")
    log_action(db, current, "dentist.delete", "dentist", dentist.id, dentist.email)
    db.delete(dentist)
    db.commit()
