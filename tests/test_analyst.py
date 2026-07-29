"""Analyst 洞察报告测试（离线 mock，不依赖真实 key）。"""
from research_agent.agents import AnalystAgent
from research_agent.survey import build_survey


def test_analyst_report_mock():
    survey = build_survey(
        "t",
        [
            {"type": "radio", "title": "满意吗", "options": ["满意", "不满意"]},
            {"type": "radio-nps", "title": "推荐意愿", "min": 0, "max": 10},
            {"type": "textarea", "title": "建议"},
        ],
    )
    qs = survey.questions
    fr, fn, ft = qs[0].field, qs[1].field, qs[2].field
    opt = {o.text: o.hash for o in qs[0].options}
    responses = [
        {fr: opt["满意"], fn: 10, ft: "很好用"},
        {fr: opt["不满意"], fn: 4, ft: "太贵了"},
    ]

    agent = AnalystAgent()
    agent.client.mock = True

    rep = agent.build_report(survey.model_dump(), responses)
    assert rep["overview"]["count"] == 2
    assert len(rep["questions"]) == 3
    assert isinstance(rep["narrative"], str) and rep["narrative"]

    text_q = next(q for q in rep["questions"] if q.get("open_text"))
    assert text_q["themes"] and text_q["themes"][0]["count"] == 2
    assert "answers" not in text_q  # 原文不下发
