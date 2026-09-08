from sqlalchemy import Column,DateTime,ForeignKey,Integer,String,func

from app.database.base import Base

class RefreshToken(Base):
    __tablename__="refresh_tokens"

    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    token_id=Column(String(64),nullable=False,unique=True,index=True)
    last_activity=Column(DateTime,nullable=False,server_default=func.now())
    expires_at=Column(DateTime,nullable=False)
    revoked_at=Column(DateTime,nullable=True)
    created_at=Column(DateTime,nullable=False,server_default=func.now())