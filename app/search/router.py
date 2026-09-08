from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_authenticated_user,
)

from app.database import get_db

from app.search.schemas import (
    SearchResult,
)

from app.search.service import (
    search_all_orders,
)

from app.users.models import User


router = APIRouter(
    tags=["search"]
)


@router.get(
    "/search",
    response_model=list[SearchResult],
)
def search_results(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    client_id = None

    if current_user.role == "client":
        client_id = current_user.id

    return search_all_orders(
        db,
        q,
        client_id=client_id,
    )