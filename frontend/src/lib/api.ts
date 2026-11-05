import type {
  ApiHealth,
  ApiStatus,
  MarketSession,
  DataHealth,
  ScanCandidate,
  Instrument,
  InstrumentDetailsResponse,
  InstrumentCandlesResponse,
  PortfolioState,
  Position,
  Order,
  Trade,
  OrderProposalRequest,
  OrderProposalResponse,
  OrderExecuteRequest,
  OrderExecuteResponse,
  StrategyDefinition,
  BacktestResponse,
  StrategyComparisonReport,
  ModelMetadata,
  AuditLog,
  FinancialEventItem,
  MarketSentimentSummary,
  SymbolSentiment,
  AIHealth,
  NewsAnalysisResult,
  SignalExplanationResult,
  StockDossierResult,
  LookaheadAuditResult,
  HyperoptLeaderboardResult,
  DecisionDossierResult,
  BotStatus,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let errDetail = `HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && typeof errJson === "object" && "detail" in errJson) {
        errDetail = String(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errDetail);
  }

  return response.json() as Promise<T>;
}

// 1. Health & Status
export function getApiHealth(signal?: AbortSignal): Promise<ApiHealth> {
  return fetchJson<ApiHealth>("/v1/health", { method: "GET", signal });
}

export function getApiStatus(signal?: AbortSignal): Promise<ApiStatus> {
  return fetchJson<ApiStatus>("/v1/status", { method: "GET", signal });
}

export function getMarketSession(signal?: AbortSignal): Promise<MarketSession> {
  return fetchJson<MarketSession>("/v1/market/session", { method: "GET", signal });
}

export function getDataHealth(signal?: AbortSignal): Promise<DataHealth> {
  return fetchJson<DataHealth>("/v1/data/health", { method: "GET", signal });
}

// 2. Market Scanner
export function getScannerCandidates(category = "all", signal?: AbortSignal): Promise<ScanCandidate[]> {
  const query = encodeURIComponent(category);
  return fetchJson<ScanCandidate[]>(`/v1/scanner/candidates?category=${query}`, { method: "GET", signal });
}

// 3. Instruments & Quotes
export function getInstruments(signal?: AbortSignal): Promise<Instrument[]> {
  return fetchJson<Instrument[]>("/v1/instruments", { method: "GET", signal });
}

export function getInstrumentDetails(symbol: string, signal?: AbortSignal): Promise<InstrumentDetailsResponse> {
  return fetchJson<InstrumentDetailsResponse>(`/v1/instruments/${encodeURIComponent(symbol)}`, { method: "GET", signal });
}

export function getInstrumentCandles(
  symbol: string,
  limit = 100,
  timeframe = "1d",
  signal?: AbortSignal
): Promise<InstrumentCandlesResponse> {
  return fetchJson<InstrumentCandlesResponse>(
    `/v1/instruments/${encodeURIComponent(symbol)}/candles?limit=${limit}&timeframe=${timeframe}`,
    { method: "GET", signal }
  );
}

// 4. Portfolio & Holdings
export function getPortfolio(signal?: AbortSignal): Promise<PortfolioState> {
  return fetchJson<PortfolioState>("/v1/portfolio", { method: "GET", signal });
}

export function getPositions(signal?: AbortSignal): Promise<Position[]> {
  return fetchJson<Position[]>("/v1/portfolio/positions", { method: "GET", signal });
}

// 5. Paper Trading Terminal & Orders
export function getOrders(limit = 50, signal?: AbortSignal): Promise<Order[]> {
  return fetchJson<Order[]>(`/v1/paper/orders?limit=${limit}`, { method: "GET", signal });
}

export function proposeOrder(req: OrderProposalRequest, signal?: AbortSignal): Promise<OrderProposalResponse> {
  return fetchJson<OrderProposalResponse>("/v1/paper/orders", {
    method: "POST",
    body: JSON.stringify(req),
    signal,
  });
}

export function executeOrder(req: OrderExecuteRequest, signal?: AbortSignal): Promise<OrderExecuteResponse> {
  return fetchJson<OrderExecuteResponse>("/v1/paper/execute", {
    method: "POST",
    body: JSON.stringify(req),
    signal,
  });
}

export function resetPaperAccount(confirmation = true, signal?: AbortSignal): Promise<{ success: boolean; message: string; portfolio: PortfolioState }> {
  return fetchJson<{ success: boolean; message: string; portfolio: PortfolioState }>("/v1/paper/reset", {
    method: "POST",
    body: JSON.stringify({ confirmation }),
    signal,
  });
}

export function getTrades(limit = 50, signal?: AbortSignal): Promise<Trade[]> {
  return fetchJson<Trade[]>(`/v1/paper/trades?limit=${limit}`, { method: "GET", signal });
}

// 6. Strategies & Backtests
export function getStrategies(signal?: AbortSignal): Promise<StrategyDefinition[]> {
  return fetchJson<StrategyDefinition[]>("/v1/strategies", { method: "GET", signal });
}

export function runBacktest(
  params: {
    strategy_name: string;
    symbols: string[];
    initial_capital?: number;
    brokerage_flat?: number;
    slippage_bps?: number;
  },
  signal?: AbortSignal
): Promise<BacktestResponse> {
  return fetchJson<BacktestResponse>("/v1/backtests/run", {
    method: "POST",
    body: JSON.stringify(params),
    signal,
  });
}

export function getStrategyComparison(symbols?: string, signal?: AbortSignal): Promise<StrategyComparisonReport> {
  const query = symbols ? `?symbols=${encodeURIComponent(symbols)}` : "";
  return fetchJson<StrategyComparisonReport>(`/v1/backtests/comparison${query}`, { method: "GET", signal });
}

// 7. Machine Learning
export function getModels(signal?: AbortSignal): Promise<ModelMetadata[]> {
  return fetchJson<ModelMetadata[]>("/v1/models", { method: "GET", signal });
}

export function trainModel(
  params: { symbol: string; model_type: string; horizon_bars: number },
  signal?: AbortSignal
): Promise<{ success: boolean; metadata: ModelMetadata }> {
  return fetchJson<{ success: boolean; metadata: ModelMetadata }>("/v1/models/train", {
    method: "POST",
    body: JSON.stringify(params),
    signal,
  });
}

// 8. Audit & Risk Kill-Switch
export function getAuditLogs(limit = 50, signal?: AbortSignal): Promise<AuditLog[]> {
  return fetchJson<AuditLog[]>(`/v1/audit?limit=${limit}`, { method: "GET", signal });
}

export function setKillSwitch(
  action: "engage" | "disengage",
  reason: string,
  signal?: AbortSignal
): Promise<{ active: boolean; reason: string }> {
  return fetchJson<{ active: boolean; reason: string }>("/v1/risk/kill-switch", {
    method: "POST",
    body: JSON.stringify({ action, reason }),
    signal,
  });
}

// 9. Financial Intelligence & News
export function getFinancialNews(category?: string, symbol?: string, limit = 50, signal?: AbortSignal): Promise<FinancialEventItem[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (symbol) params.set("symbol", symbol);
  params.set("limit", String(limit));
  return fetchJson<FinancialEventItem[]>(`/v1/intelligence/news?${params.toString()}`, { method: "GET", signal });
}

export function getFinancialSummary(signal?: AbortSignal): Promise<MarketSentimentSummary> {
  return fetchJson<MarketSentimentSummary>("/v1/intelligence/summary", { method: "GET", signal });
}

export function getSymbolSentiment(symbol: string, signal?: AbortSignal): Promise<SymbolSentiment> {
  return fetchJson<SymbolSentiment>(`/v1/intelligence/symbols/${encodeURIComponent(symbol)}`, { method: "GET", signal });
}

export function refreshFinancialNews(signal?: AbortSignal): Promise<{ success: boolean; new_events_ingested: number; refreshed_at: string }> {
  return fetchJson<{ success: boolean; new_events_ingested: number; refreshed_at: string }>("/v1/intelligence/refresh", {
    method: "POST",
    signal,
  });
}

// 10. Specialist Local Financial AI
export function getAiHealth(signal?: AbortSignal): Promise<AIHealth> {
  return fetchJson<AIHealth>("/v1/ai/health", { method: "GET", signal });
}

export function analyzeNews(
  payload: { headline: string; content?: string; symbol?: string },
  signal?: AbortSignal
): Promise<NewsAnalysisResult> {
  return fetchJson<NewsAnalysisResult>("/v1/ai/analyse-news", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function explainSignal(
  payload: {
    symbol: string;
    strategy_name: string;
    side: string;
    price: number;
    stop_loss: number;
    target?: number;
    indicators?: Record<string, any>;
  },
  signal?: AbortSignal
): Promise<SignalExplanationResult> {
  return fetchJson<SignalExplanationResult>("/v1/ai/explain-signal", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function getStockDossier(
  payload: { symbol: string; current_price?: number; regime?: string; news_headlines?: string[] },
  signal?: AbortSignal
): Promise<StockDossierResult> {
  return fetchJson<StockDossierResult>("/v1/ai/dossier", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

// 11. Strategy Auditing & Protections
export function auditStrategyLookahead(
  payload: { symbol: string; strategy_name?: string },
  signal?: AbortSignal
): Promise<LookaheadAuditResult> {
  return fetchJson<LookaheadAuditResult>("/v1/strategies/lookahead-audit", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function runStrategyHyperopt(
  payload: { symbols: string[]; max_trials?: number },
  signal?: AbortSignal
): Promise<HyperoptLeaderboardResult> {
  return fetchJson<HyperoptLeaderboardResult>("/v1/strategies/hyperopt", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function getProtectionStatus(signal?: AbortSignal): Promise<{
  is_locked: boolean;
  lock_reason?: string;
  consecutive_losses: number;
  symbols_in_cooldown: Record<string, string>;
}> {
  return fetchJson("/v1/strategies/protections", { method: "GET", signal });
}

export function resetProtections(signal?: AbortSignal): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>("/v1/strategies/protections/reset", {
    method: "POST",
    signal,
  });
}

// 12. Decision Support
export function evaluateDecision(
  payload: { symbol: string; price: number; stop_loss: number; target?: number; strategy_name?: string },
  signal?: AbortSignal
): Promise<DecisionDossierResult> {
  return fetchJson<DecisionDossierResult>("/v1/decision/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}


// 13. Autonomous Paper Trading Bot
export function getBotStatus(signal?: AbortSignal): Promise<BotStatus> {
  return fetchJson<BotStatus>("/v1/bot/status", { method: "GET", signal });
}

export function startBot(signal?: AbortSignal): Promise<{ status: string; message: string }> {
  return fetchJson<{ status: string; message: string }>("/v1/bot/start", { method: "POST", signal });
}

export function stopBot(signal?: AbortSignal): Promise<{ status: string; message: string }> {
  return fetchJson<{ status: string; message: string }>("/v1/bot/stop", { method: "POST", signal });
}

export function stepBot(signal?: AbortSignal): Promise<{ status: string; result: any }> {
  return fetchJson<{ status: string; result: any }>("/v1/bot/step", { method: "POST", signal });
}

export function configBot(
  payload: { force_market_open?: boolean; interval?: number },
  signal?: AbortSignal
): Promise<BotStatus> {
  return fetchJson<BotStatus>("/v1/bot/config", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}
