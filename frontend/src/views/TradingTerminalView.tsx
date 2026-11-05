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
  simulateTradeCosts,
} from "../lib/api";
import type { OrderProposalResponse, OrderExecuteResponse, RoundtripSimulation } from "../lib/types";
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

  // Multi-broker cost simulator state
  const [simBroker, setSimBroker] = useState<string>("ANGEL_ONE");
  const [simTradeType, setSimTradeType] = useState<string>("DELIVERY");
  const [simBuyPrice, setSimBuyPrice] = useState<number>(1000);
  const [simSellPrice, setSimSellPrice] = useState<number>(1020);
  const [simQuantity, setSimQuantity] = useState<number>(10);
  const [simResult, setSimResult] = useState<RoundtripSimulation | null>(null);

  const costSimMutation = useMutation({
    mutationFn: () =>
      simulateTradeCosts({
        symbol,
        buy_price: simBuyPrice,
        sell_price: simSellPrice,
        quantity: simQuantity,
        broker: simBroker,
        trade_type: simTradeType,
        slippage_bps: 5.0,
      }),
    onSuccess: (data) => setSimResult(data),
  });

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
      setSimBuyPrice(quoteData.quote.ltp);
      setSimSellPrice(Math.round(quoteData.quote.ltp * 1.02 * 100) / 100);
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

      {/* Multi-Broker Itemized Cost & DP Charge Simulator */}
      <section className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 space-y-4 mt-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-100">
                Institutional Multi-Broker Cost & Statutory Tax Simulator
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulate actual post-tax roundtrip returns across Angel One, Zerodha, Dhan, and Fyers including DP charges.
            </p>
          </div>

          <button
            type="button"
            onClick={() => costSimMutation.mutate()}
            disabled={costSimMutation.isPending}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition"
          >
            {costSimMutation.isPending ? "Calculating..." : "Simulate Roundtrip P&L"}
          </button>
        </div>

        {/* Input Parameters Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
          <div>
            <label className="text-[11px] text-slate-400 font-semibold block mb-1">Broker Profile</label>
            <select
              value={simBroker}
              onChange={(e) => setSimBroker(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
            >
              <option value="ANGEL_ONE">Angel One (SmartAPI / iTrade)</option>
              <option value="ZERODHA">Zerodha (Kite)</option>
              <option value="DHAN">Dhan</option>
              <option value="FYERS">Fyers</option>
              <option value="FLAT_ZERO">Flat Zero (Pure Tax Baseline)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] text-slate-400 font-semibold block mb-1">Trade Classification</label>
            <select
              value={simTradeType}
              onChange={(e) => setSimTradeType(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
            >
              <option value="DELIVERY">Delivery (CNC / Demat)</option>
              <option value="INTRADAY">Intraday (MIS / Same-day)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] text-slate-400 font-semibold block mb-1">Buy Price (₹)</label>
            <input
              type="number"
              step="0.05"
              value={simBuyPrice}
              onChange={(e) => setSimBuyPrice(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
            />
          </div>

          <div>
            <label className="text-[11px] text-slate-400 font-semibold block mb-1">Target Exit Price (₹)</label>
            <input
              type="number"
              step="0.05"
              value={simSellPrice}
              onChange={(e) => setSimSellPrice(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
            />
          </div>

          <div>
            <label className="text-[11px] text-slate-400 font-semibold block mb-1">Quantity</label>
            <input
              type="number"
              value={simQuantity}
              onChange={(e) => setSimQuantity(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
            />
          </div>
        </div>

        {/* Results Display */}
        {simResult && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400">Gross P&L</span>
                <div className={`text-base font-bold font-mono mt-1 ${simResult.gross_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  ₹{simResult.gross_pnl.toFixed(2)} ({simResult.gross_pnl_pct.toFixed(2)}%)
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400">Total Statutory & Broker Drag</span>
                <div className="text-base font-bold font-mono text-rose-400 mt-1">
                  -₹{simResult.total_costs.toFixed(2)}
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400">Net Realized P&L</span>
                <div className={`text-base font-bold font-mono mt-1 ${simResult.net_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  ₹{simResult.net_pnl.toFixed(2)} ({simResult.net_pnl_pct.toFixed(2)}%)
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-indigo-900/40">
                <span className="text-[11px] text-indigo-300 font-semibold">Exact Breakeven Exit</span>
                <div className="text-base font-bold font-mono text-indigo-200 mt-1">
                  ₹{simResult.breakeven_sell_price.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Detailed Itemized Tax & Charge Breakdown */}
            <div className="overflow-x-auto bg-slate-950/60 rounded-lg border border-slate-800 p-3">
              <table className="w-full text-xs font-mono text-left">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                    <th className="py-1 px-2">Charge Head</th>
                    <th className="py-1 px-2">Rate / Basis</th>
                    <th className="py-1 px-2 text-right">Buy Leg (₹)</th>
                    <th className="py-1 px-2 text-right">Sell Leg (₹)</th>
                    <th className="py-1 px-2 text-right">Total Roundtrip (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-300">
                  <tr>
                    <td className="py-1.5 px-2 font-semibold">Brokerage Commission</td>
                    <td className="py-1.5 px-2 text-slate-400">{simResult.broker === "FLAT_ZERO" ? "₹0 flat" : "Zero delivery / flat cap"}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.buy_costs.brokerage_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.sell_costs.brokerage_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right font-bold">₹{simResult.total_brokerage.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-2 font-semibold">Securities Transaction Tax (STT)</td>
                    <td className="py-1.5 px-2 text-slate-400">{simResult.trade_type === "DELIVERY" ? "0.10% buy & sell" : "0.025% sell only"}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.buy_costs.stt_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.sell_costs.stt_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right font-bold">₹{simResult.total_stt.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-2 font-semibold">Exchange Txn Charges (NSE)</td>
                    <td className="py-1.5 px-2 text-slate-400">0.00297% (NSE Oct 2024 circular)</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.buy_costs.exchange_charges_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.sell_costs.exchange_charges_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right font-bold">₹{simResult.total_exchange_txn.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-2 font-semibold">SEBI Turnover Fee</td>
                    <td className="py-1.5 px-2 text-slate-400">₹10 / crore (0.0001%)</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.buy_costs.sebi_charges_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.sell_costs.sebi_charges_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right font-bold">₹{simResult.total_sebi.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-2 font-semibold">Stamp Duty (State Revenue)</td>
                    <td className="py-1.5 px-2 text-slate-400">0.0015% delivery / 0.003% intraday (BUY only)</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.buy_costs.stamp_duty_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right">₹0.00</td>
                    <td className="py-1.5 px-2 text-right font-bold">₹{simResult.total_stamp_duty.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-2 font-semibold">GST on Services</td>
                    <td className="py-1.5 px-2 text-slate-400">18% on (Brokerage + Txn + SEBI)</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.buy_costs.gst_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right">₹{simResult.sell_costs.gst_inr.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right font-bold">₹{simResult.total_gst.toFixed(2)}</td>
                  </tr>
                  <tr className="bg-slate-900/40">
                    <td className="py-1.5 px-2 font-bold text-amber-300">Depository (DP) Charges (CDSL/NSDL)</td>
                    <td className="py-1.5 px-2 text-slate-400">Levied on SELL delivery debit only</td>
                    <td className="py-1.5 px-2 text-right">₹0.00</td>
                    <td className="py-1.5 px-2 text-right font-bold text-amber-300">₹{simResult.total_dp_charges.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right font-bold text-amber-300">₹{simResult.total_dp_charges.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
