"""校验与构造：field/hash 生成、按题型建空题、把简化描述装配成完整问卷。

field/hash 规则对齐 xiaoju-survey：field="data"+0..999，hash=6 位数字。
"""
from __future__ import annotations

import random
from typing import Any, Iterable

from .schema import DataConf, Option, Question, SurveySchema
from .types import (
    CHOICE_TYPES,
    INPUT_TYPES,
    QuestionType,
)

# build_question 里会读取的类型专属字段
_EXTRA_KEYS = {
    "min", "max", "minMsg", "maxMsg", "starMin", "starMax", "starStyle",
    "placeholder", "valid", "minNum", "maxNum", "innerType",
}


def gen_field(used: set[str]) -> str:
    for _ in range(10000):
        f = f"data{random.randint(0, 999)}"
        if f not in used:
            used.add(f)
            return f
    raise RuntimeError("field 空间耗尽")


def gen_hash(used: set[str]) -> str:
    for _ in range(10000):
        h = str(random.randint(100000, 999999))
        if h not in used:
            used.add(h)
            return h
    raise RuntimeError("hash 空间耗尽")


def make_options(texts: Iterable[str], used_hashes: set[str]) -> list[Option]:
    return [Option(text=str(t), hash=gen_hash(used_hashes)) for t in texts]


def _int(val: Any, default: int) -> int:
    """把外部值转 int；None/空串视为缺省，但保留合法的 0。"""
    if val is None or val == "":
        return default
    return int(val)


def build_question(
    qtype: QuestionType | str,
    title: str,
    *,
    options: list[str] | None = None,
    required: bool = True,
    used_fields: set[str] | None = None,
    used_hashes: set[str] | None = None,
    **extra: Any,
) -> Question:
    """按题型造一道完整题目（补全 field / 选项 hash / 类型专属默认值）。"""
    used_fields = used_fields if used_fields is not None else set()
    used_hashes = used_hashes if used_hashes is not None else set()
    qtype = QuestionType(qtype)

    q = Question(field=gen_field(used_fields), title=title, type=qtype, isRequired=required)

    if qtype in CHOICE_TYPES:
        if options:
            opt_texts = list(options)
        elif qtype is QuestionType.BINARY_CHOICE:
            opt_texts = ["对", "错"]
        else:
            opt_texts = ["选项1", "选项2"]
        q.options = make_options(opt_texts, used_hashes)
        if qtype is QuestionType.VOTE:
            q.innerType = extra.get("innerType", "radio")
        q.minNum = _int(extra.get("minNum"), 0)
        q.maxNum = _int(extra.get("maxNum"), 0)
    elif qtype is QuestionType.RADIO_STAR:
        q.starMin = _int(extra.get("starMin"), 1)
        q.starMax = _int(extra.get("starMax"), 5)
        q.starStyle = extra.get("starStyle", "star")
    elif qtype is QuestionType.RADIO_NPS:
        q.min = _int(extra.get("min"), 1)
        q.max = _int(extra.get("max"), 10)
        q.minMsg = extra.get("minMsg") or q.minMsg
        q.maxMsg = extra.get("maxMsg") or q.maxMsg
    elif qtype in INPUT_TYPES:
        q.placeholder = extra.get("placeholder", "")
        q.valid = extra.get("valid", "")

    return q


def build_survey(title: str, questions_spec: list[dict[str, Any]]) -> SurveySchema:
    """把「简化题目描述」列表装配成完整 SurveySchema。

    questions_spec 每项：{type, title, required?, options?[], 及类型专属键}
    —— 正是 Designer Agent 工具产出的形状。
    """
    used_fields: set[str] = set()
    used_hashes: set[str] = set()
    questions: list[Question] = []
    for spec in questions_spec:
        extra = {k: v for k, v in spec.items() if k in _EXTRA_KEYS}
        q = build_question(
            spec["type"],
            spec.get("title", ""),
            options=spec.get("options"),
            required=bool(spec.get("required", True)),
            used_fields=used_fields,
            used_hashes=used_hashes,
            **extra,
        )
        questions.append(q)

    survey = SurveySchema()
    survey.title = title
    survey.dataConf = DataConf(dataList=questions)
    return survey


def ensure_ids(survey: SurveySchema) -> SurveySchema:
    """补全缺失的 field / option.hash（幂等）。"""
    used_fields = {q.field for q in survey.questions if q.field}
    used_hashes = {
        o.hash for q in survey.questions for o in q.options if o.hash
    }
    for q in survey.questions:
        if not q.field:
            q.field = gen_field(used_fields)
        for o in q.options:
            if not o.hash:
                o.hash = gen_hash(used_hashes)
    return survey
