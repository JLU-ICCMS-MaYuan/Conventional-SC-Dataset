# 前端 — 多阶段：Vite 构建 + Nginx 提供静态文件
FROM node:22-alpine AS builder

ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /build/static /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/public/robots.txt /usr/share/nginx/html/robots.txt
EXPOSE 80
