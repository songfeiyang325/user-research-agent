"""通用「带工具的 Agent 循环」——与领域解耦。

事件流：("token", str) 助手文本增量 | ("tool_result", {name, result}) 工具执行结果。
run_stream 返回最终助手文本。工具实现由调用方注入 tool_impls。
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator

from ..llm.client import LLMClient


class ToolAgent:
    def __init__(
        self,
        client: LLMClient,
        system_prompt: str,
        tools: list[dict] | None = None,
        tool_impls: dict[str, Callable] | None = None,
        max_rounds: int = 6,
    ):
        self.client = client
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.tool_impls = tool_impls or {}
        self.max_rounds = max_rounds

    def run_stream(self, history: list[dict]) -> Iterator[tuple[str, object]]:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        messages += list(history)

        for _ in range(self.max_rounds):
            text_parts: list[str] = []
            tool_calls: list[dict] | None = None

            for kind, payload in self.client.stream(messages, self.tools):
                if kind == "token":
                    text_parts.append(payload)  # type: ignore[arg-type]
                    yield ("token", payload)
                elif kind == "tool_calls":
                    tool_calls = payload  # type: ignore[assignment]

            assistant_text = "".join(text_parts)

            if not tool_calls:
                messages.append({"role": "assistant", "content": assistant_text})
                return

            # 归一化 id，保证 assistant.tool_calls[].id 与 tool.tool_call_id 一致
            for i, tc in enumerate(tool_calls):
                if not tc.get("id"):
                    tc["id"] = f"call_{i}"

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"] or "{}",
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                result = self._exec(tc)
                yield ("tool_result", {"name": tc["name"], "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        return

    def _exec(self, tool_call: dict) -> dict:
        name = tool_call["name"]
        impl = self.tool_impls.get(name)
        if impl is None:
            return {"ok": False, "error": f"未知工具: {name}"}
        try:
            args = json.loads(tool_call.get("arguments") or "{}")
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"参数解析失败: {e}"}
        try:
            return impl(**args)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}
