"""显示逻辑：构造 + 求值。"""
from research_agent.survey import build_survey, is_visible


def test_show_logic_build_and_eval():
    survey = build_survey(
        "t",
        [
            {"type": "radio", "title": "满意吗", "options": ["满意", "不满意"]},
            {"type": "textarea", "title": "哪里不满意"},
        ],
        logic_spec=[{"show": 2, "when": 1, "op": "in", "options": ["不满意"]}],
    )
    q1, q2 = survey.questions
    sl = [r.model_dump() for r in survey.logicConf.showLogicConf]
    assert len(sl) == 1
    opt = {o.text: o.hash for o in q1.options}

    # 无作答 → 条件题隐藏
    assert is_visible(q2.field, sl, {}) is False
    # 选了"满意" → 隐藏
    assert is_visible(q2.field, sl, {q1.field: opt["满意"]}) is False
    # 选了"不满意" → 显示
    assert is_visible(q2.field, sl, {q1.field: opt["不满意"]}) is True
    # 无规则的题始终显示
    assert is_visible(q1.field, sl, {}) is True


def test_nin_operator():
    survey = build_survey(
        "t",
        [
            {"type": "checkbox", "title": "用过哪些", "options": ["A", "B", "C"]},
            {"type": "textarea", "title": "为什么没用C"},
        ],
        logic_spec=[{"show": 2, "when": 1, "op": "nin", "options": ["C"]}],
    )
    q1, q2 = survey.questions
    sl = [r.model_dump() for r in survey.logicConf.showLogicConf]
    opt = {o.text: o.hash for o in q1.options}
    # 未选 C（选了 A,B）→ nin 命中 → 显示
    assert is_visible(q2.field, sl, {q1.field: [opt["A"], opt["B"]]}) is True
    # 选了 C → 不显示
    assert is_visible(q2.field, sl, {q1.field: [opt["C"]]}) is False
