import Link from "next/link"
import SignalBadge from "@/components/SignalBadge"
import type { Position } from "@/lib/types"

interface Props {
  position: Position
}

function fmt(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default function PositionCard({ position: p }: Props) {
  const pnlPositive = p.unrealized_pnl >= 0
  const pnlColor = pnlPositive ? "text-green-400" : "text-red-400"
  const pnlSign = pnlPositive ? "+" : ""

  return (
    <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-2">
        {/* Left: ticker + name + signal badge */}
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-white text-base">{p.ticker}</span>
            {p.name && (
              <span className="text-zinc-400 text-sm truncate">{p.name}</span>
            )}
            {p.signal_label_short && (
              <SignalBadge
                label={p.signal_label_short}
                color={p.signal_color_short ?? "yellow"}
                size="sm"
              />
            )}
          </div>
          {/* Cost vs price */}
          <div className="mt-1 text-xs text-zinc-500">
            均价 {fmt(p.avg_cost)} · 现价 {fmt(p.current_price)} · {p.qty} 股
          </div>
        </div>

        {/* Right: market value + PnL */}
        <div className="text-right shrink-0">
          <div className="text-base font-semibold text-zinc-100">{fmt(p.market_value)}</div>
          <div className={`text-sm font-medium ${pnlColor}`}>
            {pnlSign}{fmt(p.unrealized_pnl)}
            <span className="ml-1 text-xs opacity-80">
              ({pnlSign}{p.unrealized_pnl_pct.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      {/* Footer: link to symbol detail */}
      <div className="mt-3 flex justify-end">
        <Link
          href={`/symbol/${p.ticker}`}
          className="text-xs text-zinc-400 hover:text-white underline"
        >
          查看详情 →
        </Link>
      </div>
    </div>
  )
}
