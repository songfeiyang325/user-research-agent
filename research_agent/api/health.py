"""健康检查：确认当前用的是不是真模型（不暴露任何密钥）。"""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "mock": settings.use_mock,        # True=离线启发式；False=真模型
        "model": settings.glm_model,
        "base_url": settings.glm_base_url,
    }
