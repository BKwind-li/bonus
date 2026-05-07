import clsx from "clsx"

interface Props {
  label: string
  color: "green" | "yellow" | "red"
  score?: number
  size?: "sm" | "md"
}

const colorMap = {
  green: "bg-green-950 text-green-400 border border-green-800",
  yellow: "bg-yellow-950 text-yellow-400 border border-yellow-800",
  red: "bg-red-950 text-red-400 border border-red-800",
}

export default function SignalBadge({ label, color, score, size = "sm" }: Props) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1 rounded-full font-medium",
      size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
      colorMap[color]
    )}>
      {color === "green" ? "🟢" : color === "yellow" ? "🟡" : "🔴"}
      {label}
      {score !== undefined && <span className="opacity-70">({score > 0 ? "+" : ""}{score})</span>}
    </span>
  )
}
