"""Designer Agent —— 对话式问卷设计。

真实模式：GLM 通过 `save_survey_draft` 工具整体覆盖问卷草稿。
mock 模式（无 API Key）：用启发式把用户描述转成问卷，保证离线可跑通全流程。
"""
from __future__ import annotations

from collections.abc import Iterator

from ..llm.client import LLMClient
from ..llm.prompts import DESIGNER_SYSTEM_PROMPT, SAVE_SURVEY_TOOL
from ..storage import repo
from ..storage.models import Survey
from ..survey import QuestionType, build_survey, text_to_schema
from .base import ToolAgent


class DesignerAgent:
    def __init__(self, survey: Survey):
        self.survey = survey
        self.client = LLMClient()
        self.agent = ToolAgent(
            self.client,
            DESIGNER_SYSTEM_PROMPT,
            tools=[SAVE_SURVEY_TOOL],
            tool_impls={"save_survey_draft": self._save_survey_draft},
        )

    # ---- 工具实现 ----
    def _save_survey_draft(self, title: str, questions: list[dict]) -> dict:
        schema = build_survey(title, questions)
        repo.save_draft(self.survey, schema)
        return {
            "ok": True,
            "title": schema.title,
            "question_count": len(schema.questions),
            "survey": self.survey.schema_data,
        }

    # ---- 对外入口 ----
    def run_stream(self, history: list[dict]) -> Iterator[tuple[str, object]]:
        if self.client.mock:
            yield from self._mock_stream(history)
        else:
            yield from self.agent.run_stream(history)

    # ---- mock（离线启发式）----
    def _mock_stream(self, history: list[dict]) -> Iterator[tuple[str, object]]:
        user = ""
        for m in reversed(history):
            if m.get("role") == "user":
                user = m.get("content", "")
                break

        parsed = text_to_schema(user)
        if parsed:
            title = self.survey.title or "调研问卷"
            spec = [self._question_to_spec(q) for q in parsed]
            note = "已按你给的题目文本解析成问卷"
        else:
            title = self.survey.title or "用户满意度调研"
            spec = _default_spec(user)
            note = "已按满意度调研的通用模板生成初稿"

        intro = (
            f"（离线 mock 模式）{note}：《{title}》，共 {len(spec)} 道题。"
            "你可以继续说「把第2题改成多选」「加一道 NPS」之类来调整。\n"
        )
        for ch in intro:
            yield ("token", ch)

        result = self._save_survey_draft(title, spec)
        yield ("tool_result", {"name": "save_survey_draft", "result": result})

    @staticmethod
    def _question_to_spec(q) -> dict:
        spec: dict = {"type": q.type, "title": q.title, "required": q.isRequired}
        if q.options:
            spec["options"] = [o.text for o in q.options]
        if q.type == QuestionType.RADIO_NPS.value:
            spec.update(min=q.min, max=q.max, minMsg=q.minMsg, maxMsg=q.maxMsg)
        return spec


def _default_spec(topic: str) -> list[dict]:
    topic = (topic or "").strip()[:20] or "本次服务"
    return [
        {
            "type": "radio",
            "title": f"您使用「{topic}」的频率？",
            "options": ["每天", "每周几次", "偶尔", "第一次使用"],
        },
        {"type": "radio-star", "title": "您对整体体验的评分", "starMax": 5},
        {
            "type": "radio-nps",
            "title": "您有多大意愿把我们推荐给同事/朋友？",
            "min": 0,
            "max": 10,
            "minMsg": "绝不推荐",
            "maxMsg": "强烈推荐",
        },
        {
            "type": "checkbox",
            "title": "您最看重以下哪些方面？",
            "options": ["响应速度", "服务态度", "价格", "功能完整度", "稳定性"],
        },
        {"type": "textarea", "title": "还有什么建议或想吐槽的？"},
    ]
