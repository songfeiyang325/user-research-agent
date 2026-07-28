# 为什么这个 Agent 能切换模型（而 Claude Code 只认 Anthropic）

> 记录一次设计讨论的结论。核心结论：**一个 agent 绑不绑某个模型，取决于它绑的是哪套 _API 协议（wire format）_，而不是模型本身。**

agent 本质是「你的代码通过 HTTP 反复调用一个模型接口 + 执行工具」。能不能换模型，看的是**接口长得一不一样**。

## 1. 能切，是因为「协议通用」，不是「模型通用」

本项目用 **OpenAI 的 Chat Completions 协议**：请求 `messages` / `tools`，回包 `choices[].delta` / `tool_calls`，流式用 SSE。而 **DeepSeek、智谱 GLM、通义、月之暗面……国内一大批模型都主动做了 OpenAI 兼容**。所以「换模型」对代码来说只是改三个配置：

```
base_url  +  api_key  +  model
```

因为接口字段一模一样。xiaoju-survey 里那段函数名叫 `callDeepSeekAPI`，其实调的就是 OpenAI 协议——名字是 DeepSeek，协议是通用的。

## 2. Claude Code 锁 Anthropic 是「产品选择」，不是「技术必然」

Claude Code 用的是 **Anthropic 自己的 Messages API**，跟 OpenAI 协议**不是一套**（消息结构、tool-use 的 content block、system 约定都不同），而且它的提示词、工具调用格式是**深度针对 Claude 调过**的。Anthropic 没有动机让自家 CLI 适配别家模型，就锁定了 Claude。

> 换句话说：不是 agent 天生只能绑一个模型，是 Claude Code **选择**绑一个。

## 3. 但「能切」≠「换了都一样好」

真正让 agent 挑模型的耦合点有四层：

| 耦合层 | 说明 |
|---|---|
| **协议 / wire format** | 最硬的一层。OpenAI 协议 / Anthropic Messages / Gemini 各不同，绑死一种就要写适配层才能换 |
| **函数调用稳定性** | 都号称「OpenAI 兼容」，但对复杂 tool schema、并行工具调用、JSON 严格度的遵循程度差很多。**代码能跑 ≠ 效果一样** |
| **提示词敏感度** | 给 A 模型调好的 system prompt，换 B 可能就退化。**代码可移植 ≠ 提示质量可移植** |
| **特性差异** | 思维链字段 `reasoning_content`、缓存、结构化输出、上下文长度……要按 provider 单独处理 |

## 4. 本项目的取舍：协议层可切、主攻一个模型

`llm/client.py` 抽一层走 OpenAI 兼容协议，于是 GLM↔DeepSeek 配置即切；但**提示词和工具调用只针对 GLM-5.2 调优、验证**，DeepSeek 之类只当兜底/备用，不假装「随便换都等效」。这样既拿到灵活性，又不自欺。
