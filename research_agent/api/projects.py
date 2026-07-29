"""项目相关 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage import repo
from ..storage.models import Survey

router = APIRouter(prefix="/api")


class ProjectIn(BaseModel):
    name: str = "未命名调研"
    goal: str = ""


def survey_brief(sv: Survey) -> dict:
    return {
        "id": sv.id,
        "title": sv.title,
        "status": sv.status,
        "share_path": sv.share_path,
        "schema": sv.schema_data,
    }


@router.post("/projects")
def create_project(body: ProjectIn) -> dict:
    project, survey = repo.create_project(body.name, body.goal)
    return {
        "project_id": project.id,
        "survey_id": survey.id,
        "survey": survey_brief(survey),
    }


@router.get("/projects/{pid}")
def get_project(pid: str) -> dict:
    project = repo.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    survey = repo.get_survey_by_project(pid)
    messages = [
        {"role": m.role, "content": m.content}
        for m in repo.get_messages(pid)
        if m.role in ("user", "assistant")
    ]
    return {
        "project_id": project.id,
        "name": project.name,
        "goal": project.goal,
        "stage": project.stage,
        "messages": messages,
        "survey": survey_brief(survey) if survey else None,
    }
