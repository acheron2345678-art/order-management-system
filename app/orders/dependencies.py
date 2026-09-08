from fastapi import HTTPException

from app.core.config import VALID_PLATFORMS
from app.orders.models import InsightsOrders, SwiggyOrders


PLATFORM_MODELS = {
    "swiggy": SwiggyOrders,
    "insights": InsightsOrders,
}


def get_platform_context(platform: str):
    platform_key = platform.lower()

    if platform_key not in PLATFORM_MODELS:
        raise HTTPException(status_code=404, detail="Platform not found")

    return {
        "key": platform_key,
        "name": VALID_PLATFORMS[platform_key],
        "model": PLATFORM_MODELS[platform_key],
    }
