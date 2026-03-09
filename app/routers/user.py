from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.schemas.user import UserCreate, UserRead
from app.models.user import User
from app.core.database import get_session

router = APIRouter()


@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = User.from_orm(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@router.get("/", response_model=List[UserRead])
def read_users(session: Session = Depends(get_session)) -> List[UserRead]:
    users = session.exec(select(User)).all()
    return users
