from sqlalchemy.orm import Session
from app.core.security import verify_password
from app.users.service import get_user_by_username

def authenticate_user(
    db:Session,
    username:str,
    password:str
):
    user=get_user_by_username(db,username)
    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password,user.password_hash):
        return None

    return user

