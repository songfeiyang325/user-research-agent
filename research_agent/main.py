"""uvicorn 入口：`uvicorn research_agent.main:app` 或 `python -m research_agent.main`。"""
from __future__ import annotations

from .app import app  # noqa: F401  (供 uvicorn research_agent.main:app 使用)


def main() -> None:
    import uvicorn

    from .config import settings

    uvicorn.run("research_agent.app:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
