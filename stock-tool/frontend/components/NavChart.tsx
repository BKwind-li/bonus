"use client"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import type { NavPoint } from "@/lib/types"

interface Props {
  data: NavPoint[]
}

function fmt(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default function NavChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="bg-zinc-900 rounded-lg p-4 text-center text-zinc-500 text-sm">
        暂无净值历史数据
      </div>
    )
  }

  const values = data.map((d) => d.total_value)
  const min = Math.min(...values) * 0.995
  const max = Math.max(...values) * 1.005

  // Format date labels: show MM-DD
  const formatted = data.map((d) => ({
    ...d,
    label: d.date.slice(5), // "2025-01-15" → "01-15"
  }))

  // Thin out X-axis ticks so labels don't overlap
  const tickCount = Math.min(6, data.length)
  const step = Math.max(1, Math.floor(data.length / tickCount))
  const ticks = formatted.filter((_, i) => i % step === 0).map((d) => d.date)

  return (
    <div className="bg-zinc-900 rounded-lg p-4">
      <p className="text-xs text-zinc-500 mb-3">净值走势（近90天）</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={formatted} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="date"
            ticks={ticks}
            tickFormatter={(v) => String(v).slice(5)}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[min, max]}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 6 }}
            labelFormatter={(v) => String(v)}
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                total_value: "总净值",
                cash: "现金",
                market_value: "持仓市值",
              }
              return [fmt(value as number), labels[name as string] ?? name]
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }}
            formatter={(value) => {
              const labels: Record<string, string> = {
                total_value: "总净值",
                cash: "现金",
                market_value: "持仓市值",
              }
              return labels[value] ?? value
            }}
          />
          <Line
            type="monotone"
            dataKey="total_value"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="cash"
            stroke="#60a5fa"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="market_value"
            stroke="#f59e0b"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            activeDot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
