from collections import Counter
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_dentist

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def summary(
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(get_current_dentist),
):
    total_screenings = db.query(func.count(models.Screening.id)).scalar() or 0
    total_patients = db.query(func.count(models.Patient.id)).scalar() or 0
    high_risk_cases = (
        db.query(func.count(models.Screening.id))
        .filter(models.Screening.risk_level == models.RiskLevel.high)
        .scalar() or 0
    )

    today = date.today()
    todays_screenings = (
        db.query(func.count(models.Screening.id))
        .filter(func.date(models.Screening.created_at) == today)
        .scalar() or 0
    )

    # Last 6 months trend
    months = []
    cursor = today.replace(day=1)
    for i in range(5, -1, -1):
        m = (cursor.month - i - 1) % 12 + 1
        y = cursor.year + ((cursor.month - i - 1) // 12)
        months.append((y, m))

    trend = []
    for (y, m) in months:
        count = (
            db.query(func.count(models.Screening.id))
            .filter(
                func.extract("year", models.Screening.created_at) == y,
                func.extract("month", models.Screening.created_at) == m,
            )
            .scalar() or 0
        )
        label = datetime(y, m, 1).strftime("%b %Y")
        trend.append(schemas.MonthlyTrendPoint(month=label, count=count))

    # Only count the fused/clinical detection set - the raw yolov8_raw /
    # yolov12_raw rows exist purely for the model-comparison view and would
    # triple-count every finding if included here.
    detections = (
        db.query(models.Detection.label)
        .filter(models.Detection.detection_set == "fused")
        .all()
    )
    breakdown_counter = Counter(d[0] for d in detections)
    breakdown = [
        schemas.DetectionBreakdownPoint(label=label, count=count)
        for label, count in breakdown_counter.most_common()
    ]

    return schemas.DashboardSummary(
        total_screenings=total_screenings,
        total_patients=total_patients,
        high_risk_cases=high_risk_cases,
        todays_screenings=todays_screenings,
        monthly_trend=trend,
        detection_breakdown=breakdown,
    )
