from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from app.core.security import hash_password
from app.users.models import User
from app.users.schemas import UserCreate
from app.utils.email_rules import (
    require_gmail_address,
)

ALLOWED_ROLES={
    "admin",
    "client"
}

def get_user_by_id(db:Session,user_id:int):
    return db.query(User).filter(User.id==user_id).first()


def get_user_by_username(db:Session,username:str):
    return db.query(User).filter(User.username==username).first()

def get_user_by_email(db:Session,email:str):
    return db.query(User).filter(User.email==email).first()

def get_users(db:Session):
    return db.query(User).all()

def get_clients(db:Session):
    return db.query(User).filter(User.role=="client",User.is_active==True).order_by(User.username.asc()).all()

def create_user(
    db: Session,
    user_data,
):

    username = (
        user_data.username
        .strip()
    )

    if not username:
        raise ValueError(
            "Username is required."
        )


    email = require_gmail_address(
        user_data.email
    )


    role = (
        user_data.role
        .strip()
        .lower()
    )


    if role not in {
        "admin",
        "client",
    }:
        raise ValueError(
            "Invalid user role."
        )


    existing_username = (
        db.query(User)
        .filter(
            User.username
            == username
        )
        .first()
    )


    if existing_username:

        raise ValueError(
            "Username already exists."
        )


    existing_email = (
        db.query(User)
        .filter(
            User.email.ilike(
                email
            )
        )
        .first()
    )


    if existing_email:

        raise ValueError(
            "Email address already exists."
        )


    new_user = User(
        username=username,
        email=email,
        password_hash = PasswordHash.recommended(),

        role=role,
        is_active=True,
    )


    try:

        db.add(
            new_user
        )

        db.commit()

        db.refresh(
            new_user
        )

        return new_user


    except Exception:

        db.rollback()

        raise


def update_user(
        db:Session,
        user:User,
        username:str,
        email:str,
        role:str    
):
    username=username.strip()
    email=email.strip().lower()
    role=role.strip().lower()

    if not username:
        raise ValueError(
            "Username is required"
        )

    if not email:
        raise ValueError(
            "Email is required"
        )

    if role not in ALLOWED_ROLES:
        raise ValueError(
            "Invalid  user role"
        )

    username_owner=(db.query(User).filter(User.username==username,User.id!=user.id).first())

    if username_owner:
        raise ValueError(
            "Username already exists"
        )

    email_owner=db.query(User).filter(User.email==email,User.id!=user.id).first()

    if email_owner:
        raise ValueError(
            "The email already exixts"
        )

    user.username=username
    user.email=email
    user.role=role
    db.commit()
    db.refresh(user)

    return user


def set_user_active_status(
        db:Session,
        user:User,
        is_active:bool
):
    user.is_active=is_active
    db.commit()
    db.refresh(user)
    return user
