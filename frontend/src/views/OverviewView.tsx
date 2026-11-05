import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Wallet,
  Activity,
  Gauge,
  Database,
  ShieldCheck,
  TrendingUp,
  Clock,
  ArrowRight,
  CandlestickChart,
  Wifi,
  Bot,
  Play,
  Pause,
} from "lucide-react";
import {
  getPortfolio,
  getMarketSession,
  getDataHealth,
  getScannerCandidates,
  getOrders,
  getBotStatus,
  startBot,
  stopBot,
} from "../lib/api";
import { Badge } from "../components/Badge";

interface OverviewViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({ onNavigate }) => {
  const queryClient = useQueryClient();

  const { data: botStatus } = useQuery({
    queryKey: ["botStatus"],
    queryFn: () => getBotStatus(),
    refetchInterval: 3000,
  });

  const startBotMutation = useMutation({
    mutationFn: () => startBot(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  const stopBotMutation = useMutation({
    mutationFn: () => stopBot(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => getPortfolio(),
    refetchInterval: 5000,
  });

  const { data: session } = useQuery({
    queryKey: ["market-session"],
    queryFn: () => getMarketSession(),
    refetchInterval: 15000,
  });

  const { data: dataHealth } = useQuery({
    queryKey: ["data-health"],
    queryFn: () => getDataHealth(),
    refetchInterval: 10000,
  });

  const { data: candidates } = useQuery({
    queryKey: ["scanner-preview"],
    queryFn: () => getScannerCandidates("all"),
    refetchInterval: 15000,
  });

  const { data: orders } = useQuery({
    queryKey: ["orders-preview"],
    queryFn: () => getOrders(5),
    refetchInterval: 5000,
  });

  const equity = portfolio?.total_equity ?? 10000;
  const startingEquity = portfolio?.day_starting_equity ?? 10000;
  const dayPnl = equity - startingEquity;
  const dayPnlPct = startingEquity > 0 ? (dayPnl / startingEquity) * 100 : 0;
  const isPnlPositive = dayPnl >= 0;

  return (
    <div className="view-container">
      {/* Simulation Safety Banner */}
      <div className="notice-bar">
        <div className="notice-icon">
          <ShieldCheck size={18} />
        </div>
        <div>
          <strong>Strict Virtual Paper-Trading Mode</strong>
          <span>Simulated execution with realistic statutory Indian delivery costs and strict risk limits. No real capital or broker routing is enabled.</span>
        </div>
        <span className="notice-status">ISOLATED SIMULATION</span>
      </div>

      {/* Autonomous Bot Banner */}
      <div className="bg-card border border-border rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${botStatus?.is_running ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}>
            <Bot size={22} />
          </div>
          <div>
            <div className="text-sm font-bold text-foreground flex items-center gap-2">
              Autonomous Paper Trading Bot
              <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-semibold ${botStatus?.is_running ? "bg-green-100 text-green-800 animate-pulse" : "bg-amber-100 text-amber-800"}`}>
                {botStatus?.is_running ? "● BOT ACTIVE & TRADING" : "○ BOT PAUSED / IDLE"}
              </span>
            </div>
            <div className="text-xs text-muted mt-0.5">
              {botStatus?.is_running
                ? `Scanning every ${botStatus.scan_interval_seconds}s for NSE momentum/swing setups & managing trailing stops.`
                : "The autonomous bot is currently paused. Click 'Start Auto-Trader' or open the Bot Controller to activate automated simulated trading."}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {botStatus?.is_running ? (
            <button
              onClick={() => stopBotMutation.mutate()}
              disabled={stopBotMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 transition"
            >
              <Pause size={14} /> Pause Bot
            </button>
          ) : (
            <button
              onClick={() => startBotMutation.mutate()}
              disabled={startBotMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-700 text-white hover:bg-green-800 transition"
            >
              <Play size={14} /> Start Auto-Trader
            </button>
          )}
          <button
            onClick={() => onNavigate("Auto-trading bot")}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-card hover:bg-muted/10 transition"
          >
            Open Bot Controller <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Top Metric Grid */}
      <section className="metric-grid" aria-label="Paper account overview">
        <article className="metric-card">
          <div className="metric-top">
            <span>TOTAL VIRTUAL EQUITY</span>
            <div className="metric-icon"><Wallet size={16} /></div>
          </div>
          <div className="metric-value">
            ₹{equity.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-detail">Starting Capital: ₹10,000.00</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>AVAILABLE CASH</span>
            <div className="metric-icon"><Database size={16} /></div>
          </div>
          <div className="metric-value">
            ₹{(portfolio?.cash_balance ?? 10000).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-detail">Reserved Margin: ₹{(portfolio?.reserved_margin ?? 0).toFixed(2)}</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>TODAY'S INTRADAY P&L</span>
            <div className="metric-icon"><TrendingUp size={16} /></div>
          </div>
          <div className={`metric-value ${isPnlPositive ? "text-good" : "text-bad"}`}>
            {isPnlPositive ? "+" : ""}₹{dayPnl.toFixed(2)}
            <span className="metric-pct"> ({isPnlPositive ? "+" : ""}{dayPnlPct.toFixed(2)}%)</span>
          </div>
          <div className="metric-detail">vs Day Starting: ₹{startingEquity.toFixed(2)}</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>MAX DRAWDOWN</span>
            <div className="metric-icon"><Gauge size={16} /></div>
          </div>
          <div className="metric-value">
            {(portfolio?.max_drawdown_pct ?? 0).toFixed(2)}%
          </div>
          <div className="metric-detail">Peak: ₹{(portfolio?.peak_equity ?? 10000).toFixed(2)}</div>
        </article>
      </section>

      {/* Market Telemetry Row */}
      <div className="telemetry-bar">
        <div className="telemetry-item">
          <Clock size={15} />
          <span>NSE Session:</span>
          <strong>{session?.is_open ? "OPEN (09:15-15:30 IST)" : "CLOSED"}</strong>
          <Badge variant={session?.is_open ? "good" : "neutral"}>
            {session?.is_open ? "Active" : "Closed"}
          </Badge>
        </div>

        <div className="telemetry-divider" />

        <div className="telemetry-item">
          <Wifi size={15} />
          <span>Feed Provenance:</span>
          <strong>{dataHealth?.data_source_label ?? "SYNTHETIC"}</strong>
          <Badge variant={dataHealth?.feed_status === "HEALTHY" ? "good" : "warning"}>
            {dataHealth?.feed_status ?? "HEALTHY"} ({dataHealth?.latency_seconds ?? 0}s latency)
          </Badge>
        </div>

        <div className="telemetry-divider" />

        <div className="telemetry-item">
          <Activity size={15} />
          <span>Active Positions:</span>
          <strong>{portfolio?.open_positions_count ?? 0}</strong>
          <span className="telemetry-sub">of max 5 limit</span>
        </div>
      </div>

      {/* Two Column Content: Opportunities & Recent Orders */}
      <div className="content-grid">
        {/* Scanner Opportunities Panel */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Market Opportunities (Screened)</h2>
              <p>Top momentum and breakout candidates from validated NSE data</p>
            </div>
            <button
              className="button-secondary"
              onClick={() => onNavigate("Market scanner")}
            >
              Full Scanner <ArrowRight size={13} />
            </button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>PRICE (₹)</th>
                  <th>1D CHG</th>
                  <th>RVOL</th>
                  <th>CATEGORY</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {candidates && candidates.length > 0 ? (
                  candidates.slice(0, 5).map((c) => {
                    const isPos = c.pct_change_1d >= 0;
                    return (
                      <tr key={c.symbol}>
                        <td>
                          <strong>{c.symbol}</strong>
                        </td>
                        <td className="tabular-num">₹{c.latest_price.toFixed(2)}</td>
                        <td className={`tabular-num ${isPos ? "text-good" : "text-bad"}`}>
                          {isPos ? "+" : ""}{(c.pct_change_1d * 100).toFixed(2)}%
                        </td>
                        <td className="tabular-num">{c.rvol.toFixed(2)}x</td>
                        <td>
                          <Badge variant={c.is_qualified ? "good" : "warning"}>
                            {c.scan_category.replace(/_/g, " ").toUpperCase()}
                          </Badge>
                        </td>
                        <td>
                          <button
                            className="btn-link"
                            onClick={() => onNavigate("Stock research", c.symbol)}
                          >
                            <CandlestickChart size={14} /> Chart
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6}>
                      <div className="table-empty">Scanning market for qualified setups...</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Recent Simulated Orders Panel */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Recent Paper Orders</h2>
              <p>Audit trail of simulated orders and risk verdicts</p>
            </div>
            <button
              className="button-secondary"
              onClick={() => onNavigate("Order history")}
            >
              View All <ArrowRight size={13} />
            </button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>TIME</th>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QTY</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {orders && orders.length > 0 ? (
                  orders.map((o) => (
                    <tr key={o.order_id}>
                      <td className="text-muted" style={{ fontSize: "11px" }}>
                        {new Date(o.created_at).toLocaleTimeString("en-IN", { hour12: false })}
                      </td>
                      <td><strong>{o.symbol}</strong></td>
                      <td>
                        <Badge variant={o.side === "BUY" ? "good" : "bad"}>
                          {o.side}
                        </Badge>
                      </td>
                      <td className="tabular-num">{o.quantity}</td>
                      <td>
                        <Badge
                          variant={
                            o.status === "FILLED"
                              ? "good"
                              : o.status === "REJECTED"
                              ? "bad"
                              : "neutral"
                          }
                        >
                          {o.status}
                        </Badge>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5}>
                      <div className="table-empty">No simulated orders recorded yet.</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};

