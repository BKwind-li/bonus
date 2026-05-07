"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import clsx from "clsx"

const tabs = [
  { href: "/portfolio", label: "持仓", exact: true },
  { href: "/portfolio/orders", label: "交易历史", exact: false },
]

export default function PortfolioTabs() {
  const pathname = usePathname()

  function isActive(href: string, exact: boolean) {
    if (exact) return pathname === href
    return pathname.startsWith(href)
  }

  return (
    <div className="flex gap-1 border-b border-zinc-800 mb-6">
      {tabs.map((t) => (
        <Link
          key={t.href}
          href={t.href}
          className={clsx(
            "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
            isActive(t.href, t.exact)
              ? "border-zinc-300 text-white"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          )}
        >
          {t.label}
        </Link>
      ))}
    </div>
  )
}
