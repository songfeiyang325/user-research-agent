"""survey 领域层测试：文本↔schema 往返、建题、id 唯一性。"""
from research_agent.survey import (
    QuestionType,
    build_question,
    build_survey,
    schema_to_text,
    text_to_schema,
)

SAMPLE = """1.您的年龄段？[单选]
18岁以下
18-30岁
30岁以上

2.您平时使用哪些出行方式？[多选]
打车
地铁
公交

3.您对本次服务的整体满意度[NPS评分]
非常不满意-非常满意

4.还有什么建议？[多行输入框]

5.请给司机打分[评分]"""


def test_text_to_schema_types_and_options():
    qs = text_to_schema(SAMPLE)
    assert [q.type for q in qs] == [
        "radio", "checkbox", "radio-nps", "textarea", "radio-star",
    ]
    assert qs[0].title == "您的年龄段？"
    assert [o.text for o in qs[0].options] == ["18岁以下", "18-30岁", "30岁以上"]
    assert len(qs[1].options) == 3
    # NPS 低/高分文案
    assert qs[2].minMsg == "非常不满意"
    assert qs[2].maxMsg == "非常满意"
    # 输入/评分类无选项
    assert qs[3].options == []
    assert qs[4].starMax == 5


def test_roundtrip_preserves_structure():
    qs1 = text_to_schema(SAMPLE)
    text2 = schema_to_text(qs1)
    qs2 = text_to_schema(text2)
    assert [q.type for q in qs1] == [q.type for q in qs2]
    assert [q.title for q in qs1] == [q.title for q in qs2]
    assert [[o.text for o in q.options] for q in qs1] == [
        [o.text for o in q.options] for q in qs2
    ]


def test_build_survey_unique_ids():
    spec = [
        {"type": "radio", "title": "Q1", "options": ["A", "B"]},
        {"type": "checkbox", "title": "Q2", "options": ["C", "D", "E"]},
        {"type": "text", "title": "Q3"},
    ]
    survey = build_survey("测试问卷", spec)
    assert survey.title == "测试问卷"
    fields = [q.field for q in survey.questions]
    assert len(fields) == len(set(fields)) == 3
    assert all(f.startswith("data") for f in fields)
    hashes = [o.hash for q in survey.questions for o in q.options]
    assert len(hashes) == len(set(hashes)) == 5
    assert all(len(h) == 6 and h.isdigit() for h in hashes)


def test_build_question_defaults():
    b = build_question(QuestionType.BINARY_CHOICE, "对错题")
    assert [o.text for o in b.options] == ["对", "错"]
    nps = build_question("radio-nps", "满意度", min=0, max=10, minMsg="差", maxMsg="好")
    assert nps.min == 0 and nps.max == 10 and nps.minMsg == "差"
