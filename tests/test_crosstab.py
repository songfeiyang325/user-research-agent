"""交叉分析测试：列联表计数 + 关联强度。"""
from research_agent.analysis.crosstab import crosstab
from research_agent.survey import build_survey


def test_crosstab_matrix_and_stats():
    survey = build_survey(
        "t",
        [
            {"type": "radio", "title": "性别", "options": ["男", "女"]},
            {"type": "radio", "title": "是否推荐", "options": ["会", "不会"]},
        ],
    )
    qa, qb = survey.questions[0], survey.questions[1]
    f_a, f_b = qa.field, qb.field
    a = {o.text: o.hash for o in qa.options}
    b = {o.text: o.hash for o in qb.options}
    responses = [
        {f_a: a["男"], f_b: b["会"]},
        {f_a: a["男"], f_b: b["会"]},
        {f_a: a["男"], f_b: b["不会"]},
        {f_a: a["女"], f_b: b["不会"]},
        {f_a: a["女"], f_b: b["不会"]},
    ]
    res = crosstab(qa.model_dump(), qb.model_dump(), responses)

    assert res["rowLabels"] == ["男", "女"]
    assert res["colLabels"] == ["会", "不会"]
    assert res["matrix"] == [[2, 1], [0, 2]]   # 男:会2/不会1；女:会0/不会2
    assert "cramersV" in res and 0.0 <= res["cramersV"] <= 1.0
