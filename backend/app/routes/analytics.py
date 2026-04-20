"""
FILE: backend/app/routes/analytics.py
============================================
Analytics & Reporting Endpoints
============================================

These endpoints power the Analytics dashboard page with:
  - Summary cards (today's counts, averages)
  - Severity breakdown (pie chart data)
  - Trend data over time (line/area chart data)

SQL AGGREGATION PATTERNS used here:
  - COUNT()          : Total number of records
  - COUNT() FILTER   : Conditional count (PostgreSQL extension to COUNT)
  - AVG()            : Average of a numeric column
  - GROUP BY         : Group rows into buckets
  - func.date()      : Extract just the date part from a timestamp
  - INTERVAL         : Date arithmetic (e.g. "last 7 days")

WHY RETURN PLAIN DICTS INSTEAD OF PYDANTIC MODELS?
  Analytics endpoints return dynamic structures (variable keys from GROUP BY).
  Plain dicts are fine here; for strict typing you'd use TypedDict or a
  custom response model per endpoint.

INTERVIEW TALKING POINT:
  "I used SQLAlchemy's func module for aggregation instead of raw SQL strings.
  This keeps the code database-agnostic — the same Python code works with
  PostgreSQL, MySQL, and SQLite, which helped during testing (SQLite in tests)."
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.accident_model import Accident, AccidentStatus

router = APIRouter()


@router.get(
    "/summary",
    summary="Dashboard summary statistics",
)
def get_summary(db: Session = Depends(get_db)):
    """
    Returns four KPI numbers used by the summary cards at the top of
    the Dashboard and Analytics pages.

    SQL equivalents:
      SELECT COUNT(*) FROM accidents WHERE DATE(detected_at) = TODAY
      SELECT COUNT(*) FROM accidents WHERE status != 'resolved'
      SELECT AVG((resolved_at - detected_at)) FROM accidents WHERE resolved_at IS NOT NULL
    """
    today = datetime.now(tz=timezone.utc).date()

    # Total accidents detected today
    total_today = (
        db.query(Accident)
        .filter(func.date(Accident.detected_at) == today)
        .count()
    )

    # All currently active incidents (not yet resolved)
    active_incidents = (
        db.query(Accident)
        .filter(Accident.status != AccidentStatus.resolved)
        .count()
    )

    # Accidents both detected AND resolved today
    resolved_today = (
        db.query(Accident)
        .filter(
            func.date(Accident.detected_at) == today,
            Accident.status == AccidentStatus.resolved,
        )
        .count()
    )

    # Average response time in minutes across all historical resolved incidents
    resolved_accidents = (
        db.query(Accident)
        .filter(Accident.resolved_at.isnot(None))
        .all()
    )

    avg_response_minutes = 0.0
    if resolved_accidents:
        times = [
            (a.resolved_at - a.detected_at).total_seconds() / 60
            for a in resolved_accidents
            if a.resolved_at and a.detected_at
        ]
        avg_response_minutes = round(sum(times) / len(times), 1) if times else 0.0

    return {
        "total_today":               total_today,
        "active_incidents":          active_incidents,
        "resolved_today":            resolved_today,
        "avg_response_time_minutes": avg_response_minutes,
    }


@router.get(
    "/severity-breakdown",
    summary="Accident count grouped by severity (pie chart data)",
)
def severity_breakdown(db: Session = Depends(get_db)):
    """
    Returns the count of accidents at each severity level.
    Used to render the severity distribution pie chart.

    SQL equivalent:
      SELECT severity, COUNT(*) as count
      FROM accidents
      GROUP BY severity
      ORDER BY count DESC
    """
    results = (
        db.query(
            Accident.severity,
            func.count(Accident.id).label("count"),
        )
        .group_by(Accident.severity)
        .order_by(func.count(Accident.id).desc())
        .all()
    )

    return [{"severity": row.severity, "count": row.count} for row in results]


@router.get(
    "/trends",
    summary="Accident count per day (line chart data)",
)
def get_trends(days: int = 7, db: Session = Depends(get_db)):
    """
    Returns daily accident counts for the last N days.
    Used to render the trend area/line chart.

    The ?days= query param lets the frontend switch between 7d / 14d / 30d views.

    SQL equivalent:
      SELECT DATE(detected_at) as date, COUNT(*) as count
      FROM accidents
      WHERE detected_at >= NOW() - INTERVAL '7 days'
      GROUP BY DATE(detected_at)
      ORDER BY date ASC
    """
    # Validate input to prevent unreasonably large queries
    if days < 1 or days > 365:
        days = 7

    start_date = datetime.now(tz=timezone.utc) - timedelta(days=days)

    results = (
        db.query(
            func.date(Accident.detected_at).label("date"),
            func.count(Accident.id).label("count"),
        )
        .filter(Accident.detected_at >= start_date)
        .group_by(func.date(Accident.detected_at))
        .order_by(func.date(Accident.detected_at).asc())
        .all()
    )

    return [{"date": str(row.date), "count": row.count} for row in results]


@router.get(
    "/status-breakdown",
    summary="Accident count grouped by status",
)
def status_breakdown(db: Session = Depends(get_db)):
    """
    Returns how many incidents are in each status (detected / responding / resolved).
    Can be used for an operational pipeline / funnel chart.
    """
    results = (
        db.query(
            Accident.status,
            func.count(Accident.id).label("count"),
        )
        .group_by(Accident.status)
        .all()
    )

    return [{"status": row.status, "count": row.count} for row in results]


@router.get(
    "/hotspots",
    summary="Top locations by accident frequency",
)
def get_hotspots(limit: int = 10, db: Session = Depends(get_db)):
    """
    Returns the most accident-prone locations.
    Useful for infrastructure planning and targeted camera deployment.

    SQL equivalent:
      SELECT location, COUNT(*) as total
      FROM accidents
      GROUP BY location
      ORDER BY total DESC
      LIMIT 10
    """
    results = (
        db.query(
            Accident.location,
            func.count(Accident.id).label("total"),
        )
        .group_by(Accident.location)
        .order_by(func.count(Accident.id).desc())
        .limit(limit)
        .all()
    )

    return [{"location": row.location, "total": row.total} for row in results]
