from sqlmodel import Session, select
from app.models.user import User
from app.schemas.user import UserCreate

def create_user(session: Session, user_in: UserCreate):
    user = User(name=user_in.name, email=user_in.email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def get_users(session: Session):
    return session.exec(select(User)).all()
