# 股票投资辅助工具 — Plan 3：部署计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端和前端打包成 Docker 镜像，通过 Docker Compose + nginx 实现一键远程部署，支持 HTTPS。

**Architecture:** 三个容器（backend、frontend、nginx），nginx 作为反向代理统一对外暴露 443 端口，Let's Encrypt 自动 HTTPS 证书。

**Tech Stack:** Docker, Docker Compose, nginx, Certbot (Let's Encrypt)

**前置条件:** Plan 1（后端）和 Plan 2（前端）均已完成并本地验证通过。

---

## 文件结构

```
stock-tool/
├── backend/
│   └── Dockerfile
├── frontend/
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf          # HTTP 版（无 HTTPS，用于首次 certbot 认证）
│   └── nginx-ssl.conf      # HTTPS 版（certbot 完成后切换）
├── docker-compose.yml
├── docker-compose.prod.yml # 生产环境覆盖（挂载证书）
├── .env.example
└── .env                    # 实际配置（不提交到 git）
```

---

## Task 1: Dockerfile（后端）

**Files:**
- Create: `stock-tool/backend/Dockerfile`

- [ ] **Step 1: 写 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 验证镜像构建**

```bash
cd stock-tool/backend
docker build -t stock-tool-backend .
```

Expected: 构建成功，无报错。

- [ ] **Step 3: 验证镜像运行**

```bash
docker run --rm \
  -e APP_PASSWORD=test123 \
  -e SECRET_KEY=test-secret-key-64chars-padded-padding-more-padding-here \
  -e DATABASE_URL=/data/data.db \
  -p 8000:8000 \
  stock-tool-backend
```

Expected: `uvicorn` 启动，访问 http://localhost:8000/health 返回 `{"status":"ok"}`

- [ ] **Step 4: Commit**

```bash
git add stock-tool/backend/Dockerfile
git commit -m "feat: backend Dockerfile"
```

---

## Task 2: Dockerfile（前端）

**Files:**
- Create: `stock-tool/frontend/Dockerfile`

- [ ] **Step 1: 写 frontend/Dockerfile**

```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 2: 更新 next.config.ts 开启 standalone 输出**

```typescript
import type { NextConfig } from "next"

const config: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://backend:8000/:path*",
      },
    ]
  },
}

export default config
```

注意：生产环境中 rewrites 的 destination 改为 `http://backend:8000`（Docker 内部网络服务名）。

- [ ] **Step 3: 验证镜像构建**

```bash
cd stock-tool/frontend
docker build \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  -t stock-tool-frontend .
```

Expected: 构建成功（约2-3分钟）。

- [ ] **Step 4: Commit**

```bash
git add stock-tool/frontend/Dockerfile stock-tool/frontend/next.config.ts
git commit -m "feat: frontend Dockerfile with standalone output"
```

---

## Task 3: nginx 配置

**Files:**
- Create: `stock-tool/nginx/nginx.conf`
- Create: `stock-tool/nginx/nginx-ssl.conf`

- [ ] **Step 1: 写 nginx/nginx.conf（HTTP，用于初次 Certbot 认证）**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name _;

        # Certbot webroot challenge
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # API 请求转发到后端
        location /api/ {
            rewrite ^/api/(.*) /$1 break;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # 其余请求转发到前端
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

- [ ] **Step 2: 写 nginx/nginx-ssl.conf（HTTPS，Certbot 后切换使用）**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name YOUR_DOMAIN;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name YOUR_DOMAIN;

        ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location /api/ {
            rewrite ^/api/(.*) /$1 break;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 120s;
        }

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

将两处 `YOUR_DOMAIN` 替换为实际域名（如 `invest.example.com`）。

- [ ] **Step 3: Commit**

```bash
git add stock-tool/nginx/
git commit -m "feat: nginx config (HTTP and HTTPS variants)"
```

---

## Task 4: Docker Compose

**Files:**
- Create: `stock-tool/docker-compose.yml`
- Create: `stock-tool/docker-compose.prod.yml`
- Create: `stock-tool/.env.example`

- [ ] **Step 1: 写 docker-compose.yml（开发/基础版）**

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    restart: unless-stopped
    environment:
      APP_PASSWORD: ${APP_PASSWORD}
      SECRET_KEY: ${SECRET_KEY}
      SMTP_HOST: ${SMTP_HOST:-smtp.gmail.com}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASS: ${SMTP_PASS:-}
      NOTIFY_EMAIL: ${NOTIFY_EMAIL:-}
      CLAUDE_API_KEY: ${CLAUDE_API_KEY:-}
      DATABASE_URL: /data/data.db
    volumes:
      - backend_data:/data
    networks:
      - app

  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_URL: ""
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: ""
    networks:
      - app

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot_www:/var/www/certbot
    networks:
      - app
    depends_on:
      - backend
      - frontend

volumes:
  backend_data:
  certbot_www:

networks:
  app:
    driver: bridge
```

- [ ] **Step 2: 写 docker-compose.prod.yml（生产 HTTPS 叠加）**

```yaml
version: "3.9"

services:
  nginx:
    volumes:
      - ./nginx/nginx-ssl.conf:/etc/nginx/nginx.conf:ro
      - certbot_www:/var/www/certbot
      - certbot_certs:/etc/letsencrypt:ro
    ports:
      - "80:80"
      - "443:443"

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_www:/var/www/certbot
      - certbot_certs:/etc/letsencrypt
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  certbot_certs:
```

- [ ] **Step 3: 写 .env.example（根目录）**

```env
APP_PASSWORD=changeme_strong_password
SECRET_KEY=replace_with_64_random_hex_chars
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_gmail_app_password
NOTIFY_EMAIL=your@gmail.com
CLAUDE_API_KEY=
```

- [ ] **Step 4: Commit**

```bash
git add stock-tool/docker-compose.yml stock-tool/docker-compose.prod.yml stock-tool/.env.example
git commit -m "feat: Docker Compose for local and production deployment"
```

---

## Task 5: 本地 Docker 集成验证

**Files:** 无新文件

- [ ] **Step 1: 复制并填写 .env**

```bash
cd stock-tool
cp .env.example .env
# 编辑 .env，填写真实密码和邮件配置
```

- [ ] **Step 2: 启动全部服务**

```bash
docker-compose up --build -d
```

Expected: 三个容器均 `Up`。

```bash
docker-compose ps
```

Expected 输出（状态为 Up）：
```
NAME                STATUS
stock-tool-backend  Up
stock-tool-frontend Up
stock-tool-nginx    Up
```

- [ ] **Step 3: 验证各接口**

```bash
# 健康检查
curl http://localhost/api/health
# 预期: {"status":"ok"}

# 登录
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"your_password"}'
# 预期: {"access_token":"...","token_type":"bearer"}
```

- [ ] **Step 4: 浏览器验证**

```
访问 http://localhost
预期：跳转到登录页，登录后可访问仪表盘
在手机浏览器中输入 http://<本机IP> 同样可访问
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: local Docker Compose integration verified"
```

---

## Task 6: VPS 远程部署

**前置条件：** 已有 VPS（推荐 Ubuntu 22.04），已绑定域名（DNS A记录指向 VPS IP）。

- [ ] **Step 1: VPS 安装 Docker**

在 VPS 上执行：

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录后生效
docker --version
docker compose version
```

Expected: `Docker version 26+`, `Docker Compose version v2+`

- [ ] **Step 2: 上传项目到 VPS**

```bash
# 本机执行（将整个 stock-tool 目录打包上传）
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' \
  stock-tool/ user@YOUR_VPS_IP:~/stock-tool/
```

- [ ] **Step 3: 在 VPS 上配置 .env**

```bash
# VPS 上执行
cd ~/stock-tool
cp .env.example .env
nano .env   # 填写真实配置
```

- [ ] **Step 4: 首次启动（HTTP 模式，获取 SSL 证书）**

```bash
# VPS 上执行（HTTP nginx.conf）
docker compose up -d --build
```

- [ ] **Step 5: 申请 Let's Encrypt 证书**

```bash
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your@email.com \
  --agree-tos \
  --no-eff-email \
  -d YOUR_DOMAIN
```

Expected: `Successfully received certificate.`

- [ ] **Step 6: 切换到 HTTPS 配置**

```bash
# 更新 nginx-ssl.conf 中的 YOUR_DOMAIN 为实际域名
# 然后用 prod 覆盖启动
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- [ ] **Step 7: 验证 HTTPS**

```bash
curl https://YOUR_DOMAIN/api/health
```

Expected: `{"status":"ok"}`

在手机浏览器访问 `https://YOUR_DOMAIN`，确认 HTTPS 锁标正常，登录流程正常。

- [ ] **Step 8: 最终 Commit**

```bash
git add .
git commit -m "feat: VPS deployment with HTTPS verified"
```

---

## 部署后维护

**查看日志：**
```bash
docker compose logs -f backend   # 后端日志（含扫描任务）
docker compose logs -f nginx      # nginx 访问日志
```

**手动触发扫描（不等定时任务）：**
```bash
# 获取 token
TOKEN=$(curl -s -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"YOUR_PASSWORD"}' | jq -r .access_token)

# 触发扫描
curl -X POST http://localhost/api/scanner/trigger \
  -H "Authorization: Bearer $TOKEN"
```

**更新应用：**
```bash
# 拉取最新代码后
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
