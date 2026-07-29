"""Orchestrator Agent —— 控制台主控，串起调研全流程。

单 Agent + 全量工具 + 阶段感知：根据"当前状态"决定推进哪一步，并在回复末尾主动建议下一步。
工具：save_survey_draft（设计/改题）、set_mode（投放方式）、publish_survey（发布）、summarize_results（看结果）。
"""
from __future__ import annotations

from collections.abc import Iterator

from ..analysis.stats import aggregate_survey
from ..config import settings
from ..llm.client import LLMClient
from ..llm.prompts import SAVE_SURVEY_TOOL
from ..storage import repo
from ..survey import build_survey, text_to_schema
from .base import ToolAgent

ORCHESTRATOR_SYSTEM = """你是滴滴内部「用户调研 Agent」的主控助手，陪研究员走完整个调研流程：
明确目标 → 设计问卷 → 选择投放方式并发布 → 采集 → 分析出洞察。

可用工具：
- save_survey_draft(title, questions)：创建/整体更新问卷草稿（改题也要传完整题目列表）
- set_mode(mode)：投放方式，form=静态表单，interview=AI 主持访谈
- publish_survey()：发布问卷并拿到分享链接（发布前必须已有题目）
- summarize_results()：获取已回收答卷的统计摘要

工作方式：
1. 参考下方「当前状态」判断该做什么，并在每次回复末尾**主动建议下一步**（刚设计完→建议发布；已发布且有回收→建议看分析）。
2. 用户要设计/改题→save_survey_draft；要发布→可先按意愿 set_mode 再 publish_survey；要看结果→summarize_results 并简要解读，然后提示可点右上"查看分析"看完整报告。
3. 一次只推进一步，中文、简洁、口语化，不要编造回收数据。"""

SET_MODE_TOOL = {
    "type": "function",
    "function": {
        "name": "set_mode",
        "description": "设置投放方式：form=静态表单，interview=AI 主持访谈",
        "parameters": {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["form", "interview"]}},
            "required": ["mode"],
        },
    },
}
PUBLISH_TOOL = {
    "type": "function",
    "function": {
        "name": "publish_survey",
        "description": "发布当前问卷并返回分享链接（发布前需已有题目）",
        "parameters": {"type": "object", "properties": {}},
    },
}
SUMMARIZE_TOOL = {
    "type": "function",
    "function": {
        "name": "summarize_results",
        "description": "获取已回收答卷的统计摘要（分布、评分均值、NPS、回收数）",
        "parameters": {"type": "object", "properties": {}},
    },
}


class OrchestratorAgent:
    def __init__(self, project, survey):
        self.project = project
        self.survey = survey
        self.client = LLMClient()
        self.agent = ToolAgent(
            self.client,
            self._system(),
            tools=[SAVE_SURVEY_TOOL, SET_MODE_TOOL, PUBLISH_TOOL, SUMMARIZE_TOOL],
            tool_impls={
                "save_survey_draft": self._save,
                "set_mode": self._set_mode,
                "publish_survey": self._publish,
                "summarize_results": self._summarize,
            },
        )

    # ---- 状态感知 ----
    def _questions(self) -> list:
        return self.survey.schema_data.get("dataConf", {}).get("dataList", [])

    def _state(self) -> str:
        rc = repo.count_responses(self.survey.id)
        parts = [
            f"- 阶段：{self.project.stage}",
            f"- 标题：{self.survey.title or '（未命名）'}",
            f"- 题目数：{len(self._questions())}",
            f"- 投放方式：{'AI 访谈' if self.survey.mode == 'interview' else '表单'}",
            f"- 状态：{'已发布' if self.survey.status == 'published' else '草稿'}",
            f"- 已回收：{rc} 份",
        ]
        if self.survey.share_path:
            parts.append(f"- 分享链接：{settings.app_base_url}/r/{self.survey.share_path}")
        return "\n".join(parts)

    def _system(self) -> str:
        return f"{ORCHESTRATOR_SYSTEM}\n\n当前状态：\n{self._state()}"

    # ---- 工具实现 ----
    def _save(self, title: str, questions: list[dict]) -> dict:
        schema = build_survey(title, questions)
        repo.save_draft(self.survey, schema)
        repo.set_project_stage(self.project, "design")
        return {"ok": True, "question_count": len(schema.questions), "survey": self.survey.schema_data}

    def _set_mode(self, mode: str) -> dict:
        if mode not in ("form", "interview"):
            return {"ok": False, "error": "mode 只能是 form 或 interview"}
        repo.set_survey_mode(self.survey, mode)
        return {"ok": True, "mode": mode}

    def _publish(self) -> dict:
        if not self._questions():
            return {"ok": False, "error": "还没有题目，无法发布"}
        repo.publish_survey(self.survey)
        repo.set_project_stage(self.project, "collect")
        return {
            "ok": True,
            "mode": self.survey.mode,
            "share_url": f"{settings.app_base_url}/r/{self.survey.share_path}",
        }

    def _summarize(self) -> dict:
        responses = [r.data for r in repo.list_responses(self.survey.id)]
        if not responses:
            return {"ok": True, "count": 0}
        agg = aggregate_survey(self.survey.schema_data, responses)
        repo.set_project_stage(self.project, "analyze")
        return {
            "ok": True,
            "count": agg["count"],
            "brief": _brief(agg),
            "report_url": f"{settings.app_base_url}/report/{self.survey.id}",
        }

    # ---- 入口 ----
    def run_stream(self, history: list[dict]) -> Iterator[tuple[str, object]]:
        if self.client.mock:
            yield from self._mock(history)
        else:
            yield from self.agent.run_stream(history)

    # ---- mock（离线启发式路由）----
    def _mock(self, history: list[dict]) -> Iterator[tuple[str, object]]:
        user = ""
        for m in reversed(history):
            if m.get("role") == "user":
                user = m.get("content", "")
                break

        if any(k in user for k in ("发布", "投放", "上线", "publish")):
            if "访谈" in user:
                self._set_mode("interview")
                yield ("tool_result", {"name": "set_mode", "result": {"ok": True, "mode": "interview"}})
            r = self._publish()
            if r["ok"]:
                for ch in f"（mock）已发布，分享链接：{r['share_url']}。发给受访者收集一些回答后，就可以来看分析啦。":
                    yield ("token", ch)
                yield ("tool_result", {"name": "publish_survey", "result": r})
            else:
                for ch in "（mock）还没有题目，先描述你的调研，我来生成问卷。":
                    yield ("token", ch)
        elif any(k in user for k in ("分析", "结果", "报告", "洞察")):
            r = self._summarize()
            msg = (
                f"（mock）已回收 {r.get('count', 0)} 份，点右上「查看分析」看完整报告。"
                if r.get("count")
                else "（mock）还没有回收数据，先把问卷发出去收集一些回答。"
            )
            for ch in msg:
                yield ("token", ch)
            yield ("tool_result", {"name": "summarize_results", "result": r})
        else:
            parsed = text_to_schema(user)
            if parsed:
                title = self.survey.title or "调研问卷"
                spec = [_q2spec(q) for q in parsed]
            else:
                title = self.survey.title or "用户满意度调研"
                spec = _DEFAULT_SPEC
            r = self._save(title, spec)
            for ch in f"（mock）已生成《{title}》，共 {r['question_count']} 道题。满意的话说「发布」，想改直接说。":
                yield ("token", ch)
            yield ("tool_result", {"name": "save_survey_draft", "result": r})


def _q2spec(q) -> dict:
    spec = {"type": q.type, "title": q.title, "required": q.isRequired}
    if q.options:
        spec["options"] = [o.text for o in q.options]
    if q.type == "radio-nps":
        spec.update(min=q.min, max=q.max, minMsg=q.minMsg, maxMsg=q.maxMsg)
    return spec


_DEFAULT_SPEC = [
    {"type": "radio-star", "title": "整体体验评分", "starMax": 5},
    {"type": "radio-nps", "title": "推荐意愿", "min": 0, "max": 10},
    {"type": "textarea", "title": "还有什么建议？"},
]


def _brief(agg: dict) -> list[dict]:
    out = []
    for q in agg["questions"]:
        if q.get("summary"):
            out.append({"title": q["title"], "summary": q["summary"]})
        elif q.get("aggregation") and q.get("type") not in ("radio-star", "radio-nps"):
            top = max(q["aggregation"], key=lambda a: a["count"], default=None)
            if top:
                out.append({"title": q["title"], "top": top["text"], "count": top["count"]})
    return out
