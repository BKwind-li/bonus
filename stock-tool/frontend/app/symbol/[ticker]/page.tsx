"use client"
import { useEffect, useState, useCallback } from "react"
import { useParams } from "next/navigation"
import { api } from "@/lib/api"
import type { Account, Position } from "@/lib/types"
import PriceChart from "@/components/PriceChart"
import SignalDetail from "@/components/SignalDetail"
import SignalBadge from "@/components/SignalBadge"
import OrderModal from "@/components/OrderModal"

function fmt(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default function SymbolPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [deepAnalysis, setDeepAnalysis] = useState("")
  const [deepLoading, setDeepLoading] = useState(false)
  const [inWatchlist, setInWatchlist] = useState(false)
  const [account, setAccount] = useState<Account | undefined>(undefined)
  const [positions, setPositions] = useState<Position[]>([])
  const [showOrderModal, setShowOrderModal] = useState(false)

  const loadAll = useCallback(async () => {
    const [analysis, watchlist, acc, pos] = await Promise.all([
      api.getAnalysis(ticker),
      api.getWatchlist(),
      api.getAccount("default").catch(() => undefined),
      api.getPositions("default").catch(() => []),
    ])
    setData(analysis)
    setInWatchlist(watchlist.some((w: any) => w.ticker === ticker))
    setAccount(acc)
    setPositions(pos as Position[])
    setLoading(false)
  }, [ticker])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  async function handleDeepAnalysis() {
    setDeepLoading(true)
    try {
      const r = await api.getDeepAnalysis(ticker)
      setDeepAnalysis(r.analysis)
    } catch {
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

  const existingPosition = positions.find((p) => p.ticker === ticker)

  const signalSnapshot = signal
    ? {
        label_short: signal.short_term?.label,
        score_short: signal.short_term?.score,
        label_long: signal.long_term?.label,
        score_long: signal.long_term?.score,
      }
    : undefined

  const pnlPositive = existingPosition ? existingPosition.unrealized_pnl >= 0 : false
  const pnlSign = pnlPositive ? "+" : ""
  const pnlColor = pnlPositive ? "text-green-400" : "text-red-400"

  return (
    <div className="space-y-4">
      {/* Header: ticker name, price, action buttons */}
      <div className="flex items-start justify-between gap-4">
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
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <button
            onClick={toggleWatchlist}
            className="bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            {inWatchlist ? "✓ 已自选" : "+ 加入自选"}
          </button>
          <button
            type="button"
            onClick={() => setShowOrderModal(true)}
            className="bg-zinc-100 hover:bg-white text-zinc-900 text-sm px-4 py-2 rounded-lg font-medium transition-colors"
          >
            💼 虚拟下单
          </button>
        </div>
      </div>

      {/* 30-day price chart */}
      <PriceChart prices={price_history} />

      {/* Mini position info (shows when user holds this ticker) */}
      {existingPosition && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex flex-wrap items-center gap-4 text-sm">
          <span className="text-zinc-400 text-xs font-medium uppercase tracking-wide">当前持仓</span>
          <span className="text-zinc-300">{existingPosition.qty} 股</span>
          <span className="text-zinc-500">·</span>
          <span className="text-zinc-400">
            均价 <span className="text-zinc-200">{fmt(existingPosition.avg_cost)}</span>
          </span>
          <span className="text-zinc-500">·</span>
          <span className={`font-medium ${pnlColor}`}>
            浮动盈亏 {pnlSign}{fmt(existingPosition.unrealized_pnl)}
            <span className="text-xs ml-1 opacity-80">
              ({pnlSign}{existingPosition.unrealized_pnl_pct.toFixed(2)}%)
            </span>
          </span>
        </div>
      )}

      {/* Signal panels */}
      <SignalDetail title="短期信号" signal={signal.short_term} />
      <SignalDetail title="长期信号" signal={signal.long_term} />

      {/* Deep analysis */}
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

      {/* Order Modal */}
      {showOrderModal && (
        <OrderModal
          ticker={ticker}
          currentPrice={signal.price}
          signalSnapshot={signalSnapshot}
          account={account}
          existingPosition={existingPosition}
          onClose={() => setShowOrderModal(false)}
          onSuccess={() => loadAll()}
        />
      )}
    </div>
  )
}
