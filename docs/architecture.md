# 架构说明（含 Docker / nginx / 网关 入门）

> 面向不熟悉 nginx / 网关 / 端口转发的读者。读完你会明白：这套系统由哪几个容器组成、它们怎么互相通信、为什么只对外开一个端口。

## 1. 总览：三个容器

```
                     浏览器  ──▶  http://localhost:8080   (唯一对外入口)
                                        │
                          ┌─────────────▼─────────────┐
                          │   web 容器 (nginx)         │
                          │   ①托管 Vue 打包静态       │
                          │   ②当"网关"转发 /api        │
                          └───────┬───────────────────┘
                                  │ /api/* → http://backend:8000
                          ┌───────▼────────┐        ┌──────────────┐
                          │  backend 容器   │───────▶│  mongo 容器   │
                          │  FastAPI:8000   │  mongodb://mongo:27017 │
                          └────────────────┘        └──────────────┘
        docker compose 把三者放进同一虚拟内网；只有 web 的 8080 映射到你的电脑
```

| 容器 | 里面跑什么 | 端口 | 对外？ |
|---|---|---|---|
| `web` | nginx（托管前端静态 + 反向代理） | 80 | ✅ 映射到宿主 8080 |
| `backend` | FastAPI（Agent / 问卷 / 分析） | 8000 | ❌ 仅内网 |
| `mongo` | MongoDB（数据库） | 27017 | ❌ 仅内网 |

## 2. 五个核心概念

**① 端口（port）**：一个程序对外的"门牌号"。FastAPI 开在 8000、Mongo 开在 27017、nginx 开在 80。同一台机器上一个端口同一时刻只能被一个程序占用。

**② 端口映射 `-p 宿主:容器`**：容器有自己独立的一套端口，默认外界访问不到。`ports: ["8080:80"]` 意思是"把宿主机的 8080 接到该容器的 80"——你在浏览器访问 `localhost:8080`，流量就进了 web 容器的 80。**我们只对 web 做了映射**，backend / mongo 没有 `ports:`，所以从宿主机**直接**访问不到它们（更安全）。

**③ 反向代理 / 网关（nginx）**：站在最前面的"总台"。浏览器只跟它说话；它看请求的 URL 决定把活儿派给谁：
- `/api/xxx` → 转发给 `backend`（这叫**反向代理** reverse proxy）
- 其它（`/`、`/r/xxx`）→ 直接返回前端静态页

因为它是所有流量的统一入口、对内分发，所以也叫**网关（gateway）**。好处：对外只开一个口、前端不用知道后端在哪、以后要加 HTTPS / 限流 / 日志都在这一层做。

**④ compose 内网 + 服务名**：`docker compose` 会建一个虚拟局域网，把三个容器都放进去。**同一网络里，容器之间可以用"服务名"当域名互相访问**：
- nginx 转发写的是 `http://backend:8000`——`backend` 就是 compose 里的服务名
- 后端连库写的是 `mongodb://mongo:27017`——`mongo` 也是服务名

Docker 内置 DNS 会把服务名解析成容器的内网 IP，不用你操心 IP。

**⑤ 为什么只暴露 nginx**：backend 和 mongo 不写 `ports:`，就不会映射到宿主机——外网碰不到它们，只有内网里的 nginx（以及 backend）能访问。攻击面就只剩 nginx 一个入口。

## 3. `docker-compose.yaml` 逐段

```yaml
services:
  mongo:
    image: mongo:7                 # 直接用官方镜像，不用自己构建
    volumes: [mongo-data:/data/db] # 把数据存到命名卷，容器重建数据不丢
    networks: [app]                # 加入 app 内网
    # 没有 ports → 不对宿主暴露，只有内网能连

  backend:
    build: .                       # 用根目录 Dockerfile 构建（FastAPI）
    environment:
      MONGO_URL: mongodb://mongo:27017   # ← 用服务名 mongo，不是 localhost
      GLM_API_KEY: ${GLM_API_KEY:-}      # 从你运行 compose 时的环境/.env 注入
    depends_on: [mongo]            # 先起 mongo（注意：只保证启动顺序，不保证 mongo 已就绪）
    networks: [app]

  web:
    build: ./frontend              # 用 frontend/Dockerfile（构建 Vue + 配 nginx）
    ports: ["8080:80"]             # ← 唯一对外映射：宿主 8080 → 容器 80
    depends_on: [backend]
    networks: [app]

volumes: { mongo-data: }           # 声明命名卷
networks: { app: { driver: bridge } }
```

## 4. `frontend/nginx.conf` 逐段

```nginx
server {
    listen 80;                     # 容器内监听 80

    root /usr/share/nginx/html;    # Vue 打包产物（dist）拷到了这里
    location / {
        try_files $uri $uri/ /index.html;   # 找不到文件就回 index.html
        # ↑ SPA 关键：/r/abc 这种前端路由在服务器上没有对应文件，
        #   回 index.html 交给 Vue Router 处理，刷新才不会 404
    }

    location /api/ {
        proxy_pass http://backend:8000;     # 转发给后端（保留 /api 前缀）
        proxy_http_version 1.1;
        proxy_buffering off;                # ← SSE 流式必须关缓冲，
        proxy_read_timeout 1h;              #   否则对话不会"逐字"返回、长连接会断
    }
}
```

> **踩过的坑**：nginx 默认会把上游响应缓冲起来再一次性发给浏览器，这会让我们的流式对话（SSE）失去"逐字蹦出"的效果。所以 `/api/` 里必须 `proxy_buffering off`，并把 `proxy_read_timeout` 拉长。

## 5. 一次"对话生成问卷"请求怎么流动

1. 浏览器（`localhost:8080`）POST `/api/projects/<id>/chat` → 进 **web 容器的 nginx**
2. nginx 看到 `/api/` → `proxy_pass` 到 **`backend:8000`**（走内网、用服务名）
3. FastAPI 跑 Designer Agent，需要读写问卷 → 连 **`mongo:27017`**
4. 后端以 SSE 逐块把 token / survey 事件往回吐 → nginx（不缓冲）→ 浏览器实时显示

## 6. 两种运行方式

**A. 本地开发（改代码热更，最快）**
```bash
docker run -d -p 27017:27017 --name ura-mongo mongo:7   # 只起个库
cd .../user-research-agent && uv run uvicorn research_agent.main:app --reload   # 后端:8000
cd frontend && npm run dev                               # 前端:5173（vite 把 /api 代理到 8000）
# 打开 http://localhost:5173
```

**B. 整栈 Docker（贴近生产）**
```bash
cp .env.example .env      # 可选：填 GLM_API_KEY（不填走 mock）
docker compose up --build # 打开 http://localhost:8080
docker compose down       # 停；加 -v 连数据卷一起删
```

常用命令：`docker compose ps`（看状态）、`docker compose logs -f backend`（看后端日志）、`docker compose build backend`（只重建后端）。
