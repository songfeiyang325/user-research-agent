"""SQLModel 数据表：Project / Survey / Message / Response（自包含 SQLite）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    """一个调研项目（全流程容器）。"""

    id: str = Field(default_factory=_uid, primary_key=True)
    name: str
    goal: str = ""
    # intake / design / collect / analyze / report
    stage: str = "design"
    created_at: datetime = Field(default_factory=_now)


class Survey(SQLModel, table=True):
    """问卷（含完整 schema）。一个项目当前对应一份问卷。"""

    id: str = Field(default_factory=_uid, primary_key=True)
    project_id: str = Field(index=True)
    title: str = ""
    schema_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    mode: str = "form"        # form | interview
    status: str = "draft"     # draft | published
    share_path: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=_now)
    published_at: Optional[datetime] = None


class Message(SQLModel, table=True):
    """设计期对话历史（研究员 ↔ Designer Agent）。"""

    id: str = Field(default_factory=_uid, primary_key=True)
    project_id: str = Field(index=True)
    role: str                 # user | assistant | tool | system
    content: str = ""
    tool_calls: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class Response(SQLModel, table=True):
    """一份提交的答卷，data 与小桔答卷同构：{field: 值}。"""

    id: str = Field(default_factory=_uid, primary_key=True)
    survey_id: str = Field(index=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    meta: dict = Field(default_factory=dict, sa_column=Column(JSON))
    channel: str = ""
    created_at: datetime = Field(default_factory=_now)
