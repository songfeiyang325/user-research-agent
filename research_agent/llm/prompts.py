"""系统提示词。当前只有 Designer；Analyst/Interviewer 在后续里程碑加入。"""
from __future__ import annotations

from ..survey import TYPE_LABELS, QuestionType

_TYPE_LINES = "\n".join(
    f"  - {label}（{qt.value}）" for qt, label in TYPE_LABELS.items()
)

DESIGNER_SYSTEM_PROMPT = f"""你是滴滴内部的用户调研问卷设计专家。通过多轮对话，帮研究员设计并迭代问卷。

可用题型：
{_TYPE_LINES}

工作方式：
1. 每当需要创建或修改问卷，都调用工具 `save_survey_draft`，传入**完整**的问卷（标题 + 全部题目）。它会整体覆盖上一版，所以修改时也要把所有题目一起传，而不是只传变化的那道。
2. 若研究员的调研目标含糊（缺对象/目的/侧重点），先用一两句话追问澄清，再给初稿；目标明确时直接给初稿。
3. 题目要精炼、口语化、无引导性，一般不超过 15 题；根据内容选最合适的题型（满意度用评分、推荐意愿用 NPS、多因素用多选等）。
4. 每次调用工具后，用一两句话说明你做了什么/为什么这样设计，方便研究员继续调整。
5. 全程用中文，语气专业友好。"""

# 题目对象的 JSON Schema（供工具参数复用）
_QUESTION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": [qt.value for qt in QuestionType],
            "description": "题型 key",
        },
        "title": {"type": "string", "description": "题干"},
        "required": {"type": "boolean", "description": "是否必填，默认 true"},
        "options": {
            "type": "array",
            "items": {"type": "string"},
            "description": "选项文本（单选/多选/投票/判断题需要）",
        },
        "min": {"type": "integer", "description": "NPS 最小分（默认 1，常用 0）"},
        "max": {"type": "integer", "description": "NPS 最大分（默认 10）"},
        "minMsg": {"type": "string", "description": "NPS 低分文案"},
        "maxMsg": {"type": "string", "description": "NPS 高分文案"},
        "starMax": {"type": "integer", "description": "评分满分（默认 5）"},
    },
    "required": ["type", "title"],
}

SAVE_SURVEY_TOOL = {
    "type": "function",
    "function": {
        "name": "save_survey_draft",
        "description": "创建或整体更新当前问卷草稿。每次必须传入完整的标题与全部题目，会覆盖上一版。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "问卷标题"},
                "questions": {
                    "type": "array",
                    "items": _QUESTION_ITEM_SCHEMA,
                    "description": "完整题目列表（按展示顺序）",
                },
                "logic": {
                    "type": "array",
                    "description": "可选的显示逻辑：仅当某题满足条件时才显示另一题",
                    "items": {
                        "type": "object",
                        "properties": {
                            "show": {"type": "integer", "description": "被条件显示的题目序号(从1开始)"},
                            "when": {"type": "integer", "description": "作为条件的题目序号(从1开始)"},
                            "op": {"type": "string", "enum": ["in", "nin", "eq", "neq"],
                                   "description": "in=选了任一 / nin=有未选 / eq=选了全部 / neq=都没选"},
                            "options": {"type": "array", "items": {"type": "string"},
                                        "description": "条件涉及的选项文本"},
                        },
                        "required": ["show", "when", "op", "options"],
                    },
                },
            },
            "required": ["title", "questions"],
        },
    },
}
