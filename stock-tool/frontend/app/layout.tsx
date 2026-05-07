import type { Metadata } from "next"
import { Inter } from "next/font/google"
import Script from "next/script"
import "./globals.css"
import NavBar from "@/components/NavBar"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "投资助手",
  description: "个人股票与外汇投资辅助工具",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body className={`${inter.className} bg-zinc-950 text-white min-h-screen`}>
        <NavBar />
        <main className="max-w-4xl mx-auto px-4 py-6">{children}</main>
        <Script id="sw-register" strategy="afterInteractive">{`
          if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
          }
        `}</Script>
      </body>
    </html>
  )
}
