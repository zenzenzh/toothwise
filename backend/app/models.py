import enum
from datetime import datetime, date, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    """Timezone-aware UTC now. Replaces deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


class DentistRole(str, enum.Enum):
    admin = "admin"
    dentist = "dentist"


class RiskLevel(str, enum.Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


class Gender(str, enum.Enum):
    male = "Male"
    female = "Female"
    other = "Other"


# Sex kept as a backward-compatible alias - some older imports/reports may
# still reference it by this name.
Sex = Gender


class Dentist(Base):
    __tablename__ = "dentists"

    id = Column(Integer, primary_key=True, index=True)
    # full_name is kept as a stored, denormalized column - it's what PDF
    # reports, notifications, and audit-log rendering already read. It's
    # computed from the three parts below on every create/update instead of
    # being collected directly, so nothing downstream has to change.
    full_name = Column(String(120), nullable=False)
    first_name = Column(String(60), nullable=True)
    middle_name = Column(String(60), nullable=True)
    last_name = Column(String(60), nullable=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(DentistRole), default=DentistRole.dentist, nullable=False)
    license_no = Column(String(60), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    screenings = relationship("Screening", back_populates="dentist")
    notes = relationship("ClinicalNote", back_populates="dentist")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    first_name = Column(String(60), nullable=True)
    middle_name = Column(String(60), nullable=True)
    last_name = Column(String(60), nullable=True)
    birthdate = Column(Date, nullable=True)
    gender = Column(SAEnum(Gender), nullable=True)
    contact_number = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    # Self-service portal login. Nullable because patients created by staff
    # through the clinic-side UI don't necessarily have an online account -
    # only patients who register themselves via the patient portal do.
    email = Column(String(150), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    screenings = relationship(
        "Screening", back_populates="patient", cascade="all, delete-orphan"
    )

    @property
    def age(self) -> int | None:
        if not self.birthdate:
            return None
        today = date.today()
        return today.year - self.birthdate.year - (
            (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
        )


class Screening(Base):
    __tablename__ = "screenings"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    dentist_id = Column(Integer, ForeignKey("dentists.id"), nullable=True)
    image_path = Column(String(255), nullable=False)
    image_width = Column(Integer, nullable=False)
    image_height = Column(Integer, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.low, nullable=False)
    risk_score = Column(Integer, default=0)
    yolov8_ms = Column(Float, default=0.0)
    yolov12_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_utcnow)

    patient = relationship("Patient", back_populates="screenings")
    dentist = relationship("Dentist", back_populates="screenings")
    detections = relationship(
        "Detection", back_populates="screening", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "Recommendation", back_populates="screening", cascade="all, delete-orphan"
    )
    notes = relationship(
        "ClinicalNote", back_populates="screening", cascade="all, delete-orphan"
    )


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(Integer, ForeignKey("screenings.id"), nullable=False)
    label = Column(String(40), nullable=False)
    confidence = Column(Float, nullable=False)
    # Normalized (0-1) box coordinates so the frontend can draw the overlay
    # at any render size without the backend needing to burn boxes into
    # the image pixels.
    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)
    x2 = Column(Float, nullable=False)
    y2 = Column(Float, nullable=False)
    source_model = Column(String(20), default="ensemble")  # yolov8 / yolov12 / ensemble
    # Which detection pass this row belongs to. "fused" is the clinical
    # result (drives risk score + recommendations); "yolov8_raw" /
    # "yolov12_raw" are each model's unfused output, kept only so the UI
    # can render a side-by-side model comparison. Without this flag, a
    # fused row whose source_model happens to be "yolov8" (single-model
    # agreement) is indistinguishable from a raw yolov8_raw row.
    detection_set = Column(String(20), default="fused", nullable=False)

    screening = relationship("Screening", back_populates="detections")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(Integer, ForeignKey("screenings.id"), nullable=False)
    text = Column(Text, nullable=False)
    priority = Column(Integer, default=0)  # 0 = normal, 1 = urgent
    order_index = Column(Integer, default=0)

    screening = relationship("Screening", back_populates="recommendations")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    screening_id = Column(Integer, ForeignKey("screenings.id"), nullable=False)
    dentist_id = Column(Integer, ForeignKey("dentists.id"), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    screening = relationship("Screening", back_populates="notes")
    dentist = relationship("Dentist", back_populates="notes")


class AuditLog(Base):
    """
    Append-only record of sensitive actions (auth, patient/dentist/screening
    CRUD, password resets) for ISO/IEC 25010 "Security - Accountability"
    and general clinical record-keeping compliance. Rows are never updated
    or deleted by the app - only inserted.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_dentist_id = Column(Integer, ForeignKey("dentists.id"), nullable=True)
    actor_email = Column(String(150), nullable=True)  # denormalized snapshot,
    # survives even if the acting account is later deleted
    action = Column(String(60), nullable=False)  # e.g. "login", "patient.create"
    entity_type = Column(String(40), nullable=True)  # e.g. "patient", "screening"
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # short human-readable context
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
