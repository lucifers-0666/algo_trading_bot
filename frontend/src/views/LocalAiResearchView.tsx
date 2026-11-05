import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Cpu, Sparkles, BrainCircuit, ArrowRight, FileText, Zap } from "lucide-react";
import { getAiHealth, analyzeNews, explainSignal, getStockDossier } from "../lib/api";
import type { NewsAnalysisResult, SignalExplanationResult, StockDossierResult } from "../lib/types";

export function LocalAiResearchView({ activeSymbol }: { activeSymbol: string }) {
  const [headlineInput, setHeadlineInput] = useState<string>(
    "Infosys signs $1.5 billion strategic cloud expansion deal with European telecom giant"
  );
  const [analysisResult, setAnalysisResult] = useState<NewsAnalysisResult | null>(null);

  const [explainSymbol, setExplainSymbol] = useState<string>(activeSymbol || "INFY");
  const [explainPrice, setExplainPrice] = useState<number>(1600.0);
  const [explainStop, setExplainStop] = useState<number>(1550.0);
  const [explainTarget, setExplainTarget] = useState<number>(1700.0);
  const [explanationResult, setExplanationResult] = useState<SignalExplanationResult | null>(null);

  const [dossierResult, setDossierResult] = useState<StockDossierResult | null>(null);

  const { data: aiHealth } = useQuery({
    queryKey: ["aiHealth"],
    queryFn: () => getAiHealth(),
    refetchInterval: 10000,
  });

  const newsMutation = useMutation({
    mutationFn: () => analyzeNews({ headline: headlineInput, symbol: activeSymbol }),
    onSuccess: (data) => setAnalysisResult(data),
  });

  const explainMutation = useMutation({
    mutationFn: () =>
      explainSignal({
        symbol: explainSymbol,
        strategy_name: "baseline_swing",
        side: "BUY",
        price: explainPrice,
        stop_loss: explainStop,
        target: explainTarget,
        indicators: { rsi_14: 58.4, sma_20: explainPrice * 0.98, sma_50: explainPrice * 0.95 },
      }),
    onSuccess: (data) => setExplanationResult(data),
  });

  const dossierMutation = useMutation({
    mutationFn: () =>
      getStockDossier({
        symbol: activeSymbol,
        current_price: explainPrice,
        regime: "BULLISH_TRENDING",
      }),
    onSuccess: (data) => setDossierResult(data),
  });

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Specialist Local Financial AI Lab</h1>
        </div>
        <p className="text-sm text-muted mt-1">
          Local quantized reasoning model (Fin-R1 / FinGPT) running with NVIDIA RTX 5060 GPU acceleration and deterministic fallback.
        </p>
      </div>

      {/* AI Server Status Card */}
      <div className="rounded-lg border border-border bg-surface p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-lg border ${
                aiHealth?.status === "ONLINE"
                  ? "bg-emerald-950/40 text-emerald-400 border-emerald-800"
                  : "bg-surface-elevated text-amber-400 border-border"
              }`}
            >
              <Cpu className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-semibold text-foreground">
                  {aiHealth ? aiHealth.model_name : "Probing Model Server..."}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                    aiHealth?.status === "ONLINE"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-amber-950 text-amber-400 border border-amber-800"
                  }`}
                >
                  {aiHealth ? aiHealth.status : "STANDBY"}
                </span>
              </div>
              <p className="text-xs text-muted mt-0.5">{aiHealth?.details}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-muted">Target GPU: </span>
              <span className="text-foreground font-semibold">NVIDIA RTX 5060 (8GB VRAM)</span>
            </div>
            <div>
              <span className="text-muted">Latency: </span>
              <span className="text-foreground font-semibold">{aiHealth?.latency_ms ?? 0} ms</span>
            </div>
            <div>
              <span className="text-muted">Acceleration: </span>
              <span className="text-foreground font-semibold">{aiHealth?.gpu_acceleration ? "Active (CUDA)" : "Heuristic Standby"}</span>
            </div>
          </div>
        </div>
        {aiHealth?.status !== "ONLINE" && (
          <div className="mt-3 pt-3 border-t border-border flex flex-wrap items-center justify-between text-xs text-muted gap-2">
            <span>
              <strong>Deterministic Fallback Active:</strong> To activate local Fin-R1 reasoning on NVIDIA RTX 5060, start Ollama:
            </span>
            <code className="px-2 py-0.5 bg-background border border-border rounded-text-[11px] font-mono text-foreground">
              ollama run fin-r1:7b-q4_k_m
            </code>
          </div>
        )}
      </div>

      {/* Two Column Grid: News Analyzer & Signal Explainer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module 1: Interactive News & Disclosure Analyzer */}
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>Financial News & Disclosure Reasoning</span>
            </div>
            <span className="text-[10px] font-mono text-muted">Symbol: {activeSymbol}</span>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-muted">Test Headline or Announcement Wire:</label>
            <textarea
              rows={3}
              value={headlineInput}
              onChange={(e) => setHeadlineInput(e.target.value)}
              className="w-full bg-background border border-border rounded-md p-3 text-xs text-foreground placeholder-muted focus:outline-none focus:ring-1 focus:ring-primary font-mono"
            />
          </div>

          <button
            onClick={() => newsMutation.mutate()}
            disabled={newsMutation.isPending || !headlineInput.trim()}
            className="w-full py-2 bg-primary text-background text-xs font-semibold rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {newsMutation.isPending ? "Analyzing Reasoning..." : "Run Financial Sentiment Reasoning"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>

          {analysisResult && (
            <div className="mt-4 p-4 rounded-lg bg-surface-elevated/50 border border-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Sentiment Classification:</span>
                <span
                  className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                    analysisResult.sentiment_label === "BULLISH"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : analysisResult.sentiment_label === "BEARISH"
                      ? "bg-rose-950 text-rose-400 border border-rose-800"
                      : "bg-surface text-amber-400 border border-border"
                  }`}
                >
                  {analysisResult.sentiment_label} ({analysisResult.sentiment_score > 0 ? `+${analysisResult.sentiment_score}` : analysisResult.sentiment_score})
                </span>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Suggested Market Action:</div>
                <div className="text-xs font-mono font-bold text-foreground mt-0.5">{analysisResult.suggested_action}</div>
              </div>

              {analysisResult.key_drivers.length > 0 && (
                <div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Key Catalysts:</div>
                  <ul className="list-disc list-inside text-xs text-foreground mt-1 space-y-0.5">
                    {analysisResult.key_drivers.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisResult.risk_factors.length > 0 && (
                <div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Risk Factors:</div>
                  <ul className="list-disc list-inside text-xs text-rose-400 mt-1 space-y-0.5">
                    {analysisResult.risk_factors.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Module 2: Trade Signal Explainability Dossier */}
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Zap className="h-4 w-4 text-primary" />
              <span>Trade Signal Explainability & Guardrail Audit</span>
            </div>
            <span className="text-[10px] font-mono text-muted">Strategy: Baseline Swing</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted">Symbol:</label>
              <input
                type="text"
                value={explainSymbol}
                onChange={(e) => setExplainSymbol(e.target.value.toUpperCase())}
                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground font-mono mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted">Entry Price (₹):</label>
              <input
                type="number"
                value={explainPrice}
                onChange={(e) => setExplainPrice(parseFloat(e.target.value) || 0)}
                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground font-mono mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted">Stop Loss (₹):</label>
              <input
                type="number"
                value={explainStop}
                onChange={(e) => setExplainStop(parseFloat(e.target.value) || 0)}
                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground font-mono mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted">Target (₹):</label>
              <input
                type="number"
                value={explainTarget}
                onChange={(e) => setExplainTarget(parseFloat(e.target.value) || 0)}
                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground font-mono mt-1"
              />
            </div>
          </div>

          <button
            onClick={() => explainMutation.mutate()}
            disabled={explainMutation.isPending}
            className="w-full py-2 bg-secondary text-foreground border border-border text-xs font-semibold rounded-md hover:bg-surface-elevated transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {explainMutation.isPending ? "Evaluating Signal..." : "Explain Trade Setup & Audit Guardrails"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>

          {explanationResult && (
            <div className="mt-4 p-4 rounded-lg bg-surface-elevated/50 border border-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Human Verdict:</span>
                <span
                  className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                    explanationResult.human_verdict === "APPROVED_FOR_PAPER"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-amber-950 text-amber-400 border border-amber-800"
                  }`}
                >
                  {explanationResult.human_verdict} (Conviction: {(explanationResult.confidence_score * 100).toFixed(0)}%)
                </span>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Trading Thesis:</div>
                <div className="text-xs text-foreground mt-0.5">{explanationResult.thesis}</div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Risk / Reward Assessment:</div>
                <div className="text-xs font-mono text-emerald-400 mt-0.5">{explanationResult.risk_reward_assessment}</div>
              </div>

              {explanationResult.caution_flags.length > 0 && (
                <div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Cautionary Guardrails:</div>
                  <ul className="list-disc list-inside text-xs text-amber-400 mt-1 space-y-0.5">
                    {explanationResult.caution_flags.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Module 3: Executive Stock Dossier Generator */}
      <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <FileText className="h-4 w-4 text-primary" />
              <span>Full Executive Research Dossier ({activeSymbol})</span>
            </div>
            <p className="text-xs text-muted mt-0.5">
              Comprehensive institutional analysis synthesizing technicals, benchmark regime, news, and quant metrics.
            </p>
          </div>

          <button
            onClick={() => dossierMutation.mutate()}
            disabled={dossierMutation.isPending}
            className="px-4 py-2 bg-primary text-background text-xs font-semibold rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {dossierMutation.isPending ? "Generating Dossier..." : `Generate ${activeSymbol} Dossier`}
          </button>
        </div>

        {dossierResult && (
          <div className="mt-4 p-5 rounded-lg bg-surface-elevated/40 border border-border space-y-4">
            <div className="flex flex-wrap items-center justify-between border-b border-border pb-3">
              <div>
                <span className="text-lg font-bold font-mono text-foreground">{dossierResult.symbol} Research Dossier</span>
                <div className="text-xs text-muted">{dossierResult.executive_summary}</div>
              </div>
              <span className="px-3 py-1 rounded bg-primary/10 text-primary border border-primary/20 text-xs font-mono font-bold">
                {dossierResult.trade_suitability}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Key Strengths & Drivers:</span>
                <ul className="list-disc list-inside text-xs text-foreground space-y-1">
                  {dossierResult.key_strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">Risks & Structural Headwinds:</span>
                <ul className="list-disc list-inside text-xs text-foreground space-y-1">
                  {dossierResult.key_risks.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex justify-between text-[11px] text-muted font-mono">
              <span>Provider: {dossierResult.ai_provider}</span>
              <span>Generated: {new Date(dossierResult.generated_at).toLocaleString("en-IN")}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
