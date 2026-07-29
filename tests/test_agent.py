"""Agent 层测试：通用工具循环（假 client）+ Designer 离线 mock 端到端。"""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from research_agent.agents import DesignerAgent, ToolAgent
from research_agent.storage import models, repo  # noqa: F401  (注册表)


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


def _memory_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_designer_mock_parses_text_into_survey():
    with _memory_session() as s:
        _proj, survey = repo.create_project(s, "满意度调研", "了解满意度")
        da = DesignerAgent(s, survey)
        da.client.mock = True  # 强制离线，测试不依赖真实 key

        events = list(
            da.run_stream(
                [{"role": "user", "content": "1.喜欢我们的服务吗？[单选]\n喜欢\n一般\n不喜欢"}]
            )
        )

        assert any(k == "tool_result" for k, _ in events)
        saved = repo.get_survey(s, survey.id)
        qs = saved.schema_data["dataConf"]["dataList"]
        assert len(qs) == 1
        assert qs[0]["type"] == "radio"
        assert [o["text"] for o in qs[0]["options"]] == ["喜欢", "一般", "不喜欢"]


def test_designer_mock_default_template():
    with _memory_session() as s:
        _proj, survey = repo.create_project(s, "新功能调研", "")
        da = DesignerAgent(s, survey)
        da.client.mock = True

        list(da.run_stream([{"role": "user", "content": "帮我调研下大家对新功能的看法"}]))

        saved = repo.get_survey(s, survey.id)
        qs = saved.schema_data["dataConf"]["dataList"]
        assert len(qs) == 5  # 通用模板 5 题
        assert any(q["type"] == "radio-nps" for q in qs)
