import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Wallet,
  TrendingUp,
  Database,
  Layers,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { getPortfolio, getPositions } from "../lib/api";

interface PortfolioViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const PortfolioView: React.FC<PortfolioViewProps> = ({ onNavigate }) => {
  const { data: portfolio, refetch: refetchPort, isFetching: isFetchingPort } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => getPortfolio(),
    refetchInterval: 5000,
  });

  const { data: positions, refetch: refetchPos } = useQuery({
    queryKey: ["positions"],
    queryFn: () => getPositions(),
    refetchInterval: 5000,
  });

  const totalEquity = portfolio?.total_equity ?? 10000;
  const cashBalance = portfolio?.cash_balance ?? 10000;
  const unrealizedPnl = portfolio?.unrealized_pnl ?? 0;
  const realizedPnl = portfolio?.realized_pnl ?? 0;
  const stockValue = totalEquity - cashBalance;
  const stockWeightPct = totalEquity > 0 ? (stockValue / totalEquity) * 100 : 0;
  const cashWeightPct = totalEquity > 0 ? (cashBalance / totalEquity) * 100 : 100;

  return (
    <div className="view-container">
      {/* Portfolio Header Metric Grid */}
      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-top">
            <span>TOTAL EQUITY (MTM)</span>
            <div className="metric-icon"><Wallet size={16} /></div>
          </div>
          <div className="metric-value">
            ₹{totalEquity.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-detail">Starting Capital: ₹10,000.00</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>AVAILABLE CASH</span>
            <div className="metric-icon"><Database size={16} /></div>
          </div>
          <div className="metric-value">
            ₹{cashBalance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-detail">{cashWeightPct.toFixed(1)}% of Portfolio</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>UNREALIZED P&L</span>
            <div className="metric-icon"><TrendingUp size={16} /></div>
          </div>
          <div className={`metric-value ${unrealizedPnl >= 0 ? "text-good" : "text-bad"}`}>
            {unrealizedPnl >= 0 ? "+" : ""}₹{unrealizedPnl.toFixed(2)}
          </div>
          <div className="metric-detail">Mark-to-Market</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>REALIZED P&L</span>
            <div className="metric-icon"><Layers size={16} /></div>
          </div>
          <div className={`metric-value ${realizedPnl >= 0 ? "text-good" : "text-bad"}`}>
            {realizedPnl >= 0 ? "+" : ""}₹{realizedPnl.toFixed(2)}
          </div>
          <div className="metric-detail">Closed trade net profits</div>
        </article>
      </section>

      {/* Asset Allocation Telemetry Bar */}
      <div className="allocation-bar-container panel" style={{ marginTop: 16, padding: "14px 18px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: "12px" }}>
          <span><strong>Capital Allocation:</strong> Stock Positions ({stockWeightPct.toFixed(1)}%) vs Available Cash ({cashWeightPct.toFixed(1)}%)</span>
          <span className="text-muted">Total: ₹{totalEquity.toFixed(2)}</span>
        </div>
        <div className="allocation-progress-track">
          <div className="allocation-stock-bar" style={{ width: `${Math.max(0, Math.min(100, stockWeightPct))}%` }} />
          <div className="allocation-cash-bar" style={{ width: `${Math.max(0, Math.min(100, cashWeightPct))}%` }} />
        </div>
      </div>

      {/* Open Positions Table */}
      <section className="panel" style={{ marginTop: 16 }}>
        <div className="panel-header">
          <div>
            <h2>Active Equity Holdings ({positions?.length ?? 0} Positions)</h2>
            <p>Open swing positions with real-time mark-to-market valuations and P&L</p>
          </div>
          <button
            className="button-secondary"
            onClick={() => {
              void refetchPort();
              void refetchPos();
            }}
          >
            <RefreshCw size={14} className={isFetchingPort ? "spin" : ""} /> Refresh
          </button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>SYMBOL</th>
                <th>QUANTITY</th>
                <th>AVG ENTRY (₹)</th>
                <th>CURRENT LTP (₹)</th>
                <th>MARKET VALUE (₹)</th>
                <th>UNREALIZED P&L</th>
                <th>REALIZED P&L</th>
                <th>WEIGHT %</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {positions && positions.length > 0 ? (
                positions.map((pos) => {
                  const mktVal = pos.quantity * pos.current_price;
                  const weightPct = totalEquity > 0 ? (mktVal / totalEquity) * 100 : 0;
                  const isPos = pos.unrealized_pnl >= 0;
                  const pnlPct = pos.average_entry_price > 0
                    ? ((pos.current_price - pos.average_entry_price) / pos.average_entry_price) * 100
                    : 0;

                  return (
                    <tr key={pos.symbol}>
                      <td>
                        <strong>{pos.symbol}</strong>
                      </td>
                      <td className="tabular-num">{pos.quantity}</td>
                      <td className="tabular-num">₹{pos.average_entry_price.toFixed(2)}</td>
                      <td className="tabular-num">₹{pos.current_price.toFixed(2)}</td>
                      <td className="tabular-num">₹{mktVal.toFixed(2)}</td>
                      <td className={`tabular-num ${isPos ? "text-good" : "text-bad"}`}>
                        <strong>{isPos ? "+" : ""}₹{pos.unrealized_pnl.toFixed(2)}</strong>
                        <span className="text-muted" style={{ fontSize: "10px" }}>
                          {" "}({isPos ? "+" : ""}{pnlPct.toFixed(2)}%)
                        </span>
                      </td>
                      <td className="tabular-num text-muted">₹{pos.realized_pnl.toFixed(2)}</td>
                      <td className="tabular-num">{weightPct.toFixed(1)}%</td>
                      <td>
                        <button
                          className="btn-action-primary"
                          onClick={() => onNavigate("Trading terminal", pos.symbol)}
                          title="Close or manage position"
                        >
                          Manage Position <ArrowRight size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={9}>
                    <div className="table-empty">
                      No active equity positions held. Use the Market Scanner or Trading Terminal to initiate simulated paper positions.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
