from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Numeric, Integer, DateTime


class RoomSizeConstraint(SQLModel, table=True):
    __tablename__ = "room_size_constraints"

    id: Optional[int] = Field(default=None, primary_key=True)
    # `name` is a reserved keyword in some contexts so we declare the column explicitly
    name: str = Field(sa_column=Column("name", String(255), nullable=False))

    min_w: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_w: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    min_h: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_h: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_area: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    min_area: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    preset_id: Optional[int] = Field(default=None, sa_column=Column(Integer))
    last_updated: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, server_default="CURRENT_TIMESTAMP"))
