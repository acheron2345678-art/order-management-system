from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "client"


class UserUpdate(BaseModel):
    username: str
    email: str
    role: str
    is_active: bool


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )