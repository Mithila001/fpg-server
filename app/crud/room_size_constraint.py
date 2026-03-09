from __future__ import annotations

from typing import Optional, Sequence

from sqlmodel import Session, select

from app.models.room_size_constraint import RoomSizeConstraint
from app.schemas.db.room_size_constraints import RoomSizeConstraintCreate


def get_all(session: Session) -> Sequence[RoomSizeConstraint]:
    """Return every row in the room_size_constraints table.

    ``Session.exec(...).all()`` returns a :class:`~typing.Sequence`, not a
    concrete list, so the annotation must reflect that to keep Pylance happy.
    """
    return session.exec(select(RoomSizeConstraint)).all()


def get_by_id(session: Session, constraint_id: int) -> Optional[RoomSizeConstraint]:
    """Fetch a single constraint by its primary key.

    Returns ``None`` if no matching record exists.
    """
    return session.get(RoomSizeConstraint, constraint_id)


def create(session: Session, data: RoomSizeConstraintCreate) -> RoomSizeConstraint:
    """Create a new row from a ``RoomSizeConstraintCreate`` schema.

    The supplied schema is validated and converted into the ORM model before
    being persisted.
    """
    record = RoomSizeConstraint.model_validate(data)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update(
    session: Session, constraint_id: int, data: RoomSizeConstraintCreate
) -> Optional[RoomSizeConstraint]:
    """Modify an existing constraint.

    Only fields present on ``data`` are updated (``exclude_unset`` behavior).
    If the row does not exist, ``None`` is returned.
    """
    record = session.get(RoomSizeConstraint, constraint_id)
    if record is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def delete(session: Session, constraint_id: int) -> bool:
    """Remove the constraint with the given id.

    Returns ``True`` if a row was deleted, ``False`` otherwise.
    """
    record = session.get(RoomSizeConstraint, constraint_id)
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True
