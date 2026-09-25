from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator

from app.models import DentistRole, RiskLevel, Gender

# Password bounds applied everywhere a password is set or changed
# (registration, dentist creation, password reset, self-registration).
# Lower bound: reject trivially weak passwords. Upper bound: 72 - bcrypt
# only uses the first 72 BYTES of a password and (in modern bcrypt
# implementations) raises rather than silently truncating past that, so
# this is enforced here, upfront, with a clear validation error, instead
# of silently cutting off part of what the user typed further down the
# stack where they'd never find out why "the same" password doesn't work
# after account creation.
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 72

# Business rule for patient birthdates - configurable here rather than as
# a magic number scattered through the codebase. A birthdate can't be in
# the future, and 120 years is a generous upper bound on plausible human
# age for a walk-in dental patient.
PATIENT_MAX_AGE_YEARS = 120


def _validate_birthdate(value: Optional[date]) -> Optional[date]:
    """Shared birthdate sanity check, reused by every schema that accepts
    one. Pydantic's `date` type only validates that the value IS a date -
    it says nothing about whether that date makes sense for a patient, so
    this fills that gap on every code path (staff-entered patients,
    patient self-registration, and record updates alike). The frontend
    performs the same checks for immediate feedback, but this is the
    check that actually matters: it runs no matter what client is calling
    the API."""
    if value is None:
        return value
    today = date.today()
    if value > today:
        raise ValueError("Birthdate cannot be in the future.")
    max_age_date = date(today.year - PATIENT_MAX_AGE_YEARS, today.month, today.day)
    if value < max_age_date:
        raise ValueError(f"Birthdate must be within the last {PATIENT_MAX_AGE_YEARS} years.")
    return value


def _normalize_email(value) -> Optional[str]:
    """Lowercases and trims whitespace from every email field on write.

    Without this, "John@gmail.com" and "john@gmail.com" are treated as two
    different accounts everywhere an email is compared by exact string
    match - the duplicate-account check on registration, the UNIQUE
    constraint at the database level, and the account lookup on login all
    do a plain equality check, none of which understands that email
    addresses are conventionally case-insensitive. That means a patient
    could accidentally end up with two accounts, or worse, get locked out
    of their own account by typing their email in different capitalization
    than they registered with.

    Normalizing here, at the schema layer, means every code path that
    creates or looks up an account (registration, dentist creation, login,
    record updates) goes through the same rule with no risk of one call
    site forgetting to apply it. This does NOT attempt Gmail's dot- or
    plus-alias folding (e.g. treating john.doe@gmail.com and
    john+x@gmail.com as the same inbox) - that's provider-specific
    behavior that would incorrectly merge distinct addresses on any
    non-Gmail provider, so it's deliberately out of scope here.
    """
    if value is None:
        return value
    return str(value).strip().lower()


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)

    _normalize_email = field_validator("email")(_normalize_email)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    dentist: "DentistOut"


# ---------- Dentist ----------
class DentistBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    middle_name: Optional[str] = Field(default=None, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    role: DentistRole = DentistRole.dentist
    license_no: Optional[str] = Field(default=None, max_length=60)

    _normalize_email = field_validator("email")(_normalize_email)


class DentistCreate(DentistBase):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class DentistUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    middle_name: Optional[str] = Field(default=None, max_length=60)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    email: Optional[EmailStr] = None
    role: Optional[DentistRole] = None
    license_no: Optional[str] = Field(default=None, max_length=60)

    _normalize_email = field_validator("email")(_normalize_email)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class DentistOut(DentistBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    is_active: bool
    created_at: datetime


class DentistPasswordReset(BaseModel):
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


Token.model_rebuild()


# ---------- Patient ----------
class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    middle_name: Optional[str] = Field(default=None, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    birthdate: Optional[date] = None
    gender: Optional[Gender] = None
    contact_number: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=255)

    _validate_birthdate = field_validator("birthdate")(_validate_birthdate)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    middle_name: Optional[str] = Field(default=None, max_length=60)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    birthdate: Optional[date] = None
    gender: Optional[Gender] = None
    contact_number: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=255)

    _validate_birthdate = field_validator("birthdate")(_validate_birthdate)


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    age: Optional[int] = None
    email: Optional[EmailStr] = None
    created_at: datetime


class PatientListOut(PatientOut):
    screening_count: int = 0
    last_risk_level: Optional[RiskLevel] = None


# ---------- Patient portal (self-service) ----------
class PatientRegister(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    middle_name: Optional[str] = Field(default=None, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    contact_number: Optional[str] = Field(default=None, max_length=30)
    birthdate: Optional[date] = None
    gender: Optional[Gender] = None
    address: Optional[str] = Field(default=None, max_length=255)

    _validate_birthdate = field_validator("birthdate")(_validate_birthdate)
    _normalize_email = field_validator("email")(_normalize_email)


class PatientLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)

    _normalize_email = field_validator("email")(_normalize_email)


class PatientToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient: "PatientOut"


# ---------- Detection / Recommendation ----------
class DetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    source_model: str
    detection_set: str


class ModelStatsOut(BaseModel):
    """Per-model runtime stats for a single screening's compare view.

    NOT accuracy/precision/recall - those require ground-truth labels,
    which a live patient photo doesn't have. This is descriptive only:
    what each model found on THIS image and how fast. Real
    precision/recall/mAP comes from evaluate_models.py run against your
    labeled test set after training.
    """
    detection_count: int
    avg_confidence: Optional[float] = None
    inference_ms: float
    detections: list[DetectionOut] = []


class ModelComparisonOut(BaseModel):
    screening_id: int
    yolov8: ModelStatsOut
    yolov12: ModelStatsOut
    fused_count: int
    # Count of yolov8/yolov12 raw detections that overlap (IoU >= 0.5) and
    # share the same label - i.e. both models independently flagged the
    # same finding. Higher agreement generally signals higher confidence
    # in that specific finding, though it is still not a substitute for
    # ground-truth-based accuracy metrics.
    agreement_count: int


class LiveDetectionOut(BaseModel):
    """Same shape as DetectionOut but without the DB-only fields (id,
    detection_set) - a live-preview frame is never persisted as a row."""
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    source_model: str


class LivePreviewOut(BaseModel):
    """Response for one live-preview frame from the intraoral camera loop.
    Nothing behind this response is written to disk or the database."""
    detections: list[LiveDetectionOut] = []
    width: int
    height: int
    inference_ms: float


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    priority: int
    order_index: int


class ClinicalNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class TierConfirm(BaseModel):
    """Dentist-reviewed severity tier for a screening. This is the ground
    truth the KNN recommender learns from - 'the AI said LOW, the dentist
    looked and said HIGH' is exactly the signal synthetic data fakes."""
    risk_level: RiskLevel


class ClinicalNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    body: str
    created_at: datetime
    dentist_id: Optional[int] = None


# ---------- Screening ----------
class ScreeningSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    risk_level: RiskLevel
    risk_score: int
    detection_count: int = 0


class ScreeningDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    dentist_id: Optional[int] = None
    image_path: str
    image_width: int
    image_height: int
    risk_level: RiskLevel
    risk_score: int
    created_at: datetime
    yolov8_ms: float
    yolov12_ms: float
    detections: list[DetectionOut] = []
    recommendations: list[RecommendationOut] = []
    notes: list[ClinicalNoteOut] = []


# Patient-portal view of a screening: no internal model-timing figures, no
# staff clinical notes (those are for staff, not necessarily patient-facing
# verbatim), and detections are pre-filtered to the fused/final set only -
# not the raw per-model debug output dentists can compare on their side.
class PatientScreeningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_path: str
    image_width: int
    image_height: int
    risk_level: RiskLevel
    risk_score: int
    created_at: datetime
    detections: list[DetectionOut] = []
    recommendations: list[RecommendationOut] = []


# ---------- Dashboard ----------
class MonthlyTrendPoint(BaseModel):
    month: str
    count: int


class DetectionBreakdownPoint(BaseModel):
    label: str
    count: int


class DashboardSummary(BaseModel):
    total_screenings: int
    total_patients: int
    high_risk_cases: int
    todays_screenings: int
    monthly_trend: list[MonthlyTrendPoint]
    detection_breakdown: list[DetectionBreakdownPoint]


# ---------- Patient risk trend ----------
class RiskTrendPoint(BaseModel):
    screening_id: int
    created_at: datetime
    risk_score: int
    risk_level: RiskLevel


# ---------- Audit log ----------
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_dentist_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime


# ---------- Health check ----------
class HealthOut(BaseModel):
    status: str  # "ok" | "degraded"
    database: str  # "connected" | "unreachable"
    detection_enabled: bool = True  # false = AI inference switched off
