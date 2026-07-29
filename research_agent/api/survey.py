"""问卷 API：获取 / 发布 / 投放模式 / 查看回收。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..storage import repo
from ..storage.models import Survey

router = APIRouter(prefix="/api")


class ModeIn(BaseModel):
    mode: str  # form | interview


def _share_url(sv: Survey) -> str:
    return f"{settings.app_base_url}/r/{sv.share_path}" if sv.share_path else ""


@router.get("/surveys/{sid}")
def get_survey(sid: str) -> dict:
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    return {
        "id": sv.id,
        "title": sv.title,
        "status": sv.status,
        "mode": sv.mode,
        "share_path": sv.share_path,
        "share_url": _share_url(sv),
        "schema": sv.schema_data,
    }


@router.post("/surveys/{sid}/mode")
def set_mode(sid: str, body: ModeIn) -> dict:
    if body.mode not in ("form", "interview"):
        raise HTTPException(400, "mode 只能是 form 或 interview")
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    repo.set_survey_mode(sv, body.mode)
    return {"ok": True, "mode": sv.mode}


@router.post("/surveys/{sid}/publish")
def publish(sid: str) -> dict:
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    data_list = sv.schema_data.get("dataConf", {}).get("dataList", [])
    if not data_list:
        raise HTTPException(400, "问卷还没有题目，无法发布")
    repo.publish_survey(sv)
    return {"ok": True, "share_path": sv.share_path, "share_url": _share_url(sv)}


@router.get("/surveys/{sid}/responses")
def responses(sid: str) -> dict:
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    rows = [
        {"id": r.id, "data": r.data, "created_at": r.created_at.isoformat()}
        for r in repo.list_responses(sid)
    ]
    return {"count": len(rows), "rows": rows}
