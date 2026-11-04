import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  RefreshCw,
  Search,
} from "lucide-react";
import { getOrders } from "../lib/api";
import { Badge } from "../components/Badge";

interface OrderHistoryViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const OrderHistoryView: React.FC<OrderHistoryViewProps> = () => {
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const { data: orders, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["orders-history"],
    queryFn: () => getOrders(100),
    refetchInterval: 5000,
  });

  const filtered = (orders ?? []).filter((o) => {
    const matchesStatus = filterStatus === "ALL" ? true : o.status === filterStatus;
    const matchesSearch = o.symbol.toLowerCase().includes(searchTerm.toLowerCase().trim()) ||
      o.order_id.toLowerCase().includes(searchTerm.toLowerCase().trim());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="view-container">
      {/* Controls Bar */}
      <div className="filter-header-bar">
        <div className="category-tabs">
          {["ALL", "FILLED", "REJECTED", "PENDING"].map((st) => (
            <button
              key={st}
              className={`category-tab ${filterStatus === st ? "category-tab-active" : ""}`}
              onClick={() => setFilterStatus(st)}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="filter-controls">
          <div className="search-box">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Filter by symbol or Order ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button
            className="button-secondary"
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            <RefreshCw size={14} className={isFetching ? "spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {/* Orders Table Panel */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Simulated Paper Order Audit Ledger ({filtered.length} Orders)</h2>
            <p>Chronological audit record of every simulated order submitted to the virtual paper broker</p>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>TIME (IST)</th>
                <th>ORDER ID</th>
                <th>SYMBOL</th>
                <th>SIDE</th>
                <th>TYPE</th>
                <th>QUANTITY</th>
                <th>PRICE (₹)</th>
                <th>STATUS</th>
                <th>AUDIT / REJECTION RATIONALE</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={9}>
                    <div className="table-empty">Loading orders ledger...</div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="table-empty">No simulated orders recorded under this filter.</div>
                  </td>
                </tr>
              ) : (
                filtered.map((ord) => {
                  const isFilled = ord.status === "FILLED";
                  const isRejected = ord.status === "REJECTED";
                  return (
                    <tr key={ord.order_id}>
                      <td className="text-muted" style={{ fontSize: "11px" }}>
                        {new Date(ord.created_at).toLocaleString("en-IN", {
                          hour12: false,
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </td>
                      <td>
                        <code style={{ fontSize: "11px", color: "#55645a" }}>{ord.order_id}</code>
                      </td>
                      <td>
                        <strong>{ord.symbol}</strong>
                      </td>
                      <td>
                        <Badge variant={ord.side === "BUY" ? "good" : "bad"}>
                          {ord.side}
                        </Badge>
                      </td>
                      <td className="text-muted">{ord.order_type}</td>
                      <td className="tabular-num">{ord.quantity}</td>
                      <td className="tabular-num">
                        {ord.limit_price != null ? `₹${ord.limit_price.toFixed(2)}` : "MKT"}
                      </td>
                      <td>
                        <Badge variant={isFilled ? "good" : isRejected ? "bad" : "neutral"}>
                          {ord.status}
                        </Badge>
                      </td>
                      <td style={{ maxWidth: 300 }}>
                        {ord.rejection_reason ? (
                          <span className="text-bad" style={{ fontSize: "11px" }}>
                            {ord.rejection_reason}
                          </span>
                        ) : isFilled ? (
                          <span className="text-good" style={{ fontSize: "11px" }}>
                            ✓ Pre-trade risk verified & filled
                          </span>
                        ) : (
                          <span className="text-muted" style={{ fontSize: "11px" }}>—</span>
                        )}
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
