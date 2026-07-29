"""文本 ↔ 问卷 schema 转换 —— 移植 xiaoju-survey 的 textToSchema 语法。

文本格式：空行分块，每块首行 `标题[题型标签]`，后续行按题型解释
（选择类每行一个选项；NPS 用 `低分文案-高分文案`）。
"""
from __future__ import annotations

import re

from .schema import Question
from .types import CHOICE_TYPES, LABEL_TO_TYPE, TYPE_LABELS, QuestionType
from .validate import build_question

_BLOCK_SEP = re.compile(r"\n\s*\n")
_HEADER = re.compile(r"^(.*?)\[(.+?)\]\s*$")
_LEADING_NUM = re.compile(r"^\s*\d+\s*[.、)．、）]?\s*")

# 给 LLM 的格式说明（Designer 也可用文本粘贴导入）
SURVEY_TEXT_FORMAT = """每道题一段，段间空一行。每题首行必须以题型标签 [类型] 结尾，可用类型：
[单行输入框] [多行输入框] [单选] [多选] [判断题] [评分] [NPS评分] [投票] [多级联动]
- 单选/多选/投票/判断题：题目下方每行一个选项
- NPS评分：题目下方一行 `低分文案-高分文案`
- 单行输入框/多行输入框/评分/多级联动：无需选项
示例：
1.您的年龄段？[单选]
18岁以下
18-30岁
30岁以上

2.您对本次服务的整体满意度[NPS评分]
非常不满意-非常满意"""


def text_to_schema(text: str) -> list[Question]:
    """把文本解析成题目列表（无法识别的块跳过）。"""
    questions: list[Question] = []
    used_fields: set[str] = set()
    used_hashes: set[str] = set()

    for block in _BLOCK_SEP.split((text or "").strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        m = _HEADER.match(lines[0])
        if not m:
            continue
        title = _LEADING_NUM.sub("", m.group(1).strip())
        label = m.group(2).strip()
        qtype = LABEL_TO_TYPE.get(label)
        if qtype is None:
            continue

        body = lines[1:]
        options: list[str] | None = None
        extra: dict = {}
        if qtype in CHOICE_TYPES:
            options = body or None
        elif qtype is QuestionType.RADIO_NPS and body:
            if "-" in body[0]:
                left, right = body[0].split("-", 1)
                extra = {"minMsg": left.strip(), "maxMsg": right.strip()}

        questions.append(
            build_question(
                qtype, title,
                options=options,
                used_fields=used_fields,
                used_hashes=used_hashes,
                **extra,
            )
        )
    return questions


def schema_to_text(questions: list[Question]) -> str:
    """把题目列表还原成文本（round-trip / 展示用）。"""
    parts: list[str] = []
    for i, q in enumerate(questions, 1):
        qtype = QuestionType(q.type)
        head = f"{i}.{q.title}[{TYPE_LABELS[qtype]}]"
        lines = [head]
        if qtype in CHOICE_TYPES:
            lines += [o.text for o in q.options]
        elif qtype is QuestionType.RADIO_NPS:
            lines.append(f"{q.minMsg}-{q.maxMsg}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
