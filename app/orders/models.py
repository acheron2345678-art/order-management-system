from sqlalchemy import Column, Integer, String, Date,DateTime, Float,ForeignKey,Text,Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SwiggyOrders(Base):
    __tablename__ = "swiggy_orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    order_number = Column(String(50), unique=True, nullable=False)
    product_id=Column(Integer,ForeignKey("products.id"),nullable=True)
    product_name=Column(String(100),nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    order_date = Column(Date, nullable=False)
    client_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    client=relationship("User",foreign_keys=[client_id])
    delivery_name = Column(
        String(100),
        nullable=True,
    )


    delivery_phone = Column(
        String(20),
        nullable=True,
    )


    delivery_address_line1 = Column(
        String(255),
        nullable=True,
    )


    delivery_address_line2 = Column(
        String(255),
        nullable=True,
    )


    delivery_city = Column(
        String(100),
        nullable=True,
    )


    delivery_state = Column(
        String(100),
        nullable=True,
    )


    delivery_postal_code = Column(
        String(20),
        nullable=True,
    )


    delivery_country = Column(
        String(100),
        nullable=True,
    )


class InsightsOrders(Base):
    __tablename__ = "insights_orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    order_number = Column(String(50), unique=True, nullable=False)
    product_id=Column(Integer,ForeignKey("products.id"),nullable=True)
    product_name=Column(String(100),nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    order_date = Column(Date, nullable=False)
    client_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    client=relationship("User",foreign_keys=[client_id])
    project_brief = Column(Text,nullable=True)
    business_goal = Column(Text,nullable=True)
    preferred_completion_date = Column(Date,nullable=True)
    additional_notes = Column(Text,nullable=True,)


class OrderHistory(Base):
    __tablename__="order_history"

    id=Column(Integer,primary_key=True,index=True)
    platform=Column(String(20),nullable=False)
    order_id=Column(Integer,nullable=False)
    action=Column(String(50),nullable=False)
    field_name=Column(String(50),nullable=True)
    old_value=Column(Text,nullable=True)
    new_value=Column(Text,nullable=True)
    changed_by=Column(Integer,ForeignKey("users.id",ondelete="SET NULL"),nullable=True)
    created_at=Column(DateTime,nullable=False,server_default=func.now())
    user=relationship("User",foreign_keys=[changed_by])


class OrderItem(Base):
    __tablename__="order_items"

    id=Column(Integer,primary_key=True,index=True)
    platform=Column(String(20),nullable=False,index=True)
    order_id=Column(Integer, nullable=False,index=True)
    product_id=Column(Integer,ForeignKey("products.id",ondelete="RESTRICT"),nullable=False,index=True)
    product_name=Column(String(255),nullable=False)
    unit_price=Column(Numeric(10,2),nullable=False)
    quantity=Column(Integer,nullable=False,default=1)
    line_total=Column(Numeric(10,2),nullable=False) 
    created_at=Column(DateTime,nullable=False,server_default=func.now())
    product=relationship("Product",foreign_keys=[product_id])