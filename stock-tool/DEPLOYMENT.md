# 部署手册

本文档涵盖两个场景：**本地 Docker 集成验证**（先在自己机器上跑通整个 stack）和 **VPS 远程部署**（带 HTTPS 的生产环境）。

> 阅读前提：Plan 3 Task 1-4 已生成的文件已在仓库中：`backend/Dockerfile`、`frontend/Dockerfile`、`nginx/nginx.conf`、`nginx/nginx-ssl.conf`、`docker-compose.yml`、`docker-compose.prod.yml`、`.env.example`。

---

## 一、本地 Docker 集成验证（Task 5）

**目的：** 在没有云资源的情况下，在本机用 Docker 跑通 backend + frontend + nginx 全栈，确保镜像能构建、容器能互通、HTTP API 工作正常。

### 前置条件

- 已安装 Docker Desktop（Windows / macOS）或 Docker Engine + Compose v2（Linux）
- 终端能执行 `docker --version` 和 `docker compose version`

### 步骤

#### 1. 准备 `.env`

```bash
cd stock-tool
cp .env.example .env
```

编辑 `.env`，至少填写：

```env
APP_PASSWORD=你自己的强密码
SECRET_KEY=用以下命令生成的64字符随机串
```

生成 `SECRET_KEY`（PowerShell）：

```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

或（bash / mac / linux）：

```bash
openssl rand -hex 32
```

SMTP / Claude API 可留空——邮件通知和深度分析功能会静默跳过，不影响其他功能。

#### 2. 构建并启动容器

```bash
cd stock-tool
docker compose up --build -d
```

首次构建大约 3-5 分钟（前端 `npm ci` + `npm run build` 占大头）。

#### 3. 检查容器状态

```bash
docker compose ps
```

预期输出三个服务状态均为 `Up`（或 `running`）：

```
NAME                   STATUS
stock-tool-backend-1   Up
stock-tool-frontend-1  Up
stock-tool-nginx-1     Up
```

如有 `Restarting` 或 `Exited` 状态，看日志定位：

```bash
docker compose logs backend     # 后端启动失败
docker compose logs frontend    # 前端构建产物缺失
docker compose logs nginx       # 上游服务名解析失败
```

#### 4. 接口烟雾测试

```bash
# 健康检查
curl http://localhost/api/health
# 预期：{"status":"ok"}

# 登录（替换 YOUR_PASSWORD 为 .env 里设的值）
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"YOUR_PASSWORD"}'
# 预期：{"access_token":"eyJ...","token_type":"bearer"}
```

如果登录返回 401，检查 `.env` 里 `APP_PASSWORD` 是否设对、容器是否重启过（修改 `.env` 后需 `docker compose up -d` 重启加载新值）。

#### 5. 浏览器测试

访问 `http://localhost` → 自动重定向到 `/login` → 输 `APP_PASSWORD` → 进入 `/dashboard`。

手机同网测试：在本机 PowerShell 跑 `ipconfig` 看 IPv4 地址（如 `192.168.1.5`），手机浏览器访问 `http://192.168.1.5`，登录页应正常。

#### 6. 验证扫描

进 `/opportunities` → 点「立即扫描」→ 等 3-5 分钟 → 结果列表自动刷新（Bug fix PR #4 引入的轮询机制会在扫描完成时自动拉新数据）。

如长时间无结果，看后端日志：

```bash
docker compose logs -f backend | grep -i "scanner\|error\|fail"
```

常见错误：yfinance HTTP 429（限流）→ 等几分钟再试，或换时段。

#### 7. 关闭

```bash
docker compose down              # 停止并移除容器，保留数据卷
docker compose down -v           # 同时清空数据库（虚拟交易记录全部消失）
```

---

## 二、VPS 远程部署（Task 6）

**目的：** 在公网 VPS 上运行完整 stack，绑定自有域名，启用 HTTPS。

### 前置条件

- 一台 VPS（推荐 Ubuntu 22.04+，2GB RAM 以上）
- 已绑定的域名（如 `invest.example.com`），DNS A 记录已指向 VPS IP
- VPS 防火墙开放 80 和 443 端口

### 步骤

#### 1. VPS 安装 Docker

```bash
# 在 VPS 上执行
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 退出 SSH 重新登录使 docker 组权限生效
docker --version              # 应输出 Docker version 26.x+
docker compose version        # 应输出 Docker Compose version v2.x+
```

#### 2. 上传项目到 VPS

**本机**（Windows PowerShell 用 WSL 或 Git Bash 执行 rsync；或用 scp 替代）：

```bash
rsync -avz \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude 'venv' \
  --exclude 'data.db' \
  --exclude '.next' \
  stock-tool/ user@YOUR_VPS_IP:~/stock-tool/
```

或者直接在 VPS 上 git clone（如果仓库公开或已配 SSH key）：

```bash
# 在 VPS 上执行
cd ~
git clone https://github.com/BKwind-li/bonus.git
cd bonus/stock-tool
```

#### 3. 配置 `.env`

**在 VPS 上**：

```bash
cd ~/stock-tool
cp .env.example .env
nano .env
```

填好 `APP_PASSWORD`、`SECRET_KEY`、SMTP（生产环境强烈建议配上）、`CLAUDE_API_KEY`（可选）。**SECRET_KEY 必须重新生成，不要复用本地的**。

#### 4. 修改 nginx-ssl.conf 中的域名占位符

```bash
# 把 4 处 YOUR_DOMAIN 替换为实际域名
sed -i 's/YOUR_DOMAIN/invest.example.com/g' nginx/nginx-ssl.conf
```

(把 `invest.example.com` 替换为你自己的域名)

确认替换无误：

```bash
grep -n "YOUR_DOMAIN\|server_name\|ssl_certificate" nginx/nginx-ssl.conf
```

应该看不到任何 `YOUR_DOMAIN` 残留。

#### 5. 首次启动（HTTP 模式，用于 Certbot 验证）

```bash
docker compose up -d --build
```

确认 nginx 监听 80：

```bash
docker compose ps
curl http://invest.example.com/api/health
# 预期：{"status":"ok"}
```

#### 6. 申请 Let's Encrypt 证书

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your@email.com \
  --agree-tos \
  --no-eff-email \
  -d invest.example.com
```

预期最后看到：

```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/invest.example.com/fullchain.pem
```

如果失败，常见原因：
- DNS A 记录未指向 VPS（`dig +short invest.example.com` 看返回 IP）
- 防火墙阻断 80（`sudo ufw status` 检查）
- 域名未生效（DNS 传播可能需要几分钟到几小时）

#### 7. 切换到 HTTPS 配置启动

```bash
# 用 prod overlay 启动（挂载 SSL 证书 + nginx-ssl.conf + 监听 443）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

#### 8. 验证 HTTPS

```bash
curl https://invest.example.com/api/health
# 预期：{"status":"ok"}

# 测试 HTTP → HTTPS 重定向
curl -I http://invest.example.com
# 预期看到 301 Location: https://...
```

浏览器访问 `https://invest.example.com`：
- 锁标正常（绿/灰色）
- 登录后能进入 dashboard
- 手机浏览器同样可访问

#### 9. 提交部署完成的状态

如果你修改了 `nginx-ssl.conf`（替换了域名）并希望保留这次配置，可以在本地另开分支 commit。**不要把替换后的实际域名 commit 回主分支**——主分支应保持 `YOUR_DOMAIN` 占位符。

---

## 三、部署后维护

### 查看日志

```bash
docker compose logs -f backend            # 后端 + 扫描调度
docker compose logs -f frontend           # 前端（Next.js 日志）
docker compose logs -f nginx              # 反向代理日志（含访问 IP）
docker compose logs --tail=100 backend    # 最近 100 行
```

### 重启某个服务

```bash
docker compose restart backend
```

### 应用代码更新（pull + 重建）

```bash
cd ~/stock-tool   # 或 ~/bonus/stock-tool
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Let's Encrypt 自动续期

`docker-compose.prod.yml` 里的 `certbot` 服务每 12 小时自动检查并续期。手动确认续期状态：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certificates
```

### 备份虚拟交易数据

```bash
# 在 VPS 上执行
docker run --rm -v stock-tool_backend_data:/data -v $PWD:/backup alpine \
  sh -c "cp /data/data.db /backup/data-$(date +%Y%m%d).db"
```

### 修改密码

编辑 `.env` 里 `APP_PASSWORD` → `docker compose restart backend` → 浏览器需要重新登录。

### 清空虚拟交易记录（重置账户）

```bash
docker compose down
docker volume rm stock-tool_backend_data
docker compose up -d
```

---

## 四、故障排查

| 现象 | 排查方向 |
|---|---|
| `docker compose up` 卡在 frontend 构建 | 网络慢导致 `npm ci` 超时；用国内镜像源（`.npmrc` 配置 registry） |
| nginx 502 Bad Gateway | backend 或 frontend 容器没起来；`docker compose logs <service>` 看错误 |
| 登录后立即跳回 login | 浏览器 cookie 没写入；F12 → Application → Cookies 看 `stock_tool_token` 是否存在；HTTPS 部署下 cookie 需要 `Secure` 属性（如有问题先用 HTTP 测试逻辑） |
| `/opportunities` 一直空 | 还没扫描过；点「立即扫描」等 3-5 分钟；后端日志看是否 yfinance 限流 |
| Certbot 续期失败 | 防火墙是否放行 80；`docker compose -f ... -f ... logs certbot` 看具体错误 |
| 容器内存爆炸（OOM） | VPS 内存不足；最低 2GB，前端构建峰值 1.5GB+；可加 swap：`sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |

如有其他问题，先看 `docker compose logs --tail=200`，错误信息一般会指向具体服务和行号。
