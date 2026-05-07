import Link from "next/link"
import clsx from "clsx"
import SignalBadge from "./SignalBadge"

interface Props {
  ticker: string
  name: string
  sector: string
  market: string
  price: number
  change_pct: number
  short_label: string
  short_color: "green" | "yellow" | "red"
  short_score: number
  long_label: string
  long_color: "green" | "yellow" | "red"
  long_score: number
  summary?: string
  isAlert?: boolean
}

const borderColor = {
  green: "border-l-green-500",
  yellow: "border-l-yellow-500",
  red: "border-l-red-500",
}

export default function SignalCard({
  ticker, name, sector, market, price, change_pct,
  short_label, short_color, short_score,
  long_label, long_color, long_score,
  summary, isAlert,
}: Props) {
  const dominantColor = short_score >= 0 ? short_color : "red"
  return (
    <Link href={`/symbol/${ticker}`}>
      <div className={clsx(
        "flex items-start gap-3 p-4 rounded-lg border-l-4 cursor-pointer",
        "bg-zinc-900 hover:bg-zinc-800 transition-colors",
        borderColor[dominantColor],
        isAlert && "ring-2 ring-orange-500 animate-pulse",
      )}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <span className="font-bold text-white">{ticker}</span>
              <span className="text-zinc-400 text-sm ml-2">{name}</span>
            </div>
            <span className={clsx(
              "font-semibold tabular-nums text-sm",
              change_pct >= 0 ? "text-green-400" : "text-red-400"
            )}>
              {price} {change_pct >= 0 ? "↑" : "↓"}{Math.abs(change_pct).toFixed(2)}%
            </span>
          </div>
          <div className="text-zinc-500 text-xs mt-0.5">{sector} · {market === "forex" ? "外汇" : "美股"}</div>
          <div className="flex gap-2 mt-2 flex-wrap">
            <SignalBadge label={`短期 ${short_label}`} color={short_color} score={short_score} />
            <SignalBadge label={`长期 ${long_label}`} color={long_color} score={long_score} />
          </div>
          {summary && <p className="text-zinc-300 text-sm mt-2 line-clamp-1">{summary}</p>}
        </div>
      </div>
    </Link>
  )
}
