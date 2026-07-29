"""AI 主持访谈：会话存储 + Interviewer/抽取（离线 mock）。"""
from research_agent.agents import InterviewerAgent, extract_answers
from research_agent.storage import repo
from research_agent.storage.models import Survey
from research_agent.survey import build_survey


def test_interview_session_lifecycle():
    _proj, survey = repo.create_project("访谈测试", "")
    repo.set_survey_mode(survey, "interview")
    assert survey.mode == "interview"

    s = repo.create_interview_session(survey.id)
    repo.append_turn(s, "assistant", "你平时怎么用我们平台？")
    repo.append_turn(s, "user", "每天上下班用")
    got = repo.get_interview_session(s.id)
    assert got.status == "active"
    assert [t["role"] for t in got.transcript] == ["assistant", "user"]

    repo.finish_interview(got, {"data1": "每天"})
    done = repo.get_interview_session(s.id)
    assert done.status == "done" and done.extracted == {"data1": "每天"}
    assert done.finished_at is not None


def test_interviewer_mock_covers_topics_then_ends():
    schema = build_survey(
        "出行调研",
        [
            {"type": "radio", "title": "多久用一次", "options": ["每天", "偶尔"]},
            {"type": "textarea", "title": "有什么建议"},
        ],
    )
    sv = Survey(project_id="p", title=schema.title, schema_data=schema.model_dump(), mode="interview")
    agent = InterviewerAgent(sv)
    agent.client.mock = True

    transcript: list[dict] = []
    opening = "".join(tok for _, tok in agent.stream_reply(transcript))
    transcript.append({"role": "assistant", "content": opening})
    assert "多久用一次" in opening

    ended, guard = False, 0
    while not ended and guard < 10:
        guard += 1
        transcript.append({"role": "user", "content": "随便答一下"})
        msg = "".join(tok for _, tok in agent.stream_reply(transcript))
        transcript.append({"role": "assistant", "content": msg})
        ended = "[END]" in msg

    assert ended
    all_asst = " ".join(t["content"] for t in transcript if t["role"] == "assistant")
    assert "有什么建议" in all_asst
    # mock 模式抽取返回空（不阻断流程）
    assert extract_answers(sv.schema_data, transcript, agent.client) == {}
