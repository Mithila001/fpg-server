from typing import Any, ClassVar, Optional

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RoomSetupTemplate(SQLModel, table=True):
    __tablename__: ClassVar[str] = "room_setup_templates"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column("name", String(255), nullable=False))
    data: list[dict[str, Any]] = Field(sa_column=Column("data", JSONB, nullable=False))
