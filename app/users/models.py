from datetime import datetime

from sqlalchemy import Integer,Boolean,DateTime,String,Column
from app.database.base import Base

from sqlalchemy.orm import relationship

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,index=True)
    username=Column(String(100),unique=True,nullable=False)
    email=Column(String(255),unique=True,nullable=False)
    password_hash=Column(String(255),nullable=False)
    role=Column(String(20),nullable=False,default="client")
    is_active=Column(Boolean,nullable=False,default=True)
    created_at=Column(DateTime,nullable=False,default=datetime.now)
    profile = relationship(
    "ClientProfile",
    back_populates="user",
    uselist=False,
    cascade="all, delete-orphan",
)