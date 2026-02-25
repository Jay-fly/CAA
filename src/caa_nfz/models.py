from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NoFlyZone(Base):
    __tablename__ = "no_fly_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layer: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    properties: Mapped[str | None] = mapped_column(Text)  # JSON string of original attributes
    geometry = mapped_column(Geometry(srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
