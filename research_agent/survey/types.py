"""题型枚举与标签 —— 对齐 xiaoju-survey 的 9 种题型协议。

参考：web/src/common/typeEnum.ts、server/src/enums/question.ts
"""
from __future__ import annotations

from enum import Enum


class QuestionType(str, Enum):
    TEXT = "text"                  # 单行输入框
    TEXTAREA = "textarea"          # 多行输入框
    RADIO = "radio"                # 单选
    CHECKBOX = "checkbox"          # 多选
    BINARY_CHOICE = "binary-choice"  # 判断题
    RADIO_STAR = "radio-star"      # 评分
    RADIO_NPS = "radio-nps"        # NPS 评分
    VOTE = "vote"                  # 投票
    CASCADER = "cascader"          # 多级联动


# 中文题型标签（文本↔schema、AI 提示词用），对齐 typeTagLabels
TYPE_LABELS: dict[QuestionType, str] = {
    QuestionType.TEXT: "单行输入框",
    QuestionType.TEXTAREA: "多行输入框",
    QuestionType.RADIO: "单选",
    QuestionType.CHECKBOX: "多选",
    QuestionType.BINARY_CHOICE: "判断题",
    QuestionType.RADIO_STAR: "评分",
    QuestionType.RADIO_NPS: "NPS评分",
    QuestionType.VOTE: "投票",
    QuestionType.CASCADER: "多级联动",
}
LABEL_TO_TYPE: dict[str, QuestionType] = {v: k for k, v in TYPE_LABELS.items()}

# 分组
INPUT_TYPES = {QuestionType.TEXT, QuestionType.TEXTAREA}
CHOICE_TYPES = {
    QuestionType.RADIO,
    QuestionType.CHECKBOX,
    QuestionType.BINARY_CHOICE,
    QuestionType.VOTE,
}
RATE_TYPES = {QuestionType.RADIO_STAR, QuestionType.RADIO_NPS}


def label_of(qtype: QuestionType | str) -> str:
    return TYPE_LABELS[QuestionType(qtype)]
