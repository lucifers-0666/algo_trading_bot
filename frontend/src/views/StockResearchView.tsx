import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  AlertOctagon,
  ShieldAlert,
  ShoppingCart,
  Compass,
  BarChart2,
  RefreshCw,
  Activity,
  Radio,
} from "lucide-react";
import { getInstrumentCandles, getMarketDepth } from "../lib/api";
import { CandlestickChart } from "../components/CandlestickChart";
import { Badge } from "../components/Badge";
import type { CandleRecord } from "../lib/types";

interface StockResearchViewProps {
  initialSymbol?: string;
  onNavigate: (page: string, symbol?: string) => void;
}

const DEFAULT_SYMBOLS = ["INFY", "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "TATAMOTORS"];
const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "1d", "1w"];

interface LiveQuotePacket {
  type: string;
  symbol: string;
  ltp: number;
  bid: number | null;
  ask: number | null;
  volume: number;
  timestamp: string;
  source: string;
}

export const StockResearchView: React.FC<StockResearchViewProps> = ({
  initialSymbol = "INFY",
  onNavigate,
}) => {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [timeframe, setTimeframe] = useState("1d");
  const [customInput, setCustomInput] = useState("");
  const [liveQuote, setLiveQuote] = useState<LiveQuotePacket | null>(null);
  const [wsStatus, setWsStatus] = useState<"CONNECTED" | "CONNECTING" | "DISCONNECTED">("DISCONNECTED");
  const [liveCandles, setLiveCandles] = useState<CandleRecord[]>([]);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["candles", symbol, timeframe],
    queryFn: () => getInstrumentCandles(symbol, 120, timeframe),
  });

  const { data: depthData, isLoading: isDepthLoading } = useQuery({
    queryKey: ["market-depth", symbol],
    queryFn: () => getMarketDepth(symbol),
    refetchInterval: 3000,
  });

  // Sync historical candles from REST query
  useEffect(() => {
    if (data?.candles) {
      setLiveCandles(data.candles);
    }
  }, [data]);

  // Real-time WebSocket connection to quotes feed
  useEffect(() => {
    let ws: WebSocket | null = null;
    let isCancelled = false;

    setWsStatus("CONNECTING");
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Connect to backend port 8000 or relative proxy
    const wsHost = window.location.port === "5173" ? "127.0.0.1:8000" : window.location.host;
    const wsUrl = `${wsProto}//${wsHost}/api/v1/ws/quotes/${symbol}`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!isCancelled) {
          setWsStatus("CONNECTED");
        }
      };

      ws.onmessage = (event) => {
        try {
          const packet = JSON.parse(event.data);
          if (packet.type === "quote" && packet.symbol === symbol) {
            setLiveQuote(packet);

            // Stream tick into latest candle close without full reload
            setLiveCandles((prev) => {
              if (!prev || prev.length === 0) return prev;
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              const last = updated[lastIdx];
              const currentLtp = packet.ltp;

              updated[lastIdx] = {
                ...last,
                close: currentLtp,
                high: Math.max(last.high, currentLtp),
                low: Math.min(last.low, currentLtp),
                volume: packet.volume > 0 ? packet.volume : last.volume,
              };
              return updated;
            });
          }
        } catch {
          // Ignore invalid parse
        }
      };

      ws.onerror = () => {
        if (!isCancelled) {
          setWsStatus("DISCONNECTED");
        }
      };

      ws.onclose = () => {
        if (!isCancelled) {
          setWsStatus("DISCONNECTED");
        }
      };
    } catch {
      setWsStatus("DISCONNECTED");
    }

    return () => {
      isCancelled = true;
      if (ws) {
        ws.close();
      }
    };
  }, [symbol]);

  const regime = data?.regime;
  const lastCandle = liveCandles && liveCandles.length > 0 ? liveCandles[liveCandles.length - 1] : null;
  const displayPrice = liveQuote?.ltp ?? lastCandle?.close ?? null;
  const dataSource = liveQuote?.source ?? data?.source ?? "SYNTHETIC";

  const handleSelectSymbol = (s: string) => {
    setSymbol(s);
    setLiveQuote(null);
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customInput.trim()) {
      setSymbol(customInput.trim().toUpperCase());
      setCustomInput("");
      setLiveQuote(null);
    }
  };

  return (
    <div className="view-container">
      {/* Symbol Selection Bar */}
      <div className="research-symbol-bar">
        <div className="symbol-pills">
          {DEFAULT_SYMBOLS.map((s) => (
            <button
              key={s}
              className={`symbol-pill ${symbol === s ? "symbol-pill-active" : ""}`}
              onClick={() => handleSelectSymbol(s)}
            >
              {s}
            </button>
          ))}
        </div>

        <form onSubmit={handleCustomSubmit} className="symbol-custom-form">
          <input
            type="text"
            placeholder="Other symbol..."
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
          />
          <button type="submit" className="button-secondary">Load</button>
        </form>

        <button
          className="button-secondary"
          onClick={() => void refetch()}
          disabled={isFetching}
          title="Refresh Data"
        >
          <RefreshCw size={14} className={isFetching ? "spin" : ""} /> Refresh
        </button>

        {lastCandle && (
          <button
            className="btn-action-primary"
            onClick={() => onNavigate("Trading terminal", symbol)}
            style={{ marginLeft: "auto" }}
          >
            <ShoppingCart size={14} /> Trade Setup
          </button>
        )}
      </div>

      {/* Live Stream Telemetry Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-lg border border-border bg-card text-xs mb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-medium">
            <Radio
              size={14}
              className={
                wsStatus === "CONNECTED"
                  ? "text-emerald-500 animate-pulse"
                  : wsStatus === "CONNECTING"
                  ? "text-amber-500 animate-spin"
                  : "text-muted-foreground"
              }
            />
            <span className={wsStatus === "CONNECTED" ? "text-emerald-500 font-semibold" : "text-muted-foreground"}>
              WS: {wsStatus}
            </span>
          </div>
          <span className="text-border">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Source Provenance:</span>
            <Badge variant={dataSource.toUpperCase() === "DHAN" ? "good" : "neutral"}>
              {dataSource.toUpperCase()}
            </Badge>
          </div>
          <span className="text-border">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Active Ticker:</span>
            <strong className="font-mono text-foreground font-semibold">{symbol}</strong>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {displayPrice !== null && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Live LTP:</span>
              <strong className="font-mono text-sm text-emerald-400 font-bold">
                ₹{displayPrice.toFixed(2)}
              </strong>
            </div>
          )}
          {liveQuote?.bid && liveQuote?.ask && (
            <div className="hidden sm:flex items-center gap-2 font-mono text-muted-foreground">
              <span>Bid: ₹{liveQuote.bid.toFixed(2)}</span>
              <span>·</span>
              <span>Ask: ₹{liveQuote.ask.toFixed(2)}</span>
            </div>
          )}
          {liveQuote?.timestamp && (
            <div className="text-muted-foreground text-[11px]">
              Tick: {new Date(liveQuote.timestamp).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST
            </div>
          )}
        </div>
      </div>

      {/* Timeframe Selector Bar */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-1.5 p-1 bg-card border border-border rounded-lg">
          <span className="text-xs text-muted-foreground px-2 font-medium">Resolution:</span>
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition-colors ${
                timeframe === tf
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              {tf.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="text-xs text-muted-foreground">
          Showing {liveCandles.length} candles ({timeframe.toUpperCase()})
        </div>
      </div>

      {/* Market Regime Banner */}
      {regime && (
        <div className="regime-banner">
          <div className="regime-left">
            <div className="regime-icon">
              {regime.trade_permission === "NO_TRADE" ? (
                <ShieldAlert size={22} className="text-bad" />
              ) : regime.trade_permission === "REDUCE_SIZE" ? (
                <AlertOctagon size={22} className="text-warning" />
              ) : (
                <Compass size={22} className="text-good" />
              )}
            </div>
            <div>
              <div className="regime-headline">
                <strong>MARKET REGIME: {regime.regime.replace(/_/g, " ")}</strong>
                <Badge
                  variant={
                    regime.trade_permission === "ALLOW_TRADING"
                      ? "good"
                      : regime.trade_permission === "REDUCE_SIZE"
                      ? "warning"
                      : "bad"
                  }
                >
                  {regime.trade_permission}
                </Badge>
              </div>
              <p className="regime-summary">{regime.summary}</p>
            </div>
          </div>

          <div className="regime-stats">
            <div className="regime-stat-item">
              <span>Trend Score</span>
              <strong>{(regime.trend_score * 100).toFixed(0)}%</strong>
            </div>
            <div className="regime-stat-item">
              <span>Volatility Ratio</span>
              <strong>{(regime.volatility_ratio * 100).toFixed(2)}%</strong>
            </div>
            <div className="regime-stat-item">
              <span>ADX Proxy</span>
              <strong>{regime.adx_estimate.toFixed(1)}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Chart Panel */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Technical Analysis & Multi-Pane Chart ({symbol} · {timeframe.toUpperCase()})</h2>
            <p>Candlesticks with SMA 20 (blue), SMA 50 (orange), Volume bars, and RSI(14) oscillator</p>
          </div>
          {displayPrice !== null && (
            <div className="chart-quick-stats">
              <span className="text-muted">Current LTP: </span>
              <strong>₹{displayPrice.toFixed(2)}</strong>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="table-empty">Computing quantitative features and rendering chart...</div>
        ) : liveCandles && liveCandles.length > 0 ? (
          <CandlestickChart candles={liveCandles} symbol={symbol} height={440} />
        ) : (
          <div className="table-empty">No candle data available for {symbol} at {timeframe}.</div>
        )}
      </section>

      {/* Technical Indicators Telemetry Grid */}
      {lastCandle && (
        <section className="metric-grid" style={{ marginTop: 16 }}>
          <article className="metric-card">
            <div className="metric-top">
              <span>RSI (14-BAR)</span>
              <div className="metric-icon"><TrendingUp size={16} /></div>
            </div>
            <div className="metric-value font-mono">
              {lastCandle.rsi_14 != null ? lastCandle.rsi_14.toFixed(1) : "—"}
            </div>
            <div className="metric-detail">
              {lastCandle.rsi_14 && lastCandle.rsi_14 > 70
                ? "Overbought Zone"
                : lastCandle.rsi_14 && lastCandle.rsi_14 < 30
                ? "Oversold Zone"
                : "Neutral Swing Zone (45-65 optimal)"}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>AVERAGE TRUE RANGE (ATR 14)</span>
              <div className="metric-icon"><BarChart2 size={16} /></div>
            </div>
            <div className="metric-value font-mono">
              ₹{lastCandle.atr_14 != null ? lastCandle.atr_14.toFixed(2) : "—"}
            </div>
            <div className="metric-detail">
              Volatility distance for 2x ATR stop: ₹{lastCandle.atr_14 ? (lastCandle.atr_14 * 2).toFixed(2) : "—"}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>TREND ALIGNMENT</span>
              <div className="metric-icon"><Compass size={16} /></div>
            </div>
            <div className="metric-value font-mono">
              {lastCandle.sma_20 && lastCandle.sma_50
                ? lastCandle.sma_20 > lastCandle.sma_50
                  ? "BULLISH CROSS"
                  : "BEARISH CROSS"
                : "PENDING"}
            </div>
            <div className="metric-detail font-mono">
              SMA20: ₹{lastCandle.sma_20?.toFixed(1) ?? "—"} · SMA50: ₹{lastCandle.sma_50?.toFixed(1) ?? "—"}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>RELATIVE VOLUME (RVOL)</span>
              <div className="metric-icon"><Activity size={16} /></div>
            </div>
            <div className="metric-value font-mono">
              {lastCandle.rvol != null ? `${lastCandle.rvol.toFixed(2)}x` : "—"}
            </div>
            <div className="metric-detail">
              {lastCandle.rvol && lastCandle.rvol > 1.2 ? "Strong volume surge" : "Normal liquidity pace"}
            </div>
          </article>
        </section>
      )}

      {/* 5-Level Market Depth & Microstructure Imbalance Section */}
      <section className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-100">
                Level-2 Market Depth Order Book & Microstructure Imbalance
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Live top-5 bid and ask liquidity levels from Angel One SmartAPI feed.
            </p>
          </div>

          {depthData && (
            <div className="flex items-center gap-3 font-mono text-xs">
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                <span className="text-slate-400">Spread:</span>
                <span className="text-slate-200 font-bold">₹{depthData.spread.toFixed(2)}</span>
                <span className="text-slate-500">({depthData.spread_pct.toFixed(2)}%)</span>
              </div>
              <Badge variant={depthData.source?.toLowerCase().includes("synthetic") ? "neutral" : "good"}>
                {depthData.source || "REAL-TIME"}
              </Badge>
            </div>
          )}
        </div>

        {isDepthLoading ? (
          <div className="p-6 text-center text-xs text-slate-400">Polling Level-2 order book depth...</div>
        ) : depthData && depthData.levels && depthData.levels.length > 0 ? (
          <div className="space-y-4">
            {/* Imbalance Meter */}
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <div className="flex justify-between text-xs font-mono mb-1.5">
                <span className="text-emerald-400 font-bold">
                  Bids: {depthData.total_bid_quantity.toLocaleString("en-IN")} ({((depthData.total_bid_quantity / (depthData.total_bid_quantity + depthData.total_ask_quantity || 1)) * 100).toFixed(1)}%)
                </span>
                <span className="text-slate-300 font-semibold">
                  Imbalance: {depthData.top5_imbalance > 0 ? "+" : ""}{depthData.top5_imbalance.toFixed(3)}
                </span>
                <span className="text-rose-400 font-bold">
                  Asks: {depthData.total_ask_quantity.toLocaleString("en-IN")} ({((depthData.total_ask_quantity / (depthData.total_bid_quantity + depthData.total_ask_quantity || 1)) * 100).toFixed(1)}%)
                </span>
              </div>

              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
                <div
                  className="bg-emerald-500 h-full transition-all duration-300"
                  style={{
                    width: `${((depthData.total_bid_quantity / (depthData.total_bid_quantity + depthData.total_ask_quantity || 1)) * 100)}%`,
                  }}
                />
                <div
                  className="bg-rose-500 h-full transition-all duration-300"
                  style={{
                    width: `${((depthData.total_ask_quantity / (depthData.total_bid_quantity + depthData.total_ask_quantity || 1)) * 100)}%`,
                  }}
                />
              </div>
            </div>

            {/* Depth Table: Bids vs Asks */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Bids Column */}
              <div className="overflow-x-auto rounded-lg border border-slate-800/80 bg-slate-950/50">
                <div className="px-3 py-1.5 bg-emerald-950/40 text-emerald-300 text-xs font-bold uppercase tracking-wider border-b border-slate-800 flex justify-between">
                  <span>Buyer Depth (Bids)</span>
                  <span className="font-mono">Best: ₹{depthData.best_bid.toFixed(2)}</span>
                </div>
                <table className="w-full text-xs text-left font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-1.5 px-3">Orders</th>
                      <th className="py-1.5 px-3 text-right">Qty</th>
                      <th className="py-1.5 px-3 text-right">Bid Price (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {depthData.levels.map((lvl) => (
                      <tr key={`bid-${lvl.level}`} className="hover:bg-slate-800/30">
                        <td className="py-1.5 px-3 text-slate-400">{lvl.bid_orders}</td>
                        <td className="py-1.5 px-3 text-right text-slate-200">
                          {lvl.bid_quantity.toLocaleString("en-IN")}
                        </td>
                        <td className="py-1.5 px-3 text-right text-emerald-400 font-bold">
                          {lvl.bid_price.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Asks Column */}
              <div className="overflow-x-auto rounded-lg border border-slate-800/80 bg-slate-950/50">
                <div className="px-3 py-1.5 bg-rose-950/40 text-rose-300 text-xs font-bold uppercase tracking-wider border-b border-slate-800 flex justify-between">
                  <span>Seller Depth (Asks)</span>
                  <span className="font-mono">Best: ₹{depthData.best_ask.toFixed(2)}</span>
                </div>
                <table className="w-full text-xs text-left font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-1.5 px-3">Ask Price (₹)</th>
                      <th className="py-1.5 px-3 text-right">Qty</th>
                      <th className="py-1.5 px-3 text-right">Orders</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {depthData.levels.map((lvl) => (
                      <tr key={`ask-${lvl.level}`} className="hover:bg-slate-800/30">
                        <td className="py-1.5 px-3 text-rose-400 font-bold">
                          {lvl.ask_price.toFixed(2)}
                        </td>
                        <td className="py-1.5 px-3 text-right text-slate-200">
                          {lvl.ask_quantity.toLocaleString("en-IN")}
                        </td>
                        <td className="py-1.5 px-3 text-right text-slate-400">{lvl.ask_orders}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 text-center text-xs text-slate-400">Order book depth currently unavailable.</div>
        )}
      </section>
    </div>
  );
};
