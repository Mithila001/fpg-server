from typing import Optional

from sqlmodel import Session, select

from app.models.room_size_constraint import RoomSizeConstraint
from app.schemas.room_size_constraints import RoomSizeConstraintCreate


def get_all(session: Session) -> list[RoomSizeConstraint]:
    return session.exec(select(RoomSizeConstraint)).all()


def get_by_id(session: Session, constraint_id: int) -> Optional[RoomSizeConstraint]:
    return session.get(RoomSizeConstraint, constraint_id)


def create(session: Session, data: RoomSizeConstraintCreate) -> RoomSizeConstraint:
    record = RoomSizeConstraint.model_validate(data)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update(
    session: Session, constraint_id: int, data: RoomSizeConstraintCreate
) -> Optional[RoomSizeConstraint]:
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
    record = session.get(RoomSizeConstraint, constraint_id)
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True
