from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str

class UserRead(UserCreate):
    id: int
