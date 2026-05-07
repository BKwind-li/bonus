"use client"
import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api"
import type { Order } from "@/lib/types"
import OrderRow from "@/components/OrderRow"
import PortfolioTabs from "@/components/PortfolioTabs"

const PAGE_SIZE = 50

const statusOptions = [
  { value: "", label: "全部状态" },
  { value: "filled", label: "已成交" },
  { value: "pending", label: "待成交" },
  { value: "cancelled", label: "已取消" },
  { value: "rejected", label: "被拒" },
]

const sideOptions = [
  { value: "", label: "全部方向" },
  { value: "buy", label: "买" },
  { value: "sell", label: "卖" },
]

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [page, setPage] = useState(1)

  const [filterStatus, setFilterStatus] = useState("")
  const [filterSide, setFilterSide] = useState("")

  const fetchOrders = useCallback(async (reset = false) => {
    setLoading(true)
    setError(null)
    const currentPage = reset ? 1 : page
    const limit = currentPage * PAGE_SIZE
    try {
      const data = await api.getOrders("default", {
        ...(filterStatus ? { status: filterStatus } : {}),
        ...(filterSide ? { side: filterSide } : {}),
        limit: limit + 1,
      })
      setHasMore(data.length > limit)
      setOrders(data.slice(0, limit))
      if (reset) setPage(1)
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败")
    } finally {
      setLoading(false)
    }
  }, [filterStatus, filterSide, page])

  // Reset and fetch on filter change
  useEffect(() => {
    setPage(1)
    setOrders([])
    fetchOrders(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, filterSide])

  function handleLoadMore() {
    const nextPage = page + 1
    setPage(nextPage)
  }

  // Fetch more when page increases
  useEffect(() => {
    if (page > 1) fetchOrders(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  function handleRefresh() {
    fetchOrders(true)
  }

  return (
    <div className="space-y-4">
      <PortfolioTabs />

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">交易历史</h1>
        <span className="text-xs text-zinc-500">虚拟账户 · default</span>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-sm text-zinc-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-zinc-500"
        >
          {statusOptions.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={filterSide}
          onChange={(e) => setFilterSide(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-sm text-zinc-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-zinc-500"
        >
          {sideOptions.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* List */}
      {error && (
        <div className="text-center py-8 text-red-400 text-sm">
          {error}
          <button
            onClick={handleRefresh}
            className="block mx-auto mt-2 text-zinc-400 hover:text-white underline text-xs"
          >
            重试
          </button>
        </div>
      )}

      {!error && !loading && orders.length === 0 && (
        <div className="text-center py-16 text-zinc-500">
          <p className="text-3xl mb-3">📋</p>
          <p>暂无订单</p>
        </div>
      )}

      {orders.length > 0 && (
        <div className="space-y-3">
          {orders.map((o) => (
            <OrderRow key={o.id} order={o} onRefresh={handleRefresh} />
          ))}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-zinc-900 rounded-lg border border-zinc-800 animate-pulse" />
          ))}
        </div>
      )}

      {/* Load more */}
      {hasMore && !loading && (
        <div className="text-center pt-2">
          <button
            onClick={handleLoadMore}
            className="text-sm text-zinc-400 hover:text-white underline"
          >
            加载更多
          </button>
        </div>
      )}
    </div>
  )
}
