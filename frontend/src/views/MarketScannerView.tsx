import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  CandlestickChart,
  ShoppingCart,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { getScannerCandidates } from "../lib/api";
import { Badge } from "../components/Badge";

interface MarketScannerViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

const CATEGORIES = [
  { id: "all", label: "All Setups" },
  { id: "top_gainers", label: "Top Gainers" },
  { id: "top_losers", label: "Top Losers" },
  { id: "momentum", label: "Momentum" },
  { id: "breakout", label: "Breakout" },
  { id: "rvol", label: "High RVOL" },
];

export const MarketScannerView: React.FC<MarketScannerViewProps> = ({ onNavigate }) => {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [onlyQualified, setOnlyQualified] = useState(false);

  const { data: candidates, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["scanner", selectedCategory],
    queryFn: () => getScannerCandidates(selectedCategory),
  });

  const filtered = (candidates ?? []).filter((c) => {
    const matchesSearch = c.symbol.toLowerCase().includes(searchTerm.toLowerCase().trim());
    const matchesQual = onlyQualified ? c.is_qualified : true;
    return matchesSearch && matchesQual;
  });

  return (
    <div className="view-container">
      {/* Category Tabs & Controls */}
      <div className="filter-header-bar">
        <div className="category-tabs">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              className={`category-tab ${selectedCategory === cat.id ? "category-tab-active" : ""}`}
              onClick={() => setSelectedCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="filter-controls">
          <div className="search-box">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Search symbol (e.g. INFY)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={onlyQualified}
              onChange={(e) => setOnlyQualified(e.target.checked)}
            />
            <span>Liquid Only</span>
          </label>

          <button
            className="button-secondary"
            onClick={() => void refetch()}
            disabled={isFetching}
            title="Refresh Scan"
          >
            <RefreshCw size={14} className={isFetching ? "spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {/* Main Candidates Table */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Market Scanner Candidates ({filtered.length})</h2>
            <p>Candidate discovery with transparent quantitative inclusion and exclusion rationale</p>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>SYMBOL</th>
                <th>PRICE</th>
                <th>1D %</th>
                <th>RVOL</th>
                <th>VOLUME</th>
                <th>INDICATORS</th>
                <th>QUALIFICATION</th>
                <th>REASONING</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={9}>
                    <div className="table-empty">Running multi-factor screening algorithms...</div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="table-empty">No stocks matched the active scanner filters.</div>
                  </td>
                </tr>
              ) : (
                filtered.map((c) => {
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
                      <td className="tabular-num text-muted">{c.volume.toLocaleString()}</td>
                      <td>
                        <div className="indicator-chips">
                          {c.indicators.rsi_14 != null && (
                            <span className="mini-chip">RSI: {c.indicators.rsi_14.toFixed(1)}</span>
                          )}
                          {c.indicators.sma_20 != null && (
                            <span className="mini-chip">SMA20: ₹{c.indicators.sma_20.toFixed(0)}</span>
                          )}
                        </div>
                      </td>
                      <td>
                        {c.is_qualified ? (
                          <Badge variant="good">
                            <CheckCircle2 size={11} style={{ marginRight: 4 }} />
                            QUALIFIED
                          </Badge>
                        ) : (
                          <Badge variant="warning">
                            <AlertTriangle size={11} style={{ marginRight: 4 }} />
                            RESTRICTED
                          </Badge>
                        )}
                      </td>
                      <td style={{ maxWidth: 260 }}>
                        <div className="reasoning-cell">
                          {c.inclusion_reasons.map((r, i) => (
                            <div key={`inc-${i}`} className="reason-inc">✓ {r}</div>
                          ))}
                          {c.exclusion_reasons.map((r, i) => (
                            <div key={`exc-${i}`} className="reason-exc">✗ {r}</div>
                          ))}
                        </div>
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            className="btn-action"
                            onClick={() => onNavigate("Stock research", c.symbol)}
                            title="Open Technical Research Chart"
                          >
                            <CandlestickChart size={14} /> Chart
                          </button>
                          <button
                            className="btn-action-primary"
                            onClick={() => onNavigate("Trading terminal", c.symbol)}
                            title="Propose Paper Order"
                          >
                            <ShoppingCart size={14} /> Trade
                          </button>
                        </div>
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
  );
};
