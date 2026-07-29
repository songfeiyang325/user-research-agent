"""受访者侧 API：取已发布问卷 schema + 提交答卷（页面由前端 Vue 渲染）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage import repo

router = APIRouter(prefix="/api")


class SubmitIn(BaseModel):
    data: dict
    meta: dict = {}


@router.get("/r/{path}/schema")
def respond_schema(path: str) -> dict:
    sv = repo.get_survey_by_path(path)
    if not sv or sv.status != "published":
        raise HTTPException(404, "问卷不存在或未发布")
    return {"title": sv.title, "schema": sv.schema_data}


@router.post("/r/{path}")
def submit(path: str, body: SubmitIn) -> dict:
    sv = repo.get_survey_by_path(path)
    if not sv or sv.status != "published":
        raise HTTPException(404, "问卷不存在或未发布")
    repo.add_response(sv.id, body.data, body.meta, channel="web")
    return {"ok": True}
