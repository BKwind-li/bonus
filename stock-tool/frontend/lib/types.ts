export interface IndicatorResult {
  name: string
  raw_value: string
  description: string
  contribution: number
}

export interface SignalScore {
  score: number
  label: string
  color: "green" | "yellow" | "red"
  indicators: IndicatorResult[]
}

export interface SignalResult {
  ticker: string
  name: string
  sector: string
  market: "stock" | "forex"
  price: number
  change_pct: number
  short_term: SignalScore
  long_term: SignalScore
  scanned_at: string
  // DB fields (scanner results)
  short_score?: number
  short_label?: string
  short_color?: string
  long_score?: number
  long_label?: string
  long_color?: string
  short_indicators?: IndicatorResult[]
  long_indicators?: IndicatorResult[]
}

export interface WatchlistItem {
  ticker: string
  name: string
  market: string
  sector: string
  added_at?: string
}

export interface PriceAlert {
  id: number
  ticker: string
  condition: "above" | "below"
  threshold: number
  active: boolean
  created_at: string
}

export interface SignalAlert {
  id: number
  ticker: string
  condition: "any_change" | "strong_only" | "rsi_extreme"
  active: boolean
  created_at: string
}

export interface AlertHistoryItem {
  id: number
  ticker: string
  alert_type: string
  message: string
  triggered_at: string
  read: boolean
}
