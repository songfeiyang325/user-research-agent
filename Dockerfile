# syntax=docker/dockerfile:1
# 多阶段构建：Docker Hub 的 python 基础镜像 + pip 装 uv（避开 ghcr.io，国内更稳）
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv
# 先只装依赖（利用缓存），再拷源码装项目
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --no-install-project --no-dev
COPY research_agent ./research_agent
RUN uv sync --no-dev

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "research_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
