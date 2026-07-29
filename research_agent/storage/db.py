"""SQLite 引擎与建表（自包含存储）。"""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from ..config import settings

# 确保数据目录存在
_dir = os.path.dirname(settings.db_path)
if _dir:
    os.makedirs(_dir, exist_ok=True)

engine = create_engine(
    settings.sqlite_url,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # 导入 models 以注册表元数据
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
