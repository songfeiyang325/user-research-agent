"""MongoDB 文档模型（纯 Pydantic）。

用 `id`（别名 `_id`）作主键，值为 uuid 字符串。存取时用 by_alias 与 Mongo 的 _id 对齐。
保留属性访问（`survey.schema_data` 等），上层代码与 M1 一致。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _Doc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(default_factory=_uid, alias="_id")

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class Project(_Doc):
    name: str
    goal: str = ""
    stage: str = "design"  # intake/design/collect/analyze/report
    created_at: datetime = Field(default_factory=_now)


class Survey(_Doc):
    project_id: str
    title: str = ""
    schema_data: dict = Field(default_factory=dict)
    mode: str = "form"          # form | interview
    status: str = "draft"       # draft | published
    share_path: str = ""
    created_at: datetime = Field(default_factory=_now)
    published_at: Optional[datetime] = None


class Message(_Doc):
    project_id: str
    role: str                   # user | assistant | tool | system
    content: str = ""
    tool_calls: Optional[dict] = None
    created_at: datetime = Field(default_factory=_now)


class Response(_Doc):
    survey_id: str
    data: dict = Field(default_factory=dict)   # {field: 值}，与小桔答卷同构
    meta: dict = Field(default_factory=dict)
    channel: str = ""
    created_at: datetime = Field(default_factory=_now)
