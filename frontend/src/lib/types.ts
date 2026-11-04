export type DataSource = "REAL-TIME" | "HISTORICAL" | "DELAYED" | "CACHED" | "SYNTHETIC" | "UNAVAILABLE";

export interface ApiHealth {
  status: "ok" | "degraded";
  mode: "paper";
  service: string;
  timestamp: string;
}

export interface ApiStatus {
  mode: string;
  real_order_routing_enabled: boolean;
  market_data_provider: string;
  market_data_status: string;
  scanner_status: string;
  ml_inference_status: string;
  kill_switch_active: boolean;
  kill_switch_reason: string;
}

export interface MarketSession {
  is_open: boolean;
  current_time_ist: string;
  regular_hours: string;
  is_trading_day: boolean;
  next_session_open: string;
  statutory_holidays_count: number;
}

export interface DataHealth {
  data_source_label: string;
  feed_status: "HEALTHY" | "DELAYED" | "STALE" | "DISCONNECTED";
  is_actionable: boolean;
  latency_seconds: number;
  message: string;
}

export interface ScanCandidate {
  symbol: string;
  latest_price: number;
  pct_change_1d: number;
  volume: number;
  rvol: number;
  indicators: Record<string, number>;
  timestamp: string;
  source: string;
  scan_category: string;
  is_qualified: boolean;
  inclusion_reasons: string[];
  exclusion_reasons: string[];
}

export interface Instrument {
  symbol: string;
  name: string;
  series: string;
  isin?: string;
  tick_size: number;
  lot_size: number;
  is_active: boolean;
  industry?: string;
}

export interface InstrumentDetailsResponse {
  instrument: Instrument;
  quote: {
    symbol: string;
    ltp: number;
    bid?: number;
    ask?: number;
    volume?: number;
    timestamp?: string;
    source: string;
  };
}

export interface CandleRecord {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma_20?: number | null;
  sma_50?: number | null;
  rsi_14?: number | null;
  atr_14?: number | null;
  rvol?: number | null;
}

export interface RegimeAssessment {
  regime: "BULL_TRENDING" | "BEAR_TRENDING" | "SIDEWAYS_CONSOLIDATION" | "HIGH_VOLATILITY" | "LOW_VOLATILITY";
  trade_permission: "ALLOW_TRADING" | "REDUCE_SIZE" | "NO_TRADE";
  trend_score: number;
  volatility_ratio: number;
  adx_estimate: number;
  summary: string;
  reasons: string[];
}

export interface InstrumentCandlesResponse {
  symbol: string;
  count: number;
  regime: RegimeAssessment;
  candles: CandleRecord[];
}

export interface Position {
  symbol: string;
  quantity: number;
  average_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  open_timestamp: string;
  updated_timestamp: string;
}

export interface PortfolioState {
  starting_cash: number;
  cash_balance: number;
  day_starting_equity: number;
  last_day_reset: string;
  reserved_margin: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_equity: number;
  peak_equity: number;
  max_drawdown_pct: number;
  open_positions_count: number;
  updated_at: string;
}

export interface Order {
  order_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  order_type: "MARKET" | "LIMIT" | "STOP_LOSS";
  quantity: number;
  limit_price?: number | null;
  stop_price?: number | null;
  status: "PENDING" | "FILLED" | "REJECTED" | "CANCELLED";
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Trade {
  trade_id: string;
  order_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  slippage_inr: number;
  brokerage_inr: number;
  stt_inr: number;
  exchange_charges_inr: number;
  gst_inr: number;
  stamp_duty_inr: number;
  total_costs_inr: number;
  net_value_inr: number;
  timestamp: string;
}

export interface OrderProposalRequest {
  symbol: string;
  side: "BUY" | "SELL";
  price: number;
  stop_loss?: number | null;
  quantity?: number | null;
  order_type?: "MARKET" | "LIMIT" | "STOP_LOSS";
}

export interface OrderProposalResponse {
  symbol: string;
  side: string;
  approved: boolean;
  approved_quantity: number;
  rejection_reasons: string[];
  sizing?: {
    approved: boolean;
    quantity: number;
    entry_price: number;
    stop_loss: number;
    risk_budget_inr: number;
    calculated_risk_inr: number;
    allocated_capital_inr: number;
    reason: string;
  } | null;
}

export interface OrderExecuteRequest {
  symbol: string;
  side: "BUY" | "SELL";
  price: number;
  stop_loss?: number | null;
  quantity?: number | null;
  order_type?: "MARKET" | "LIMIT" | "STOP_LOSS";
}

export interface OrderExecuteResponse {
  success: boolean;
  order: Order;
  trade?: Trade | null;
  risk_assessment: {
    approved: boolean;
    approved_quantity: number;
    rejection_reasons: string[];
    risk_amount_inr: number;
  };
}

export interface StrategyDefinition {
  id: string;
  name: string;
  description: string;
  default_params: Record<string, any>;
}

export interface BacktestPerformanceMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  cagr_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  max_drawdown_duration_bars: number;
  win_rate_pct: number;
  profit_factor: number;
  expectancy_inr: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  gross_pnl_inr: number;
  net_pnl_inr: number;
  total_costs_paid_inr: number;
  total_brokerage_inr: number;
  total_stt_inr: number;
  total_exchange_charges_inr: number;
  total_gst_inr: number;
  total_stamp_duty_inr: number;
  total_slippage_inr: number;
  average_holding_bars: number;
}

export interface BacktestTradeRecord {
  symbol: string;
  entry_timestamp: string;
  entry_price: number;
  exit_timestamp: string;
  exit_price: number;
  quantity: number;
  gross_pnl: number;
  net_pnl: number;
  total_costs: number;
  return_pct: number;
  holding_bars: number;
  exit_reason: string;
}

export interface BacktestResponse {
  strategy_name: string;
  metrics: BacktestPerformanceMetrics;
  equity_curve: { date: string; equity: number }[];
  trade_records: BacktestTradeRecord[];
}

export interface StrategyComparisonRow {
  strategy_name: string;
  total_net_return_pct: number;
  net_pnl_inr: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  win_rate_pct: number;
  profit_factor: number;
  expectancy_inr: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_costs_inr: number;
  average_holding_bars: number;
}

export interface StrategyComparisonReport {
  initial_capital: number;
  test_symbols: string[];
  start_date: string;
  end_date: string;
  benchmark_buy_hold_return_pct: number;
  comparison_table: StrategyComparisonRow[];
}

export interface ModelMetadata {
  model_id: string;
  model_type: string;
  trained_at: string;
  feature_names: string[];
  train_samples: number;
  test_samples: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  metrics: {
    accuracy?: number | null;
    precision?: number | null;
    recall?: number | null;
    f1?: number | null;
    roc_auc?: number | null;
    pr_auc?: number | null;
    brier_score?: number | null;
    precision_at_k?: number | null;
  };
  artifact_path: string;
}

export interface AuditLog {
  event_id: string;
  event_type: string;
  symbol?: string | null;
  details: Record<string, any>;
  timestamp: string;
}

