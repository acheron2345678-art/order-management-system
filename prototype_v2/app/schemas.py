from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import OrderStatus, UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: UserRole


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str | None
    currency: str
    is_open: bool


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    name: str
    description: str | None
    category: str
    price: Decimal
    image_url: str | None
    is_available: bool


class OrderItemCreate(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    store_id: int = Field(gt=0)
    customer_id: int | None = Field(default=None, gt=0)
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: str = Field(min_length=5, max_length=255)
    customer_phone: str | None = Field(default=None, max_length=32)
    delivery_address: str = Field(min_length=5, max_length=500)
    notes: str | None = Field(default=None, max_length=500)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=80)

    @field_validator("customer_name", "customer_email", "delivery_address", mode="before")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    menu_item_id: int | None
    item_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    customer_id: int | None
    customer_name: str
    customer_email: str
    customer_phone: str | None
    delivery_address: str
    notes: str | None
    status: OrderStatus
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class StatusBreakdownItem(BaseModel):
    status: str
    count: int


class RevenuePoint(BaseModel):
    date: date
    revenue: Decimal
    orders: int


class TopItem(BaseModel):
    name: str
    quantity: int
    revenue: Decimal


class DashboardAnalytics(BaseModel):
    store_id: int
    total_revenue: Decimal
    order_count: int
    active_orders: int
    average_order_value: Decimal
    top_items: list[TopItem]
    status_breakdown: list[StatusBreakdownItem]
    revenue_trend: list[RevenuePoint]
