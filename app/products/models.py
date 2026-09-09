from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import relationship

from app.database.base import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    description = Column(
        String(500),
        nullable=True,
    )

    cuisines = Column(
        String(255),
        nullable=False,
        default="Multi-cuisine",
    )

    rating = Column(
        Numeric(2, 1),
        nullable=False,
        default=4.0,
    )

    delivery_min_minutes = Column(
        Integer,
        nullable=False,
        default=20,
    )

    delivery_max_minutes = Column(
        Integer,
        nullable=False,
        default=30,
    )

    location = Column(
        String(150),
        nullable=True,
    )

    offer_text = Column(
        String(150),
        nullable=True,
    )

    image_url = Column(
        String(500),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
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

    products = relationship(
        "Product",
        back_populates="restaurant",
        passive_deletes=True,
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    product_name = Column(
        String(100),
        nullable=False,
    )

    description = Column(
        String(255)
    )

    price = Column(
        Numeric(10, 2),
        nullable=False,
    )

    platform = Column(
        String(20),
        nullable=False,
    )

    image_url = Column(
        String(500),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    stock_quantity = Column(
        Integer,
        nullable=False,
        default=0,
    )

    reorder_level = Column(
        Integer,
        nullable=False,
        default=5,
    )

    last_restocked = Column(
        DateTime,
        nullable=True,
    )

    restaurant_id = Column(
        Integer,
        ForeignKey(
            "restaurants.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    menu_category = Column(
        String(100),
        nullable=True,
    )

    is_bestseller = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    restaurant = relationship(
        "Restaurant",
        back_populates="products",
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_cart_user_product",
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
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=1,
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