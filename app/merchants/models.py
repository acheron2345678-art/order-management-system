from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import relationship

from app.database.base import Base
from app.products.models import Restaurant
from app.users.models import User


class MerchantRestaurant(Base):
    __tablename__ = "merchant_restaurants"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_merchant_restaurants_user_id",
        ),
        UniqueConstraint(
            "restaurant_id",
            name="uq_merchant_restaurants_restaurant_id",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    restaurant_id = Column(
        Integer,
        ForeignKey(
            "restaurants.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        User,
        lazy="joined",
    )

    restaurant = relationship(
        Restaurant,
        lazy="joined",
    )