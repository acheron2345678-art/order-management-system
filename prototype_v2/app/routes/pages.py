from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def storefront(request: Request):
    return templates.TemplateResponse(request=request, name="store.html")


@router.get("/track/{order_id}", response_class=HTMLResponse)
def track(request: Request, order_id: int):
    return templates.TemplateResponse(request=request, name="track.html", context={"order_id": order_id})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")
