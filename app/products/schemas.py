from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


ProductPlatform = Literal[
    "swiggy",
    "insights",
]


class CreateProduct(BaseModel):
    product_name: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    price: Decimal = Field(
        gt=0
    )

    platform: ProductPlatform

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    is_active: bool = True


class UpdateProduct(BaseModel):
    product_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    price: Decimal | None = Field(
        default=None,
        gt=0,
    )

    platform: ProductPlatform | None = None

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    product_name: str
    description: str | None = None
    price: Decimal
    platform: ProductPlatform
    image_url: str | None = None
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )