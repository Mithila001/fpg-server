from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.schemas.room_size_constraints import (
    RoomSizeConstraintCreate,
    RoomSizeConstraintRead,
)
from app.crud import room_size_constraint as crud

router = APIRouter()


@router.get("/", response_model=List[RoomSizeConstraintRead])
def get_all(session: Session = Depends(get_session)):
    return crud.get_all(session)


@router.get("/{constraint_id}", response_model=RoomSizeConstraintRead)
def get_by_id(constraint_id: int, session: Session = Depends(get_session)):
    record = crud.get_by_id(session, constraint_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Room size constraint not found")
    return record


@router.post("/", response_model=RoomSizeConstraintRead, status_code=201)
def create(data: RoomSizeConstraintCreate, session: Session = Depends(get_session)):
    return crud.create(session, data)


@router.put("/{constraint_id}", response_model=RoomSizeConstraintRead)
def update(
    constraint_id: int,
    data: RoomSizeConstraintCreate,
    session: Session = Depends(get_session),
):
    record = crud.update(session, constraint_id, data)
    if record is None:
        raise HTTPException(status_code=404, detail="Room size constraint not found")
    return record


@router.delete("/{constraint_id}", status_code=204)
def delete(constraint_id: int, session: Session = Depends(get_session)):
    deleted = crud.delete(session, constraint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Room size constraint not found")
