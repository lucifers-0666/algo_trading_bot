import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  RefreshCw,
  Search,
} from "lucide-react";
import { getAuditLogs } from "../lib/api";
import { Badge } from "../components/Badge";

interface AuditLogsViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const AuditLogsView: React.FC<AuditLogsViewProps> = () => {
  const [searchTerm, setSearchTerm] = useState("");

  const { data: logs, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => getAuditLogs(100),
    refetchInterval: 5000,
  });

  const filtered = (logs ?? []).filter((l) => {
    const s = searchTerm.toLowerCase().trim();
    return (
      l.event_type.toLowerCase().includes(s) ||
      (l.symbol && l.symbol.toLowerCase().includes(s)) ||
      l.event_id.toLowerCase().includes(s)
    );
  });

  return (
    <div className="view-container">
      {/* Filter Bar */}
      <div className="filter-header-bar">
        <div>
          <h2>Immutable System & Risk Audit Trail</h2>
          <p>Cryptographically sequenced event log of every order, fill, rejection, and risk event</p>
        </div>

        <div className="filter-controls">
          <div className="search-box">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Search event type or symbol..."
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

      {/* Audit Log Table */}
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>TIMESTAMP (IST)</th>
                <th>EVENT TYPE</th>
                <th>SYMBOL</th>
                <th>EVENT ID</th>
                <th>EVENT DETAILS & PAYLOAD</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5}>
                    <div className="table-empty">Loading audit events...</div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="table-empty">No audit events logged yet.</div>
                  </td>
                </tr>
              ) : (
                filtered.map((log) => {
                  const isKill = log.event_type.includes("KILL_SWITCH");
                  const isReject = log.event_type.includes("REJECT");
                  const isFill = log.event_type.includes("FILL");

                  return (
                    <tr key={log.event_id}>
                      <td className="text-muted" style={{ fontSize: "11px" }}>
                        {new Date(log.timestamp).toLocaleString("en-IN", {
                          hour12: false,
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </td>
                      <td>
                        <Badge
                          variant={
                            isKill || isReject
                              ? "bad"
                              : isFill
                              ? "good"
                              : "neutral"
                          }
                        >
                          {log.event_type}
                        </Badge>
                      </td>
                      <td>
                        <strong>{log.symbol ?? "—"}</strong>
                      </td>
                      <td>
                        <code style={{ fontSize: "10px", color: "#6c7a71" }}>
                          {log.event_id}
                        </code>
                      </td>
                      <td>
                        <div className="audit-json-wrap">
                          <pre style={{ margin: 0, fontSize: "10px", color: "#415046" }}>
                            {JSON.stringify(log.details, null, 1)}
                          </pre>
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
