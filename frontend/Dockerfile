# 多阶段：node 构建 Vue → nginx 托管静态 + 网关（= web 容器）
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --registry https://registry.npmmirror.com --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
