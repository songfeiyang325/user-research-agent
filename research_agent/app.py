"""FastAPI 应用装配（纯 JSON API；前端由独立 Vue 工程 + nginx 提供）。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import design, health, projects, respond, survey
from .storage.db import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="用户调研 Agent API", version="0.2.0")
    # 本地开发时前端在 5173、后端在 8000 跨源；生产经 nginx 同源。放开 CORS 便于开发。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (projects, design, survey, respond, health):
        app.include_router(module.router)
    return app


app = create_app()
