from datetime import date

from pydantic import BaseModel


class SearchResult(BaseModel):
    platform: str
    id: int
    client_id:int |None=None
    client_username:str |None=None
    client_email:str |None=None
    customer_name: str
    order_number: str
    product_name:str |None=None
    amount: float
    status: str
    order_date: date
    platform:str
