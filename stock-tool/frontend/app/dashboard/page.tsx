"use client"
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import SignalCard from "@/components/SignalCard"
import AlertBanner from "@/components/AlertBanner"
import PortfolioSummary from "@/components/PortfolioSummary"
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
      <PortfolioSummary />

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
