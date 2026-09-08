from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: str
    total: int
    pending: int
    processing: int
    completed: int
    cancelled: int
    amount: float


class PlatformSummary(BaseModel):
    total: int
    pending: int
    processing: int
    completed: int
    cancelled: int
    amount: float
    trend: list[TrendPoint]


class CombinedSummary(BaseModel):
    total: int
    pending: int
    processing: int
    completed: int
    cancelled: int
    amount: float
    average_order_value: float


class OverallSummary(BaseModel):
    total_orders: int
    revenue: float
    completion_rate: float
    average_order_value: float


class ProductPerformance(BaseModel):
    product_name: str
    orders: int
    revenue: float


class DashboardSummary(BaseModel):
    swiggy: PlatformSummary
    insights: PlatformSummary
    combined: CombinedSummary
    summary: OverallSummary
    products: list[ProductPerformance]

    total_orders: int
    total_amount: float


class DashboardDrilldownOrder(BaseModel):
    platform: str

    id: int

    customer_name: str

    order_number: str

    product_name: str | None = None

    amount: float

    status: str

    order_date: str


class DashboardDrilldownResponse(BaseModel):
    platform: str

    metric: str

    metric_label: str

    date: str

    order_count: int

    total_amount: float

    orders: list[
        DashboardDrilldownOrder
    ]