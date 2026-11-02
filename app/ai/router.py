"""Authenticated page and API routes for the local AI guidance assistant."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.ai.service import AIServiceFailed, AIServiceUnavailable, answer_question
from app.ai.data_service import answer_data_question
from app.ai.inventory_service import answer_inventory_question
from sqlalchemy.exc import SQLAlchemyError
from app.auth.dependencies import get_current_user, require_authenticated_user
from app.core import templates
from app.database import get_db
from app.merchants.models import MerchantRestaurant
from app.users.models import User

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)


class AskResponse(BaseModel):
    answer: str


@router.get("/assistant", response_class=HTMLResponse)
def ai_assistant_page(
    request: Request,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    restaurant = None
    if current_user.role == "merchant":
        assignment = (
            db.query(MerchantRestaurant)
            .filter(MerchantRestaurant.user_id == current_user.id)
            .first()
        )
        if assignment is not None:
            restaurant = assignment.restaurant

    # The merchant template requires the assigned restaurant in its context.
    layout = "merchant/base.html" if restaurant is not None else "base.html"
    return templates.TemplateResponse(
        request=request,
        name="ai/assistant.html",
        context={
            "request": request,
            "current_user": current_user,
            "layout_template": layout,
            "restaurant": restaurant,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.post("/ask", response_model=AskResponse)
async def ai_ask(
    payload: AskRequest,
    response: Response,
    current_user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Unlike the HTML page, an API must return 401, not a redirect to login.
    if current_user is None:
        raise HTTPException(status_code=401, detail="Sign in to use the AI assistant.")

    question = payload.question.strip()
    if len(question) < 3:
        raise HTTPException(status_code=422, detail="Enter a longer question.")

    cleaned_history = [
        {"role": item.role, "content": item.content.strip()}
        for item in payload.history
        if item.content.strip()
    ]

    try:
        answer = answer_data_question(db=db, user=current_user, question=question)
        if answer is None:
            answer = answer_inventory_question(
                db=db, user=current_user, question=question
            )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503, detail="Unable to load restaurant report right now."
        ) from exc

    if answer is not None:
        response.headers["Cache-Control"] = "no-store"
        return AskResponse(answer=answer)

    try:
        answer = await answer_question(
            question=question,
            role=current_user.role,
            username=current_user.username,
            history=cleaned_history,
        )
    except AIServiceUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Local AI is unavailable. Make sure Ollama is running.",
        ) from exc
    except AIServiceFailed as exc:
        raise HTTPException(
            status_code=502,
            detail="The local model could not produce a response.",
        ) from exc

    response.headers["Cache-Control"] = "no-store"
    return AskResponse(answer=answer)
