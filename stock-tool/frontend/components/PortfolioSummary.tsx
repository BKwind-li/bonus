"use client"
import { useEffect, useState } from "react"
import Link from "next/link"
import { api } from "@/lib/api"
import type { Account, Position } from "@/lib/types"

interface Props {
  account?: Account
  positions?: Position[]
}

function fmt(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

function computeSummary(account: Account, positions: Position[]) {
  const marketValue = positions.reduce((sum, p) => sum + p.market_value, 0)
  const totalValue = account.cash_balance + marketValue
  const totalPnl = totalValue - account.initial_cash
  const totalPnlPct = account.initial_cash > 0 ? (totalPnl / account.initial_cash) * 100 : 0
  return { marketValue, totalValue, totalPnl, totalPnlPct }
}

export default function PortfolioSummary({ account: propAccount, positions: propPositions }: Props) {
  const [account, setAccount] = useState<Account | null>(propAccount ?? null)
  const [positions, setPositions] = useState<Position[]>(propPositions ?? [])
  const [loading, setLoading] = useState(!propAccount)

  useEffect(() => {
    // If props were provided, use them directly — no fetch needed
    if (propAccount) {
      setAccount(propAccount)
      setPositions(propPositions ?? [])
      setLoading(false)
      return
    }
    // Self-fetching mode (used from /dashboard)
    let cancelled = false
    async function load() {
      try {
        const [acc, pos] = await Promise.all([
          api.getAccount("default"),
          api.getPositions("default"),
        ])
        if (!cancelled) {
          setAccount(acc)
          setPositions(pos)
        }
      } catch {
        // silently ignore — backend may not be running locally
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [propAccount, propPositions])

  if (loading) {
    return (
      <div className="block mb-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-lg bg-zinc-900 border border-zinc-800 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i}>
              <div className="h-3 w-16 bg-zinc-700 rounded mb-2" />
              <div className="h-5 w-24 bg-zinc-700 rounded" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!account) {
    // Fallback placeholder when data never loaded
    return (
      <Link
        href="/portfolio"
        className="block mb-6"
      >
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-lg bg-zinc-900 border border-zinc-800">
          <div>
            <div className="text-xs text-zinc-500 mb-1">现金</div>
            <div className="text-lg font-semibold text-zinc-400">— USD</div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 mb-1">持仓市值</div>
            <div className="text-lg font-semibold text-zinc-400">—</div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 mb-1">总净值</div>
            <div className="text-lg font-semibold text-zinc-400">—</div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 mb-1">累计盈亏</div>
            <div className="text-lg font-semibold text-zinc-400">—</div>
          </div>
        </div>
        <p className="text-center text-xs text-zinc-600 mt-1">虚拟账户 · 点击查看详情</p>
      </Link>
    )
  }

  const { marketValue, totalValue, totalPnl, totalPnlPct } = computeSummary(account, positions)
  const pnlPositive = totalPnl >= 0
  const pnlColor = pnlPositive ? "text-green-400" : "text-red-400"
  const pnlSign = pnlPositive ? "+" : ""

  return (
    <Link href="/portfolio" className="block mb-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-colors">
        <div>
          <div className="text-xs text-zinc-500 mb-1">现金</div>
          <div className="text-lg font-semibold text-zinc-100">{fmt(account.cash_balance)}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500 mb-1">持仓市值</div>
          <div className="text-lg font-semibold text-zinc-100">{fmt(marketValue)}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500 mb-1">总净值</div>
          <div className="text-lg font-semibold text-zinc-100">{fmt(totalValue)}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500 mb-1">累计盈亏</div>
          <div className={`text-lg font-semibold ${pnlColor}`}>
            {pnlSign}{fmt(totalPnl)}
            <span className="text-sm ml-1 opacity-80">
              ({pnlSign}{totalPnlPct.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>
      <p className="text-center text-xs text-zinc-600 mt-1">虚拟账户 · 点击查看详情</p>
    </Link>
  )
}
