from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db.session import get_session
from app.crud.user import create_user, get_users
from app.schemas.user import UserCreate, UserRead

router = APIRouter()

@router.post("/", response_model=UserRead)
def create(user: UserCreate, session: Session = Depends(get_session)):
    return create_user(session, user)

@router.get("/", response_model=list[UserRead])
def read(session: Session = Depends(get_session)):
    return get_users(session)
