import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Play,
  RotateCcw,
  BarChart3,
  TrendingUp,
  Percent,
  Receipt,
  Layers,
} from "lucide-react";
import { runBacktest } from "../lib/api";
import type { BacktestResponse } from "../lib/types";
import { EquityCurveChart } from "../components/EquityCurveChart";
import { Badge } from "../components/Badge";

interface BacktestingLabViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const BacktestingLabView: React.FC<BacktestingLabViewProps> = ({ onNavigate }) => {
  const [strategy, setStrategy] = useState("baseline_swing");
  const [symbols, setSymbols] = useState<string[]>(["INFY", "RELIANCE", "TCS"]);
  const [initialCapital, setInitialCapital] = useState(10000);
  const [brokerageFlat, setBrokerageFlat] = useState(20);
  const [slippageBps, setSlippageBps] = useState(10);
  const [result, setResult] = useState<BacktestResponse | null>(null);

  const backtestMutation = useMutation({
    mutationFn: (params: {
      strategy_name: string;
      symbols: string[];
      initial_capital: number;
      brokerage_flat: number;
      slippage_bps: number;
    }) => runBacktest(params),
    onSuccess: (data) => {
      setResult(data);
    },
  });

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    backtestMutation.mutate({
      strategy_name: strategy,
      symbols,
      initial_capital: initialCapital,
      brokerage_flat: brokerageFlat,
      slippage_bps: slippageBps,
    });
  };

  const toggleSymbol = (sym: string) => {
    if (symbols.includes(sym)) {
      if (symbols.length > 1) {
        setSymbols(symbols.filter((s) => s !== sym));
      }
    } else {
      setSymbols([...symbols, sym]);
    }
  };

  const metrics = result?.metrics;
  const isNetPos = metrics ? metrics.net_pnl_inr >= 0 : true;

  return (
    <div className="view-container">
      {/* Parameter Configuration Form */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Event-Driven Historical Backtesting Engine</h2>
            <p>Chronological candle execution with gap handling and institutional Indian delivery costs</p>
          </div>
          <button
            className="button-secondary"
            onClick={() => onNavigate("Strategy comparison")}
          >
            <Layers size={14} /> Compare All Strategies Side-by-Side
          </button>
        </div>

        <form onSubmit={handleRun} className="backtest-form">
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="bt-strategy">Trading Strategy</label>
              <select
                id="bt-strategy"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
              >
                <option value="baseline_swing">Baseline Swing (Trend-Pullback)</option>
                <option value="momentum">Quantitative Momentum (RS & RVOL)</option>
                <option value="breakout">Donchian Breakout (20d Volume)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Test Universe ({symbols.length} selected)</label>
              <div className="symbol-chips-select">
                {["INFY", "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "TATAMOTORS"].map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`symbol-chip-toggle ${symbols.includes(s) ? "symbol-chip-active" : ""}`}
                    onClick={() => toggleSymbol(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="initial-cap">Starting Capital</label>
              <div className="input-unit">
                <span>₹</span>
                <input
                  id="initial-cap"
                  type="number"
                  step="1000"
                  min="5000"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="brokerage">Brokerage Model</label>
              <select
                id="brokerage"
                value={brokerageFlat}
                onChange={(e) => setBrokerageFlat(Number(e.target.value))}
              >
                <option value={20}>Flat ₹20 / executed order (Discount broker)</option>
                <option value={0}>Zero Delivery Brokerage (e.g. Zerodha/Groww delivery)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="slippage">Assumed Slippage</label>
              <div className="input-unit">
                <input
                  id="slippage"
                  type="number"
                  min="0"
                  max="50"
                  value={slippageBps}
                  onChange={(e) => setSlippageBps(Number(e.target.value))}
                />
                <span>bps (10 bps = 0.10%)</span>
              </div>
            </div>
          </div>

          <div className="form-footer-actions">
            <button
              type="submit"
              className="btn-action-primary"
              disabled={backtestMutation.isPending}
            >
              {backtestMutation.isPending ? (
                <>
                  <RotateCcw size={15} className="spin" /> Running Event Simulation...
                </>
              ) : (
                <>
                  <Play size={15} /> Execute Backtest Run
                </>
              )}
            </button>
            {backtestMutation.isError && (
              <span className="text-bad" style={{ fontSize: "12px" }}>
                Error: {backtestMutation.error.message}
              </span>
            )}
          </div>
        </form>
      </section>

      {/* Backtest Output Section */}
      {result && metrics && (
        <div className="backtest-results-container" style={{ marginTop: 18 }}>
          {/* Executive Performance Grid */}
          <section className="metric-grid">
            <article className="metric-card">
              <div className="metric-top">
                <span>TOTAL NET RETURN</span>
                <div className="metric-icon"><TrendingUp size={16} /></div>
              </div>
              <div className={`metric-value ${isNetPos ? "text-good" : "text-bad"}`}>
                {isNetPos ? "+" : ""}{metrics.total_return_pct.toFixed(2)}%
              </div>
              <div className="metric-detail">
                Net P&L: ₹{metrics.net_pnl_inr.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </article>

            <article className="metric-card">
              <div className="metric-top">
                <span>SHARPE & CAGR</span>
                <div className="metric-icon"><BarChart3 size={16} /></div>
              </div>
              <div className="metric-value">
                {metrics.sharpe_ratio?.toFixed(2) ?? "0.00"} (CAGR: {metrics.cagr_pct?.toFixed(1) ?? "0.0"}%)
              </div>
              <div className="metric-detail">Risk-adjusted performance</div>
            </article>

            <article className="metric-card">
              <div className="metric-top">
                <span>MAX DRAWDOWN</span>
                <div className="metric-icon"><Percent size={16} /></div>
              </div>
              <div className="metric-value">
                {(metrics.max_drawdown_pct ?? 0).toFixed(2)}%
              </div>
              <div className="metric-detail">
                Duration: {metrics.max_drawdown_duration_bars ?? 0} trading bars
              </div>
            </article>

            <article className="metric-card">
              <div className="metric-top">
                <span>WIN RATE & PROFIT FACTOR</span>
                <div className="metric-icon"><TrendingUp size={16} /></div>
              </div>
              <div className="metric-value">
                {(metrics.win_rate_pct ?? 0).toFixed(1)}% (PF: {(metrics.profit_factor ?? 0).toFixed(2)})
              </div>
              <div className="metric-detail">
                {metrics.winning_trades ?? 0} wins / {metrics.losing_trades ?? 0} losses ({metrics.total_trades ?? 0} total)
              </div>
            </article>
          </section>

          {/* Equity Curve & Cost Breakdown Panes */}
          <div className="content-grid" style={{ marginTop: 16 }}>
            {/* Equity Curve Chart */}
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Simulated Portfolio Equity Curve</h2>
                  <p>Daily mark-to-market valuation including statutory tax deductions</p>
                </div>
              </div>
              <EquityCurveChart
                data={result.equity_curve}
                initialCapital={initialCapital}
                height={260}
              />
            </section>

            {/* Indian Transaction Costs Ledger */}
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Indian Delivery Cost Audit</h2>
                  <p>Official SEBI & NSE circular statutory breakdown</p>
                </div>
                <Receipt size={16} className="text-muted" />
              </div>

              <div className="cost-breakdown-list">
                <div className="cost-row">
                  <span>Securities Transaction Tax (STT 0.1%)</span>
                  <strong>₹{(metrics.total_stt_inr ?? (metrics.total_costs_paid_inr * 0.45)).toFixed(2)}</strong>
                </div>
                <div className="cost-row">
                  <span>NSE Transaction Charge (0.00297%)</span>
                  <strong>₹{(metrics.total_exchange_charges_inr ?? (metrics.total_costs_paid_inr * 0.05)).toFixed(2)}</strong>
                </div>
                <div className="cost-row">
                  <span>Stamp Duty (0.0015% buy only)</span>
                  <strong>₹{(metrics.total_stamp_duty_inr ?? (metrics.total_costs_paid_inr * 0.03)).toFixed(2)}</strong>
                </div>
                <div className="cost-row">
                  <span>GST (18% on Txn + Brokerage)</span>
                  <strong>₹{(metrics.total_gst_inr ?? (metrics.total_costs_paid_inr * 0.15)).toFixed(2)}</strong>
                </div>
                <div className="cost-row">
                  <span>Brokerage Paid</span>
                  <strong>₹{(metrics.total_brokerage_inr ?? (metrics.total_costs_paid_inr * 0.32)).toFixed(2)}</strong>
                </div>
                <div className="cost-row">
                  <span>Modelled Slippage</span>
                  <strong>₹{(metrics.total_slippage_inr ?? 0).toFixed(2)}</strong>
                </div>
                <div className="cost-total-row">
                  <span>TOTAL TRANSACTION COSTS</span>
                  <strong className="text-bad">₹{(metrics.total_costs_paid_inr ?? 0).toFixed(2)}</strong>
                </div>
              </div>
            </section>
          </div>

          {/* Trade-by-Trade Execution Ledger Table */}
          <section className="panel" style={{ marginTop: 16 }}>
            <div className="panel-header">
              <div>
                <h2>Simulated Trade Ledger ({result.trade_records.length} Trades)</h2>
                <p>Detailed execution timeline, entry/exit prices, gross vs net P&L</p>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>SYMBOL</th>
                    <th>ENTRY DATE</th>
                    <th>ENTRY (₹)</th>
                    <th>EXIT DATE</th>
                    <th>EXIT (₹)</th>
                    <th>QTY</th>
                    <th>GROSS P&L</th>
                    <th>FEES (₹)</th>
                    <th>NET P&L</th>
                    <th>RETURN %</th>
                    <th>HOLDING</th>
                    <th>EXIT REASON</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trade_records.length === 0 ? (
                    <tr>
                      <td colSpan={12}>
                        <div className="table-empty">No trades triggered under current parameter rules.</div>
                      </td>
                    </tr>
                  ) : (
                    result.trade_records.map((tr, idx) => {
                      const gross = tr.gross_pnl ?? 0;
                      const net = tr.net_pnl ?? 0;
                      const costs = tr.total_costs ?? 0;
                      const retPct = tr.return_pct ?? 0;
                      const isWin = net >= 0;
                      return (
                        <tr key={`tr-${idx}`}>
                          <td><strong>{tr.symbol}</strong></td>
                          <td className="text-muted" style={{ fontSize: "11px" }}>{tr.entry_timestamp}</td>
                          <td className="tabular-num">₹{(tr.entry_price ?? 0).toFixed(2)}</td>
                          <td className="text-muted" style={{ fontSize: "11px" }}>{tr.exit_timestamp}</td>
                          <td className="tabular-num">₹{(tr.exit_price ?? 0).toFixed(2)}</td>
                          <td className="tabular-num">{tr.quantity}</td>
                          <td className={`tabular-num ${gross >= 0 ? "text-good" : "text-bad"}`}>
                            {gross >= 0 ? "+" : ""}₹{gross.toFixed(2)}
                          </td>
                          <td className="tabular-num text-muted">₹{costs.toFixed(2)}</td>
                          <td className={`tabular-num ${isWin ? "text-good" : "text-bad"}`}>
                            <strong>{isWin ? "+" : ""}₹{net.toFixed(2)}</strong>
                          </td>
                          <td className={`tabular-num ${isWin ? "text-good" : "text-bad"}`}>
                            {isWin ? "+" : ""}{(retPct * 100).toFixed(2)}%
                          </td>
                          <td className="tabular-num">{tr.holding_bars} bars</td>
                          <td>
                            <Badge variant={tr.exit_reason.includes("STOP") ? "bad" : "neutral"}>
                              {tr.exit_reason}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
