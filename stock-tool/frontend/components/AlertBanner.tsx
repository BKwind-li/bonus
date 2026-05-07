"use client"
interface Props {
  alerts: Array<{ ticker: string; message: string }>
  onDismiss: () => void
}

export default function AlertBanner({ alerts, onDismiss }: Props) {
  if (alerts.length === 0) return null
  return (
    <div className="bg-orange-950 border border-orange-700 text-orange-300 px-4 py-3 rounded-lg mb-4 flex items-start justify-between gap-3">
      <div>
        <span className="font-semibold">⚠️ 异常信号</span>
        <ul className="mt-1 space-y-0.5">
          {alerts.map((a, i) => (
            <li key={i} className="text-sm">{a.ticker}: {a.message}</li>
          ))}
        </ul>
      </div>
      <button onClick={onDismiss} className="text-orange-400 hover:text-white text-xl leading-none">×</button>
    </div>
  )
}
