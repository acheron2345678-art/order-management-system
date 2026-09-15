from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem, Store
from ..schemas import MenuItemOut, StoreOut

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("", response_model=list[StoreOut])
def list_stores(
    q: str | None = Query(default=None, max_length=100),
    open_only: bool = True,
    db: Session = Depends(get_db),
):
    stmt = select(Store)
    if open_only:
        stmt = stmt.where(Store.is_open.is_(True))
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(Store.name.ilike(term), Store.description.ilike(term)))
    return db.scalars(stmt.order_by(Store.name)).all()


@router.get("/{store_id}/menu", response_model=list[MenuItemOut])
def store_menu(
    store_id: int,
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
    available_only: bool = True,
    db: Session = Depends(get_db),
):
    if not db.get(Store, store_id):
        raise HTTPException(status_code=404, detail="Store not found")
    stmt = select(MenuItem).where(MenuItem.store_id == store_id)
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    if category:
        stmt = stmt.where(MenuItem.category == category)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(MenuItem.name.ilike(term), MenuItem.description.ilike(term)))
    return db.scalars(stmt.order_by(MenuItem.category, MenuItem.name)).all()
