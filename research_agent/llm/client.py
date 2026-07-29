"""智谱 GLM 客户端封装（OpenAI 兼容协议）。

只做一件事：把「一次带工具的流式对话」标准化成事件流。切换 GLM↔DeepSeek↔
内部网关只改 .env 的 base_url/model/key。无 API Key 时进入 mock 模式，本类不被调用。
"""
from __future__ import annotations

from collections.abc import Iterator

from ..config import settings

# 事件：("token", str) 文本增量 | ("tool_calls", list[dict]) 工具调用 | ("done", str) 结束
Event = tuple[str, object]


class LLMClient:
    def __init__(self, model: str | None = None):
        self.model = model or settings.glm_model
        self.mock = settings.use_mock
        self._client = None
        if not self.mock:
            from openai import OpenAI  # 延迟导入，mock 模式无需 openai

            self._client = OpenAI(
                api_key=settings.glm_api_key, base_url=settings.glm_base_url
            )

    def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.6,
    ) -> Iterator[Event]:
        if self._client is None:
            raise RuntimeError("LLM 未配置：mock 模式下不应调用 client.stream")

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            stream=True,
            temperature=temperature,
        )

        tool_acc: dict[int, dict] = {}
        for chunk in resp:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if getattr(delta, "content", None):
                yield ("token", delta.content)

            for tc in getattr(delta, "tool_calls", None) or []:
                slot = tool_acc.setdefault(
                    tc.index, {"id": "", "name": "", "arguments": ""}
                )
                if tc.id:
                    slot["id"] = tc.id
                fn = getattr(tc, "function", None)
                if fn is not None:
                    if fn.name:
                        slot["name"] = fn.name
                    if fn.arguments:
                        slot["arguments"] += fn.arguments

            if choice.finish_reason:
                if tool_acc:
                    yield ("tool_calls", [tool_acc[i] for i in sorted(tool_acc)])
                yield ("done", choice.finish_reason)
