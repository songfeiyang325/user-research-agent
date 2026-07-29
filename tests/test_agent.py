"""Agent 层测试：通用工具循环（假 client）+ Designer 离线 mock 端到端（mongomock）。"""
from research_agent.agents import DesignerAgent, ToolAgent
from research_agent.storage import repo
from research_agent.survey import build_survey


class FakeClient:
    """模拟 GLM：第一轮请求工具调用，第二轮给出最终回答。"""

    def __init__(self):
        self.calls = 0
        self.mock = False

    def stream(self, messages, tools=None, temperature=0.6):
        self.calls += 1
        if self.calls == 1:
            yield ("tool_calls", [{"id": "c1", "name": "echo", "arguments": '{"x": 5}'}])
            yield ("done", "tool_calls")
        else:
            yield ("token", "结果是 ")
            yield ("token", "10")
            yield ("done", "stop")


def test_tool_agent_loop_executes_tool_and_finishes():
    def echo(x):
        return {"doubled": x * 2}

    agent = ToolAgent(FakeClient(), "sys", tools=[], tool_impls={"echo": echo})
    events = list(agent.run_stream([{"role": "user", "content": "double 5"}]))

    tool_results = [p for k, p in events if k == "tool_result"]
    assert tool_results and tool_results[0]["result"]["doubled"] == 10
    tokens = "".join(p for k, p in events if k == "token")
    assert tokens == "结果是 10"


def test_designer_mock_parses_text_into_survey():
    _proj, survey = repo.create_project("满意度调研", "了解满意度")
    da = DesignerAgent(survey)
    da.client.mock = True  # 强制离线，测试不依赖真实 key

    events = list(
        da.run_stream(
            [{"role": "user", "content": "1.喜欢我们的服务吗？[单选]\n喜欢\n一般\n不喜欢"}]
        )
    )

    assert any(k == "tool_result" for k, _ in events)
    saved = repo.get_survey(survey.id)
    qs = saved.schema_data["dataConf"]["dataList"]
    assert len(qs) == 1
    assert qs[0]["type"] == "radio"
    assert [o["text"] for o in qs[0]["options"]] == ["喜欢", "一般", "不喜欢"]


def test_designer_mock_default_template():
    _proj, survey = repo.create_project("新功能调研", "")
    da = DesignerAgent(survey)
    da.client.mock = True

    list(da.run_stream([{"role": "user", "content": "帮我调研下大家对新功能的看法"}]))

    saved = repo.get_survey(survey.id)
    qs = saved.schema_data["dataConf"]["dataList"]
    assert len(qs) == 5  # 通用模板 5 题
    assert any(q["type"] == "radio-nps" for q in qs)


def test_repo_publish_and_responses():
    _proj, survey = repo.create_project("投放测试", "")
    repo.save_draft(survey, build_survey("t", [{"type": "text", "title": "Q1"}]))
    repo.publish_survey(survey)
    assert survey.share_path
    assert repo.get_survey_by_path(survey.share_path).id == survey.id

    field0 = survey.schema_data["dataConf"]["dataList"][0]["field"]
    repo.add_response(survey.id, {field0: "hi"})
    assert repo.count_responses(survey.id) == 1
