from sqlalchemy.orm import Session
from app.orders.models import OrderHistory

def record_order_created(
    db:Session,
    platform:str,
    order_id:int,
    changed_by:int |None
):
    history=OrderHistory(
        platform=platform,
        order_id=order_id,
        action="create",
        field_name=None,
        old_value=None,
        new_value=None,
        changed_by=changed_by
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history

def record_order_deleted(
        db:Session,
        platform:str,
        order_id:int,
        changed_by:int|None
):
    history=OrderHistory(
        platform=platform,
        order_id=order_id,
        action="delete",
        field_name=None,
        old_value=None,
        new_value=None,
        changed_by=changed_by
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history

def get_order_history(
        db:Session,
        platform:str,
        order_id:int
):
    return(
        db.query(OrderHistory).filter(OrderHistory.platform==platform,OrderHistory.order_id==order_id).order_by(OrderHistory.created_at.desc(),OrderHistory.id.desc()).all()
    )

def record_order_change(
        db:Session,
        platform:str,
        order_id:int,
        field_name:str,
        old_value,
        new_value,
        changed_by:int |None
):
    old_text=(
        None
        if old_value is None
        else str(old_value)
    )

    new_text=(
        None
        if new_value is None
        else str(new_value)
    )

    if old_text==new_text:
        return None

    history=OrderHistory(
        platform=platform,
        order_id=order_id,
        action="update",
        field_name=field_name,
        old_value=old_text,
        new_value=new_text,
        changed_by=changed_by
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history

