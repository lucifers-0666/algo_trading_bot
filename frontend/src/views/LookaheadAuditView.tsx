import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ShieldCheck, Sliders, RefreshCw, AlertTriangle, CheckCircle2, Search, Trophy } from "lucide-react";
import { auditStrategyLookahead, runStrategyHyperopt, getProtectionStatus, resetProtections } from "../lib/api";
import type { LookaheadAuditResult, HyperoptLeaderboardResult } from "../lib/types";

export function LookaheadAuditView({ activeSymbol }: { activeSymbol: string }) {
  const [auditSymbol, setAuditSymbol] = useState<string>(activeSymbol || "INFY");
  const [auditStrategy, setAuditStrategy] = useState<string>("baseline_swing");
  const [auditResult, setAuditResult] = useState<LookaheadAuditResult | null>(null);

  const [hyperoptSymbols, setHyperoptSymbols] = useState<string>("INFY,TCS");
  const [hyperoptResult, setHyperoptResult] = useState<HyperoptLeaderboardResult | null>(null);

  const { data: protections, refetch: refetchProtections } = useQuery({
    queryKey: ["protectionsStatus"],
    queryFn: () => getProtectionStatus(),
    refetchInterval: 15000,
  });

  const auditMutation = useMutation({
    mutationFn: () =>
      auditStrategyLookahead({
        symbol: auditSymbol.toUpperCase(),
        strategy_name: auditStrategy,
      }),
    onSuccess: (data) => setAuditResult(data),
  });

  const hyperoptMutation = useMutation({
    mutationFn: () =>
      runStrategyHyperopt({
        symbols: hyperoptSymbols.split(",").map((s) => s.trim().toUpperCase()),
        max_trials: 10,
      }),
    onSuccess: (data) => setHyperoptResult(data),
  });

  const resetProtectionsMutation = useMutation({
    mutationFn: () => resetProtections(),
    onSuccess: () => refetchProtections(),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Quantitative Reliability, Lookahead Audit & Protections
          </h1>
        </div>
        <p className="text-sm text-muted mt-1">
          Clean-room Freqtrade patterns: Lookahead bias detection, parameter optimization (Hyperopt), and consecutive-loss circuit breakers.
        </p>
      </div>

      {/* Protections Telemetry Card */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-foreground">Risk Protections & Cooldown Circuit</span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                  protections?.is_locked
                    ? "bg-rose-950 text-rose-400 border border-rose-800"
                    : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                }`}
              >
                {protections?.is_locked ? "TRADING PAUSED" : "ACTIVE / PERMITTED"}
              </span>
            </div>
            <p className="text-xs text-muted mt-1">
              Consecutive losses: <span className="font-mono text-foreground font-bold">{protections?.consecutive_losses ?? 0}</span> / 3 limit.
              {protections?.lock_reason && <span className="text-rose-400 ml-2">{protections.lock_reason}</span>}
            </p>
          </div>

          <button
            onClick={() => resetProtectionsMutation.mutate()}
            disabled={resetProtectionsMutation.isPending}
            className="px-4 py-2 bg-secondary text-xs font-semibold rounded-md border border-border hover:bg-surface-elevated text-foreground transition-colors disabled:opacity-50"
          >
            {resetProtectionsMutation.isPending ? "Resetting..." : "Reset Active Protections"}
          </button>
        </div>

        {protections && Object.keys(protections.symbols_in_cooldown || {}).length > 0 && (
          <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 text-xs">
            <span className="text-muted">Symbols in Post-Stop Cooldown:</span>
            {Object.entries(protections.symbols_in_cooldown).map(([sym, status]) => (
              <span key={sym} className="px-2 py-0.5 rounded bg-surface-elevated text-amber-300 font-mono text-[11px]">
                {sym} ({status})
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Grid: Lookahead Audit & Hyperopt */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module 1: Lookahead Bias Detection */}
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Search className="h-4 w-4 text-primary" />
              <span>Strategy Lookahead Bias Detector</span>
            </div>
            <span className="text-[10px] font-mono text-muted">Point-in-Time Slice Verification</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted">Symbol:</label>
              <input
                type="text"
                value={auditSymbol}
                onChange={(e) => setAuditSymbol(e.target.value.toUpperCase())}
                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground font-mono mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted">Strategy:</label>
              <select
                value={auditStrategy}
                onChange={(e) => setAuditStrategy(e.target.value)}
                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground mt-1"
              >
                <option value="baseline_swing">Baseline Swing</option>
                <option value="momentum">Momentum Strategy</option>
                <option value="breakout">Donchian Breakout</option>
              </select>
            </div>
          </div>

          <button
            onClick={() => auditMutation.mutate()}
            disabled={auditMutation.isPending}
            className="w-full py-2 bg-primary text-background text-xs font-semibold rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${auditMutation.isPending ? "animate-spin" : ""}`} />
            {auditMutation.isPending ? "Auditing Completed Bars..." : "Run Lookahead Audit"}
          </button>

          {auditResult && (
            <div className="mt-4 p-4 rounded-lg bg-surface-elevated/40 border border-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted">Audit Result:</span>
                <span
                  className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold flex items-center gap-1.5 ${
                    auditResult.is_clean
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-rose-950 text-rose-400 border border-rose-800"
                  }`}
                >
                  {auditResult.is_clean ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                  {auditResult.is_clean ? "100% CLEAN (0 LEAKAGE)" : "LOOKAHEAD BIASED"}
                </span>
              </div>

              <div className="text-xs text-foreground">{auditResult.verdict}</div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-border">
                <div>
                  <span className="text-muted block">Audited Sessions:</span>
                  <span className="text-foreground font-semibold">{auditResult.total_bars_audited} bars</span>
                </div>
                <div>
                  <span className="text-muted block">Discrepancies:</span>
                  <span className="text-emerald-400 font-semibold">{auditResult.discrepancies_count}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Module 2: Strategy Hyperopt Optimizer */}
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Trophy className="h-4 w-4 text-primary" />
              <span>Hyperparameter Optimizer (Hyperopt)</span>
            </div>
            <span className="text-[10px] font-mono text-muted">Sortino / Calmar Loss Function</span>
          </div>

          <div>
            <label className="text-xs text-muted">Universe Symbols (comma-separated):</label>
            <input
              type="text"
              value={hyperoptSymbols}
              onChange={(e) => setHyperoptSymbols(e.target.value.toUpperCase())}
              className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground font-mono mt-1"
            />
          </div>

          <button
            onClick={() => hyperoptMutation.mutate()}
            disabled={hyperoptMutation.isPending}
            className="w-full py-2 bg-secondary text-foreground border border-border text-xs font-semibold rounded-md hover:bg-surface-elevated transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Sliders className="h-3.5 w-3.5" />
            {hyperoptMutation.isPending ? "Exploring Parameter Grid..." : "Run Hyperopt Parameter Search"}
          </button>

          {hyperoptResult && (
            <div className="mt-4 p-4 rounded-lg bg-surface-elevated/40 border border-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted">Best Parameters:</span>
                <span className="text-xs font-mono font-bold text-primary">Score: {hyperoptResult.best_score}</span>
              </div>

              <div className="text-xs font-mono bg-background p-2 rounded border border-border">
                {JSON.stringify(hyperoptResult.best_params)}
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs font-mono pt-2 border-t border-border">
                <div>
                  <span className="text-muted block">Return</span>
                  <span className="text-emerald-400 font-semibold">{hyperoptResult.best_metrics.total_return_pct}%</span>
                </div>
                <div>
                  <span className="text-muted block">Win Rate</span>
                  <span className="text-foreground font-semibold">{hyperoptResult.best_metrics.win_rate_pct}%</span>
                </div>
                <div>
                  <span className="text-muted block">Max Drawdown</span>
                  <span className="text-rose-400 font-semibold">{hyperoptResult.best_metrics.max_drawdown_pct}%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
