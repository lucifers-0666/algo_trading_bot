import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  Percent,
  Receipt,
  BarChart3,
} from "lucide-react";
import { getPortfolio, getTrades } from "../lib/api";
import { EquityCurveChart } from "../components/EquityCurveChart";
import { Badge } from "../components/Badge";

interface PerformanceAnalyticsViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const PerformanceAnalyticsView: React.FC<PerformanceAnalyticsViewProps> = () => {
  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => getPortfolio(),
  });

  const { data: trades } = useQuery({
    queryKey: ["trades"],
    queryFn: () => getTrades(100),
  });

  const totalEquity = portfolio?.total_equity ?? 10000;
  const startingCash = portfolio?.starting_cash ?? 10000;
  const netReturnPct = startingCash > 0 ? ((totalEquity - startingCash) / startingCash) * 100 : 0;
  const isPos = netReturnPct >= 0;

  // Calculate stats from trades
  const tradeList = trades ?? [];
  let totalCosts = 0;
  tradeList.forEach((t) => {
    totalCosts += t.total_costs_inr;
  });

  // Construct synthetic equity trajectory points
  const equityPoints = [
    { date: "Start", equity: startingCash },
    { date: "Current", equity: totalEquity },
  ];

  return (
    <div className="view-container">
      {/* Top Performance Grid */}
      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-top">
            <span>CUMULATIVE RETURN</span>
            <div className="metric-icon"><TrendingUp size={16} /></div>
          </div>
          <div className={`metric-value ${isPos ? "text-good" : "text-bad"}`}>
            {isPos ? "+" : ""}{netReturnPct.toFixed(2)}%
          </div>
          <div className="metric-detail">Net Profit: ₹{(totalEquity - startingCash).toFixed(2)}</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>MAX DRAWDOWN</span>
            <div className="metric-icon"><Percent size={16} /></div>
          </div>
          <div className="metric-value">
            {(portfolio?.max_drawdown_pct ?? 0).toFixed(2)}%
          </div>
          <div className="metric-detail">Peak: ₹{(portfolio?.peak_equity ?? 10000).toFixed(2)}</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>TOTAL EXECUTED TRADES</span>
            <div className="metric-icon"><BarChart3 size={16} /></div>
          </div>
          <div className="metric-value">
            {tradeList.length}
          </div>
          <div className="metric-detail">Virtual paper fills</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>STATUTORY TAXES & FEES</span>
            <div className="metric-icon"><Receipt size={16} /></div>
          </div>
          <div className="metric-value text-bad">
            ₹{totalCosts.toFixed(2)}
          </div>
          <div className="metric-detail">STT, GST, Exchange, Stamp Duty</div>
        </article>
      </section>

      {/* Equity Trajectory Chart Pane */}
      <div className="content-grid" style={{ marginTop: 16 }}>
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Paper Portfolio Equity Trajectory</h2>
              <p>Simulated equity progression since account initialization</p>
            </div>
          </div>
          <EquityCurveChart data={equityPoints} initialCapital={startingCash} height={250} />
        </section>

        {/* Closed Fills Summary */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Executed Trades Ledger</h2>
              <p>Recent fills with statutory cost breakdown</p>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QTY</th>
                  <th>PRICE (₹)</th>
                  <th>FEES (₹)</th>
                  <th>NET VAL (₹)</th>
                </tr>
              </thead>
              <tbody>
                {tradeList.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
                      <div className="table-empty">No simulated trades filled yet.</div>
                    </td>
                  </tr>
                ) : (
                  tradeList.slice(0, 6).map((tr) => (
                    <tr key={tr.trade_id}>
                      <td><strong>{tr.symbol}</strong></td>
                      <td>
                        <Badge variant={tr.side === "BUY" ? "good" : "bad"}>{tr.side}</Badge>
                      </td>
                      <td className="tabular-num">{tr.quantity}</td>
                      <td className="tabular-num">₹{tr.price.toFixed(2)}</td>
                      <td className="tabular-num text-muted">₹{tr.total_costs_inr.toFixed(2)}</td>
                      <td className="tabular-num">₹{tr.net_value_inr.toFixed(2)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
