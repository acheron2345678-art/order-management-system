from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("PROTOTYPE_APP_NAME", "Nova Order Management Prototype")
    api_prefix: str = "/api/v1"
    database_url: str = os.getenv(
        "PROTOTYPE_DATABASE_URL",
        "sqlite:///./prototype.db",
    )
    tax_rate: float = float(os.getenv("PROTOTYPE_TAX_RATE", "0.10"))
    seed_demo: bool = os.getenv("PROTOTYPE_SEED_DEMO", "true").lower() in {"1", "true", "yes", "on"}


settings = Settings()
