from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.routes.auth import get_admin_user
from app.models.hospital_model import Hospital

router = APIRouter()

_INITIAL_HOSPITALS = [
    {"name": "KEM Hospital Pune", "latitude": 18.5169, "longitude": 73.8478},
    {"name": "Ruby Hall Clinic", "latitude": 18.5359, "longitude": 73.8809},
    {"name": "Jehangir Hospital", "latitude": 18.5299, "longitude": 73.8800},
    {"name": "Sassoon General Hospital", "latitude": 18.5175, "longitude": 73.8553},
    {"name": "Poona Hospital", "latitude": 18.5284, "longitude": 73.8474},
    {"name": "Deenanath Mangeshkar Hospital", "latitude": 18.5008, "longitude": 73.8153},
]


@router.post("/admin/seed-hospitals", summary="Seed initial hospitals (admin)")
async def seed_hospitals(db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)) -> List[Hospital]:
    created = []
    for h in _INITIAL_HOSPITALS:
        hospital = Hospital(name=h["name"], latitude=h["latitude"], longitude=h["longitude"], is_active=True)
        db.add(hospital)
        created.append(hospital)
    await db.commit()
    # Refresh to get IDs
    for hosp in created:
        await db.refresh(hosp)
    return created
