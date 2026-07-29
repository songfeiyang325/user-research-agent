# user-research-agent（用户调研 Agent）

面向内部使用的**用户调研 Agent**：用一套对话式 + 全流程的智能体，覆盖调研问卷的「设计 → 投放 → 采集 → 分析 → 报告」闭环。

参考并移植了滴滴开源的 [XiaoJu Survey（小桔问卷）](https://github.com/didi/xiaoju-survey) 的题型协议与统计算法，但以 **Python 后端 + Vue 前端 + MongoDB** 独立实现，前后端分离、多容器部署。

## 现状

✅ **R1 架构版已跑通** —「对话式设计问卷 → 发布 → 表单采集」在目标架构（多容器 / 前后端分离 / MongoDB / nginx 网关）下端到端可用。下一步 M2：结果分析。

## 核心能力

1. **对话式问卷设计** — 多轮对话迭代设计/修改问卷 ✅
2. **结果分析与洞察** — 分题统计、交叉分析、开放题聚类，AI 洞察报告（M2）
3. **AI 主持访谈** — 受访侧 Agent 动态追问，替代静态表单（M3）
4. **全流程编排** — 阶段感知的主控 Agent（M4）

## 架构

三容器，`docker compose` 编排，只有 nginx 对外（详见 [`docs/architecture.md`](docs/architecture.md)）：

```
浏览器 → :8080 → web(nginx: 前端静态 + /api 网关) → backend(FastAPI:8000) → mongo(27017)
```

| 层 | 选型 |
|---|---|
| 前端 | Vue3 + Vite（`frontend/`） |
| 网关 | nginx（托管前端静态 + 反向代理 `/api`） |
| 后端 | FastAPI + uvicorn（`research_agent/`），uv 管依赖 |
| 数据库 | MongoDB（pymongo） |
| 模型 | 智谱 GLM-5.2（OpenAI 兼容，可切 DeepSeek/内部网关；无 key 走离线 mock） |

## 快速开始

**整栈 Docker（推荐先跑通看效果）**
```bash
cp .env.example .env          # 可选：填 GLM_API_KEY（不填自动走 mock）
docker compose up --build     # 打开 http://localhost:8080
```

**本地开发（改代码热更）**
```bash
docker run -d -p 27017:27017 --name ura-mongo mongo:7
uv sync && uv run uvicorn research_agent.main:app --reload   # 后端 :8000
cd frontend && npm install && npm run dev                     # 前端 :5173
# 打开 http://localhost:5173
```

**测试**
```bash
uv run pytest        # survey 纯逻辑 + mongomock 下的 repo/agent
```

## 目录

```
research_agent/      后端：survey(题型/schema) · agents(Agent) · llm(GLM 客户端) · storage(Mongo) · api(FastAPI)
frontend/            前端：Vue3 + Vite（ConsoleView 控制台 / RespondView 受访页 / QuestionItem）+ nginx.conf + Dockerfile
docker-compose.yaml  三容器编排
Dockerfile           后端镜像
docs/                plan / decisions / architecture / research 规格
tests/               pytest
```

## 文档

- [`docs/architecture.md`](docs/architecture.md) — 架构 + Docker/nginx/网关入门（推荐先读）
- [`docs/plan.md`](docs/plan.md) — 实现方案与里程碑
- [`docs/decisions.md`](docs/decisions.md) — 已确认决策
- [`docs/notes/llm-portability.md`](docs/notes/llm-portability.md) — 为什么本 agent 可切模型
- [`docs/research/`](docs/research/) — xiaoju-survey 题型/schema、答卷/统计/API 规格
