from decimal import Decimal
from typing import Literal

from pydantic import BaseModel,ConfigDict

class CreateProduct(BaseModel):
    product_name:str
    description:str | None = None
    price:Decimal
    platform:Literal["Swiggy","Insights"]
    image_url:str | None=None
    is_active:bool=True

class UpdateProduct(BaseModel):
    product_name:str | None=None
    description:str | None=None
    price:Decimal | None=None
    platform:Literal["Swiggy","insights"] |None=None
    image_url:str | None=None
    is_active:bool |None=None

class ProductResponse(BaseModel):
    id:int 
    product_name:str
    description:str | None = None
    price:Decimal
    platform:Literal["Swiggy","Insights"]
    image_url:str | None=None
    is_active:bool

    model_config=ConfigDict(from_attributes=True)
    