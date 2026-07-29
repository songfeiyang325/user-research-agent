"""对话式设计 API（SSE 流式）。"""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents import DesignerAgent
from ..storage import repo

router = APIRouter(prefix="/api")


class ChatIn(BaseModel):
    message: str


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/projects/{pid}/chat")
def chat(pid: str, body: ChatIn) -> StreamingResponse:
    project = repo.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    survey = repo.get_survey_by_project(pid)
    if survey is None:
        raise HTTPException(404, "问卷不存在")

    repo.add_message(pid, "user", body.message)
    history = [
        {"role": m.role, "content": m.content}
        for m in repo.get_messages(pid)
        if m.role in ("user", "assistant")
    ]
    designer = DesignerAgent(survey)

    def gen() -> Iterator[str]:
        acc: list[str] = []
        try:
            for kind, payload in designer.run_stream(history):
                if kind == "token":
                    acc.append(payload)  # type: ignore[arg-type]
                    yield _sse({"type": "token", "text": payload})
                elif kind == "tool_result":
                    p = payload  # type: ignore[assignment]
                    result = p.get("result", {})
                    if p.get("name") == "save_survey_draft" and result.get("ok"):
                        yield _sse({"type": "survey", "survey": result["survey"]})
            repo.add_message(pid, "assistant", "".join(acc))
            yield _sse({"type": "done"})
        except Exception as e:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
