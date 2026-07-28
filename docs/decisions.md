# 已确认决策与需求

> 本文件记录「用户调研 Agent」项目的需求对齐结论，作为后续实现的依据。日期：2026-07-28。

## 一句话目标

做一个**面向内部使用、覆盖调研全流程的用户调研 Agent**，用 **Python 全新独立实现**（不改 NestJS 的 xiaoju-survey 仓库），把小桔问卷的题型协议/统计算法作为**参考规格**移植过来，并补齐它缺失的能力。

## 背景：现有 AI 能力的局限

xiaoju-survey 已内置「AI 一句话生成问卷」，但只是**一次性文生问卷**：

- 前端 `web/src/management/pages/list/components/AIGenerate.vue` → 后端 `/api/ai-generate/call-deepseek`（`server/src/modules/survey/services/ai-generate.service.ts`）
- 走 OpenAI 兼容流式接口，系统提示词让模型按固定文本格式吐题目，前端 `textToSchema` 解析预览
- **局限**：不支持多轮对话修改（UI 明示）、题型固定、上限 12 题、**完全不分析回收数据**、无工具调用/无迭代

## 已确认决策

| 维度 | 结论 |
|---|---|
| **核心能力** | 四块全做：①对话式问卷设计 ②结果分析与洞察 ③AI 主持访谈 ④全流程编排 |
| **模型** | **智谱 GLM-5.2 纯文本**（OpenAI 兼容接口；不用视觉/VLM，尽管父目录名为「智谱-VLM」） |
| **落地** | **用 Python 完整做一个**，独立于 NestJS 仓库；xiaoju-survey 作参考/可选对接对象 |
| **交互形态** | **FastAPI + 轻量 Web UI**（研究员控制台 + 可分享的受访/访谈页） |
| **问卷/数据** | **自包含**：自带 SQLite 存储、自出受访页，不依赖 NestJS + Mongo |
| **环境/依赖** | **uv** 管理（`pyproject.toml` + `uv.lock`，`uv add`/`uv sync`/`uv run`） |
| **部署** | 本机有 **Docker**；M1 起提供 Dockerfile（uv 多阶段构建，自包含 SQLite 无需额外容器） |

## 关键设计原则：模型「协议可切、主攻一个」

我们的 agent 走 **OpenAI 兼容协议**（`messages`/`tools`/`tool_calls`/SSE），`llm/client.py` 抽一层，所以换 GLM↔DeepSeek↔内部网关只改 `base_url`/`api_key`/`model` 三个配置。**但「能调用」不等于「效果一样」**：函数调用稳定性、提示词敏感度、特性差异都会让同一套 prompt 在不同模型上表现不同。因此**提示词与工具调用只针对 GLM-5.2 调优、验证**，其余仅作兜底。详见 [`notes/llm-portability.md`](notes/llm-portability.md)。

## 四大能力定义

1. **对话式问卷设计** — 多轮对话澄清目的、迭代修改题目/题型/逻辑（升级一次性生成）
2. **结果分析与洞察** — 分题统计、交叉分析、开放题聚类，产出 AI 叙事洞察报告
3. **AI 主持访谈** — 受访者侧由 Agent 根据回答动态追问，像访谈一样采集深度定性反馈
4. **全流程编排** — 目标澄清 → 设计 → 投放 → 采集 → 分析 → 报告，串成一个 Agent 流程

## 仓库 / 环境事实（2026-07-28 探明）

- GitHub 账号 `songfeiyang325` 已通过 SSH 密钥 `id_rsa` 绑定本机（`ssh -T` 返回 `Hi songfeiyang325!`）
- 网络（国内）：github.com 的 SSH-22、HTTPS **直连不通**；**SSH 走 443（ssh.github.com:443）通**、**api.github.com 通**；`gh` CLI 未安装
- 本仓库 `origin` 使用 `ssh://git@ssh.github.com:443/...` 走 443 推送
- 仓库可见性：**Public**（内容基于已开源的 xiaoju-survey，无真正机密）
- 本机工具链：uv 0.11.30 · Python 3.10.11 · Docker 29.1.3

## 待定项

- 智谱账号可用的确切 GLM 模型 id（默认 `glm-5.2`，配置化；上线按控制台/模型列表确认）
- 控制台 MVP 先不做鉴权（内部工具），后续可加简单 token
