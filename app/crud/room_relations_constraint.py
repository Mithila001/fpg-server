from __future__ import annotations

from typing import Optional, Sequence

from sqlmodel import Session, select

from app.models.room_relations_constraint import RoomRelationsConstraint
from app.schemas.db.room_relations_constraints import (
    RoomRelationsConstraintCreate,
)


def get_all(session: Session) -> Sequence[RoomRelationsConstraint]:
    """Return every row in the room_relations_constraints table."""
    return session.exec(select(RoomRelationsConstraint)).all()


def get_by_id(
    session: Session, constraint_id: int
) -> Optional[RoomRelationsConstraint]:
    """Fetch a single record by its primary key. Returns ``None`` if absent."""
    return session.get(RoomRelationsConstraint, constraint_id)


def create(
    session: Session, data: RoomRelationsConstraintCreate
) -> RoomRelationsConstraint:
    """Create a new relation constraint from a schema."""
    record = RoomRelationsConstraint.model_validate(data)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update(
    session: Session, constraint_id: int, data: RoomRelationsConstraintCreate
) -> Optional[RoomRelationsConstraint]:
    """Modify an existing row, returning the updated object or ``None``."""
    record = session.get(RoomRelationsConstraint, constraint_id)
    if record is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def delete(session: Session, constraint_id: int) -> bool:
    """Remove the specified constraint.

    Returns ``True`` if a row was deleted, ``False`` if it didn't exist.
    """
    record = session.get(RoomRelationsConstraint, constraint_id)
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True
