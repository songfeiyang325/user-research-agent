"""数据访问（CRUD）。所有函数接收一个 Session。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..survey import SurveySchema
from .models import Message, Project, Response, Survey


# ---------------- Project ----------------
def create_project(session: Session, name: str, goal: str = "") -> tuple[Project, Survey]:
    """创建项目，并为其建一份空白草稿问卷。"""
    project = Project(name=name, goal=goal)
    session.add(project)
    session.commit()
    session.refresh(project)

    survey = Survey(project_id=project.id, title=name, schema_data=SurveySchema().model_dump())
    session.add(survey)
    session.commit()
    session.refresh(survey)
    return project, survey


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def list_projects(session: Session) -> list[Project]:
    return list(session.exec(select(Project).order_by(Project.created_at.desc())))


# ---------------- Message ----------------
def add_message(
    session: Session,
    project_id: str,
    role: str,
    content: str = "",
    tool_calls: dict | None = None,
) -> Message:
    msg = Message(project_id=project_id, role=role, content=content, tool_calls=tool_calls)
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


def get_messages(session: Session, project_id: str) -> list[Message]:
    return list(
        session.exec(
            select(Message)
            .where(Message.project_id == project_id)
            .order_by(Message.created_at)
        )
    )


# ---------------- Survey ----------------
def get_survey(session: Session, survey_id: str) -> Survey | None:
    return session.get(Survey, survey_id)


def get_survey_by_project(session: Session, project_id: str) -> Survey | None:
    return session.exec(
        select(Survey).where(Survey.project_id == project_id).order_by(Survey.created_at)
    ).first()


def get_survey_by_path(session: Session, share_path: str) -> Survey | None:
    if not share_path:
        return None
    return session.exec(select(Survey).where(Survey.share_path == share_path)).first()


def save_draft(session: Session, survey: Survey, schema: SurveySchema) -> Survey:
    """保存问卷草稿（整份 schema 覆盖，title 同步 banner 主标题）。"""
    survey.schema_data = schema.model_dump()
    survey.title = schema.title or survey.title
    session.add(survey)
    session.commit()
    session.refresh(survey)
    return survey


def publish_survey(session: Session, survey: Survey) -> Survey:
    if not survey.share_path:
        survey.share_path = _unique_share_path(session)
    survey.status = "published"
    survey.published_at = datetime.now(timezone.utc)
    session.add(survey)
    session.commit()
    session.refresh(survey)
    return survey


def _unique_share_path(session: Session) -> str:
    for _ in range(50):
        token = uuid.uuid4().hex[:8]
        if not get_survey_by_path(session, token):
            return token
    raise RuntimeError("无法生成唯一分享路径")


# ---------------- Response ----------------
def add_response(
    session: Session,
    survey_id: str,
    data: dict,
    meta: dict | None = None,
    channel: str = "",
) -> Response:
    resp = Response(survey_id=survey_id, data=data, meta=meta or {}, channel=channel)
    session.add(resp)
    session.commit()
    session.refresh(resp)
    return resp


def list_responses(session: Session, survey_id: str) -> list[Response]:
    return list(
        session.exec(
            select(Response)
            .where(Response.survey_id == survey_id)
            .order_by(Response.created_at)
        )
    )


def count_responses(session: Session, survey_id: str) -> int:
    return len(list_responses(session, survey_id))
