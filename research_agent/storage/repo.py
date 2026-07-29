"""数据访问（CRUD）—— pymongo 实现。函数签名与 M1 基本一致（去掉 session）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..survey import SurveySchema
from .db import get_db
from .models import InterviewSession, Message, Project, Response, Survey


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------- Project ----------------
def create_project(name: str, goal: str = "") -> tuple[Project, Survey]:
    project = Project(name=name, goal=goal)
    get_db().projects.insert_one(project.to_mongo())

    survey = Survey(project_id=project.id, title=name, schema_data=SurveySchema().model_dump())
    get_db().surveys.insert_one(survey.to_mongo())
    return project, survey


def get_project(project_id: str) -> Project | None:
    doc = get_db().projects.find_one({"_id": project_id})
    return Project.model_validate(doc) if doc else None


def list_projects() -> list[Project]:
    cur = get_db().projects.find().sort("created_at", -1)
    return [Project.model_validate(d) for d in cur]


# ---------------- Message ----------------
def add_message(project_id: str, role: str, content: str = "", tool_calls: dict | None = None) -> Message:
    msg = Message(project_id=project_id, role=role, content=content, tool_calls=tool_calls)
    get_db().messages.insert_one(msg.to_mongo())
    return msg


def get_messages(project_id: str) -> list[Message]:
    cur = get_db().messages.find({"project_id": project_id}).sort("created_at", 1)
    return [Message.model_validate(d) for d in cur]


# ---------------- Survey ----------------
def get_survey(survey_id: str) -> Survey | None:
    doc = get_db().surveys.find_one({"_id": survey_id})
    return Survey.model_validate(doc) if doc else None


def get_survey_by_project(project_id: str) -> Survey | None:
    doc = get_db().surveys.find_one({"project_id": project_id})
    return Survey.model_validate(doc) if doc else None


def get_survey_by_path(share_path: str) -> Survey | None:
    if not share_path:
        return None
    doc = get_db().surveys.find_one({"share_path": share_path})
    return Survey.model_validate(doc) if doc else None


def save_draft(survey: Survey, schema: SurveySchema) -> Survey:
    survey.schema_data = schema.model_dump()
    survey.title = schema.title or survey.title
    get_db().surveys.update_one(
        {"_id": survey.id},
        {"$set": {"schema_data": survey.schema_data, "title": survey.title}},
    )
    return survey


def publish_survey(survey: Survey) -> Survey:
    if not survey.share_path:
        survey.share_path = _unique_share_path()
    survey.status = "published"
    survey.published_at = _now()
    get_db().surveys.update_one(
        {"_id": survey.id},
        {"$set": {
            "share_path": survey.share_path,
            "status": survey.status,
            "published_at": survey.published_at,
        }},
    )
    return survey


def _unique_share_path() -> str:
    for _ in range(50):
        token = uuid.uuid4().hex[:8]
        if get_survey_by_path(token) is None:
            return token
    raise RuntimeError("无法生成唯一分享路径")


# ---------------- Response ----------------
def add_response(survey_id: str, data: dict, meta: dict | None = None, channel: str = "") -> Response:
    resp = Response(survey_id=survey_id, data=data, meta=meta or {}, channel=channel)
    get_db().responses.insert_one(resp.to_mongo())
    return resp


def list_responses(survey_id: str) -> list[Response]:
    cur = get_db().responses.find({"survey_id": survey_id}).sort("created_at", 1)
    return [Response.model_validate(d) for d in cur]


def count_responses(survey_id: str) -> int:
    return get_db().responses.count_documents({"survey_id": survey_id})


# ---------------- 投放模式 ----------------
def set_survey_mode(survey: Survey, mode: str) -> Survey:
    survey.mode = mode
    get_db().surveys.update_one({"_id": survey.id}, {"$set": {"mode": mode}})
    return survey


def set_project_stage(project: Project, stage: str) -> Project:
    project.stage = stage
    get_db().projects.update_one({"_id": project.id}, {"$set": {"stage": stage}})
    return project


# ---------------- 访谈会话 ----------------
def create_interview_session(survey_id: str) -> InterviewSession:
    s = InterviewSession(survey_id=survey_id)
    get_db().interview_sessions.insert_one(s.to_mongo())
    return s


def get_interview_session(session_id: str) -> InterviewSession | None:
    doc = get_db().interview_sessions.find_one({"_id": session_id})
    return InterviewSession.model_validate(doc) if doc else None


def append_turn(session: InterviewSession, role: str, content: str) -> InterviewSession:
    session.transcript.append({"role": role, "content": content})
    get_db().interview_sessions.update_one(
        {"_id": session.id}, {"$set": {"transcript": session.transcript}}
    )
    return session


def finish_interview(session: InterviewSession, extracted: dict) -> InterviewSession:
    session.status = "done"
    session.extracted = extracted
    session.finished_at = _now()
    get_db().interview_sessions.update_one(
        {"_id": session.id},
        {"$set": {"status": "done", "extracted": extracted, "finished_at": session.finished_at}},
    )
    return session
