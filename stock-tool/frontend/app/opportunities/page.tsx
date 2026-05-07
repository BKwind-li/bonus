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
  const [scanStarted, setScanStarted] = useState(false)
  const [lastScan, setLastScan] = useState<string | null>(null)
  const [filters, setFilters] = useState({ market: "all", signalType: "all", sortBy: "short" })

  const loadResults = useCallback(async () => {
    setLoading(true)
    const [data, scanTime] = await Promise.all([
      api.getScanResults({
        market: filters.market === "all" ? undefined : filters.market,
        signal_type: filters.signalType === "all" ? undefined : filters.signalType,
        sort_by: filters.sortBy,
      }),
      api.getLastScanTime(),
    ])
    setResults(data)
    setLastScan(scanTime.last_scan)
    setLoading(false)
  }, [filters])

  useEffect(() => { loadResults() }, [loadResults])

  async function handleTriggerScan() {
    setScanning(true)
    setScanStarted(false)
    await api.triggerScan()
    setScanStarted(true)
    setTimeout(() => {
      setScanning(false)
      setScanStarted(false)
      loadResults()
    }, 3000)
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

      {scanStarted && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-zinc-800 text-sm text-zinc-300">
          扫描已开始，结果将在数分钟后更新
        </div>
      )}

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
