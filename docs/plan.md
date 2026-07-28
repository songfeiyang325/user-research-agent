# 用户调研 Agent — 实现方案

> 实现方案（设计稿）。已确认决策见 [`decisions.md`](decisions.md)；参考规格见 [`research/`](research/)。

## 目标

做一个**面向内部、覆盖调研全流程的独立 Agent**，用 **Python 全新实现**（不改 NestJS 仓库），把小桔问卷的题型协议/统计算法作为**参考规格**移植，并补齐它没有的能力。四大能力全做：

1. **对话式问卷设计** — 多轮对话迭代设计/修改问卷（升级一次性生成）
2. **结果分析与洞察** — 分题统计、交叉分析、开放题聚类，产出 AI 洞察报告
3. **AI 主持访谈** — 受访者侧由 Agent 动态追问，替代静态表单
4. **全流程编排** — 目标澄清 → 设计 → 投放 → 采集 → 分析 → 报告

## 技术选型

- **Python 3.10+**，`FastAPI` + `uvicorn`（REST + SSE 流式；访谈用 SSE）
- **SQLite**（`SQLModel` = SQLAlchemy 2 + Pydantic v2，模型即 ORM）
- **智谱 GLM**：用 `openai` SDK 指向 `https://open.bigmodel.cn/api/paas/v4/`，OpenAI 风格 `tools`/`tool_calls` 函数调用 + `stream`。`base_url`/`model` 全走 `.env`，可无缝切 DeepSeek/内部网关
- **分析**：`pandas` + `numpy` + `scipy`（交叉分析卡方/Cramér's V）
- **前端**：**buildless**（无 Node 构建）——Jinja2 模板 + 原生 JS/CSS，交互用 `fetch`+SSE；图表用 Chart.js（CDN）

## 目录结构（新建 Python 包 `research_agent/`）

```
research_agent/
  main.py                 # uvicorn 入口
  app.py                  # FastAPI 装配：路由 + StaticFiles + Jinja2
  config.py               # pydantic-settings 读 .env（GLM key/base_url/model、db 路径）
  llm/
    client.py             # GLM 客户端封装：chat / stream / tools（provider 可切换）
    prompts.py            # designer / analyst / interviewer / orchestrator 系统提示词
  agents/
    base.py               # 通用「带工具的 Agent 循环」：messages↔tools↔stream
    orchestrator.py       # 控制台主 Agent：按项目 stage/意图 分发 + 推进阶段
    interviewer.py        # 受访侧访谈 Agent：动态追问、话题覆盖、抽取结构化
  survey/
    types.py              # 9 种题型枚举 + 各型默认值（对齐 meta.js）
    schema.py             # Pydantic 模型：Survey / Question / Option / LogicRule
    textscheme.py         # 文本↔schema 转换（移植 textToSchema 语法）
    validate.py           # 校验 + field(dataNNN)/hash(6位) 生成
  analysis/
    stats.py              # 分题聚合 + 评分/NPS 汇总（均值/中位数/样本方差/NPS）
    crosstab.py           # 交叉分析（原项目缺失，新建）：列联表 + 卡方 + Cramér's V
    textmining.py         # 开放题主题聚类（LLM 辅助）
    report.py             # 汇总为洞察报告（LLM 叙事 + 图表数据）
  storage/
    db.py                 # SQLite 引擎/会话
    models.py             # Project / Survey / Message / Response / InterviewSession/Turn
    repo.py               # CRUD
  api/
    projects.py design.py survey.py respond.py interview.py analysis.py
  web/
    templates/            # console.html / respond.html / interview.html / report.html
    static/               # css + 原生 js
tests/                    # pytest：schema 往返、统计算法、交叉分析、mock-LLM 工具循环
.env.example  requirements.txt  README.md
```

## 参考规格（从 xiaoju-survey 移植，非改动）

详见 [`research/xiaoju-survey-schema-spec.md`](research/xiaoju-survey-schema-spec.md) 与 [`research/xiaoju-survey-response-analysis-spec.md`](research/xiaoju-survey-response-analysis-spec.md)。

- **9 种题型**（`web/src/common/typeEnum.ts` / `server/src/enums/question.ts`）：`text, textarea, radio, checkbox, binary-choice, radio-star, radio-nps, vote, cascader`
- **Survey/Question/Option 结构**（`server/src/interfaces/survey.ts`、模板 `templateBase.json`）：`question` 的 `field/title/type/isRequired/options[]`，`option` 的 `text/hash/others`
- **逻辑规则**（`web/src/common/logicEngine/*`）：`{target, scope, conditions:[{field, operator(in/eq/nin/neq), value[]}]}`，AND/OR + 成员语义
- **文本↔schema 语法**（`web/src/management/utils/textToSchema.ts`）：空行分块、首行 `标题[类型]`、后续行为选项
- **统计算法**（`server/.../dataStatistic.service.ts` + `utils/index.ts`）：分题计数、多选拆分求和、评分/NPS 的 `average/median/样本方差/NPS%`。**交叉分析原项目无实现**

## 数据模型（SQLite）

- `Project`：调研项目（全流程容器）— `id, name, goal, stage(intake/design/collect/analyze/report), created_at`
- `Survey`：`id, project_id, title, schema_json, mode(form|interview), status(draft/published), share_path, published_at`
- `Message`：设计期对话历史 `role/content/tool_calls`
- `Response`：`id, survey_id, data_json({field:值}, 与小桔答卷同构), meta(diffTime…), channel, created_at`
- `InterviewSession` / `InterviewTurn`：访谈会话 + 逐轮问答 + 抽取的结构化数据（结束时合成一条 `Response` 供分析）

## 四大能力如何落地

**① 对话式设计**：控制台左侧聊天、右侧实时预览。Designer 用**函数调用**维护一份问卷草稿（工具：`set_meta / upsert_questions / remove_question / set_logic`），"把第3题改成多选""加一道NPS"这类多轮修改天然支持；结构化工具输出替代文本解析，避免格式脆弱（文本语法保留为粘贴导入）。定稿 → 存 Survey → 发布 → 分享链接。

**② 结果分析**：`analysis/stats.py` 用 pandas 复刻分题统计 + 评分/NPS 汇总；`crosstab.py` 新建交叉分析（Q×Q 列联表 + 卡方 + Cramér's V）；`textmining.py` 用 GLM 对开放题聚类主题。Analyst Agent 以这些为工具，产出叙事式洞察报告（发现/人群差异/建议），`report.html` 用 Chart.js 出图。

**③ AI 主持访谈**：`Survey.mode=interview` 时受访者进聊天页。Interviewer Agent 持有研究目标 + 话题大纲，一次一问、按回答动态追问、跟踪话题覆盖度，结束时抽取结构化 + 保留逐字稿，合成 `Response` 进分析。SSE 流式、按 session 持久化（刷新不丢）。

**④ 全流程编排**：`orchestrator.py` 作为控制台主 Agent，感知 `Project.stage`，按意图把请求分派给设计/分析工具并推进阶段，主动建议下一步（"已收集 30 份，是否生成报告？"）。单 Agent + 全量工具 + 阶段感知，比多 Agent 路由更稳。

## LLM 集成

`openai` SDK：`base_url` / `api_key` / `model`（默认 `glm-4-plus`，廉价任务用 `glm-4-flash`）全走 `.env`。工具走 OpenAI `tools` 协议，`stream=True`。抽象一层 `llm/client.py`，切 DeepSeek/内部网关只改配置。**待确认**：账号可用的确切 GLM 模型 id。

## 构建顺序（分里程碑，先打通竖切再铺开）

- **M1 地基 + 设计闭环**：包脚手架、config、SQLite 模型、GLM 客户端、题型/schema/校验、文本↔schema、Designer Agent + 控制台（聊天+预览）、发布+分享、静态表单受访页+提交 → 打通「设计→发布→采集(表单)」
- **M2 分析**：stats + crosstab + 开放题聚类 + Analyst Agent + 报告页出图；附造数脚本
- **M3 AI 访谈**：Interviewer Agent + 访谈受访页(SSE) + 会话存储 + 合成答卷进分析
- **M4 编排收尾**：项目生命周期/阶段推进/主动建议；pytest + README + .env.example

先交付 **M1 完整可跑**（`uvicorn` 起服务即可端到端跑通），再逐里程碑推进。

## 验证方式

- `pip install -r requirements.txt` → 配 `.env`（GLM key）→ `uvicorn research_agent.main:app --reload`
- `/console` 对话设计问卷 → 发布拿分享链接 → 打开链接填表/做 AI 访谈 → 提交 → 回控制台生成分析报告
- `pytest`：文本↔schema 往返、统计算法（对拍手算的均值/中位数/方差/NPS）、交叉分析、mock-LLM 的工具循环；造数脚本灌假答卷演示分析

## 假设 / 待定

- GLM 模型 id 以账号实际可用为准（默认 `glm-4-plus`，配置化）
- 控制台 MVP 先不做鉴权（内部工具），后续可加简单 token
- UI 中文、代码注释中文，与团队一致
