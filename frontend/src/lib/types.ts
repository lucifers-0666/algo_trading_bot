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
  timeframe?: string;
  source?: string;
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

export interface FinancialEventItem {
  event_id: string;
  source: string;
  category: string;
  headline: string;
  summary?: string | null;
  symbols: string[];
  sentiment_score: number;
  impact_level: "POSITIVE" | "NEGATIVE" | "NEUTRAL" | "HIGH_VOLATILITY";
  url?: string | null;
  published_at: string;
  created_at: string;
}

export interface MarketSentimentSummary {
  overall_sentiment_score: number;
  sentiment_label: "BULLISH" | "BEARISH" | "NEUTRAL";
  total_events_analyzed: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  category_breakdown: Record<string, number>;
}

export interface SymbolSentiment {
  symbol: string;
  sentiment_score: number;
  sentiment_label: string;
  events_count: number;
  recent_headlines: {
    headline: string;
    published_at: string;
    category: string;
    impact: string;
    score: number;
  }[];
}

export interface AIHealth {
  status: string;
  model_name: string;
  provider: string;
  gpu_acceleration: boolean;
  endpoint: string;
  latency_ms: number;
  details: string;
}

export interface NewsAnalysisResult {
  symbol?: string | null;
  sentiment_score: number;
  sentiment_label: string;
  impact_level: string;
  key_drivers: string[];
  risk_factors: string[];
  suggested_action: string;
  reasoning: string;
}

export interface SignalExplanationResult {
  symbol: string;
  strategy_name: string;
  thesis: string;
  technical_rationale: string[];
  risk_reward_assessment: string;
  caution_flags: string[];
  confidence_score: number;
  human_verdict: string;
}

export interface StockDossierResult {
  symbol: string;
  executive_summary: string;
  trend_verdict: string;
  sentiment_verdict: string;
  key_strengths: string[];
  key_risks: string[];
  trade_suitability: string;
  generated_at: string;
  ai_provider: string;
}

export interface LookaheadAuditResult {
  strategy_name: string;
  is_clean: boolean;
  total_bars_audited: number;
  discrepancies_count: number;
  discrepancies: {
    bar_index: number;
    timestamp: string;
    symbol: string;
    issue_type: string;
    details: string;
    indicators_diff: Record<string, any>;
  }[];
  verdict: string;
}

export interface HyperoptLeaderboardResult {
  strategy_name: string;
  trials_evaluated: number;
  best_params: Record<string, any>;
  best_score: number;
  best_metrics: Record<string, any>;
  leaderboard: {
    params: Record<string, any>;
    total_trades: number;
    win_rate_pct: number;
    total_return_pct: number;
    max_drawdown_pct: number;
    profit_factor: number;
    sortino_ratio: number;
    calmar_ratio: number;
    score: number;
  }[];
}

export interface DecisionDossierResult {
  symbol: string;
  action: "APPROVE_PAPER_BUY" | "WAIT_FOR_CONFIRMATION" | "REJECT";
  composite_score: number;
  technical_conviction: number;
  ml_conviction: number;
  sentiment_conviction: number;
  regime_conviction: number;
  entry_price: number;
  stop_loss: number;
  target: number;
  risk_reward_ratio: number;
  suggested_quantity: number;
  risk_approved: boolean;
  rejection_reasons: string[];
  key_catalysts: string[];
  caution_flags: string[];
  timestamp: string;
  human_confirmation_required: boolean;
}




export interface BotLogEntry {
  timestamp: string;
  event_type: string;
  symbol: string;
  message: string;
  details?: Record<string, any>;
}

export interface BotStatus {
  is_running: boolean;
  force_market_open: boolean;
  scan_interval_seconds: number;
  is_market_hours: boolean;
  effective_market_active: boolean;
  last_scan_time?: string;
  open_positions_count: number;
  cash_balance: number;
  total_equity: number;
  total_auto_trades: number;
  recent_logs: BotLogEntry[];
}

export interface MarketDepthLevel {
  level: number;
  bid_price: number;
  bid_quantity: number;
  bid_orders: number;
  ask_price: number;
  ask_quantity: number;
  ask_orders: number;
}

export interface MarketDepth {
  symbol: string;
  exchange: string;
  levels: MarketDepthLevel[];
  best_bid: number;
  best_ask: number;
  spread: number;
  spread_pct: number;
  total_bid_quantity: number;
  total_ask_quantity: number;
  top5_imbalance: number;
  timestamp: string;
  source: string;
  warning?: string;
}

export interface MarketDataStatus {
  active_provider_setting: string;
  resolved_source_type: string;
  is_live: boolean;
  is_configured: boolean;
  is_connected: boolean;
  angelone: {
    configured: boolean;
    connected: boolean;
    source: string;
    free_data_feed: boolean;
  };
  dhan: {
    configured: boolean;
    connected: boolean;
    source: string;
  };
  truedata: {
    configured: boolean;
    connected: boolean;
  };
  csv_available: boolean;
  synthetic_ready: boolean;
  data_provenance: "REAL_TIME" | "SYNTHETIC" | "OFFLINE";
  disclaimer: string;
  last_update: string;
}

export interface BaselineComparison {
  zero_return_direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  persistence_direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  trend_following_direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  model_beats_persistence_historical: boolean;
  model_beats_zero_return_historical: boolean;
}

export interface NextSessionForecast {
  forecast_id: string;
  symbol: string;
  generated_at: string;
  target_date: string;
  current_price: number;
  direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  prob_up: number;
  prob_down: number;
  expected_return_pct: number;
  expected_range_low: number;
  expected_range_high: number;
  confidence_score: number;
  atr_volatility_pct: number;
  historical_volatility_20d: number;
  primary_technical_drivers: string[];
  baselines: BaselineComparison;
  model_type: string;
  disclaimer: string;
}

export interface ForecastLedgerEntry {
  forecast_id: string;
  symbol: string;
  generated_at: string;
  target_date: string;
  forecast_price: number;
  predicted_direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  prob_up: number;
  expected_return_pct: number;
  expected_range_low: number;
  expected_range_high: number;
  status: "PENDING" | "EVALUATED" | "EXPIRED";
  realized_close?: number | null;
  realized_high?: number | null;
  realized_low?: number | null;
  realized_return_pct?: number | null;
  direction_hit?: boolean | null;
  range_hit?: boolean | null;
  absolute_error_pct?: number | null;
  evaluated_at?: string | null;
}

export interface ForecastHistoryResponse {
  symbol?: string;
  total_records: number;
  evaluated_records: number;
  historical_accuracy_pct: number;
  entries: ForecastLedgerEntry[];
}

export interface TradeCostBreakdown {
  broker: string;
  trade_type: string;
  side: "BUY" | "SELL";
  gross_price: number;
  effective_price: number;
  quantity: number;
  gross_trade_value: number;
  slippage_inr: number;
  market_impact_inr: number;
  brokerage_inr: number;
  stt_inr: number;
  exchange_charges_inr: number;
  sebi_charges_inr: number;
  stamp_duty_inr: number;
  gst_inr: number;
  dp_charges_inr: number;
  statutory_charges_inr: number;
  total_statutory_taxes: number;
  broker_charges_inr: number;
  total_costs_inr: number;
  net_trade_amount: number;
}

export interface RoundtripSimulation {
  symbol: string;
  broker: string;
  trade_type: string;
  quantity: number;
  buy_price: number;
  sell_price: number;
  gross_pnl: number;
  gross_pnl_pct: number;
  total_brokerage: number;
  total_stt: number;
  total_exchange_txn: number;
  total_sebi: number;
  total_stamp_duty: number;
  total_gst: number;
  total_dp_charges: number;
  total_statutory_taxes: number;
  total_costs: number;
  net_pnl: number;
  net_pnl_pct: number;
  breakeven_sell_price: number;
  buy_costs: TradeCostBreakdown;
  sell_costs: TradeCostBreakdown;
}
