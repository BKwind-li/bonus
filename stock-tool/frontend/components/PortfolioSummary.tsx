import Link from "next/link"

export default function PortfolioSummary() {
  return (
    <Link
      href="/portfolio"
      aria-disabled
      tabIndex={-1}
      className="block mb-6 cursor-not-allowed opacity-60 pointer-events-none"
      title="即将上线"
    >
      <div className="grid grid-cols-3 gap-3 p-4 rounded-lg bg-zinc-900 border border-zinc-800">
        <div>
          <div className="text-xs text-zinc-500 mb-1">现金</div>
          <div className="text-lg font-semibold text-zinc-400">— USD</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500 mb-1">账户总净值</div>
          <div className="text-lg font-semibold text-zinc-400">—</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500 mb-1">今日盈亏</div>
          <div className="text-lg font-semibold text-zinc-400">—</div>
        </div>
      </div>
      <p className="text-center text-xs text-zinc-600 mt-1">虚拟账户 · 即将上线</p>
    </Link>
  )
}
