"""开放题主题聚类（LLM 辅助；无 key 时给出兜底，不阻断流程）。"""
from __future__ import annotations

import json

from ..llm.client import LLMClient

_SYS = "你是用户研究分析助手，擅长把开放题回答归纳成清晰的主题。"


def cluster_open_text(title: str, answers: list[str], client: LLMClient) -> list[dict]:
    answers = [a.strip() for a in answers if a and a.strip()]
    if not answers:
        return []
    if client.mock:
        return [{"theme": "（离线未做语义聚类）", "count": len(answers), "examples": answers[:3]}]

    prompt = (
        f"题目：{title}\n下面是 {len(answers)} 条开放题回答，请归纳成不超过 6 个主题。"
        '输出 JSON 数组，每项 {"theme": 简短主题, "count": 大致条数(整数), '
        '"examples": 最多2条代表性原文}。只输出 JSON。\n\n回答：\n'
        + "\n".join(f"- {a}" for a in answers[:200])
    )
    try:
        raw = client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": prompt}]
        )
        return _parse_json_array(raw)
    except Exception:  # noqa: BLE001
        return [{"theme": "（聚类失败，展示原文）", "count": len(answers), "examples": answers[:3]}]


def _parse_json_array(raw: str) -> list[dict]:
    i, j = raw.find("["), raw.rfind("]")
    if i < 0 or j <= i:
        raise ValueError("no json array")
    data = json.loads(raw[i : j + 1])
    out: list[dict] = []
    for it in data if isinstance(data, list) else []:
        out.append(
            {
                "theme": str(it.get("theme", "")),
                "count": int(it.get("count", 0) or 0),
                "examples": [str(x) for x in (it.get("examples") or [])][:2],
            }
        )
    return out
