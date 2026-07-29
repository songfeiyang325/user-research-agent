"""页面路由：控制台。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..web import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/console", response_class=HTMLResponse)
def console(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "console.html")
