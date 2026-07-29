"""Analyst Agent —— 把统计结果 + 开放题主题编排成一份洞察报告。

真实模式：GLM 基于统计数字写叙事洞察；mock 模式：用数字拼一份可读的模板报告。
"""
from __future__ import annotations

import json

from ..analysis.stats import aggregate_survey
from ..analysis.textmining import cluster_open_text
from ..llm.client import LLMClient

_SYS = "你是资深用户研究分析师，善于从问卷数据中提炼可执行的洞察。"


class AnalystAgent:
    def __init__(self):
        self.client = LLMClient()

    def build_report(self, schema: dict, responses: list[dict]) -> dict:
        stats = aggregate_survey(schema, responses)
        for q in stats["questions"]:
            if q.get("open_text") and q.get("answers"):
                q["themes"] = cluster_open_text(q["title"], q["answers"], self.client)
            q.pop("answers", None)  # 原文不下发到概览（主题里已带代表性 examples）
        return {
            "overview": {"count": stats["count"]},
            "questions": stats["questions"],
            "narrative": self._narrative(stats),
        }

    def _narrative(self, stats: dict) -> str:
        if self.client.mock:
            return _mock_narrative(stats)
        prompt = (
            "基于以下问卷统计结果，写一份简洁的中文洞察报告（markdown 格式），包含：整体概览、"
            "关键发现（3–5 条，务必引用具体数字/占比）、值得注意的差异或风险、下一步建议。"
            "不要编造数据。\n\n" + json.dumps(_compact(stats), ensure_ascii=False)
        )
        try:
            return self.client.complete(
                [{"role": "system", "content": _SYS}, {"role": "user", "content": prompt}],
                temperature=0.5,
            )
        except Exception as e:  # noqa: BLE001
            return f"（AI 叙事生成失败：{e}）\n\n" + _mock_narrative(stats)


def _compact(stats: dict) -> dict:
    qs = []
    for q in stats["questions"]:
        c: dict = {"title": q["title"], "type": q["type"]}
        if q.get("summary"):
            c["summary"] = q["summary"]
        elif q.get("aggregation"):
            c["options"] = [
                {"text": a["text"], "count": a["count"], "percent": a.get("percent")}
                for a in q["aggregation"]
            ]
        if q.get("themes"):
            c["themes"] = [{"theme": t["theme"], "count": t["count"]} for t in q["themes"]]
        qs.append(c)
    return {"responseCount": stats["count"], "questions": qs}


def _mock_narrative(stats: dict) -> str:
    lines = [
        "## 洞察概览（离线 mock）",
        f"共收集 **{stats['count']}** 份有效回答。",
        "",
        "### 关键发现",
    ]
    for q in stats["questions"]:
        if q.get("summary"):
            s = q["summary"]
            extra = f"，NPS {s['nps']}" if "nps" in s else ""
            lines.append(f"- **{q['title']}**：均值 {s.get('average')}{extra}")
        elif q.get("aggregation") and q.get("type") not in ("radio-star", "radio-nps"):
            top = max(q["aggregation"], key=lambda a: a["count"], default=None)
            if top and top["count"]:
                lines.append(
                    f"- **{q['title']}**：最集中于「{top['text']}」"
                    f"（{top['count']} 次，{top.get('percent')}%）"
                )
        elif q.get("themes"):
            th = "、".join(t["theme"] for t in q["themes"][:3])
            lines.append(f"- **{q['title']}**（开放题）：主要主题 {th}")
    lines += ["", "### 建议", "- 配置 GLM key 后可获得更深入的 AI 叙事分析与交叉洞察。"]
    return "\n".join(lines)
