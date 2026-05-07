"use client"
import { useEffect, useState } from "react"
import Link from "next/link"
import { api } from "@/lib/api"
import type { Account, Position, NavPoint } from "@/lib/types"
import PortfolioSummary from "@/components/PortfolioSummary"
import NavChart from "@/components/NavChart"
import PositionCard from "@/components/PositionCard"

export default function PortfolioPage() {
  const [account, setAccount] = useState<Account | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [navHistory, setNavHistory] = useState<NavPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [acc, pos, nav] = await Promise.all([
          api.getAccount("default"),
          api.getPositions("default"),
          api.getNavHistory("default", 90),
        ])
        if (!cancelled) {
          setAccount(acc)
          setPositions(pos)
          setNavHistory(nav)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "加载失败")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        {/* Summary skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-lg bg-zinc-900 border border-zinc-800 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i}>
              <div className="h-3 w-16 bg-zinc-700 rounded mb-2" />
              <div className="h-5 w-24 bg-zinc-700 rounded" />
            </div>
          ))}
        </div>
        {/* Chart skeleton */}
        <div className="h-48 bg-zinc-900 rounded-lg border border-zinc-800 animate-pulse" />
        {/* Positions skeleton */}
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 bg-zinc-900 rounded-lg border border-zinc-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-16 text-zinc-500">
        <p className="text-3xl mb-3">⚠️</p>
        <p className="text-red-400">{error}</p>
        <button
          className="mt-4 text-sm text-zinc-400 hover:text-white underline"
          onClick={() => window.location.reload()}
        >
          重试
        </button>
      </div>
    )
  }

  // Sort positions by market_value descending
  const sortedPositions = [...positions].sort((a, b) => b.market_value - a.market_value)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">持仓总览</h1>
        <span className="text-xs text-zinc-500">虚拟账户 · default</span>
      </div>

      {/* Summary card — pass props so no double-fetch */}
      {account && (
        <PortfolioSummary account={account} positions={positions} />
      )}

      {/* NAV chart */}
      <NavChart data={navHistory} />

      {/* Position list */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wide">
          当前持仓 ({sortedPositions.length})
        </h2>

        {sortedPositions.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <p className="text-3xl mb-3">📂</p>
            <p>暂无持仓，去{" "}
              <Link href="/opportunities" className="text-zinc-300 underline hover:text-white">
                机会发现
              </Link>
              {" "}挑一个？
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedPositions.map((p) => (
              <PositionCard key={p.ticker} position={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
