import { getToken } from "./auth"
import type {
  Account,
  Position,
  NavPoint,
  Order,
  PlaceOrderRequest,
  OrderFilter,
  Performance,
} from "./types"

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
    // Avoid redirect loop when an /auth/login call itself returns 401, or when
    // some background fetch on /login fires before the user has a token.
    if (
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/login")
    ) {
      window.location.href = "/login"
    }
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
    // URLSearchParams stringifies `undefined` as the literal "undefined", which
    // the backend then matches against a non-existent market. Strip first.
    const clean = Object.fromEntries(
      Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== null)
    ) as Record<string, string>
    const q = new URLSearchParams(clean).toString()
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

  // ── Virtual Trading / Portfolio ───────────────────────────────────────────
  getAccount: (id: string) =>
    request<Account>(`/portfolio/accounts/${id}`),
  getPositions: (id: string) =>
    request<Position[]>(`/portfolio/accounts/${id}/positions`),
  getNavHistory: (id: string, days = 90) =>
    request<NavPoint[]>(`/portfolio/accounts/${id}/nav-history?days=${days}`),
  getOrders: (id: string, filter: OrderFilter = {}) => {
    // Same precaution as getScanResults — drop undefined values so the URL
    // does not contain `?status=undefined&...`.
    const clean = Object.fromEntries(
      Object.entries(filter).filter(([, v]) => v !== undefined && v !== null)
    ) as Record<string, string>
    const q = new URLSearchParams(clean).toString()
    return request<Order[]>(`/portfolio/accounts/${id}/orders${q ? "?" + q : ""}`)
  },
  placeOrder: (id: string, req: PlaceOrderRequest) =>
    request<Order>(`/portfolio/accounts/${id}/orders`, {
      method: "POST",
      body: JSON.stringify(req),
    }),
  cancelOrder: (id: string, orderId: string) =>
    request<Order>(`/portfolio/accounts/${id}/orders/${orderId}`, { method: "DELETE" }),
  getPerformance: (id: string) =>
    request<Performance>(`/portfolio/accounts/${id}/performance`),
}
