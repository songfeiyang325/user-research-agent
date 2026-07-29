"""分题统计测试：选项计数、评分/NPS 汇总、开放题收集。"""
from research_agent.analysis import aggregate_survey
from research_agent.survey import build_survey


def test_aggregate_choice_nps_and_text():
    survey = build_survey(
        "t",
        [
            {"type": "radio", "title": "满意吗", "options": ["满意", "一般", "不满意"]},
            {"type": "radio-nps", "title": "推荐意愿", "min": 0, "max": 10},
            {"type": "textarea", "title": "建议"},
        ],
    )
    qs = survey.questions
    f_radio, f_nps, f_txt = qs[0].field, qs[1].field, qs[2].field
    opt = {o.text: o.hash for o in qs[0].options}
    responses = [
        {f_radio: opt["满意"], f_nps: 10, f_txt: "很好"},
        {f_radio: opt["满意"], f_nps: 9},
        {f_radio: opt["一般"], f_nps: 6, f_txt: "一般般"},
        {f_radio: opt["不满意"], f_nps: 3},
    ]
    agg = aggregate_survey(survey.model_dump(), responses)

    assert agg["count"] == 4
    q0 = agg["questions"][0]
    assert {a["text"]: a["count"] for a in q0["aggregation"]} == {
        "满意": 2, "一般": 1, "不满意": 1
    }
    assert q0["submissionCount"] == 4

    q1 = agg["questions"][1]
    assert q1["summary"]["average"] == 7.0            # (10+9+6+3)/4
    assert q1["summary"]["variance"] == 10.0          # 样本方差 30/3
    assert q1["summary"]["nps"] == 0.0                # 推荐2 - 贬损2 = 0

    q2 = agg["questions"][2]
    assert q2["open_text"] is True and q2["answered"] == 2


def test_checkbox_explodes_multiselect():
    survey = build_survey(
        "t", [{"type": "checkbox", "title": "看重", "options": ["价格", "服务", "速度"]}]
    )
    q = survey.questions[0]
    f = q.field
    h = {o.text: o.hash for o in q.options}
    responses = [
        {f: [h["价格"], h["服务"]]},
        {f: [h["价格"]]},
        {f: [h["速度"], h["服务"]]},
    ]
    agg = aggregate_survey(survey.model_dump(), responses)
    counts = {a["text"]: a["count"] for a in agg["questions"][0]["aggregation"]}
    assert counts == {"价格": 2, "服务": 2, "速度": 1}
    assert agg["questions"][0]["submissionCount"] == 3
