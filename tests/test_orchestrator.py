"""Orchestrator 全流程编排测试（离线 mock）：设计→发布(访谈)→看结果，阶段自动推进。"""
from research_agent.agents import OrchestratorAgent
from research_agent.storage import repo


def _names(events):
    return [p["name"] for k, p in events if k == "tool_result"]


def _run(pid, sid, msg):
    o = OrchestratorAgent(repo.get_project(pid), repo.get_survey(sid))
    o.client.mock = True
    return list(o.run_stream([{"role": "user", "content": msg}]))


def test_orchestrator_mock_lifecycle():
    proj, survey = repo.create_project("编排测试", "")
    pid, sid = proj.id, survey.id

    # 1) 设计
    ev = _run(pid, sid, "帮我做一个满意度问卷")
    assert "save_survey_draft" in _names(ev)
    assert repo.get_project(pid).stage == "design"
    assert repo.get_survey(sid).schema_data["dataConf"]["dataList"]

    # 2) 发布为 AI 访谈
    ev = _run(pid, sid, "发布吧，用 AI 访谈")
    assert "publish_survey" in _names(ev)
    sv = repo.get_survey(sid)
    assert sv.status == "published" and sv.mode == "interview" and sv.share_path
    assert repo.get_project(pid).stage == "collect"

    # 3) 看结果（先造一条回收）
    repo.add_response(sid, {}, channel="test")
    ev = _run(pid, sid, "看看结果怎么样")
    assert "summarize_results" in _names(ev)
    assert repo.get_project(pid).stage == "analyze"
