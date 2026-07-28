# user-research-agent（用户调研 Agent）

面向内部使用的**用户调研 Agent**：用一套对话式 + 全流程的智能体，覆盖调研问卷的「设计 → 投放 → 采集 → 分析 → 报告」闭环。

参考并移植了滴滴开源的 [XiaoJu Survey（小桔问卷）](https://github.com/didi/xiaoju-survey) 的题型协议与统计算法，但以 **Python 独立实现**，不修改原仓库。

## 现状

🚧 **M1 建设中** — 需求对齐、参考规格分析、实现方案已完成（见 `docs/`）。正在搭建 `research_agent/`，打通「对话式设计问卷 → 发布 → 表单采集」竖切。

## 核心能力（规划）

1. **对话式问卷设计** — 多轮对话迭代设计/修改问卷
2. **结果分析与洞察** — 分题统计、交叉分析、开放题聚类，产出 AI 洞察报告
3. **AI 主持访谈** — 受访侧由 Agent 动态追问，替代静态表单
4. **全流程编排** — 阶段感知的主控 Agent 串起调研全流程

## 技术选型

| 层 | 选型 |
|---|---|
| 语言 | Python 3.10+ |
| 环境/依赖 | **uv**（`pyproject.toml` + `uv.lock`） |
| 服务 | FastAPI + uvicorn（REST + SSE 流式） |
| 存储 | SQLite（SQLModel = SQLAlchemy 2 + Pydantic v2） |
| 模型 | **智谱 GLM-5.2** 纯文本（OpenAI 兼容接口，`base_url`/`model` 配置化，可切 DeepSeek/内部网关） |
| 分析 | pandas + numpy + scipy |
| 前端 | buildless：Jinja2 + 原生 JS/CSS + Chart.js(CDN) |
| 部署 | Docker（uv 多阶段构建，自包含 SQLite） |

## 快速开始

```bash
uv sync                                    # 安装依赖（读 pyproject.toml/uv.lock）
cp .env.example .env                       # 填入 GLM_API_KEY 等
uv run uvicorn research_agent.main:app --reload
# 打开 http://127.0.0.1:8000/console
```

Docker：

```bash
docker build -t user-research-agent .
docker run -p 8000:8000 --env-file .env user-research-agent
```

## 文档

- [`docs/plan.md`](docs/plan.md) — 完整实现方案（技术栈、目录结构、四大能力、M1–M4）
- [`docs/decisions.md`](docs/decisions.md) — 已确认决策与需求
- [`docs/notes/llm-portability.md`](docs/notes/llm-portability.md) — 为什么这个 agent 能切模型（vs Claude Code 锁 Anthropic）
- [`docs/research/`](docs/research/) — xiaoju-survey 题型/schema、答卷/统计/API 规格
