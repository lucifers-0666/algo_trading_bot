import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  RefreshCw,
  Scale,
  ShieldAlert,
  Calendar,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Activity,
} from "lucide-react";
import {
  getNextSessionForecast,
  getForecastHistory,
  evaluateForecastLedger,
} from "../lib/api";
import type { NextSessionForecast } from "../lib/types";

const FORECAST_UNIVERSE = [
  "NIFTY",
  "SENSEX",
  "RELIANCE",
  "TCS",
  "INFY",
  "HDFCBANK",
  "ICICIBANK",
  "SBIN",
  "BHARTIARTL",
  "TATAMOTORS",
  "LT",
];

export function NextSessionForecastView({
  onNavigateToAi,
}: {
  onNavigateToAi?: (symbol: string) => void;
}) {
  const queryClient = useQueryClient();
  const [selectedSymbol, setSelectedSymbol] = useState<string>("NIFTY");

  const {
    data: forecast,
    isLoading: isForecastLoading,
    isFetching: isForecastFetching,
    refetch: refetchForecast,
    error: forecastError,
  } = useQuery<NextSessionForecast>({
    queryKey: ["next-session-forecast", selectedSymbol],
    queryFn: () => getNextSessionForecast(selectedSymbol),
    staleTime: 60_000,
  });

  const {
    data: history,
    isLoading: isHistoryLoading,
  } = useQuery({
    queryKey: ["forecast-history", selectedSymbol],
    queryFn: () => getForecastHistory(selectedSymbol, 30),
    staleTime: 30_000,
  });

  const evalMutation = useMutation({
    mutationFn: () => evaluateForecastLedger(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forecast-history"] });
      queryClient.invalidateQueries({ queryKey: ["next-session-forecast"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header & Symbol Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h1 className="text-xl font-bold text-slate-100">
              Institutional Next-Session Quantitative Forecasting
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Ensemble econometric & statistical model forecasting direction, returns, and volatility cones for the next Indian trading session.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 overflow-x-auto max-w-full">
            {FORECAST_UNIVERSE.map((sym) => (
              <button
                key={sym}
                onClick={() => setSelectedSymbol(sym)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                  selectedSymbol === sym
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
              >
                {sym}
              </button>
            ))}
          </div>

          <button
            onClick={() => refetchForecast()}
            disabled={isForecastFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isForecastFetching ? "animate-spin" : ""}`} />
            <span>Recalculate</span>
          </button>
        </div>
      </div>

      {/* Main Forecast Card */}
      {isForecastLoading ? (
        <div className="p-12 text-center bg-slate-900/40 rounded-xl border border-slate-800">
          <Activity className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-300">Extracting chronological features & computing next-session drift...</p>
        </div>
      ) : forecastError ? (
        <div className="p-6 bg-red-950/30 border border-red-800/50 rounded-xl text-red-300 text-sm">
          Failed to load next-session forecast: {(forecastError as Error).message}
        </div>
      ) : forecast ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Column 1 & 2: Primary Forecast Dossier */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                    Target Trading Session
                  </div>
                  <div className="text-lg font-bold text-slate-100 flex items-center gap-2 mt-0.5">
                    <Calendar className="w-4 h-4 text-indigo-400" />
                    <span>{forecast.target_date}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                      {forecast.symbol}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-slate-400">Current Reference Close</div>
                  <div className="text-lg font-bold text-slate-100 font-mono tabular-nums">
                    ₹{forecast.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              {/* Direction & Probability Banner */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Direction Outlook</span>
                  <div className="flex items-center gap-2 mt-2">
                    {forecast.direction === "BULLISH" ? (
                      <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-xl">
                        <TrendingUp className="w-6 h-6" />
                        <span>BULLISH</span>
                      </div>
                    ) : forecast.direction === "BEARISH" ? (
                      <div className="flex items-center gap-1.5 text-rose-400 font-bold text-xl">
                        <TrendingDown className="w-6 h-6" />
                        <span>BEARISH</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-amber-400 font-bold text-xl">
                        <Minus className="w-6 h-6" />
                        <span>NEUTRAL</span>
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2">
                    Confidence: {(forecast.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Upward Probability</span>
                  <div className="mt-2">
                    <div className="flex justify-between text-xs font-mono mb-1">
                      <span className="text-emerald-400 font-bold">{(forecast.prob_up * 100).toFixed(1)}% Up</span>
                      <span className="text-rose-400 font-bold">{(forecast.prob_down * 100).toFixed(1)}% Down</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden flex">
                      <div
                        className="bg-emerald-500 h-full transition-all duration-500"
                        style={{ width: `${forecast.prob_up * 100}%` }}
                      />
                      <div
                        className="bg-rose-500 h-full transition-all duration-500"
                        style={{ width: `${forecast.prob_down * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2">
                    Calibrated via logistic sigmoid
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Expected Mean Drift</span>
                  <div className="mt-2">
                    <span
                      className={`text-2xl font-bold font-mono tabular-nums ${
                        forecast.expected_return_pct > 0
                          ? "text-emerald-400"
                          : forecast.expected_return_pct < 0
                          ? "text-rose-400"
                          : "text-slate-300"
                      }`}
                    >
                      {forecast.expected_return_pct > 0 ? "+" : ""}
                      {forecast.expected_return_pct.toFixed(2)}%
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2">
                    Next-session percentage drift
                  </span>
                </div>
              </div>

              {/* Volatility Range Cone */}
              <div className="mt-6 p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Scale className="w-4 h-4 text-indigo-400" />
                    <span className="text-sm font-semibold text-slate-200">
                      Expected Next-Session Trading Range (1.1x ATR Band)
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    ATR Volatility: {forecast.atr_volatility_pct.toFixed(2)}% | 20d Ann. Vol: {forecast.historical_volatility_20d.toFixed(1)}%
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center pt-2">
                  <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-900/40">
                    <div className="text-[11px] text-rose-300 uppercase font-semibold">Lower Bound Low</div>
                    <div className="text-base font-bold text-rose-200 font-mono tabular-nums mt-1">
                      ₹{forecast.expected_range_low.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700">
                    <div className="text-[11px] text-slate-300 uppercase font-semibold">Current Close</div>
                    <div className="text-base font-bold text-slate-100 font-mono tabular-nums mt-1">
                      ₹{forecast.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-900/40">
                    <div className="text-[11px] text-emerald-300 uppercase font-semibold">Upper Bound High</div>
                    <div className="text-base font-bold text-emerald-200 font-mono tabular-nums mt-1">
                      ₹{forecast.expected_range_high.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Technical Drivers */}
              <div className="mt-6">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Primary Quantitative Drivers
                </h4>
                <div className="space-y-1.5">
                  {forecast.primary_technical_drivers.map((drv, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2 text-xs text-slate-300 bg-slate-950/40 p-2 rounded-lg border border-slate-800/80"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
                      <span>{drv}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Column 3: Baselines & Local AI Integration */}
          <div className="space-y-6">
            {/* Non-ML Baselines Card */}
            <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800">
              <div className="flex items-center gap-2 mb-3">
                <Scale className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-slate-200">
                  Non-ML Financial Baselines
                </h3>
              </div>
              <p className="text-xs text-slate-400 mb-4">
                Quantitative validation against standard random-walk and naive momentum benchmarks:
              </p>

              <div className="space-y-2.5">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                  <div>
                    <span className="font-semibold text-slate-300">Random Walk / Martingale</span>
                    <p className="text-[10px] text-slate-500">Expected drift = 0%</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300">
                    {forecast.baselines.zero_return_direction}
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                  <div>
                    <span className="font-semibold text-slate-300">Persistence Benchmark</span>
                    <p className="text-[10px] text-slate-500">Repeats previous day sign</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      forecast.baselines.persistence_direction === "BULLISH"
                        ? "bg-emerald-950 text-emerald-300"
                        : "bg-rose-950 text-rose-300"
                    }`}
                  >
                    {forecast.baselines.persistence_direction}
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                  <div>
                    <span className="font-semibold text-slate-300">Trend Following (20d SMA)</span>
                    <p className="text-[10px] text-slate-500">Price vs 20d moving average</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      forecast.baselines.trend_following_direction === "BULLISH"
                        ? "bg-emerald-950 text-emerald-300"
                        : "bg-rose-950 text-rose-300"
                    }`}
                  >
                    {forecast.baselines.trend_following_direction}
                  </span>
                </div>
              </div>
            </div>

            {/* Local AI Fin-R1 Deep Catalyst Analysis */}
            <div className="bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-900/60 p-5 rounded-xl border border-indigo-900/40">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Fin-R1 GPU Qualitative Reasoning
                </h3>
              </div>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                Connect this numerical forecast with verified Indian corporate filings, earnings announcements, and macroeconomic catalysts using the local Fin-R1 7B financial specialist LLM.
              </p>

              {onNavigateToAi && (
                <button
                  onClick={() => onNavigateToAi(forecast.symbol)}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition shadow-sm"
                >
                  <span>Analyze {forecast.symbol} with Fin-R1</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Regulatory & Safety Disclaimer */}
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60 text-[11px] text-slate-400 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>{forecast.disclaimer}</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* Historical Ledger & Out-of-Sample Scorecard */}
      <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              <span>Immutable Prediction Ledger & Realized Evaluation</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Tracks forward predictions and scores direction accuracy & volatility containment once next-session market candles arrive.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {history && (
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-slate-400">Historical Hit Rate:</span>
                <span className="text-emerald-400 font-bold px-2 py-0.5 bg-emerald-950/60 rounded border border-emerald-900/50">
                  {history.historical_accuracy_pct}%
                </span>
              </div>
            )}

            <button
              onClick={() => evalMutation.mutate()}
              disabled={evalMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${evalMutation.isPending ? "animate-spin" : ""}`} />
              <span>{evalMutation.isPending ? "Evaluating..." : "Evaluate Realized Sessions"}</span>
            </button>
          </div>
        </div>

        {isHistoryLoading ? (
          <div className="p-8 text-center text-xs text-slate-400">Loading prediction ledger...</div>
        ) : history && history.entries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/40">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Target Date</th>
                  <th className="py-2.5 px-3">Forecast Close</th>
                  <th className="py-2.5 px-3">Predicted Dir</th>
                  <th className="py-2.5 px-3">Expected Drift</th>
                  <th className="py-2.5 px-3">Realized Close</th>
                  <th className="py-2.5 px-3">Realized Ret</th>
                  <th className="py-2.5 px-3">Direction Hit</th>
                  <th className="py-2.5 px-3">Range Containment</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {history.entries.map((entry) => (
                  <tr key={entry.forecast_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-2.5 px-3 font-semibold text-slate-200">{entry.symbol}</td>
                    <td className="py-2.5 px-3 text-slate-400">{entry.target_date}</td>
                    <td className="py-2.5 px-3 text-slate-300">₹{entry.forecast_price.toFixed(2)}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          entry.predicted_direction === "BULLISH"
                            ? "bg-emerald-950 text-emerald-300"
                            : entry.predicted_direction === "BEARISH"
                            ? "bg-rose-950 text-rose-300"
                            : "bg-slate-800 text-slate-300"
                        }`}
                      >
                        {entry.predicted_direction}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">{entry.expected_return_pct.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-slate-300">
                      {entry.realized_close ? `₹${entry.realized_close.toFixed(2)}` : "—"}
                    </td>
                    <td className="py-2.5 px-3">
                      {entry.realized_return_pct !== null && entry.realized_return_pct !== undefined ? (
                        <span
                          className={
                            entry.realized_return_pct > 0
                              ? "text-emerald-400"
                              : entry.realized_return_pct < 0
                              ? "text-rose-400"
                              : "text-slate-400"
                          }
                        >
                          {entry.realized_return_pct > 0 ? "+" : ""}
                          {entry.realized_return_pct.toFixed(2)}%
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {entry.status === "EVALUATED" ? (
                        entry.direction_hit ? (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>HIT</span>
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-rose-400">
                            <XCircle className="w-3.5 h-3.5" />
                            <span>MISS</span>
                          </span>
                        )
                      ) : (
                        <span className="text-slate-500">PENDING</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {entry.status === "EVALUATED" ? (
                        entry.range_hit ? (
                          <span className="text-emerald-400">CONTAINED</span>
                        ) : (
                          <span className="text-amber-400">BREACHED</span>
                        )
                      ) : (
                        <span className="text-slate-500">PENDING</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] ${
                          entry.status === "EVALUATED"
                            ? "bg-indigo-950 text-indigo-300"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-400 bg-slate-950/40 rounded-lg">
            No prediction ledger records yet. Next-session predictions are automatically recorded when generated.
          </div>
        )}
      </div>
    </div>
  );
}
