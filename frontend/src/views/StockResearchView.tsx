import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  AlertOctagon,
  ShieldAlert,
  ShoppingCart,
  Compass,
  BarChart2,
  RefreshCw,
} from "lucide-react";
import { getInstrumentCandles } from "../lib/api";
import { CandlestickChart } from "../components/CandlestickChart";
import { Badge } from "../components/Badge";

interface StockResearchViewProps {
  initialSymbol?: string;
  onNavigate: (page: string, symbol?: string) => void;
}

const DEFAULT_SYMBOLS = ["INFY", "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "TATAMOTORS"];

export const StockResearchView: React.FC<StockResearchViewProps> = ({
  initialSymbol = "INFY",
  onNavigate,
}) => {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [customInput, setCustomInput] = useState("");

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["candles", symbol],
    queryFn: () => getInstrumentCandles(symbol, 100),
  });

  const regime = data?.regime;
  const lastCandle = data?.candles && data.candles.length > 0 ? data.candles[data.candles.length - 1] : null;

  const handleSelectSymbol = (s: string) => {
    setSymbol(s);
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customInput.trim()) {
      setSymbol(customInput.trim().toUpperCase());
      setCustomInput("");
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
            <h2>Technical Analysis & Indicator Multi-Pane Chart ({symbol})</h2>
            <p>Daily candlesticks with SMA 20 (blue), SMA 50 (orange), Volume bars, and RSI(14) oscillator</p>
          </div>
          {lastCandle && (
            <div className="chart-quick-stats">
              <span className="text-muted">Latest Close: </span>
              <strong>₹{lastCandle.close.toFixed(2)}</strong>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="table-empty">Computing quantitative features and rendering chart...</div>
        ) : data?.candles ? (
          <CandlestickChart candles={data.candles} symbol={symbol} height={440} />
        ) : (
          <div className="table-empty">No candle data available for {symbol}.</div>
        )}
      </section>

      {/* Technical Indicators Telemetry Grid */}
      {lastCandle && (
        <section className="metric-grid" style={{ marginTop: 16 }}>
          <article className="metric-card">
            <div className="metric-top">
              <span>RSI (14-DAY)</span>
              <div className="metric-icon"><TrendingUp size={16} /></div>
            </div>
            <div className="metric-value">
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
            <div className="metric-value">
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
            <div className="metric-value">
              {lastCandle.sma_20 && lastCandle.sma_50
                ? lastCandle.sma_20 > lastCandle.sma_50
                  ? "BULLISH CROSS"
                  : "BEARISH CROSS"
                : "PENDING"}
            </div>
            <div className="metric-detail">
              SMA20: ₹{lastCandle.sma_20?.toFixed(1) ?? "—"} · SMA50: ₹{lastCandle.sma_50?.toFixed(1) ?? "—"}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>RELATIVE VOLUME (RVOL)</span>
              <div className="metric-icon"><BarChart2 size={16} /></div>
            </div>
            <div className="metric-value">
              {lastCandle.rvol != null ? `${lastCandle.rvol.toFixed(2)}x` : "—"}
            </div>
            <div className="metric-detail">
              {lastCandle.rvol && lastCandle.rvol > 1.2 ? "Strong volume surge" : "Normal liquidity pace"}
            </div>
          </article>
        </section>
      )}
    </div>
  );
};
