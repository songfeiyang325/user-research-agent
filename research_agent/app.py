"""FastAPI 应用装配。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import design, pages, projects, respond, survey
from .storage.db import init_db
from .web import STATIC_DIR


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="用户调研 Agent", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for module in (pages, projects, design, survey, respond):
        app.include_router(module.router)
    return app


app = create_app()
