# 股票投资辅助工具 — Plan 2：前端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建响应式 Next.js Web 应用，包含仪表盘、机会发现、品种详情和提醒管理四个页面，支持手机浏览器访问。

**Architecture:** Next.js 15 App Router，Tailwind CSS 样式，Recharts 折线图，JWT token 存入 localStorage，API 调用后端 FastAPI（Plan 1）。所有页面服务端无需认证，认证在客户端中间件处理。

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts, clsx

**前置条件:** Plan 1（后端）已运行在 http://localhost:8000

---

## 文件结构

```
stock-tool/frontend/
├── app/
│   ├── layout.tsx             # 根布局，全局字体/样式
│   ├── page.tsx               # / → 重定向到 /dashboard
│   ├── login/page.tsx         # 登录页
│   ├── dashboard/page.tsx     # 仪表盘（自选列表 + 摘要）
│   ├── opportunities/page.tsx # 机会发现（扫描结果列表）
│   ├── symbol/[ticker]/
│   │   └── page.tsx           # 品种详情页
│   └── alerts/page.tsx        # 提醒管理页
├── components/
│   ├── SignalBadge.tsx         # 信号标签（颜色 + 文字）
│   ├── SignalCard.tsx          # 卡片（一览用）
│   ├── AlertBanner.tsx         # 顶部警告横幅
│   ├── PriceChart.tsx          # 30天折线图
│   ├── FilterBar.tsx           # 筛选栏（市场/信号类型/排序）
│   ├── SignalDetail.tsx        # 短期/长期信号详情块
│   └── NavBar.tsx              # 顶部导航栏
├── lib/
│   ├── types.ts                # TypeScript 接口定义
│   ├── api.ts                  # API 客户端（封装 fetch）
│   └── auth.ts                 # Token 存取
├── public/
│   └── sw.js                   # Service Worker（Web Push）
├── middleware.ts                # Next.js 路由守卫
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## Task 1: 项目初始化

**Files:**
- Create: `stock-tool/frontend/` (整个目录)

- [ ] **Step 1: 初始化 Next.js 项目**

```bash
cd stock-tool
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*"
cd frontend
```

- [ ] **Step 2: 安装额外依赖**

```bash
npm install recharts clsx
npm install -D @types/node
```

- [ ] **Step 3: 写 lib/types.ts**

```typescript
export interface IndicatorResult {
  name: string
  raw_value: string
  description: string
  contribution: number
}

export interface SignalScore {
  score: number
  label: string
  color: "green" | "yellow" | "red"
  indicators: IndicatorResult[]
}

export interface SignalResult {
  ticker: string
  name: string
  sector: string
  market: "stock" | "forex"
  price: number
  change_pct: number
  short_term: SignalScore
  long_term: SignalScore
  scanned_at: string
  // DB fields (scanner results)
  short_score?: number
  short_label?: string
  short_color?: string
  long_score?: number
  long_label?: string
  long_color?: string
  short_indicators?: IndicatorResult[]
  long_indicators?: IndicatorResult[]
}

export interface WatchlistItem {
  ticker: string
  name: string
  market: string
  sector: string
  added_at?: string
}

export interface PriceAlert {
  id: number
  ticker: string
  condition: "above" | "below"
  threshold: number
  active: boolean
  created_at: string
}

export interface SignalAlert {
  id: number
  ticker: string
  condition: "any_change" | "strong_only" | "rsi_extreme"
  active: boolean
  created_at: string
}

export interface AlertHistoryItem {
  id: number
  ticker: string
  alert_type: string
  message: string
  triggered_at: string
  read: boolean
}
```

- [ ] **Step 4: 写 lib/auth.ts**

```typescript
const TOKEN_KEY = "stock_tool_token"

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function isLoggedIn(): boolean {
  return !!getToken()
}
```

- [ ] **Step 5: 写 lib/api.ts**

```typescript
import { getToken } from "./auth"

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    window.location.href = "/login"
    throw new Error("Unauthorized")
  }
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export const api = {
  login: (password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST", body: JSON.stringify({ password }),
    }),
  getWatchlist: () => request<any[]>("/watchlist"),
  addToWatchlist: (item: { ticker: string; name: string; market: string; sector: string }) =>
    request("/watchlist", { method: "POST", body: JSON.stringify(item) }),
  removeFromWatchlist: (ticker: string) =>
    request(`/watchlist/${ticker}`, { method: "DELETE" }),
  getScanResults: (params?: { market?: string; signal_type?: string; sort_by?: string }) => {
    const q = new URLSearchParams(params as any).toString()
    return request<any[]>(`/scanner/results${q ? "?" + q : ""}`)
  },
  triggerScan: () => request("/scanner/trigger", { method: "POST" }),
  getLastScanTime: () => request<{ last_scan: string | null }>("/scanner/last-scan-time"),
  getAnalysis: (ticker: string) => request<{ signal: any; price_history: number[] }>(`/analysis/${ticker}`),
  getDeepAnalysis: (ticker: string) => request<{ analysis: string }>(`/analysis/${ticker}/deep`, { method: "POST" }),
  getPriceAlerts: () => request<any[]>("/alerts/price"),
  createPriceAlert: (data: { ticker: string; condition: string; threshold: number }) =>
    request("/alerts/price", { method: "POST", body: JSON.stringify(data) }),
  deletePriceAlert: (id: number) => request(`/alerts/price/${id}`, { method: "DELETE" }),
  getSignalAlerts: () => request<any[]>("/alerts/signal"),
  createSignalAlert: (data: { ticker: string; condition: string }) =>
    request("/alerts/signal", { method: "POST", body: JSON.stringify(data) }),
  deleteSignalAlert: (id: number) => request(`/alerts/signal/${id}`, { method: "DELETE" }),
  getAlertHistory: () => request<any[]>("/alerts/history"),
  getUnreadCount: () => request<{ count: number }>("/alerts/unread-count"),
  markAlertRead: (id: number) => request(`/alerts/history/${id}/read`, { method: "POST" }),
}
```

- [ ] **Step 6: 写 middleware.ts（路由守卫）**

```typescript
import { NextRequest, NextResponse } from "next/server"

const PUBLIC_PATHS = ["/login"]

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next()

  // Token is in localStorage (client-side), middleware can only read cookies.
  // We use a cookie mirror for SSR guard.
  const token = req.cookies.get("stock_tool_token")?.value
  if (!token) {
    return NextResponse.redirect(new URL("/login", req.url))
  }
  return NextResponse.next()
}

export const config = { matcher: ["/((?!_next|favicon.ico|sw.js).*)"] }
```

> Note: 登录成功后同时写 `document.cookie = "stock_tool_token=<token>;path=/"` 确保中间件可读取。

- [ ] **Step 7: 配置 next.config.ts**

```typescript
import type { NextConfig } from "next"

const config: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ]
  },
}

export default config
```

- [ ] **Step 8: 验证项目启动**

```bash
npm run dev
```

Expected: 访问 http://localhost:3000 正常，因 cookie 不存在，重定向到 /login（404 暂时可接受，下一步实现）。

- [ ] **Step 9: Commit**

```bash
git add stock-tool/frontend
git commit -m "feat: Next.js frontend scaffolding with types, API client, and auth"
```

---

## Task 2: 共享组件

**Files:**
- Create: `stock-tool/frontend/components/SignalBadge.tsx`
- Create: `stock-tool/frontend/components/SignalCard.tsx`
- Create: `stock-tool/frontend/components/NavBar.tsx`
- Create: `stock-tool/frontend/components/AlertBanner.tsx`

- [ ] **Step 1: 写 components/SignalBadge.tsx**

```tsx
import clsx from "clsx"

interface Props {
  label: string
  color: "green" | "yellow" | "red"
  score?: number
  size?: "sm" | "md"
}

const colorMap = {
  green: "bg-green-950 text-green-400 border border-green-800",
  yellow: "bg-yellow-950 text-yellow-400 border border-yellow-800",
  red: "bg-red-950 text-red-400 border border-red-800",
}

export default function SignalBadge({ label, color, score, size = "sm" }: Props) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1 rounded-full font-medium",
      size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
      colorMap[color]
    )}>
      {color === "green" ? "🟢" : color === "yellow" ? "🟡" : "🔴"}
      {label}
      {score !== undefined && <span className="opacity-70">({score > 0 ? "+" : ""}{score})</span>}
    </span>
  )
}
```

- [ ] **Step 2: 写 components/SignalCard.tsx**

```tsx
import Link from "next/link"
import clsx from "clsx"
import SignalBadge from "./SignalBadge"

interface Props {
  ticker: string
  name: string
  sector: string
  market: string
  price: number
  change_pct: number
  short_label: string
  short_color: "green" | "yellow" | "red"
  short_score: number
  long_label: string
  long_color: "green" | "yellow" | "red"
  long_score: number
  summary?: string
  isAlert?: boolean
}

const borderColor = {
  green: "border-l-green-500",
  yellow: "border-l-yellow-500",
  red: "border-l-red-500",
}

export default function SignalCard({
  ticker, name, sector, market, price, change_pct,
  short_label, short_color, short_score,
  long_label, long_color, long_score,
  summary, isAlert,
}: Props) {
  const dominantColor = short_score >= 0 ? short_color : "red"
  return (
    <Link href={`/symbol/${ticker}`}>
      <div className={clsx(
        "flex items-start gap-3 p-4 rounded-lg border-l-4 cursor-pointer",
        "bg-zinc-900 hover:bg-zinc-800 transition-colors",
        borderColor[dominantColor],
        isAlert && "ring-2 ring-orange-500 animate-pulse",
      )}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <span className="font-bold text-white">{ticker}</span>
              <span className="text-zinc-400 text-sm ml-2">{name}</span>
            </div>
            <span className={clsx(
              "font-semibold tabular-nums text-sm",
              change_pct >= 0 ? "text-green-400" : "text-red-400"
            )}>
              {price} {change_pct >= 0 ? "↑" : "↓"}{Math.abs(change_pct).toFixed(2)}%
            </span>
          </div>
          <div className="text-zinc-500 text-xs mt-0.5">{sector} · {market === "forex" ? "外汇" : "美股"}</div>
          <div className="flex gap-2 mt-2 flex-wrap">
            <SignalBadge label={`短期 ${short_label}`} color={short_color} score={short_score} />
            <SignalBadge label={`长期 ${long_label}`} color={long_color} score={long_score} />
          </div>
          {summary && <p className="text-zinc-300 text-sm mt-2 line-clamp-1">{summary}</p>}
        </div>
      </div>
    </Link>
  )
}
```

- [ ] **Step 3: 写 components/NavBar.tsx**

```tsx
"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import clsx from "clsx"
import { useEffect, useState } from "react"
import { api } from "@/lib/api"

const links = [
  { href: "/dashboard", label: "仪表盘" },
  { href: "/opportunities", label: "机会发现" },
  { href: "/alerts", label: "提醒" },
]

export default function NavBar() {
  const pathname = usePathname()
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    api.getUnreadCount().then((r) => setUnread(r.count)).catch(() => {})
  }, [pathname])

  return (
    <nav className="sticky top-0 z-50 bg-zinc-950 border-b border-zinc-800 px-4 py-3">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <span className="font-bold text-white text-lg">📈 投资助手</span>
        <div className="flex gap-1">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className={clsx(
              "px-3 py-1.5 rounded text-sm font-medium transition-colors relative",
              pathname.startsWith(l.href) ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"
            )}>
              {l.label}
              {l.href === "/alerts" && unread > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {unread}
                </span>
              )}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}
```

- [ ] **Step 4: 写 components/AlertBanner.tsx**

```tsx
"use client"
interface Props {
  alerts: Array<{ ticker: string; message: string }>
  onDismiss: () => void
}

export default function AlertBanner({ alerts, onDismiss }: Props) {
  if (alerts.length === 0) return null
  return (
    <div className="bg-orange-950 border border-orange-700 text-orange-300 px-4 py-3 rounded-lg mb-4 flex items-start justify-between gap-3">
      <div>
        <span className="font-semibold">⚠️ 异常信号</span>
        <ul className="mt-1 space-y-0.5">
          {alerts.map((a, i) => (
            <li key={i} className="text-sm">{a.ticker}: {a.message}</li>
          ))}
        </ul>
      </div>
      <button onClick={onDismiss} className="text-orange-400 hover:text-white text-xl leading-none">×</button>
    </div>
  )
}
```

- [ ] **Step 5: 更新 app/layout.tsx**

```tsx
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import NavBar from "@/components/NavBar"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "投资助手",
  description: "个人股票与外汇投资辅助工具",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body className={`${inter.className} bg-zinc-950 text-white min-h-screen`}>
        <NavBar />
        <main className="max-w-4xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  )
}
```

- [ ] **Step 6: 验证组件无 TypeScript 错误**

```bash
npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 7: Commit**

```bash
git add stock-tool/frontend/components stock-tool/frontend/app/layout.tsx
git commit -m "feat: shared UI components (SignalBadge, SignalCard, NavBar, AlertBanner)"
```

---

## Task 3: 登录页

**Files:**
- Create: `stock-tool/frontend/app/login/page.tsx`

- [ ] **Step 1: 写 app/login/page.tsx**

```tsx
"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"
import { saveToken } from "@/lib/auth"

export default function LoginPage() {
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")
    try {
      const { access_token } = await api.login(password)
      saveToken(access_token)
      // Also write cookie for middleware
      document.cookie = `stock_tool_token=${access_token};path=/;max-age=2592000`
      router.push("/dashboard")
    } catch {
      setError("密码错误，请重试")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center mb-8">📈 投资助手</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-zinc-400 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-zinc-500"
              placeholder="输入访问密码"
              autoFocus
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-zinc-700 hover:bg-zinc-600 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? "登录中..." : "进入"}
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 写 app/page.tsx（重定向）**

```tsx
import { redirect } from "next/navigation"
export default function Home() { redirect("/dashboard") }
```

- [ ] **Step 3: 启动后端，手动测试登录**

```bash
# 确保后端运行中
# 访问 http://localhost:3000/login
# 输入 APP_PASSWORD 中配置的密码
# 验证成功后跳转到 /dashboard
```

Expected: 登录成功跳转，密码错误显示错误提示。

- [ ] **Step 4: Commit**

```bash
git add stock-tool/frontend/app/login stock-tool/frontend/app/page.tsx
git commit -m "feat: login page with JWT token and cookie"
```

---

## Task 4: 仪表盘页面

**Files:**
- Create: `stock-tool/frontend/app/dashboard/page.tsx`

- [ ] **Step 1: 写 app/dashboard/page.tsx**

```tsx
"use client"
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import SignalCard from "@/components/SignalCard"
import AlertBanner from "@/components/AlertBanner"
import Link from "next/link"

function toSignalColor(color: string): "green" | "yellow" | "red" {
  if (color === "green") return "green"
  if (color === "red") return "red"
  return "yellow"
}

export default function DashboardPage() {
  const [watchlist, setWatchlist] = useState<any[]>([])
  const [scanResults, setScanResults] = useState<Record<string, any>>({})
  const [alertItems, setAlertItems] = useState<any[]>([])
  const [showBanner, setShowBanner] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const [wl, results, history] = await Promise.all([
        api.getWatchlist(),
        api.getScanResults(),
        api.getAlertHistory(),
      ])
      setWatchlist(wl)
      const map: Record<string, any> = {}
      for (const r of results) map[r.ticker] = r
      setScanResults(map)
      const unread = history.filter((h: any) => !h.read)
      setAlertItems(unread.slice(0, 5))
      setLoading(false)
    }
    load()
  }, [])

  const alertTickers = new Set(alertItems.map((a: any) => a.ticker))

  const bullishCount = Object.values(scanResults).filter((r: any) => r.short_score > 0).length
  const bearishCount = Object.values(scanResults).filter((r: any) => r.short_score < 0).length

  if (loading) return <div className="text-zinc-400 text-center py-20">加载中...</div>

  return (
    <div>
      {showBanner && alertItems.length > 0 && (
        <AlertBanner
          alerts={alertItems.map((a: any) => ({ ticker: a.ticker, message: a.message }))}
          onDismiss={() => setShowBanner(false)}
        />
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">仪表盘</h1>
        <div className="flex gap-3 text-sm text-zinc-400">
          <span className="text-green-400">🟢 {bullishCount} 看涨</span>
          <span className="text-red-400">🔴 {bearishCount} 看跌</span>
          <Link href="/opportunities" className="text-zinc-300 hover:text-white underline">查看机会发现 →</Link>
        </div>
      </div>

      {watchlist.length === 0 ? (
        <div className="text-center py-16 text-zinc-500">
          <p className="text-4xl mb-3">📋</p>
          <p>自选列表为空</p>
          <p className="text-sm mt-2">前往<Link href="/opportunities" className="text-zinc-300 underline ml-1">机会发现</Link>添加品种</p>
        </div>
      ) : (
        <div className="space-y-3">
          {watchlist.map((item: any) => {
            const scan = scanResults[item.ticker]
            if (!scan) return (
              <div key={item.ticker} className="p-4 bg-zinc-900 rounded-lg text-zinc-500 text-sm">
                {item.ticker} — 暂无扫描数据
              </div>
            )
            return (
              <SignalCard
                key={item.ticker}
                ticker={scan.ticker}
                name={scan.name}
                sector={scan.sector}
                market={scan.market}
                price={scan.price}
                change_pct={scan.change_pct}
                short_label={scan.short_label}
                short_color={toSignalColor(scan.short_color)}
                short_score={scan.short_score}
                long_label={scan.long_label}
                long_color={toSignalColor(scan.long_color)}
                long_score={scan.long_score}
                isAlert={alertTickers.has(scan.ticker)}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 在浏览器中验证仪表盘**

```
访问 http://localhost:3000/dashboard
预期：
- 若自选列表为空，显示空状态提示
- 顶部统计摘要显示看涨/看跌数量
- 有告警时显示橙色横幅
```

- [ ] **Step 3: Commit**

```bash
git add stock-tool/frontend/app/dashboard
git commit -m "feat: dashboard page with watchlist and alert banner"
```

---

## Task 5: 机会发现页面

**Files:**
- Create: `stock-tool/frontend/app/opportunities/page.tsx`
- Create: `stock-tool/frontend/components/FilterBar.tsx`

- [ ] **Step 1: 写 components/FilterBar.tsx**

```tsx
"use client"
interface Props {
  market: string
  signalType: string
  sortBy: string
  onChange: (key: string, value: string) => void
}

const filterGroups = [
  {
    key: "market",
    options: [
      { value: "all", label: "全部" },
      { value: "stock", label: "美股" },
      { value: "forex", label: "外汇" },
    ],
  },
  {
    key: "signalType",
    options: [
      { value: "all", label: "全部信号" },
      { value: "bullish", label: "🟢 看涨" },
      { value: "bearish", label: "🔴 看跌" },
    ],
  },
  {
    key: "sortBy",
    options: [
      { value: "short", label: "短期强度" },
      { value: "long", label: "长期强度" },
    ],
  },
]

export default function FilterBar({ market, signalType, sortBy, onChange }: Props) {
  const values: Record<string, string> = { market, signalType, sortBy }
  return (
    <div className="flex flex-wrap gap-3 mb-6">
      {filterGroups.map((group) => (
        <div key={group.key} className="flex rounded-lg bg-zinc-800 overflow-hidden">
          {group.options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onChange(group.key, opt.value)}
              className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                values[group.key] === opt.value
                  ? "bg-zinc-600 text-white"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: 写 app/opportunities/page.tsx**

```tsx
"use client"
import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import SignalCard from "@/components/SignalCard"
import FilterBar from "@/components/FilterBar"

function toColor(c: string): "green" | "yellow" | "red" {
  return c === "green" ? "green" : c === "red" ? "red" : "yellow"
}

export default function OpportunitiesPage() {
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [lastScan, setLastScan] = useState<string | null>(null)
  const [filters, setFilters] = useState({ market: "all", signalType: "all", sortBy: "short" })

  const loadResults = useCallback(async () => {
    setLoading(true)
    const [results, scanTime] = await Promise.all([
      api.getScanResults({
        market: filters.market === "all" ? undefined : filters.market,
        signal_type: filters.signalType === "all" ? undefined : filters.signalType,
        sort_by: filters.sortBy,
      }),
      api.getLastScanTime(),
    ])
    setResults(results)
    setLastScan(scanTime.last_scan)
    setLoading(false)
  }, [filters])

  useEffect(() => { loadResults() }, [loadResults])

  async function handleTriggerScan() {
    setScanning(true)
    await api.triggerScan()
    setTimeout(() => { setScanning(false); loadResults() }, 3000)
  }

  function handleFilterChange(key: string, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">机会发现</h1>
          {lastScan && (
            <p className="text-xs text-zinc-500 mt-0.5">
              上次扫描：{new Date(lastScan).toLocaleString("zh-CN")}
            </p>
          )}
        </div>
        <button
          onClick={handleTriggerScan}
          disabled={scanning}
          className="bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {scanning ? "扫描中..." : "🔄 立即扫描"}
        </button>
      </div>

      <FilterBar {...filters} onChange={handleFilterChange} />

      {loading ? (
        <div className="text-zinc-400 text-center py-20">加载中...</div>
      ) : results.length === 0 ? (
        <div className="text-center py-16 text-zinc-500">
          <p className="text-4xl mb-3">🔍</p>
          <p>暂无扫描结果</p>
          <p className="text-sm mt-2">点击「立即扫描」开始分析</p>
        </div>
      ) : (
        <div className="space-y-3">
          {results.map((r: any) => (
            <SignalCard
              key={r.ticker}
              ticker={r.ticker}
              name={r.name}
              sector={r.sector}
              market={r.market}
              price={r.price}
              change_pct={r.change_pct}
              short_label={r.short_label}
              short_color={toColor(r.short_color)}
              short_score={r.short_score}
              long_label={r.long_label}
              long_color={toColor(r.long_color)}
              long_score={r.long_score}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 手动测试机会发现页**

```
访问 http://localhost:3000/opportunities
预期：
- 筛选栏正常切换
- 「立即扫描」触发后端扫描（需等待约30-60秒出现结果）
- 结果按信号强度排列
```

- [ ] **Step 4: Commit**

```bash
git add stock-tool/frontend/app/opportunities stock-tool/frontend/components/FilterBar.tsx
git commit -m "feat: opportunity discovery page with filter bar and scan trigger"
```

---

## Task 6: 品种详情页

**Files:**
- Create: `stock-tool/frontend/app/symbol/[ticker]/page.tsx`
- Create: `stock-tool/frontend/components/PriceChart.tsx`
- Create: `stock-tool/frontend/components/SignalDetail.tsx`

- [ ] **Step 1: 写 components/PriceChart.tsx**

```tsx
"use client"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface Props {
  prices: number[]
}

export default function PriceChart({ prices }: Props) {
  const data = prices.map((price, i) => ({ day: i + 1, price: Number(price.toFixed(4)) }))
  const min = Math.min(...prices) * 0.998
  const max = Math.max(...prices) * 1.002

  return (
    <div className="bg-zinc-900 rounded-lg p-4">
      <p className="text-xs text-zinc-500 mb-3">近30天价格走势</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={data}>
          <XAxis dataKey="day" hide />
          <YAxis domain={[min, max]} hide />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 6 }}
            labelFormatter={(v) => `第${v}天`}
            formatter={(v: number) => [v, "价格"]}
          />
          <Line
            type="monotone" dataKey="price" stroke="#22c55e"
            strokeWidth={2} dot={false} activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: 写 components/SignalDetail.tsx**

```tsx
import SignalBadge from "./SignalBadge"
import { SignalScore } from "@/lib/types"

interface Props {
  title: string
  signal: SignalScore
}

const contribColor = { 1: "text-green-400", "-1": "text-red-400" }

export default function SignalDetail({ title, signal }: Props) {
  return (
    <div className="bg-zinc-900 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-zinc-300">{title}</h3>
        <SignalBadge label={signal.label} color={signal.color} score={signal.score} size="md" />
      </div>
      <div className="space-y-2">
        {signal.indicators.map((ind) => (
          <div key={ind.name} className="flex items-start justify-between gap-3 text-sm">
            <div className="flex-1">
              <span className="text-zinc-400 font-medium">{ind.name}</span>
              <span className="text-zinc-500 text-xs ml-2">{ind.raw_value}</span>
              <p className="text-zinc-300 text-xs mt-0.5">{ind.description}</p>
            </div>
            <span className={contribColor[ind.contribution as 1 | -1] ?? "text-zinc-400"}>
              {ind.contribution > 0 ? "+1" : "-1"}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 写 app/symbol/[ticker]/page.tsx**

```tsx
"use client"
import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { api } from "@/lib/api"
import PriceChart from "@/components/PriceChart"
import SignalDetail from "@/components/SignalDetail"
import SignalBadge from "@/components/SignalBadge"

export default function SymbolPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [deepAnalysis, setDeepAnalysis] = useState("")
  const [deepLoading, setDeepLoading] = useState(false)
  const [inWatchlist, setInWatchlist] = useState(false)

  useEffect(() => {
    async function load() {
      const [analysis, watchlist] = await Promise.all([
        api.getAnalysis(ticker),
        api.getWatchlist(),
      ])
      setData(analysis)
      setInWatchlist(watchlist.some((w: any) => w.ticker === ticker))
      setLoading(false)
    }
    load()
  }, [ticker])

  async function handleDeepAnalysis() {
    setDeepLoading(true)
    try {
      const r = await api.getDeepAnalysis(ticker)
      setDeepAnalysis(r.analysis)
    } catch (e: any) {
      setDeepAnalysis("深度分析暂不可用（需配置 Claude API Key）")
    } finally {
      setDeepLoading(false)
    }
  }

  async function toggleWatchlist() {
    if (inWatchlist) {
      await api.removeFromWatchlist(ticker)
      setInWatchlist(false)
    } else {
      const s = data?.signal
      await api.addToWatchlist({
        ticker,
        name: s?.name ?? ticker,
        market: s?.market ?? "stock",
        sector: s?.sector ?? "未知",
      })
      setInWatchlist(true)
    }
  }

  if (loading) return <div className="text-zinc-400 text-center py-20">加载中...</div>
  if (!data) return <div className="text-zinc-400 text-center py-20">数据获取失败</div>

  const { signal, price_history } = data

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{ticker}</h1>
          <p className="text-zinc-400">{signal.name} · {signal.sector}</p>
          <p className="text-3xl font-bold mt-2">
            {signal.price}
            <span className={`text-lg ml-2 ${signal.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
              {signal.change_pct >= 0 ? "↑" : "↓"}{Math.abs(signal.change_pct).toFixed(2)}%
            </span>
          </p>
        </div>
        <button
          onClick={toggleWatchlist}
          className="bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-4 py-2 rounded-lg"
        >
          {inWatchlist ? "✓ 已自选" : "+ 加入自选"}
        </button>
      </div>

      <PriceChart prices={price_history} />

      <SignalDetail title="短期信号" signal={signal.short_term} />
      <SignalDetail title="长期信号" signal={signal.long_term} />

      <div>
        <button
          onClick={handleDeepAnalysis}
          disabled={deepLoading}
          className="w-full bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {deepLoading ? "分析中..." : "🤖 深度分析（Claude AI）"}
        </button>
        {deepAnalysis && (
          <div className="mt-3 p-4 bg-zinc-900 rounded-lg text-zinc-300 text-sm leading-relaxed">
            {deepAnalysis}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 手动测试详情页**

```
访问 http://localhost:3000/symbol/AAPL
预期：
- 显示价格和涨跌幅
- 30天折线图
- 短期/长期信号两个区块，各4个指标
- 「加入自选」按钮
- 点击「深度分析」（需配置 CLAUDE_API_KEY）
```

- [ ] **Step 5: Commit**

```bash
git add stock-tool/frontend/app/symbol stock-tool/frontend/components/PriceChart.tsx stock-tool/frontend/components/SignalDetail.tsx
git commit -m "feat: symbol detail page with price chart and signal breakdown"
```

---

## Task 7: 提醒管理页面

**Files:**
- Create: `stock-tool/frontend/app/alerts/page.tsx`

- [ ] **Step 1: 写 app/alerts/page.tsx**

```tsx
"use client"
import { useEffect, useState } from "react"
import { api } from "@/lib/api"

const CONDITION_LABELS: Record<string, string> = {
  above: "价格突破",
  below: "价格跌破",
  any_change: "信号跳变",
  strong_only: "强烈信号",
  rsi_extreme: "RSI极端值",
}

export default function AlertsPage() {
  const [tab, setTab] = useState<"price" | "signal" | "history">("history")
  const [priceAlerts, setPriceAlerts] = useState<any[]>([])
  const [signalAlerts, setSignalAlerts] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])
  const [form, setForm] = useState({ ticker: "", condition: "above", threshold: "", signalCondition: "any_change" })

  async function load() {
    const [pa, sa, hist] = await Promise.all([
      api.getPriceAlerts(), api.getSignalAlerts(), api.getAlertHistory(),
    ])
    setPriceAlerts(pa)
    setSignalAlerts(sa)
    setHistory(hist)
  }

  useEffect(() => { load() }, [])

  async function addPriceAlert() {
    if (!form.ticker || !form.threshold) return
    await api.createPriceAlert({
      ticker: form.ticker.toUpperCase(),
      condition: form.condition,
      threshold: Number(form.threshold),
    })
    setForm((p) => ({ ...p, ticker: "", threshold: "" }))
    load()
  }

  async function addSignalAlert() {
    if (!form.ticker) return
    await api.createSignalAlert({ ticker: form.ticker.toUpperCase(), condition: form.signalCondition })
    setForm((p) => ({ ...p, ticker: "" }))
    load()
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">提醒管理</h1>

      <div className="flex gap-1 mb-6 bg-zinc-800 rounded-lg p-1 w-fit">
        {(["history", "price", "signal"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${tab === t ? "bg-zinc-600 text-white" : "text-zinc-400"}`}>
            {t === "history" ? "历史记录" : t === "price" ? "价格提醒" : "信号提醒"}
          </button>
        ))}
      </div>

      {tab === "history" && (
        <div className="space-y-2">
          {history.length === 0 && <p className="text-zinc-500 text-center py-12">暂无提醒记录</p>}
          {history.map((h: any) => (
            <div key={h.id} className={`p-3 rounded-lg border text-sm ${h.read ? "bg-zinc-900 border-zinc-800 text-zinc-400" : "bg-zinc-800 border-zinc-600 text-white"}`}>
              <div className="flex justify-between">
                <span className="font-medium">{h.ticker}</span>
                <span className="text-zinc-500 text-xs">{new Date(h.triggered_at).toLocaleString("zh-CN")}</span>
              </div>
              <p className="mt-1">{h.message}</p>
            </div>
          ))}
        </div>
      )}

      {tab === "price" && (
        <div className="space-y-4">
          <div className="bg-zinc-900 p-4 rounded-lg space-y-3">
            <h3 className="text-sm font-semibold text-zinc-300">添加价格提醒</h3>
            <div className="flex gap-2 flex-wrap">
              <input
                placeholder="代码（如 AAPL）"
                value={form.ticker}
                onChange={(e) => setForm((p) => ({ ...p, ticker: e.target.value }))}
                className="bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white w-32"
              />
              <select
                value={form.condition}
                onChange={(e) => setForm((p) => ({ ...p, condition: e.target.value }))}
                className="bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white"
              >
                <option value="above">突破价格</option>
                <option value="below">跌破价格</option>
              </select>
              <input
                placeholder="目标价格"
                type="number"
                value={form.threshold}
                onChange={(e) => setForm((p) => ({ ...p, threshold: e.target.value }))}
                className="bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white w-28"
              />
              <button onClick={addPriceAlert} className="bg-zinc-700 hover:bg-zinc-600 text-white px-4 py-2 rounded text-sm">添加</button>
            </div>
          </div>
          <div className="space-y-2">
            {priceAlerts.map((a: any) => (
              <div key={a.id} className="flex items-center justify-between bg-zinc-900 p-3 rounded-lg text-sm">
                <span><strong>{a.ticker}</strong> {CONDITION_LABELS[a.condition]} {a.threshold}</span>
                <button onClick={() => api.deletePriceAlert(a.id).then(load)} className="text-zinc-500 hover:text-red-400">删除</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "signal" && (
        <div className="space-y-4">
          <div className="bg-zinc-900 p-4 rounded-lg space-y-3">
            <h3 className="text-sm font-semibold text-zinc-300">添加信号提醒</h3>
            <div className="flex gap-2 flex-wrap">
              <input
                placeholder="代码（如 NVDA）"
                value={form.ticker}
                onChange={(e) => setForm((p) => ({ ...p, ticker: e.target.value }))}
                className="bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white w-32"
              />
              <select
                value={form.signalCondition}
                onChange={(e) => setForm((p) => ({ ...p, signalCondition: e.target.value }))}
                className="bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white"
              >
                <option value="any_change">信号跳变（±2分）</option>
                <option value="strong_only">出现强烈信号（±3/4）</option>
                <option value="rsi_extreme">RSI超买/超卖</option>
              </select>
              <button onClick={addSignalAlert} className="bg-zinc-700 hover:bg-zinc-600 text-white px-4 py-2 rounded text-sm">添加</button>
            </div>
          </div>
          <div className="space-y-2">
            {signalAlerts.map((a: any) => (
              <div key={a.id} className="flex items-center justify-between bg-zinc-900 p-3 rounded-lg text-sm">
                <span><strong>{a.ticker}</strong> — {CONDITION_LABELS[a.condition]}</span>
                <button onClick={() => api.deleteSignalAlert(a.id).then(load)} className="text-zinc-500 hover:text-red-400">删除</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 手动测试提醒管理页**

```
访问 http://localhost:3000/alerts
预期：
- 三个标签页：历史记录 / 价格提醒 / 信号提醒
- 可添加和删除提醒
- 历史记录显示已触发提醒
```

- [ ] **Step 3: Commit**

```bash
git add stock-tool/frontend/app/alerts
git commit -m "feat: alerts management page with price and signal alert CRUD"
```

---

## Task 8: Web Push Service Worker

**Files:**
- Create: `stock-tool/frontend/public/sw.js`
- Modify: `stock-tool/frontend/app/layout.tsx`

- [ ] **Step 1: 写 public/sw.js**

```javascript
self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {}
  event.waitUntil(
    self.registration.showNotification(data.title || "投资助手提醒", {
      body: data.body || "",
      icon: "/favicon.ico",
      badge: "/favicon.ico",
    })
  )
})

self.addEventListener("notificationclick", (event) => {
  event.notification.close()
  event.waitUntil(clients.openWindow("/alerts"))
})
```

- [ ] **Step 2: 在 layout.tsx 中注册 Service Worker**

在 `<body>` 前添加：

```tsx
import Script from "next/script"
// 在 body 内末尾添加
<Script id="sw-register" strategy="afterInteractive">{`
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
  }
`}</Script>
```

- [ ] **Step 3: 验证 Service Worker 注册**

```
访问 http://localhost:3000/dashboard
打开 DevTools → Application → Service Workers
预期：sw.js 显示为 activated and running
```

- [ ] **Step 4: Commit**

```bash
git add stock-tool/frontend/public/sw.js stock-tool/frontend/app/layout.tsx
git commit -m "feat: Web Push service worker registration"
```

---

前端实现完成。访问 http://localhost:3000 可使用完整功能。
