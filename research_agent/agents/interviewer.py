"""Interviewer Agent —— AI 主持半结构化访谈。

- stream_reply(transcript)：产出主持人的下一句（开场/追问/下一题/结束）。真实模式走 GLM；
  mock 模式按话题顺序脚本化提问。主持人在访谈结束时单独一行输出 [END]。
- extract_answers(schema, transcript, client)：访谈结束后把逐字稿抽取成 {field: 值}，
  与表单答卷同构，直接进分析。mock 模式返回空。
"""
from __future__ import annotations

import json
from collections.abc import Iterator

from ..llm.client import LLMClient

END_MARK = "[END]"

_SYSTEM = """你是一位专业、亲和的用户研究访谈主持人。围绕下面的调研主题与话题，对受访者做半结构化访谈。

调研主题：{title}
需覆盖的话题：
{topics}

规则：
1. 一次只问一个问题，中文、口语化、简短自然。
2. 依据受访者的回答适度追问 1 次（挖"为什么/具体怎样"），不要纠缠。
3. 按顺序覆盖所有话题，已聊过的不要重复问。
4. 开场先用一句话说明来意，然后问第一个问题。
5. 所有话题聊完后，先真诚致谢并用一句话总结，然后**单独一行只输出** {end} 表示结束。"""


class InterviewerAgent:
    def __init__(self, survey):
        self.survey = survey
        self.client = LLMClient()
        self.topics = [
            q["title"]
            for q in survey.schema_data.get("dataConf", {}).get("dataList", [])
        ]

    def _system(self) -> str:
        topics = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(self.topics))
        return _SYSTEM.format(title=self.survey.title, topics=topics, end=END_MARK)

    def stream_reply(self, transcript: list[dict]) -> Iterator[tuple[str, str]]:
        if self.client.mock:
            yield from self._mock_reply(transcript)
            return
        messages = [{"role": "system", "content": self._system()}]
        for t in transcript:
            role = "assistant" if t["role"] == "assistant" else "user"
            messages.append({"role": role, "content": t["content"]})
        for kind, payload in self.client.stream(messages, tools=None, temperature=0.7):
            if kind == "token":
                yield ("token", payload)

    def _mock_reply(self, transcript: list[dict]) -> Iterator[tuple[str, str]]:
        asked = sum(1 for t in transcript if t["role"] == "assistant")
        if asked < len(self.topics):
            prefix = "你好，占用你几分钟做个简短访谈～ " if asked == 0 else ""
            yield ("token", f"{prefix}{self.topics[asked]}")
        else:
            yield ("token", f"感谢你的参与，访谈到此结束。\n{END_MARK}")


def extract_answers(schema: dict, transcript: list[dict], client: LLMClient) -> dict:
    questions = schema.get("dataConf", {}).get("dataList", [])
    if client.mock or not questions:
        return {}

    desc = []
    for q in questions:
        d = {"field": q["field"], "type": q["type"], "title": q["title"]}
        if q.get("options"):
            d["options"] = [{"hash": o["hash"], "text": o["text"]} for o in q["options"]]
        desc.append(d)
    convo = "\n".join(
        f'{"主持" if t["role"] == "assistant" else "受访"}：{t["content"]}'
        for t in transcript
    )
    prompt = (
        "根据下面的访谈记录，为每道题给出该受访者的作答，输出 JSON 对象 {field: 值}：\n"
        "- 单选/判断题 → 选项 hash 字符串；多选/投票 → hash 字符串数组；\n"
        "- 评分 → 1..满分 的整数；NPS → 0..10 的整数；文本类 → 一句话概括；\n"
        "- 访谈未涉及的题目省略该键。只输出 JSON。\n\n"
        f"题目：{json.dumps(desc, ensure_ascii=False)}\n\n访谈记录：\n{convo}"
    )
    try:
        raw = client.complete(
            [{"role": "system", "content": "你是严谨的数据抽取助手。"},
             {"role": "user", "content": prompt}]
        )
        data = _parse_json_object(raw)
    except Exception:  # noqa: BLE001
        return {}
    return _normalize(questions, data)


def _parse_json_object(raw: str) -> dict:
    i, j = raw.find("{"), raw.rfind("}")
    if i < 0 or j <= i:
        return {}
    return json.loads(raw[i : j + 1])


def _to_hash(q: dict, v) -> str | None:
    v = str(v)
    for o in q.get("options", []):
        if o["hash"] == v or o["text"] == v:
            return o["hash"]
    return None


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


def _normalize(questions: list[dict], data: dict) -> dict:
    qmap = {q["field"]: q for q in questions}
    out: dict = {}
    for f, v in (data or {}).items():
        q = qmap.get(f)
        if not q or v in (None, "", []):
            continue
        t = q["type"]
        if t in ("radio", "binary-choice"):
            h = _to_hash(q, v)
            if h:
                out[f] = h
        elif t in ("checkbox", "vote"):
            hs = [_to_hash(q, x) for x in (v if isinstance(v, list) else [v])]
            hs = [h for h in hs if h]
            if hs:
                out[f] = hs
        elif t == "radio-star":
            iv = _to_int(v)
            if iv is not None:
                out[f] = max(1, min(int(q.get("starMax", 5) or 5), iv))
        elif t == "radio-nps":
            iv = _to_int(v)
            if iv is not None:
                out[f] = max(int(q.get("min", 0) or 0), min(int(q.get("max", 10) or 10), iv))
        elif t in ("text", "textarea"):
            out[f] = str(v)
    return out
