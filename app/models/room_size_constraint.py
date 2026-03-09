from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Numeric, Integer, DateTime, text


class RoomSizeConstraint(SQLModel, table=True):
    __tablename__ = "room_size_constraints"

    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(sa_column=Column("type", String(50), nullable=False))

    min_w: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_w: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    min_h: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_h: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_area: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    min_area: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    preset_id: Optional[int] = Field(default=None, sa_column=Column(Integer))
    last_updated: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("CURRENT_TIMESTAMP")),
    )
