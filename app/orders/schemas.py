from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


OrderStatus = Literal["pending", "processing", "completed", "cancelled"]


class CreateOrder(BaseModel):
    customer_name: str
    order_number: str
    amount: float
    status: OrderStatus = "pending"
    order_date: date


class UpdateOrder(BaseModel):
    customer_name: str
    order_number: str
    amount: float
    status: OrderStatus
    order_date: date


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    order_number: str
    amount: float
    status: OrderStatus
    order_date: date
