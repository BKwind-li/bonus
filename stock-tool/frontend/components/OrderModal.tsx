"use client"
import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import type { Account, Position, PlaceOrderRequest } from "@/lib/types"

interface SignalSnapshot {
  label_short?: string
  score_short?: number
  label_long?: string
  score_long?: number
}

interface Props {
  ticker: string
  currentPrice: number
  signalSnapshot?: SignalSnapshot
  account?: Account
  existingPosition?: Position
  onClose: () => void
  onSuccess: () => void
}

type Side = "buy" | "sell"
type OrderType = "market" | "limit"

/** Returns true when the US stock market is closed (rough ET rule, no holiday check) */
function isMarketClosed(): boolean {
  const now = new Date()
  // ET offset: UTC-5 standard, UTC-4 daylight (rough — use UTC-4 as conservative year-round for display)
  const etOffsetMs = -4 * 60 * 60 * 1000
  const etMs = now.getTime() + (now.getTimezoneOffset() * 60 * 1000) + etOffsetMs
  const et = new Date(etMs)
  const day = et.getDay() // 0=Sun, 6=Sat
  if (day === 0 || day === 6) return true
  const hour = et.getHours()
  const minute = et.getMinutes()
  const minuteOfDay = hour * 60 + minute
  return minuteOfDay < 9 * 60 + 30 || minuteOfDay >= 16 * 60
}

function fmt(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default function OrderModal({
  ticker,
  currentPrice,
  signalSnapshot,
  account,
  existingPosition,
  onClose,
  onSuccess,
}: Props) {
  const [side, setSide] = useState<Side>("buy")
  const [orderType, setOrderType] = useState<OrderType>("market")
  const [qty, setQty] = useState("")
  const [limitPrice, setLimitPrice] = useState("")
  const [validationError, setValidationError] = useState<string | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const isFX = ticker.endsWith("=X")
  const marketClosed = !isFX && isMarketClosed()

  const maxBuyQty =
    account && currentPrice > 0 ? Math.floor(account.cash_balance / currentPrice) : null

  function validate(): string | null {
    const qtyNum = Number(qty)
    if (!qty || isNaN(qtyNum) || qtyNum <= 0 || !Number.isInteger(qtyNum)) {
      return "数量必须为正整数"
    }
    if (side === "sell") {
      const held = existingPosition?.qty ?? 0
      if (qtyNum > held) {
        return `卖出数量不可超过持仓数量 (${held} 股)`
      }
    }
    if (orderType === "limit") {
      const lp = Number(limitPrice)
      if (!limitPrice || isNaN(lp) || lp <= 0) {
        return "限价必须大于 0"
      }
    }
    return null
  }

  function handleSubmitForm(e: React.FormEvent) {
    e.preventDefault()
    setServerError(null)
    const err = validate()
    if (err) {
      setValidationError(err)
      return
    }
    setValidationError(null)
    setConfirming(true)
  }

  async function handleConfirm() {
    setSubmitting(true)
    setServerError(null)
    try {
      const req: PlaceOrderRequest = {
        ticker,
        side,
        order_type: orderType,
        qty: Number(qty),
        ...(orderType === "limit" ? { limit_price: Number(limitPrice) } : {}),
      }
      await api.placeOrder("default", req)
      setToast("下单成功！")
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 800)
    } catch (err: unknown) {
      setConfirming(false)
      // Try to extract detail from JSON or plain text
      let msg = "下单失败，请稍后重试"
      if (err instanceof Error) {
        try {
          const parsed = JSON.parse(err.message)
          msg = parsed.detail ?? err.message
        } catch {
          msg = err.message
        }
      }
      setServerError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const qtyNum = Number(qty)
  const estimatedCost =
    orderType === "market"
      ? qtyNum * currentPrice
      : qtyNum * (Number(limitPrice) || 0)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-lg font-bold">💼 虚拟下单 · {ticker}</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white text-xl leading-none"
            aria-label="关闭"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 overflow-y-auto max-h-[70vh]">

          {/* Current price */}
          <div className="text-sm text-zinc-400">
            当前价格 <span className="text-white font-semibold">{fmt(currentPrice)}</span>
          </div>

          {/* Signal snapshot (read-only) */}
          {signalSnapshot && (signalSnapshot.label_short || signalSnapshot.label_long) && (
            <div className="bg-zinc-800 rounded-lg p-3 text-xs space-y-1">
              <p className="text-zinc-400 font-medium mb-1">信号快照（下单时记录）</p>
              {signalSnapshot.label_short && (
                <div className="flex justify-between">
                  <span className="text-zinc-500">短期</span>
                  <span className="text-zinc-200">
                    {signalSnapshot.label_short}
                    {signalSnapshot.score_short !== undefined &&
                      <span className="ml-1 opacity-60">
                        ({signalSnapshot.score_short > 0 ? "+" : ""}{signalSnapshot.score_short})
                      </span>
                    }
                  </span>
                </div>
              )}
              {signalSnapshot.label_long && (
                <div className="flex justify-between">
                  <span className="text-zinc-500">长期</span>
                  <span className="text-zinc-200">
                    {signalSnapshot.label_long}
                    {signalSnapshot.score_long !== undefined &&
                      <span className="ml-1 opacity-60">
                        ({signalSnapshot.score_long > 0 ? "+" : ""}{signalSnapshot.score_long})
                      </span>
                    }
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Account info */}
          {account && (
            <div className="text-xs text-zinc-400 flex gap-4">
              <span>可用现金 <span className="text-white">{fmt(account.cash_balance)}</span></span>
              {side === "buy" && maxBuyQty !== null && (
                <span>最多可买 <span className="text-white">{maxBuyQty} 股</span></span>
              )}
              {side === "sell" && existingPosition && (
                <span>持仓 <span className="text-white">{existingPosition.qty} 股</span></span>
              )}
            </div>
          )}

          {/* Closed-market warning */}
          {marketClosed && (
            <div className="bg-yellow-950 border border-yellow-800 text-yellow-400 text-xs rounded-lg px-3 py-2">
              ⚠️ 美股当前处于闭市时段，将在下次开盘后排队成交
            </div>
          )}

          {/* Form — only show when not confirming */}
          {!confirming ? (
            <form onSubmit={handleSubmitForm} className="space-y-4">
              {/* Side radio */}
              <div>
                <p className="text-xs text-zinc-400 mb-2">方向</p>
                <div className="flex gap-3">
                  {(["buy", "sell"] as Side[]).map((s) => (
                    <label
                      key={s}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg border cursor-pointer text-sm font-medium transition-colors
                        ${side === s
                          ? s === "buy"
                            ? "bg-green-900 border-green-600 text-green-300"
                            : "bg-red-900 border-red-600 text-red-300"
                          : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-600"
                        }`}
                    >
                      <input
                        type="radio"
                        className="sr-only"
                        value={s}
                        checked={side === s}
                        onChange={() => { setSide(s); setValidationError(null) }}
                      />
                      {s === "buy" ? "买入 (Buy)" : "卖出 (Sell)"}
                    </label>
                  ))}
                </div>
              </div>

              {/* Order type radio */}
              <div>
                <p className="text-xs text-zinc-400 mb-2">订单类型</p>
                <div className="flex gap-3">
                  {(["market", "limit"] as OrderType[]).map((t) => (
                    <label
                      key={t}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg border cursor-pointer text-sm font-medium transition-colors
                        ${orderType === t
                          ? "bg-zinc-700 border-zinc-500 text-white"
                          : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-600"
                        }`}
                    >
                      <input
                        type="radio"
                        className="sr-only"
                        value={t}
                        checked={orderType === t}
                        onChange={() => { setOrderType(t); setValidationError(null) }}
                      />
                      {t === "market" ? "市价单" : "限价单"}
                    </label>
                  ))}
                </div>
              </div>

              {/* Qty */}
              <div>
                <label className="text-xs text-zinc-400 block mb-1">数量（股）</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={qty}
                  onChange={(e) => { setQty(e.target.value); setValidationError(null) }}
                  placeholder="输入整数股数"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
                />
              </div>

              {/* Limit price (only when limit) */}
              {orderType === "limit" && (
                <div>
                  <label className="text-xs text-zinc-400 block mb-1">限价（USD）</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={limitPrice}
                    onChange={(e) => { setLimitPrice(e.target.value); setValidationError(null) }}
                    placeholder={`参考价 ${currentPrice.toFixed(2)}`}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
                  />
                </div>
              )}

              {/* Estimated cost summary */}
              {qtyNum > 0 && (
                <div className="text-xs text-zinc-500">
                  预计金额约{" "}
                  <span className="text-zinc-300">{fmt(estimatedCost)}</span>
                  {orderType === "market" && " （市价单以实际成交为准）"}
                </div>
              )}

              {/* Validation error */}
              {validationError && (
                <p className="text-red-400 text-sm">{validationError}</p>
              )}

              {/* Server error */}
              {serverError && (
                <p className="text-red-400 text-sm">{serverError}</p>
              )}

              <button
                type="submit"
                className="w-full py-2.5 rounded-lg text-sm font-semibold bg-zinc-100 text-zinc-900 hover:bg-white transition-colors"
              >
                下一步：确认
              </button>
            </form>
          ) : (
            /* Confirmation panel */
            <div className="space-y-4">
              <div className="bg-zinc-800 rounded-lg p-4 space-y-2 text-sm">
                <p className="text-zinc-400 text-xs font-medium mb-2 uppercase tracking-wide">请确认以下订单</p>
                <div className="flex justify-between">
                  <span className="text-zinc-500">品种</span>
                  <span className="text-white font-medium">{ticker}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">方向</span>
                  <span className={side === "buy" ? "text-green-400 font-medium" : "text-red-400 font-medium"}>
                    {side === "buy" ? "买入" : "卖出"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">类型</span>
                  <span className="text-white">{orderType === "market" ? "市价单" : "限价单"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">数量</span>
                  <span className="text-white">{qty} 股</span>
                </div>
                {orderType === "limit" && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">限价</span>
                    <span className="text-white">{fmt(Number(limitPrice))}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-zinc-500">预计金额</span>
                  <span className="text-zinc-300">{fmt(estimatedCost)}</span>
                </div>
              </div>

              {serverError && (
                <p className="text-red-400 text-sm">{serverError}</p>
              )}

              {toast && (
                <p className="text-green-400 text-sm text-center">{toast}</p>
              )}

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => { setConfirming(false); setServerError(null) }}
                  disabled={submitting}
                  className="flex-1 py-2.5 rounded-lg text-sm font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors disabled:opacity-50"
                >
                  返回修改
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  disabled={submitting}
                  className="flex-1 py-2.5 rounded-lg text-sm font-semibold bg-zinc-100 text-zinc-900 hover:bg-white transition-colors disabled:opacity-50"
                >
                  {submitting ? "提交中..." : "确认下单"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
