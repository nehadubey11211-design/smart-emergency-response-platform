from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index
from sqlalchemy.sql import func

from app.database.db import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_hospital_location", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<Hospital id={self.id} name={self.name!r} lat={self.latitude} lon={self.longitude}>"
    