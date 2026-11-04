import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Play,
  RotateCcw,
  Zap,
} from "lucide-react";
import {
  proposeOrder,
  executeOrder,
  getInstrumentDetails,
} from "../lib/api";
import type { OrderProposalResponse, OrderExecuteResponse } from "../lib/types";
import { Badge } from "../components/Badge";

interface TradingTerminalViewProps {
  initialSymbol?: string;
  onNavigate: (page: string, symbol?: string) => void;
}

export const TradingTerminalView: React.FC<TradingTerminalViewProps> = ({
  initialSymbol = "INFY",
  onNavigate,
}) => {
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [price, setPrice] = useState<number>(1000);
  const [stopLoss, setStopLoss] = useState<number>(970);
  const [quantity, setQuantity] = useState<number | undefined>(undefined);
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [proposal, setProposal] = useState<OrderProposalResponse | null>(null);
  const [lastExecution, setLastExecution] = useState<OrderExecuteResponse | null>(null);

  // Fetch instrument quote
  const { data: quoteData } = useQuery({
    queryKey: ["instrument-details", symbol],
    queryFn: () => getInstrumentDetails(symbol),
    enabled: !!symbol,
  });

  // Sync price from quote
  useEffect(() => {
    if (quoteData?.quote.ltp) {
      setPrice(quoteData.quote.ltp);
      setStopLoss(Math.round(quoteData.quote.ltp * 0.97 * 100) / 100);
    }
  }, [quoteData]);

  // Risk Pre-Trade Verification Mutation
  const verifyMutation = useMutation({
    mutationFn: () =>
      proposeOrder({
        symbol,
        side,
        price,
        stop_loss: stopLoss,
        quantity: quantity || undefined,
        order_type: orderType,
      }),
    onSuccess: (data) => {
      setProposal(data);
      if (data.approved && !quantity && data.approved_quantity > 0) {
        setQuantity(data.approved_quantity);
      }
    },
  });

  // Execute Simulated Order Mutation
  const executeMutation = useMutation({
    mutationFn: () =>
      executeOrder({
        symbol,
        side,
        price,
        stop_loss: stopLoss,
        quantity: quantity || proposal?.approved_quantity || 1,
        order_type: orderType,
      }),
    onSuccess: (data) => {
      setLastExecution(data);
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    verifyMutation.mutate();
  };

  const handleExecute = () => {
    executeMutation.mutate();
  };

  return (
    <div className="view-container">
      {/* Strict Paper Trading Notice */}
      <div className="notice-bar">
        <div className="notice-icon">
          <ShieldCheck size={18} className="text-good" />
        </div>
        <div>
          <strong>Virtual Paper Trading Terminal (Indian Equities)</strong>
          <span>
            Orders are executed against synthetic or historical bid/ask queues with official Indian statutory delivery taxes and risk limits. No demat account is connected.
          </span>
        </div>
        <Badge variant="good">SAFE-BY-DEFAULT</Badge>
      </div>

      <div className="content-grid" style={{ marginTop: 16 }}>
        {/* Left Pane: Order Form */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Order Entry Form (Simulated)</h2>
              <p>Configure order parameters for risk verification</p>
            </div>
            <Zap size={16} className="text-good" />
          </div>

          <form onSubmit={handleVerify} className="terminal-form">
            <div className="form-group">
              <label htmlFor="term-symbol">Symbol</label>
              <select
                id="term-symbol"
                value={symbol}
                onChange={(e) => {
                  setSymbol(e.target.value);
                  setProposal(null);
                  setLastExecution(null);
                }}
              >
                <option value="INFY">INFY (Infosys Ltd)</option>
                <option value="RELIANCE">RELIANCE (Reliance Industries)</option>
                <option value="TCS">TCS (Tata Consultancy Services)</option>
                <option value="HDFCBANK">HDFCBANK (HDFC Bank)</option>
                <option value="ICICIBANK">ICICIBANK (ICICI Bank)</option>
                <option value="TATAMOTORS">TATAMOTORS (Tata Motors)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Order Side</label>
              <div className="side-toggle-group">
                <button
                  type="button"
                  className={`side-btn side-btn-buy ${side === "BUY" ? "side-btn-buy-active" : ""}`}
                  onClick={() => {
                    setSide("BUY");
                    setProposal(null);
                  }}
                >
                  BUY (LONG)
                </button>
                <button
                  type="button"
                  className={`side-btn side-btn-sell ${side === "SELL" ? "side-btn-sell-active" : ""}`}
                  onClick={() => {
                    setSide("SELL");
                    setProposal(null);
                  }}
                >
                  SELL (EXIT)
                </button>
              </div>
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label htmlFor="term-price">Order Price (₹)</label>
                <input
                  id="term-price"
                  type="number"
                  step="0.05"
                  value={price}
                  onChange={(e) => setPrice(Number(e.target.value))}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="term-stop">Stop Loss (₹)</label>
                <input
                  id="term-stop"
                  type="number"
                  step="0.05"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(Number(e.target.value))}
                  required
                />
              </div>
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label htmlFor="term-qty">Quantity (Shares)</label>
                <input
                  id="term-qty"
                  type="number"
                  placeholder="Auto-sized from risk"
                  value={quantity ?? ""}
                  onChange={(e) => setQuantity(e.target.value ? Number(e.target.value) : undefined)}
                />
              </div>

              <div className="form-group">
                <label htmlFor="term-type">Order Type</label>
                <select
                  id="term-type"
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value as "MARKET" | "LIMIT")}
                >
                  <option value="MARKET">MARKET</option>
                  <option value="LIMIT">LIMIT</option>
                </select>
              </div>
            </div>

            <div className="terminal-actions">
              <button
                type="submit"
                className="button-secondary"
                disabled={verifyMutation.isPending}
                style={{ flex: 1, justifyContent: "center" }}
              >
                {verifyMutation.isPending ? "Evaluating Risk Limits..." : "Verify Pre-Trade Risk"}
              </button>
            </div>
          </form>
        </section>

        {/* Right Pane: Risk Assessment & Sizing Preview */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Pre-Trade Risk Verification & Execution</h2>
              <p>Institutional guardrails, sizing allocation, and order submission</p>
            </div>
          </div>

          <div className="risk-preview-pane">
            {proposal ? (
              <div className="proposal-summary">
                <div className={`verdict-banner ${proposal.approved ? "verdict-pass" : "verdict-fail"}`}>
                  <div className="verdict-icon">
                    {proposal.approved ? (
                      <CheckCircle2 size={20} className="text-good" />
                    ) : (
                      <AlertTriangle size={20} className="text-bad" />
                    )}
                  </div>
                  <div>
                    <strong>
                      {proposal.approved ? "RISK VERIFICATION PASSED" : "RISK VERIFICATION REJECTED"}
                    </strong>
                    <p>
                      {proposal.approved
                        ? `Approved allocation of ${proposal.approved_quantity} shares for ${proposal.symbol}.`
                        : "Order violates portfolio risk guardrails."}
                    </p>
                  </div>
                </div>

                {/* Sizing Details */}
                {proposal.sizing && (
                  <div className="sizing-specs-grid">
                    <div className="sizing-spec-item">
                      <span>Max Capital Allocation</span>
                      <strong>₹{(proposal.sizing.allocated_capital_inr ?? 0).toFixed(2)}</strong>
                    </div>
                    <div className="sizing-spec-item">
                      <span>Approved Quantity</span>
                      <strong>{proposal.sizing.quantity ?? proposal.approved_quantity} shares</strong>
                    </div>
                    <div className="sizing-spec-item">
                      <span>Risk Budget</span>
                      <strong>₹{(proposal.sizing.risk_budget_inr ?? 0).toFixed(2)}</strong>
                    </div>
                    <div className="sizing-spec-item">
                      <span>Max Calculated Risk</span>
                      <strong>₹{(proposal.sizing.calculated_risk_inr ?? 0).toFixed(2)}</strong>
                    </div>
                  </div>
                )}

                {/* Rejection reasons if rejected */}
                {!proposal.approved && proposal.rejection_reasons.length > 0 && (
                  <div className="rejection-box">
                    <strong>Rejection Violations:</strong>
                    <ul>
                      {proposal.rejection_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Submit Simulated Order Button */}
                {proposal.approved && (
                  <div className="execute-action-box" style={{ marginTop: 16 }}>
                    <button
                      type="button"
                      className="btn-action-primary"
                      onClick={handleExecute}
                      disabled={executeMutation.isPending}
                      style={{ width: "100%", justifyContent: "center", padding: "12px" }}
                    >
                      {executeMutation.isPending ? (
                        <>
                          <RotateCcw size={16} className="spin" /> Executing Simulated Fill...
                        </>
                      ) : (
                        <>
                          <Play size={16} /> Execute Simulated {side} Order ({quantity || proposal.approved_quantity} shares @ ₹{price})
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="table-empty">
                Fill in the order details on the left and click "Verify Pre-Trade Risk" to evaluate risk sizing and capital guardrails.
              </div>
            )}

            {/* Execution Result Feedback */}
            {lastExecution && (
              <div
                className={`execution-feedback-card ${lastExecution.success ? "feedback-card-pass" : "feedback-card-fail"}`}
                style={{ marginTop: 16 }}
              >
                <div className="feedback-header">
                  {lastExecution.success ? (
                    <>
                      <CheckCircle2 size={16} className="text-good" />
                      <strong>Simulated Order Filled Successfully!</strong>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={16} className="text-bad" />
                      <strong className="text-bad">Simulated Order Rejected by Risk Engine</strong>
                    </>
                  )}
                </div>
                <div className="feedback-details">
                  <div>Order ID: <code>{lastExecution.order.order_id}</code></div>
                  <div>Status: <strong>{lastExecution.order.status}</strong></div>
                  {lastExecution.success ? (
                    <>
                      <div>Filled Qty: <strong>{lastExecution.order.quantity} shares</strong></div>
                      <div>Fill Price: <strong>₹{lastExecution.trade?.price.toFixed(2)}</strong></div>
                      <div>Total Statutory Fees: <strong>₹{lastExecution.trade?.total_costs_inr.toFixed(2)}</strong></div>
                    </>
                  ) : (
                    <div style={{ gridColumn: "1 / -1", color: "#b95d5d", marginTop: 4 }}>
                      Reason: <strong>{lastExecution.order.rejection_reason}</strong>
                    </div>
                  )}
                </div>
                {lastExecution.success && (
                  <button
                    className="button-secondary"
                    onClick={() => onNavigate("Portfolio & holdings")}
                    style={{ marginTop: 10 }}
                  >
                    View Open Position in Portfolio
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};
