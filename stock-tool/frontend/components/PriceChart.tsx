"use client"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface Props {
  prices: number[]
}

export default function PriceChart({ prices }: Props) {
  const data = prices.map((price, i) => ({ day: i + 1, price: Number(price.toFixed(4)) }))
  const min = Math.min(...prices) * 0.998
  const max = Math.max(...prices) * 1.002

  return (
    <div className="bg-zinc-900 rounded-lg p-4">
      <p className="text-xs text-zinc-500 mb-3">近30天价格走势</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={data}>
          <XAxis dataKey="day" hide />
          <YAxis domain={[min, max]} hide />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 6 }}
            labelFormatter={(v) => `第${v}天`}
            formatter={(v) => [v, "价格"]}
          />
          <Line
            type="monotone" dataKey="price" stroke="#22c55e"
            strokeWidth={2} dot={false} activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
