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

  async function markRead(id: number) {
    await api.markAlertRead(id)
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
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{h.ticker}</span>
                  {!h.read && <span className="text-xs bg-zinc-600 text-white px-1.5 py-0.5 rounded">未读</span>}
                  <span className="text-xs text-zinc-500">{h.alert_type}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-zinc-500 text-xs">{new Date(h.triggered_at).toLocaleString("zh-CN")}</span>
                  {!h.read && (
                    <button onClick={() => markRead(h.id)} className="text-xs text-zinc-400 hover:text-white underline whitespace-nowrap">
                      标为已读
                    </button>
                  )}
                </div>
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
