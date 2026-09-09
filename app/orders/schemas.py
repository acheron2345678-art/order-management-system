from datetime import date
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


OrderStatus = Literal[
    "pending",
    "processing",
    "completed",
    "cancelled",
]


class CreateOrder(BaseModel):
    customer_name: str = Field(
        min_length=1,
        max_length=100,
    )

    order_number: str = Field(
        min_length=3,
        max_length=50,
        pattern=(
            r"^[A-Za-z0-9]"
            r"[A-Za-z0-9_-]{2,49}$"
        ),
    )

    amount: float = Field(
        gt=0
    )

    status: OrderStatus = (
        "pending"
    )

    order_date: date


class UpdateOrder(BaseModel):
    customer_name: str = Field(
        min_length=1,
        max_length=100,
    )

    order_number: str = Field(
        min_length=3,
        max_length=50,
        pattern=(
            r"^[A-Za-z0-9]"
            r"[A-Za-z0-9_-]{2,49}$"
        ),
    )

    amount: float = Field(
        gt=0
    )

    status: OrderStatus

    order_date: date


class OrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    customer_name: str
    order_number: str
    amount: float
    status: OrderStatus
    order_date: date