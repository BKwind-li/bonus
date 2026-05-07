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
          {/* TODO(Task 10): Replace disabled placeholder with OrderModal trigger once paper trading
              module is implemented. Also add mini-position display below PriceChart at that point. */}
          <button
            type="button"
            disabled
            className="px-4 py-2 rounded bg-zinc-800 text-zinc-500 cursor-not-allowed"
            title="即将上线（Task 10 后启用）"
          >
            💼 虚拟下单
          </button>
        </div>
      </div>

      {/* 30-day price chart */}
      <PriceChart prices={price_history} />

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
    </div>
  )
}
