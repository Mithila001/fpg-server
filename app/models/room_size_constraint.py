from datetime import datetime
from typing import Optional, ClassVar

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Numeric, Integer, DateTime, text, UniqueConstraint


class RoomSizeConstraint(SQLModel, table=True):
    __tablename__: ClassVar[str] = "room_size_constraints"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("type", "size", name="uq_type_size"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    # match varchar(255)
    type: str = Field(
        sa_column=Column("type", String(255), nullable=False)
    )
    size: Optional[str] = Field(default=None, sa_column=Column(String(50)))

    min_w: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_w: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    min_h: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_h: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    max_area: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    min_area: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    preset_id: Optional[str] = Field(default=None, sa_column=Column(String(50)))
    last_updated: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=text("CURRENT_TIMESTAMP")),
    )
