import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, AlertTriangle, ShieldCheck, ArrowRight, Target, Sliders, ShieldX, Check } from "lucide-react";
import { evaluateDecision, executeOrder } from "../lib/api";
import type { DecisionDossierResult, OrderExecuteResponse } from "../lib/types";

export function DecisionSupportView({
  activeSymbol,
  onNavigateToPortfolio,
}: {
  activeSymbol: string;
  onNavigateToPortfolio?: () => void;
}) {
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState<string>(activeSymbol || "INFY");
  const [price, setPrice] = useState<number>(1600.0);
  const [stopLoss, setStopLoss] = useState<number>(1550.0);
  const [target, setTarget] = useState<number>(1700.0);
  const [dossier, setDossier] = useState<DecisionDossierResult | null>(null);
  const [executionResult, setExecutionResult] = useState<OrderExecuteResponse | null>(null);
  const [confirmationStep, setConfirmationStep] = useState<boolean>(false);

  const evalMutation = useMutation({
    mutationFn: () =>
      evaluateDecision({
        symbol: symbol.toUpperCase(),
        price,
        stop_loss: stopLoss,
        target,
        strategy_name: "baseline_swing",
      }),
    onSuccess: (data) => {
      setDossier(data);
      setExecutionResult(null);
      setConfirmationStep(false);
    },
  });

  const execMutation = useMutation({
    mutationFn: () => {
      if (!dossier) throw new Error("No evaluated dossier to execute");
      return executeOrder({
        symbol: dossier.symbol,
        side: "BUY",
        price: dossier.entry_price,
        stop_loss: dossier.stop_loss,
        quantity: dossier.suggested_quantity,
        order_type: "MARKET",
      });
    },
    onSuccess: (res) => {
      setExecutionResult(res);
      setConfirmationStep(false);
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Unified Decision Support System</h1>
        </div>
        <p className="text-sm text-muted mt-1">
          Synthesizes multi-model technicals, benchmark regime, machine learning, and news sentiment into an actionable decision dossier.
        </p>
      </div>

      {/* Input Parameters Form */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Sliders className="h-4 w-4 text-primary" />
          <span>Candidate Trade Parameters</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div>
            <label className="text-xs font-medium text-slate-400">Symbol:</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-full bg-[#0b0f19] border border-[#1e2638] rounded-md px-3 py-1.5 text-xs text-slate-100 font-mono mt-1 outline-none focus:border-sky-500"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-400">Estimated Entry (₹):</label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#0b0f19] border border-[#1e2638] rounded-md px-3 py-1.5 text-xs text-slate-100 font-mono mt-1 outline-none focus:border-sky-500"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-400">Stop Loss (₹):</label>
            <input
              type="number"
              value={stopLoss}
              onChange={(e) => setStopLoss(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#0b0f19] border border-[#1e2638] rounded-md px-3 py-1.5 text-xs text-slate-100 font-mono mt-1 outline-none focus:border-sky-500"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-400">Profit Target (₹):</label>
            <input
              type="number"
              value={target}
              onChange={(e) => setTarget(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#0b0f19] border border-[#1e2638] rounded-md px-3 py-1.5 text-xs text-slate-100 font-mono mt-1 outline-none focus:border-sky-500"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={() => evalMutation.mutate()}
            disabled={evalMutation.isPending || price <= 0 || stopLoss <= 0}
            className="px-5 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-md transition-colors disabled:opacity-50 flex items-center gap-2 cursor-pointer shadow-xs"
          >
            {evalMutation.isPending ? "Synthesizing Models..." : "Evaluate Decision Confluence"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Decision Output Dossier */}
      {dossier && (
        <div className="space-y-6">
          {/* Main Recommendation Banner */}
          <div
            className={`rounded-lg border p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 ${
              dossier.action === "APPROVE_PAPER_BUY"
                ? "bg-emerald-950/30 border-emerald-800/80"
                : dossier.action === "WAIT_FOR_CONFIRMATION"
                ? "bg-amber-950/30 border-amber-800/80"
                : "bg-rose-950/30 border-rose-800/80"
            }`}
          >
            <div>
              <div className="flex items-center gap-2">
                {dossier.action === "APPROVE_PAPER_BUY" ? (
                  <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                ) : dossier.action === "WAIT_FOR_CONFIRMATION" ? (
                  <AlertTriangle className="h-6 w-6 text-amber-400" />
                ) : (
                  <ShieldX className="h-6 w-6 text-rose-400" />
                )}
                <span className="text-xl font-bold font-mono tracking-tight text-foreground">
                  {dossier.action === "APPROVE_PAPER_BUY"
                    ? "RECOMMENDATION: APPROVE SIMULATED BUY"
                    : dossier.action === "WAIT_FOR_CONFIRMATION"
                    ? "RECOMMENDATION: WAIT FOR TECHNICAL / REGIME CONFIRMATION"
                    : "RECOMMENDATION: REJECT SETUP (RISK / REGIME VIOLATION)"}
                </span>
              </div>
              <p className="text-xs text-muted mt-1.5 max-w-2xl">
                Multi-model conviction evaluated at {dossier.composite_score.toFixed(1)} / 100.
                {dossier.action === "APPROVE_PAPER_BUY"
                  ? " All institutional risk controls, sizing limits, and statutory delivery cost guards passed."
                  : " Caution flags or risk guardrails detected. Review details below before proceeding."}
              </p>
            </div>

            {/* Score Ring / Pill */}
            <div className="flex items-center gap-6">
              <div className="text-right font-mono">
                <div className="text-xs text-muted uppercase tracking-wider">Confluence Score</div>
                <div className="text-3xl font-extrabold text-foreground">{dossier.composite_score.toFixed(1)}%</div>
              </div>
            </div>
          </div>

          {/* Model Conviction Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-xs text-muted">Technical Conviction</div>
              <div className="text-xl font-bold font-mono text-foreground mt-1">{dossier.technical_conviction.toFixed(1)}%</div>
              <div className="w-full bg-surface-elevated rounded-full h-1.5 mt-2 overflow-hidden">
                <div className="bg-primary h-full rounded-full" style={{ width: `${dossier.technical_conviction}%` }} />
              </div>
            </div>

            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-xs text-muted">Regime Conviction</div>
              <div className="text-xl font-bold font-mono text-foreground mt-1">{dossier.regime_conviction.toFixed(1)}%</div>
              <div className="w-full bg-surface-elevated rounded-full h-1.5 mt-2 overflow-hidden">
                <div className="bg-emerald-400 h-full rounded-full" style={{ width: `${dossier.regime_conviction}%` }} />
              </div>
            </div>

            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-xs text-muted">ML Model Conviction</div>
              <div className="text-xl font-bold font-mono text-foreground mt-1">{dossier.ml_conviction.toFixed(1)}%</div>
              <div className="w-full bg-surface-elevated rounded-full h-1.5 mt-2 overflow-hidden">
                <div className="bg-sky-400 h-full rounded-full" style={{ width: `${dossier.ml_conviction}%` }} />
              </div>
            </div>

            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-xs text-muted">News Sentiment Conviction</div>
              <div className="text-xl font-bold font-mono text-foreground mt-1">{dossier.sentiment_conviction.toFixed(1)}%</div>
              <div className="w-full bg-surface-elevated rounded-full h-1.5 mt-2 overflow-hidden">
                <div className="bg-amber-400 h-full rounded-full" style={{ width: `${dossier.sentiment_conviction}%` }} />
              </div>
            </div>
          </div>

          {/* Trade Execution & Sizing Card */}
          <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Target className="h-4 w-4 text-primary" />
                <span>Simulated Order Execution Preview (₹10,000 Starting Capital)</span>
              </div>
              <span className="text-xs font-mono font-semibold text-primary">
                Risk-Approved Quantity: {dossier.suggested_quantity} shares
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div>
                <span className="text-muted block">Entry Price</span>
                <span className="text-foreground font-semibold text-sm">₹{dossier.entry_price.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-muted block">Stop Loss</span>
                <span className="text-rose-400 font-semibold text-sm">₹{dossier.stop_loss.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-muted block">Profit Target</span>
                <span className="text-emerald-400 font-semibold text-sm">₹{dossier.target.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-muted block">Risk / Reward</span>
                <span className="text-foreground font-semibold text-sm">{dossier.risk_reward_ratio}:1</span>
              </div>
            </div>

            {/* Catalysts and Warnings */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {dossier.key_catalysts.length > 0 && (
                <div className="rounded bg-surface-elevated/40 p-3 border border-border">
                  <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block mb-1">
                    Confluence Catalysts:
                  </span>
                  <ul className="list-disc list-inside text-xs text-foreground space-y-0.5">
                    {dossier.key_catalysts.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(dossier.caution_flags.length > 0 || dossier.rejection_reasons.length > 0) && (
                <div className="rounded bg-surface-elevated/40 p-3 border border-border">
                  <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider block mb-1">
                    Caution Flags & Rejections:
                  </span>
                  <ul className="list-disc list-inside text-xs text-amber-300 space-y-0.5">
                    {[...dossier.rejection_reasons, ...dossier.caution_flags].map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Human in the loop Confirmation & Execution Trigger */}
            <div className="pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-xs text-muted">
                <span className="font-semibold text-foreground">Human-in-the-Loop Guardrail: </span>
                Orders are never placed automatically. Operator must review and explicitly authorize simulated execution.
              </div>

              {!confirmationStep ? (
                <button
                  onClick={() => setConfirmationStep(true)}
                  disabled={dossier.suggested_quantity <= 0 || !dossier.risk_approved}
                  className="px-6 py-2.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-md transition-colors disabled:opacity-40 cursor-pointer shadow-xs"
                >
                  Authorize Simulated Paper Trade
                </button>
              ) : (
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setConfirmationStep(false)}
                    className="px-4 py-2 bg-[#161e30] hover:bg-[#1c263c] text-slate-200 text-xs rounded-md border border-[#1e2638] cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => execMutation.mutate()}
                    disabled={execMutation.isPending}
                    className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <Check className="h-4 w-4" />
                    {execMutation.isPending ? "Executing Virtual Fill..." : "Confirm & Execute Simulated Buy"}
                  </button>
                </div>
              )}
            </div>

            {executionResult && (
              <div className="p-4 rounded bg-emerald-950/40 border border-emerald-800 text-xs text-emerald-300 space-y-2">
                <div className="font-bold flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  Simulated Trade Filled Successfully!
                </div>
                <div className="font-mono">
                  Order ID: {executionResult.order.order_id} | Trade ID: {executionResult.trade?.trade_id}
                </div>
                <div>
                  Filled {executionResult.order.quantity} shares of {executionResult.order.symbol} @ ₹
                  {executionResult.trade?.price.toFixed(2)} (Statutory Costs: ₹
                  {executionResult.trade?.total_costs_inr.toFixed(2)})
                </div>
                {onNavigateToPortfolio && (
                  <button
                    onClick={onNavigateToPortfolio}
                    className="mt-2 text-primary font-semibold hover:underline inline-flex items-center gap-1 text-xs"
                  >
                    View in Portfolio & Holdings <ArrowRight className="h-3 w-3" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
