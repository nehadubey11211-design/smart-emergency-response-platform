"""
FILE: backend/app/routes/analytics.py
============================================
Analytics & Reporting Endpoints
============================================
"""

import time
from datetime import datetime, timedelta, timezone
from functools import wraps

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.routes.auth import get_current_user_from_header
from app.models.accident_model import Accident, AccidentStatus

router = APIRouter(dependencies=[Depends(get_current_user_from_header)])

_cache: dict = {}


def ttl_cache(seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "db"}
            key = f"{func.__name__}:{args}:{sorted(cache_kwargs.items())}"
            if key in _cache:
                result, expires = _cache[key]
                if time.monotonic() < expires:
                    return result
            result = await func(*args, **kwargs)
            _cache[key] = (result, time.monotonic() + seconds)
            return result
        return wrapper
    return decorator


@router.get(
    "/summary",
    summary="Dashboard summary statistics",
)
@ttl_cache(seconds=60)
async def get_summary(db: AsyncSession = Depends(get_db)):
    today = datetime.now(tz=timezone.utc).date()

    total_today = await db.scalar(
        select(func.count()).select_from(Accident).where(func.date(Accident.detected_at) == today)
    )

    active_incidents = await db.scalar(
        select(func.count()).select_from(Accident).where(Accident.status != AccidentStatus.resolved)
    )

    resolved_today = await db.scalar(
        select(func.count()).select_from(Accident).where(
            func.date(Accident.detected_at) == today,
            Accident.status == AccidentStatus.resolved,
        )
    )

    # Compute average response time in the database to avoid loading rows into Python
    avg_seconds_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Accident.resolved_at) -
                func.extract("epoch", Accident.detected_at)
            )
        ).where(Accident.resolved_at.isnot(None))
    )
    avg_seconds = avg_seconds_result.scalar() or 0.0
    avg_response_minutes = round(avg_seconds / 60, 1)

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
@ttl_cache(seconds=300)
async def get_trends(
    days: int = Query(default=7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
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
async def get_hotspots(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
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
