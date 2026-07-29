"""受访者侧：答题页 + 提交。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session

from ..storage import repo
from ..storage.db import get_session
from ..web import templates

router = APIRouter()


class SubmitIn(BaseModel):
    data: dict
    meta: dict = {}


@router.get("/r/{path}", response_class=HTMLResponse)
def respond_page(path: str, request: Request, session: Session = Depends(get_session)):
    sv = repo.get_survey_by_path(session, path)
    if not sv or sv.status != "published":
        return HTMLResponse("<h3 style='font-family:sans-serif;text-align:center;margin-top:80px'>问卷不存在或未发布</h3>", status_code=404)
    return templates.TemplateResponse(
        request,
        "respond.html",
        {
            "title": sv.title or "问卷",
            "path": path,
            "survey_json": json.dumps(sv.schema_data, ensure_ascii=False),
        },
    )


@router.post("/api/r/{path}")
def submit(path: str, body: SubmitIn, session: Session = Depends(get_session)) -> dict:
    sv = repo.get_survey_by_path(session, path)
    if not sv or sv.status != "published":
        raise HTTPException(404, "问卷不存在或未发布")
    repo.add_response(session, sv.id, body.data, body.meta, channel="web")
    return {"ok": True}
