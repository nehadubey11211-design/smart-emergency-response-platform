"""
FILE: backend/app/routes/analytics.py
============================================
Analytics & Reporting Endpoints
============================================
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.accident_model import Accident, accident_status

router = APIRouter()


@router.get(
    "/summary",
    summary="Dashboard summary statistics",
)
async def get_summary(db: AsyncSession = Depends(get_db)):
    today = datetime.now(tz=timezone.utc).date()

    total_today = await db.scalar(
        select(func.count()).select_from(Accident).where(func.date(Accident.detected_at) == today)
    )

    active_incidents = await db.scalar(
        select(func.count()).select_from(Accident).where(Accident.status != accident_status.resolved)
    )

    resolved_today = await db.scalar(
        select(func.count()).select_from(Accident).where(
            func.date(Accident.detected_at) == today,
            Accident.status == accident_status.resolved,
        )
    )

    result = await db.execute(select(Accident).where(Accident.resolved_at.isnot(None)))
    resolved_accidents = result.scalars().all()

    avg_response_minutes = 0.0
    if resolved_accidents:
        times = [
            (a.resolved_at - a.detected_at).total_seconds() / 60
            for a in resolved_accidents
            if a.resolved_at and a.detected_at
        ]
        avg_response_minutes = round(sum(times) / len(times), 1) if times else 0.0

    return {
        "total_today": total_today,
        "active_incidents": active_incidents,
        "resolved_today": resolved_today,
        "avg_response_time_minutes": avg_response_minutes,
    }


@router.get(
    "/severity-breakdown",
    summary="Accident count grouped by severity (pie chart data)",
)
async def severity_breakdown(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Accident.severity,
            func.count(Accident.id).label("count"),
        )
        .group_by(Accident.severity)
        .order_by(func.count(Accident.id).desc())
    )
    return [{"severity": row.severity, "count": row.count} for row in result]


@router.get(
    "/trends",
    summary="Accident count per day (line chart data)",
)
async def get_trends(days: int = 7, db: AsyncSession = Depends(get_db)):
    if days < 1 or days > 365:
        days = 7

    start_date = datetime.now(tz=timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Accident.detected_at).label("date"),
            func.count(Accident.id).label("count"),
        )
        .where(Accident.detected_at >= start_date)
        .group_by(func.date(Accident.detected_at))
        .order_by(func.date(Accident.detected_at).asc())
    )

    return [{"date": str(row.date), "count": row.count} for row in result]


@router.get(
    "/status-breakdown",
    summary="Accident count grouped by status",
)
async def status_breakdown(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Accident.status,
            func.count(Accident.id).label("count"),
        )
        .group_by(Accident.status)
    )

    return [{"status": row.status, "count": row.count} for row in result]


@router.get(
    "/hotspots",
    summary="Top locations by accident frequency",
)
async def get_hotspots(limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Accident.location,
            func.count(Accident.id).label("total"),
        )
        .group_by(Accident.location)
        .order_by(func.count(Accident.id).desc())
        .limit(limit)
    )
    return [{"location": row.location, "total": row.total} for row in result]
