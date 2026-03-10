from __future__ import annotations

from typing import Any

from sqlmodel import SQLModel


class RoomSetupTemplateBase(SQLModel):
    """Shared properties of a room setup template."""

    name: str
    data: list[dict[str, Any]]


class RoomSetupTemplateCreate(RoomSetupTemplateBase):
    """Properties required when creating a new template."""
    ...


class RoomSetupTemplateRead(RoomSetupTemplateBase):
    """Properties returned in API responses."""

    id: int
