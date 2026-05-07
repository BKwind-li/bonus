"use client"
interface Props {
  market: string
  signalType: string
  sortBy: string
  onChange: (key: string, value: string) => void
}

const filterGroups = [
  {
    key: "market",
    options: [
      { value: "all", label: "全部" },
      { value: "stock", label: "美股" },
      { value: "forex", label: "外汇" },
    ],
  },
  {
    key: "signalType",
    options: [
      { value: "all", label: "全部信号" },
      { value: "bullish", label: "🟢 看涨" },
      { value: "bearish", label: "🔴 看跌" },
    ],
  },
  {
    key: "sortBy",
    options: [
      { value: "short", label: "短期强度" },
      { value: "long", label: "长期强度" },
    ],
  },
]

export default function FilterBar({ market, signalType, sortBy, onChange }: Props) {
  const values: Record<string, string> = { market, signalType, sortBy }
  return (
    <div className="flex flex-wrap gap-3 mb-6">
      {filterGroups.map((group) => (
        <div key={group.key} className="flex rounded-lg bg-zinc-800 overflow-hidden">
          {group.options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onChange(group.key, opt.value)}
              className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                values[group.key] === opt.value
                  ? "bg-zinc-600 text-white"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}
