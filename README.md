# 股票投资辅助工具

一个智能的个人股票和外汇投资助手，帮助你发现投资机会、监控自选标的异常信号，并通过邮件和 Web 通知及时提醒。

## 核心特性

### 📊 智能信号生成
- **短期信号**（日线/小时线）：基于 EMA、RSI、MACD、成交量等指标，回答"现在进场时机好不好？"
- **长期信号**（日线/周线）：基于 EMA 金叉/死叉、周线 RSI 等，回答"大方向是涨还是跌？"
- **统一评分系统**：-4 分（强烈看跌）到 +4 分（强烈看涨）
- **中文结论**：用户只看投资建议，无需理解技术指标细节

### 🔍 机会发现
- 自动扫描标普 500 成分股 + 20 个主要外汇对
- 按信号强度排序，快速识别投资机会
- 实时价格和涨跌幅展示

### 📱 自选监控
- 添加关注的品种到自选列表
- 异常信号实时高亮提醒
- 支持价格预警和信号变动通知

### 🔔 智能通知
- **邮件通知**：关键信号变化及时发送
- **Web Push**：浏览器桌面提醒
- **通知历史**：记录所有提醒记录

### 🤖 深度分析（可选）
- 集成 Claude AI，生成 200 字中文投资分析
- 按需调用，帮助理解市场动态

## 项目架构

```
stock-tool/
├── backend/                     # Python FastAPI 后端
│   ├── routers/                # API 路由
│   │   ├── auth.py            # 用户认证
│   │   ├── watchlist.py       # 自选管理
│   │   ├── scanner.py         # 机会扫描
│   │   ├── alerts.py          # 通知管理
│   │   └── analysis.py        # 品种分析
│   ├── services/              # 业务逻辑
│   │   ├── data_fetcher.py    # yfinance 行情获取
│   │   ├── indicator_engine.py # 技术指标计算
│   │   ├── signal_engine.py   # 信号评分规则引擎
│   │   ├── scanner_service.py # 批量扫描服务
│   │   ├── notifier.py        # 邮件通知
│   │   └── scheduler.py       # 定时任务
│   ├── data/
│   │   └── universe.py        # 资产池（S&P500 + FX）
│   ├── tests/                 # 单元测试
│   ├── main.py               # FastAPI 入口
│   ├── config.py             # 配置管理
│   ├── database.py           # SQLite 操作
│   └── models.py             # 数据模型
└── docs/                      # 设计文档
    ├── specs/                # 项目规格说明
    └── plans/                # 实现计划
```

## 技术栈

| 层级 | 技术 |
|-----|------|
| **后端** | Python 3.11+ / FastAPI |
| **前端** | Next.js + Tailwind CSS（待实现） |
| **数据库** | SQLite（本地单用户） |
| **行情数据** | yfinance（美股 + 外汇，15分钟延迟） |
| **指标计算** | pandas-ta |
| **定时任务** | APScheduler |
| **通知** | SMTP 邮件 + Web Push |
| **AI 分析** | Claude API（可选） |
| **部署** | Docker Compose + nginx |

## 快速开始

### 环境要求
- Python 3.11+
- pip 或 conda

### 后端安装

```bash
# 进入后端目录
cd stock-tool/backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 编辑 .env 文件，配置邮件服务、Claude API 密钥等
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# CLAUDE_API_KEY=sk-...

# 初始化数据库
python main.py  # 首次运行时自动初始化

# 开发模式启动（支持热重载）
uvicorn main:app --reload --port 8000
```

访问 API 文档：http://localhost:8000/docs

### 前端安装（待实现）

```bash
cd stock-tool/frontend

npm install
npm run dev  # 开发模式，访问 http://localhost:3000
```

## API 主要端点

### 认证
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出

### 自选管理
- `GET /watchlist` - 获取自选列表
- `POST /watchlist` - 添加自选品种
- `DELETE /watchlist/{ticker}` - 删除自选品种

### 机会扫描
- `GET /scanner/results` - 获取最新扫描结果
- `POST /scanner/trigger` - 手动触发扫描

### 通知管理
- `GET /alerts/price` - 获取价格提醒
- `POST /alerts/price` - 创建价格提醒
- `GET /alerts/signal` - 获取信号提醒
- `POST /alerts/signal` - 创建信号提醒
- `GET /alerts/history` - 获取通知历史

### 品种分析
- `GET /analysis/{ticker}` - 获取品种信号分析
- `POST /analysis/{ticker}/deep` - 获取 AI 深度分析

## 核心功能说明

### 信号评分系统

| 分值范围 | 信号标签 | 含义 |
|---------|---------|------|
| +3 ~ +4 | 🟢 强烈看涨 | 多个强势买入信号，短期买点明确 |
| +1 ~ +2 | 🟢 看涨信号 | 偏向上升，可考虑布局 |
| 0 | 🟡 中性观望 | 信号混乱，建议暂观望 |
| -1 ~ -2 | 🔴 看跌信号 | 偏向下降，谨慎操作 |
| -3 ~ -4 | 🔴 强烈看跌 | 多个卖出信号，短期风险大 |

### 技术指标

**短期指标（日线 + 小时线）**
- EMA (20/50)：趋势方向
- RSI (14)：超买超卖
- MACD：动能指标
- 成交量：资金参与度

**长期指标（日线 + 周线）**
- EMA (50/200)：金叉/死叉
- RSI (周线)：长期强度
- 趋势方向判断

## 支持的资产

### 美股
- 标普 500 成分股（约 500 种）

### 外汇（主要对 + 交叉盘，约 20 对）
- EUR/USD、GBP/USD、USD/JPY、USD/CHF
- AUD/USD、USD/CAD、NZD/USD 等

## 测试

```bash
# 进入后端目录
cd stock-tool/backend

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_indicator_engine.py -v

# 查看覆盖率
pytest --cov=. tests/
```

## 配置文件

参考 `backend/.env.example`：

```env
# 数据库
DATABASE_URL=sqlite:///./stock_tool.db

# JWT 认证
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SMTP 邮件
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=your-email@gmail.com

# Claude AI（可选）
CLAUDE_API_KEY=sk-...

# 定时扫描
SCAN_INTERVAL_MINUTES=60  # 每小时扫描一次

# 前端 URL
FRONTEND_URL=http://localhost:3000
```

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t stock-tool-backend ./backend

# 运行容器
docker run -p 8000:8000 -e DATABASE_URL=sqlite:///./stock_tool.db stock-tool-backend

# 使用 Docker Compose
docker-compose up -d
```

### 生产部署

项目配有 Dockerfile 和 docker-compose.yml，可直接在 VPS 上部署。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 注意事项

⚠️ **重要提示**
- 此工具仅供参考，不构成投资建议
- 市场风险，入市需谨慎
- yfinance 数据有 15 分钟左右的延迟
- 建议与其他分析工具结合使用
- 个人资产管理工具，请妥善保管 API 密钥

## 许可证

MIT License

---

**项目状态**：开发中 🚀  
**前端**：待实现  
**后端**：核心功能已完成
