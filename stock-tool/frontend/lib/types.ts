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

// ── Virtual Trading / Portfolio ─────────────────────────────────────────────

export interface Account {
  id: string
  name: string
  cash_balance: number
  initial_cash: number
  created_at: string
}

export interface Position {
  ticker: string
  name: string
  qty: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  signal_label_short?: string
  signal_color_short?: "green" | "yellow" | "red"
}

export interface NavPoint {
  date: string
  cash: number
  market_value: number
  total_value: number
}

export interface Order {
  id: string
  account_id: string
  ticker: string
  side: "buy" | "sell"
  order_type: "market" | "limit"
  qty: number
  limit_price?: number
  status: "pending" | "queued" | "filled" | "cancelled" | "rejected"
  filled_price?: number
  filled_at?: string
  created_at: string
}

export interface PlaceOrderRequest {
  ticker: string
  side: "buy" | "sell"
  order_type: "market" | "limit"
  qty: number
  limit_price?: number
}

export interface OrderFilter {
  status?: string
  side?: string
  limit?: number
}

export interface Performance {
  total_trades: number
  total_buys: number
  total_sells: number
  total_return_pct: number
  realized_pnl: number
  unrealized_pnl: number
  signal_win_rate: number
}
