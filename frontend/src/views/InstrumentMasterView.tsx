import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  Building2,
  CheckCircle,
  Hash,
  CandlestickChart,
  ShoppingCart,
  Layers,
} from "lucide-react";
import { getInstruments, getInstrumentDetails } from "../lib/api";
import { Badge } from "../components/Badge";

interface InstrumentMasterViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const InstrumentMasterView: React.FC<InstrumentMasterViewProps> = ({ onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("INFY");

  const { data: instruments, isLoading } = useQuery({
    queryKey: ["instruments"],
    queryFn: () => getInstruments(),
  });

  const { data: details } = useQuery({
    queryKey: ["instrument-details", selectedSymbol],
    queryFn: () => getInstrumentDetails(selectedSymbol),
    enabled: !!selectedSymbol,
  });

  const filtered = (instruments ?? []).filter((i) =>
    i.symbol.toLowerCase().includes(searchTerm.toLowerCase().trim()) ||
    i.name.toLowerCase().includes(searchTerm.toLowerCase().trim())
  );

  return (
    <div className="view-container">
      <div className="instrument-layout">
        {/* Left Column: Instruments List */}
        <section className="panel instrument-list-pane">
          <div className="panel-header">
            <div>
              <h2>NSE Cash Equity Universe</h2>
              <p>Active trading instruments master record</p>
            </div>
          </div>

          <div className="pane-search">
            <div className="search-box">
              <Search size={14} className="search-icon" />
              <input
                type="text"
                placeholder="Search symbol or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="instrument-list-items">
            {isLoading ? (
              <div className="table-empty">Loading universe...</div>
            ) : filtered.length === 0 ? (
              <div className="table-empty">No instruments found.</div>
            ) : (
              filtered.map((inst) => (
                <div
                  key={inst.symbol}
                  className={`instrument-item-row ${selectedSymbol === inst.symbol ? "instrument-item-active" : ""}`}
                  onClick={() => setSelectedSymbol(inst.symbol)}
                >
                  <div className="inst-main">
                    <strong>{inst.symbol}</strong>
                    <span>{inst.name}</span>
                  </div>
                  <div className="inst-meta">
                    <Badge variant="neutral">{inst.series}</Badge>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Right Column: Instrument Deep Inspector Card */}
        <section className="panel instrument-detail-pane">
          <div className="panel-header">
            <div>
              <h2>Instrument Master Specification</h2>
              <p>Trading limits, ISIN, lot sizing, and live market quotes</p>
            </div>
            {details && (
              <div className="detail-header-actions">
                <button
                  className="btn-action"
                  onClick={() => onNavigate("Stock research", selectedSymbol)}
                >
                  <CandlestickChart size={14} /> View Chart
                </button>
                <button
                  className="btn-action-primary"
                  onClick={() => onNavigate("Trading terminal", selectedSymbol)}
                >
                  <ShoppingCart size={14} /> Propose Order
                </button>
              </div>
            )}
          </div>

          {details ? (
            <div className="instrument-card-content">
              {/* Quote Snapshot Header */}
              <div className="quote-banner">
                <div className="quote-main">
                  <div className="quote-symbol-badge">{details.instrument.symbol}</div>
                  <div>
                    <h3>{details.instrument.name}</h3>
                    <span className="quote-sub">{details.instrument.industry ?? "Equities / Large Cap"}</span>
                  </div>
                </div>
                <div className="quote-price-box">
                  <div className="quote-ltp">₹{details.quote.ltp.toFixed(2)}</div>
                  <div className="quote-provenance">
                    <Badge variant="info">SOURCE: {details.quote.source}</Badge>
                  </div>
                </div>
              </div>

              {/* Specification Grid */}
              <div className="spec-grid">
                <div className="spec-card">
                  <div className="spec-label">
                    <Hash size={13} /> ISIN Code
                  </div>
                  <div className="spec-value">{details.instrument.isin ?? "INE009A01021"}</div>
                </div>

                <div className="spec-card">
                  <div className="spec-label">
                    <Layers size={13} /> Series & Market
                  </div>
                  <div className="spec-value">{details.instrument.series} (NSE Cash EQ)</div>
                </div>

                <div className="spec-card">
                  <div className="spec-label">
                    <Building2 size={13} /> Industry / Sector
                  </div>
                  <div className="spec-value">{details.instrument.industry ?? "Information Technology"}</div>
                </div>

                <div className="spec-card">
                  <div className="spec-label">
                    <CheckCircle size={13} /> Lot & Tick Size
                  </div>
                  <div className="spec-value">
                    Lot: {details.instrument.lot_size} · Tick: ₹{details.instrument.tick_size.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Bid/Ask Depth Mock Table */}
              <div className="depth-section">
                <h4>Market Depth & Liquidity Snapshot</h4>
                <div className="depth-table-wrap">
                  <table className="depth-table">
                    <thead>
                      <tr>
                        <th>BID QTY</th>
                        <th>BID (₹)</th>
                        <th>ASK (₹)</th>
                        <th>ASK QTY</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="tabular-num text-good">1,450</td>
                        <td className="tabular-num text-good">₹{(details.quote.bid ?? details.quote.ltp * 0.9995).toFixed(2)}</td>
                        <td className="tabular-num text-bad">₹{(details.quote.ask ?? details.quote.ltp * 1.0005).toFixed(2)}</td>
                        <td className="tabular-num text-bad">2,100</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="table-empty">Select an instrument from the list to inspect master details.</div>
          )}
        </section>
      </div>
    </div>
  );
};
