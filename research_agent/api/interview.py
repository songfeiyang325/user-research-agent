"""AI 主持访谈 API（受访者侧，SSE 流式）。

- start：新建会话，流式返回开场问题（首事件带 session_id）
- reply：受访者回答 → 流式返回主持人下一句；遇 [END] 则抽取结构化 → 建 Response → 结束
- get：拉取会话逐字稿（刷新续接用）
"""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents import InterviewerAgent, extract_answers
from ..agents.interviewer import END_MARK
from ..storage import repo
from ..storage.models import InterviewSession, Survey

router = APIRouter(prefix="/api")


class ReplyIn(BaseModel):
    message: str


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _stream(survey: Survey, session: InterviewSession, is_start: bool, user_msg: str | None = None) -> StreamingResponse:
    agent = InterviewerAgent(survey)
    if not is_start and user_msg is not None:
        repo.append_turn(session, "user", user_msg)

    def gen() -> Iterator[str]:
        if is_start:
            yield _sse({"type": "session", "session_id": session.id})
        acc: list[str] = []
        try:
            for _kind, tok in agent.stream_reply(session.transcript):
                acc.append(tok)
                yield _sse({"type": "token", "text": tok})
            full = "".join(acc)
            ended = END_MARK in full
            clean = full.replace(END_MARK, "").strip()
            repo.append_turn(session, "assistant", clean)
            if ended:
                data = extract_answers(survey.schema_data, session.transcript, agent.client)
                repo.add_response(survey.id, data, {"interview_session": session.id}, channel="interview")
                repo.finish_interview(session, data)
                yield _sse({"type": "end"})
            else:
                yield _sse({"type": "done"})
        except Exception as e:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/r/{path}/interview/start")
def start(path: str) -> StreamingResponse:
    sv = repo.get_survey_by_path(path)
    if not sv or sv.status != "published":
        raise HTTPException(404, "问卷不存在或未发布")
    session = repo.create_interview_session(sv.id)
    return _stream(sv, session, is_start=True)


@router.post("/interview/{sid}/reply")
def reply(sid: str, body: ReplyIn) -> StreamingResponse:
    session = repo.get_interview_session(sid)
    if not session:
        raise HTTPException(404, "会话不存在")
    if session.status == "done":
        raise HTTPException(400, "访谈已结束")
    sv = repo.get_survey(session.survey_id)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    return _stream(sv, session, is_start=False, user_msg=body.message)


@router.get("/interview/{sid}")
def get_session(sid: str) -> dict:
    session = repo.get_interview_session(sid)
    if not session:
        raise HTTPException(404, "会话不存在")
    sv = repo.get_survey(session.survey_id)
    return {
        "session_id": session.id,
        "status": session.status,
        "title": sv.title if sv else "",
        "transcript": session.transcript,
    }
