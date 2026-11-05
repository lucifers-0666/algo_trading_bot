import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Award,
  TrendingUp,
  Percent,
  RefreshCw,
  Scale,
} from "lucide-react";
import { getStrategyComparison } from "../lib/api";

interface StrategyComparisonViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const StrategyComparisonView: React.FC<StrategyComparisonViewProps> = () => {
  const symbols = "INFY,RELIANCE,TCS";

  const { data: report, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["strategy-comparison", symbols],
    queryFn: () => getStrategyComparison(symbols),
  });

  const comparisonRows = report?.comparison_table ?? [];

  // Find best performers
  const bestSharpe = [...comparisonRows].sort((a, b) => b.sharpe_ratio - a.sharpe_ratio)[0];
  const bestReturn = [...comparisonRows].sort((a, b) => b.total_net_return_pct - a.total_net_return_pct)[0];
  const lowestDrawdown = [...comparisonRows].sort((a, b) => a.max_drawdown_pct - b.max_drawdown_pct)[0];

  return (
    <div className="view-container">
      {/* Header Bar */}
      <div className="filter-header-bar">
        <div>
          <h2>Quantitative Multi-Strategy Comparison Matrix</h2>
          <p>
            Simultaneous evaluation on identical universe, starting capital (₹10,000), and institutional taxes
          </p>
        </div>

        <div className="filter-controls">
          <button
            className="button-secondary"
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            <RefreshCw size={14} className={isFetching ? "spin" : ""} /> Re-run Comparison
          </button>
        </div>
      </div>

      {/* Champion Highlight Cards */}
      {comparisonRows.length > 0 && (
        <section className="metric-grid" style={{ marginBottom: 18 }}>
          <article className="metric-card">
            <div className="metric-top">
              <span>BEST RISK-ADJUSTED (SHARPE)</span>
              <div className="metric-icon"><Award size={16} /></div>
            </div>
            <div className="metric-value text-good">
              {bestSharpe?.strategy_name.split("(")[0].trim()}
            </div>
            <div className="metric-detail">
              Sharpe: {bestSharpe?.sharpe_ratio.toFixed(2)} · Sortino: {bestSharpe?.sortino_ratio.toFixed(2)}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>HIGHEST NET RETURN</span>
              <div className="metric-icon"><TrendingUp size={16} /></div>
            </div>
            <div className={`metric-value ${bestReturn && bestReturn.total_net_return_pct >= 0 ? "text-good" : "text-bad"}`}>
              {bestReturn ? `${bestReturn.total_net_return_pct.toFixed(2)}%` : "—"}
            </div>
            <div className="metric-detail">
              Net P&L: ₹{bestReturn?.net_pnl_inr.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>LOWEST PEAK DRAWDOWN</span>
              <div className="metric-icon"><Percent size={16} /></div>
            </div>
            <div className="metric-value">
              {lowestDrawdown ? `${lowestDrawdown.max_drawdown_pct.toFixed(2)}%` : "—"}
            </div>
            <div className="metric-detail">
              {lowestDrawdown?.strategy_name.split("(")[0].trim()}
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span>BUY & HOLD BENCHMARK</span>
              <div className="metric-icon"><Scale size={16} /></div>
            </div>
            <div className="metric-value">
              {report?.benchmark_buy_hold_return_pct.toFixed(2)}%
            </div>
            <div className="metric-detail">Equal-weight buy & hold return</div>
          </article>
        </section>
      )}

      {/* Comparison Matrix Table */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Side-by-Side Comparison Ledger</h2>
            <p>Tested on: {report?.test_symbols.join(", ") ?? "INFY, RELIANCE, TCS"} ({report?.start_date} to {report?.end_date})</p>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>STRATEGY</th>
                <th>NET RETURN %</th>
                <th>NET P&L (₹)</th>
                <th>MAX DRAWDOWN</th>
                <th>SHARPE</th>
                <th>SORTINO</th>
                <th>WIN RATE</th>
                <th>PROFIT FACTOR</th>
                <th>EXPECTANCY</th>
                <th>TOTAL TRADES</th>
                <th>COSTS (₹)</th>
                <th>AVG HOLDING</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={12}>
                    <div className="table-empty">Running multi-strategy comparison pipeline...</div>
                  </td>
                </tr>
              ) : comparisonRows.length === 0 ? (
                <tr>
                  <td colSpan={12}>
                    <div className="table-empty">No comparison results generated.</div>
                  </td>
                </tr>
              ) : (
                comparisonRows.map((row) => {
                  const isPos = row.net_pnl_inr >= 0;
                  return (
                    <tr key={row.strategy_name}>
                      <td>
                        <strong>{row.strategy_name}</strong>
                      </td>
                      <td className={`tabular-num ${isPos ? "text-good" : "text-bad"}`}>
                        <strong>{isPos ? "+" : ""}{row.total_net_return_pct.toFixed(2)}%</strong>
                      </td>
                      <td className={`tabular-num ${isPos ? "text-good" : "text-bad"}`}>
                        {isPos ? "+" : ""}₹{row.net_pnl_inr.toFixed(2)}
                      </td>
                      <td className="tabular-num text-bad">{row.max_drawdown_pct.toFixed(2)}%</td>
                      <td className="tabular-num"><strong>{row.sharpe_ratio.toFixed(2)}</strong></td>
                      <td className="tabular-num">{row.sortino_ratio.toFixed(2)}</td>
                      <td className="tabular-num">{row.win_rate_pct.toFixed(1)}%</td>
                      <td className="tabular-num">{row.profit_factor.toFixed(2)}</td>
                      <td className="tabular-num">₹{row.expectancy_inr.toFixed(2)}</td>
                      <td className="tabular-num">{row.total_trades} ({row.winning_trades}W / {row.losing_trades}L)</td>
                      <td className="tabular-num text-muted">₹{row.total_costs_inr.toFixed(2)}</td>
                      <td className="tabular-num">{row.average_holding_bars.toFixed(1)} bars</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
