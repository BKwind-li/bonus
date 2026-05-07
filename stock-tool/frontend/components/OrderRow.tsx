"use client"
import { useState } from "react"
import { api } from "@/lib/api"
import type { Order } from "@/lib/types"
import clsx from "clsx"

interface Props {
  order: Order
  onRefresh: () => void
}

const statusLabel: Record<string, string> = {
  filled: "已成交",
  pending: "待成交",
  queued: "排队中",
  cancelled: "已取消",
  rejected: "被拒",
}

const statusStyle: Record<string, string> = {
  filled: "bg-green-950 text-green-400 border border-green-800",
  pending: "bg-yellow-950 text-yellow-400 border border-yellow-800",
  queued: "bg-yellow-950 text-yellow-400 border border-yellow-800",
  cancelled: "bg-zinc-800 text-zinc-500 border border-zinc-700",
  rejected: "bg-red-950 text-red-400 border border-red-800",
}

function fmt(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  })
}

export default function OrderRow({ order: o, onRefresh }: Props) {
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canCancel = o.status === "queued" || o.status === "pending"
  const displayTime = o.status === "filled" && o.filled_at ? o.filled_at : o.created_at

  async function handleCancel() {
    setCancelling(true)
    setError(null)
    try {
      await api.cancelOrder("default", o.id)
      onRefresh()
    } catch (err: unknown) {
      let msg = "取消失败"
      if (err instanceof Error) {
        try {
          const parsed = JSON.parse(err.message)
          msg = parsed.detail ?? err.message
        } catch {
          msg = err.message
        }
      }
      setError(msg)
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-3">
        {/* Left: status + info */}
        <div className="min-w-0 space-y-1.5">
          {/* Row 1: badge + ticker + side */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={clsx(
              "inline-flex items-center rounded-full text-xs font-medium px-2 py-0.5",
              statusStyle[o.status] ?? "bg-zinc-800 text-zinc-400 border border-zinc-700"
            )}>
              {statusLabel[o.status] ?? o.status}
            </span>
            <span className="font-bold text-white">{o.ticker}</span>
            <span className={clsx(
              "text-xs font-medium",
              o.side === "buy" ? "text-green-400" : "text-red-400"
            )}>
              {o.side === "buy" ? "买入" : "卖出"}
            </span>
            <span className="text-xs text-zinc-400">{o.order_type === "market" ? "市价" : "限价"}</span>
          </div>

          {/* Row 2: qty + price */}
          <div className="text-xs text-zinc-400 flex flex-wrap gap-3">
            <span>{o.qty} 股</span>
            {o.status === "filled" && o.filled_price != null && (
              <span>成交价 <span className="text-zinc-200">{fmt(o.filled_price)}</span></span>
            )}
            {o.status !== "filled" && o.order_type === "limit" && o.limit_price != null && (
              <span>限价 <span className="text-zinc-200">{fmt(o.limit_price)}</span></span>
            )}
          </div>

          {/* Row 3: time */}
          <div className="text-xs text-zinc-600">
            {o.status === "filled" ? "成交时间" : "下单时间"} {fmtDate(displayTime)}
          </div>

          {/* Signal labels if present */}
          {((o as any).signal_label_short || (o as any).signal_label_long) && (
            <div className="flex gap-2 flex-wrap">
              {(o as any).signal_label_short && (
                <span className="text-xs bg-zinc-800 text-zinc-400 border border-zinc-700 rounded-full px-2 py-0.5">
                  短 {(o as any).signal_label_short}
                </span>
              )}
              {(o as any).signal_label_long && (
                <span className="text-xs bg-zinc-800 text-zinc-400 border border-zinc-700 rounded-full px-2 py-0.5">
                  长 {(o as any).signal_label_long}
                </span>
              )}
            </div>
          )}

          {error && <p className="text-red-400 text-xs">{error}</p>}
        </div>

        {/* Right: cancel button */}
        {canCancel && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white transition-colors disabled:opacity-50"
          >
            {cancelling ? "取消中..." : "撤单"}
          </button>
        )}
      </div>
    </div>
  )
}
