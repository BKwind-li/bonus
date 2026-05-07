"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import clsx from "clsx"
import { useEffect, useState } from "react"
import { api } from "@/lib/api"

const links = [
  { href: "/dashboard", label: "仪表盘" },
  { href: "/opportunities", label: "机会发现" },
  { href: "/portfolio", label: "持仓" },
  { href: "/alerts", label: "提醒" },
]

export default function NavBar() {
  const pathname = usePathname()
  const [unread, setUnread] = useState(0)

  // Don't render or fetch on the login page — there's no token, so getUnreadCount
  // would 401 and bounce the user back to /login, creating an infinite loop.
  const isAuthPage = pathname === "/login"

  useEffect(() => {
    if (isAuthPage) return
    api.getUnreadCount().then((r) => setUnread(r.count)).catch(() => {})
  }, [pathname, isAuthPage])

  if (isAuthPage) return null

  return (
    <nav className="sticky top-0 z-50 bg-zinc-950 border-b border-zinc-800 px-4 py-3">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <span className="font-bold text-white text-lg">📈 投资助手</span>
        <div className="flex gap-1">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className={clsx(
              "px-3 py-1.5 rounded text-sm font-medium transition-colors relative",
              pathname.startsWith(l.href) ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"
            )}>
              {l.label}
              {l.href === "/alerts" && unread > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {unread}
                </span>
              )}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}
