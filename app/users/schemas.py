from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


UserRole = Literal[
    "admin",
    "client",
]


class UserCreate(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=100,
    )

    email: str = Field(
        min_length=1,
        max_length=255,
    )

    password: str = Field(
        min_length=12,
        max_length=128,
    )

    role: UserRole = "client"


class UserUpdate(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=100,
    )

    email: str = Field(
        min_length=1,
        max_length=255,
    )

    role: UserRole

    is_active: bool


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )
