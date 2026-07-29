"""MongoDB 连接（pymongo）。

- 惰性连接：首次 get_db() 时才连，import 不触发网络。
- set_db() 供测试注入 mongomock，无需真实 Mongo。
"""
from __future__ import annotations

from typing import Any

from ..config import settings

_client: Any = None
_db: Any = None


def _connect() -> None:
    global _client, _db
    from pymongo import MongoClient

    _client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
    _db = _client[settings.mongo_db]


def get_db() -> Any:
    if _db is None:
        _connect()
    return _db


def set_db(database: Any) -> None:
    """测试用：注入 mongomock 的 database。"""
    global _db
    _db = database


def init_db() -> None:
    """建索引（幂等；mongomock 下部分索引特性缺失，故 best-effort）。"""
    d = get_db()
    try:
        d.surveys.create_index("project_id")
        d.surveys.create_index("share_path")
        d.messages.create_index("project_id")
        d.responses.create_index("survey_id")
    except Exception:  # noqa: BLE001
        pass
