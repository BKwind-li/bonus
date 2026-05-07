import SignalBadge from "./SignalBadge"
import { SignalScore } from "@/lib/types"

interface Props {
  title: string
  signal: SignalScore
}

const contribColor: Record<string, string> = {
  "1": "text-green-400",
  "-1": "text-red-400",
}

export default function SignalDetail({ title, signal }: Props) {
  return (
    <div className="bg-zinc-900 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-zinc-300">{title}</h3>
        <SignalBadge label={signal.label} color={signal.color} score={signal.score} size="md" />
      </div>
      <div className="space-y-2">
        {signal.indicators.map((ind) => (
          <div key={ind.name} className="flex items-start justify-between gap-3 text-sm">
            <div className="flex-1">
              <span className="text-zinc-400 font-medium">{ind.name}</span>
              <span className="text-zinc-500 text-xs ml-2">{ind.raw_value}</span>
              <p className="text-zinc-300 text-xs mt-0.5">{ind.description}</p>
            </div>
            <span className={contribColor[String(ind.contribution)] ?? "text-zinc-400"}>
              {ind.contribution > 0 ? "+1" : "-1"}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
