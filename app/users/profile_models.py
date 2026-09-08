from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)

from sqlalchemy.orm import (
    relationship,
)

from app.database import Base


class ClientProfile(Base):
    __tablename__ = (
        "client_profiles"
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
        unique=True,
        index=True,
    )


    full_name = Column(
        String(100),
        nullable=True,
    )


    company_name = Column(
        String(100),
        nullable=True,
    )


    phone = Column(
        String(20),
        nullable=True,
    )


    address_line1 = Column(
        String(255),
        nullable=True,
    )


    address_line2 = Column(
        String(255),
        nullable=True,
    )


    city = Column(
        String(100),
        nullable=True,
    )


    state = Column(
        String(100),
        nullable=True,
    )


    postal_code = Column(
        String(20),
        nullable=True,
    )


    country = Column(
        String(100),
        nullable=False,
        default="India",
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
        "User",
        back_populates="profile",
    )