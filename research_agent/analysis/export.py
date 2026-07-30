"""导出：把答卷明细 + 分题统计写成 Excel（openpyxl）。"""
from __future__ import annotations

import io

from openpyxl import Workbook

from .stats import aggregate_survey


def _opt_map(q: dict) -> dict:
    return {o["hash"]: o["text"] for o in q.get("options", [])}


def _display(q: dict, value) -> str:
    """把存储值还原成可读文本（选项 hash→文案；多选拼接；其余原样）。"""
    if value in (None, ""):
        return ""
    t = q["type"]
    if t in ("radio", "binary-choice"):
        return _opt_map(q).get(str(value), str(value))
    if t in ("checkbox", "vote"):
        m = _opt_map(q)
        vals = value if isinstance(value, list) else [value]
        return "、".join(m.get(str(x), str(x)) for x in vals)
    return str(value)


def build_workbook(schema: dict, title: str, rows: list[dict]) -> bytes:
    """rows: [{"data": {field:值}, "created_at": str}]。返回 xlsx 字节。"""
    questions = schema.get("dataConf", {}).get("dataList", [])
    wb = Workbook()

    # Sheet1 答卷明细：一行一份，列=题目
    ws = wb.active
    ws.title = "答卷明细"
    ws.append([q["title"] for q in questions] + ["提交时间"])
    for row in rows:
        data = row.get("data", {})
        ws.append(
            [_display(q, data.get(q["field"])) for q in questions] + [row.get("created_at", "")]
        )

    # Sheet2 分题统计
    ws2 = wb.create_sheet("分题统计")
    ws2.append(["题目", "选项/分值", "计数", "占比%"])
    agg = aggregate_survey(schema, [r.get("data", {}) for r in rows])
    for q in agg["questions"]:
        if q.get("aggregation"):
            for a in q["aggregation"]:
                ws2.append([q["title"], a["text"], a["count"], a.get("percent", "")])
            if q.get("summary"):
                s = q["summary"]
                extra = f"，NPS {s['nps']}" if "nps" in s else ""
                ws2.append([q["title"], f"[均值 {s.get('average')}／中位数 {s.get('median')}{extra}]", "", ""])
        elif q.get("open_text"):
            ws2.append([q["title"], f"（开放题，{q.get('answered', 0)} 条回答）", "", ""])

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
