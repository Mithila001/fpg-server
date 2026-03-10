from datetime import date
from typing import ClassVar, List, Optional

from sqlalchemy import Column, String, Date, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RoomRelationsConstraint(SQLModel, table=True):
    __tablename__: ClassVar[str] = "room_relations_constraints"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    room_type: str = Field(
        sa_column=Column("room_type", String(255), nullable=False, unique=True)
    )
    related_room: Optional[List[str]] = Field(
        default=None, sa_column=Column("related_room", JSONB)
    )
    last_updated: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, server_default=text("CURRENT_DATE")),
    )
