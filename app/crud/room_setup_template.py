from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.models.room_setup_template import RoomSetupTemplate
from app.schemas.db.room_setup_template import RoomSetupTemplateCreate


def get_first(session: Session) -> Optional[RoomSetupTemplate]:
    """Return the first record in room_setup_templates, or ``None`` if the table is empty."""
    return session.exec(select(RoomSetupTemplate)).first()


def get_by_id(session: Session, template_id: int) -> Optional[RoomSetupTemplate]:
    """Fetch a single template by its primary key."""
    return session.get(RoomSetupTemplate, template_id)


def get_all(session: Session) -> list[RoomSetupTemplate]:
    """Return every row in room_setup_templates."""
    return list(session.exec(select(RoomSetupTemplate)).all())


def create(session: Session, data: RoomSetupTemplateCreate) -> RoomSetupTemplate:
    """Create a new template row."""
    record = RoomSetupTemplate.model_validate(data)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
