"""分题统计 —— 复刻 xiaoju-survey 的聚合算法（纯函数，不依赖 LLM）。

参考：server/src/modules/survey/services/dataStatistic.service.ts + utils/index.ts
- 选择类：按选项计数（多选拆数组求和），零计数选项也保留
- 评分/NPS：分值桶计数 + 汇总（均值/中位数/样本方差；NPS 百分比）
- 文本类：收集原文，交给 textmining 做主题聚类
"""
from __future__ import annotations

from statistics import median as _median

CHOICE_TYPES = {"radio", "checkbox", "binary-choice", "vote"}
RATE_TYPES = {"radio-star", "radio-nps"}
TEXT_TYPES = {"text", "textarea"}

_EMPTY = (None, "", [])


def aggregate_choice(q: dict, responses: list[dict]) -> dict:
    options = q.get("options", [])
    text_of = {o["hash"]: o["text"] for o in options}
    counts: dict[str, int] = {o["hash"]: 0 for o in options}
    submission = 0
    for r in responses:
        v = r.get(q["field"])
        if v in _EMPTY:
            continue
        submission += 1
        for hv in v if isinstance(v, list) else [v]:
            counts[hv] = counts.get(hv, 0) + 1
    agg = [
        {
            "id": h,
            "text": text_of.get(h, h),
            "count": c,
            "percent": round(c * 100 / submission, 1) if submission else 0.0,
        }
        for h, c in counts.items()
    ]
    return {"aggregation": agg, "submissionCount": submission}


def aggregate_rate(q: dict, responses: list[dict]) -> dict:
    if q["type"] == "radio-star":
        lo, hi = 1, int(q.get("starMax", 5) or 5)
    else:  # radio-nps
        lo, hi = int(q.get("min", 0) or 0), int(q.get("max", 10) or 10)

    buckets = {v: 0 for v in range(lo, hi + 1)}
    vals: list[int] = []
    for r in responses:
        v = r.get(q["field"])
        if v in (None, ""):
            continue
        try:
            iv = int(v)
        except (TypeError, ValueError):
            continue
        vals.append(iv)
        buckets[iv] = buckets.get(iv, 0) + 1

    n = len(vals)
    summary: dict = {}
    if n:
        avg = sum(vals) / n
        summary["average"] = round(avg, 2)
        summary["median"] = _median(sorted(vals))
        summary["variance"] = (
            round(sum((x - avg) ** 2 for x in vals) / (n - 1), 2) if n > 1 else 0.0
        )
        if q["type"] == "radio-nps":
            promoters = sum(1 for x in vals if x >= 9)
            detractors = sum(1 for x in vals if x <= 6)
            summary["nps"] = round((promoters - detractors) * 100 / n, 2)

    agg = [{"id": str(v), "text": str(v), "count": buckets[v]} for v in range(lo, hi + 1)]
    return {"aggregation": agg, "submissionCount": n, "summary": summary}


def collect_text(q: dict, responses: list[dict]) -> dict:
    answers = [
        r[q["field"]].strip()
        for r in responses
        if isinstance(r.get(q["field"]), str) and r[q["field"]].strip()
    ]
    return {"answers": answers, "answered": len(answers)}


def aggregate_survey(schema: dict, responses: list[dict]) -> dict:
    """对整份问卷做分题统计。返回结构直接供前端渲染。"""
    out: dict = {"count": len(responses), "questions": []}
    for q in schema.get("dataConf", {}).get("dataList", []):
        t = q["type"]
        item: dict = {"field": q["field"], "title": q["title"], "type": t}
        if t in CHOICE_TYPES:
            item.update(aggregate_choice(q, responses))
        elif t in RATE_TYPES:
            item.update(aggregate_rate(q, responses))
        elif t in TEXT_TYPES:
            item.update(collect_text(q, responses))
            item["open_text"] = True
        else:
            item["skip"] = True
        out["questions"].append(item)
    return out
