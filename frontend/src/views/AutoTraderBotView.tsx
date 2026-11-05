import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Play,
  Pause,
  RefreshCw,
  Sliders,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
} from "lucide-react";
import { getBotStatus, startBot, stopBot, stepBot, configBot } from "../lib/api";

export function AutoTraderBotView() {
  const queryClient = useQueryClient();
  const [filterType, setFilterType] = useState<string>("ALL");

  const { data: status, isLoading } = useQuery({
    queryKey: ["botStatus"],
    queryFn: () => getBotStatus(),
    refetchInterval: 3000,
  });

  const startMutation = useMutation({
    mutationFn: () => startBot(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  const stopMutation = useMutation({
    mutationFn: () => stopBot(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  const stepMutation = useMutation({
    mutationFn: () => stepBot(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["botStatus"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const configMutation = useMutation({
    mutationFn: (payload: { force_market_open?: boolean; interval?: number }) => configBot(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  const isRunning = status?.is_running ?? false;
  const logs = status?.recent_logs ?? [];
  const filteredLogs = logs.filter((log) => {
    if (filterType === "ALL") return true;
    if (filterType === "BUYS") return log.event_type === "AUTO_BUY";
    if (filterType === "SELLS") return log.event_type.startsWith("AUTO_SELL");
    if (filterType === "SCANS") return log.event_type === "SCAN" || log.event_type === "DECISION_SKIP";
    if (filterType === "RISK") return log.event_type === "RISK_LIMIT" || log.event_type === "PROTECTION";
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isRunning ? "bg-green-100 text-green-700" : "bg-muted text-muted-foreground"}`}>
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                Autonomous Paper Trading Bot
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    isRunning ? "bg-green-100 text-green-800 animate-pulse" : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {isRunning ? "● BOT ACTIVE (AUTO-TRADING)" : "○ BOT PAUSED / IDLE"}
                </span>
              </h1>
              <p className="text-sm text-muted mt-1">
                Fully automated, institutional decision-support and simulated paper order execution for Indian equities.
              </p>
            </div>
          </div>
        </div>

        {/* Bot Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {isRunning ? (
            <button
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 text-white hover:bg-red-700 transition"
            >
              <Pause className="h-4 w-4" />
              Pause Auto-Trader
            </button>
          ) : (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-green-700 text-white hover:bg-green-800 transition"
            >
              <Play className="h-4 w-4" />
              Start Auto-Trader
            </button>
          )}

          <button
            onClick={() => stepMutation.mutate()}
            disabled={stepMutation.isPending}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-border bg-card hover:bg-muted/10 transition"
            title="Execute 1 evaluation and paper trading cycle now"
          >
            <RefreshCw className={`h-4 w-4 ${stepMutation.isPending ? "animate-spin" : ""}`} />
            Run 1 Step Now
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted font-medium">
            <span>MARKET STATUS</span>
            <Clock className="h-4 w-4 text-primary" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            {status?.is_market_hours ? (
              <span className="text-green-700">NSE Open</span>
            ) : (
              <span className="text-amber-700">NSE Closed</span>
            )}
            <span className="text-xs font-normal text-muted">
              ({status?.force_market_open ? "24/7 Sim Active" : "Hours Only"})
            </span>
          </div>
          <div className="mt-2 text-xs text-muted flex items-center justify-between">
            <span>Last Scan:</span>
            <span className="font-mono text-foreground">{status?.last_scan_time ?? "Pending"}</span>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted font-medium">
            <span>TOTAL AUTO TRADES</span>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-foreground font-mono">
            {status?.total_auto_trades ?? 0}
          </div>
          <div className="mt-2 text-xs text-muted">Executed by Autonomous Daemon</div>
        </div>

        <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted font-medium">
            <span>ACTIVE HOLDINGS</span>
            <Layers className="h-4 w-4 text-blue-600" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-foreground font-mono">
            {status?.open_positions_count ?? 0} <span className="text-xs text-muted font-normal">/ 5 max</span>
          </div>
          <div className="mt-2 text-xs text-muted">Monitored for Trailing Stops & Targets</div>
        </div>

        <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted font-medium">
            <span>VIRTUAL CASH</span>
            <ShieldCheck className="h-4 w-4 text-green-600" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-foreground font-mono">
            ₹{(status?.cash_balance ?? 10000).toFixed(2)}
          </div>
          <div className="mt-2 text-xs text-muted">
            Equity: ₹{(status?.total_equity ?? 10000).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Autonomous Controls & Parameters */}
      <div className="bg-card border border-border rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Sliders className="h-5 w-5 text-primary" />
          <div>
            <div className="text-sm font-semibold text-foreground">Bot Execution Mode</div>
            <div className="text-xs text-muted">
              Controls whether the bot runs strictly during 09:15-15:30 IST market hours or also in 24/7 simulation mode.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
            <input
              type="checkbox"
              checked={status?.force_market_open ?? true}
              onChange={(e) => configMutation.mutate({ force_market_open: e.target.checked })}
              className="rounded text-primary focus:ring-primary"
            />
            <span>Allow Simulated Trades Outside Market Hours</span>
          </label>

          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted">Interval:</span>
            <select
              value={status?.scan_interval_seconds ?? 30}
              onChange={(e) => configMutation.mutate({ interval: Number(e.target.value) })}
              className="border border-border rounded px-2 py-1 text-xs bg-background"
            >
              <option value="10">10s (High frequency)</option>
              <option value="30">30s (Default)</option>
              <option value="60">60s (Standard)</option>
              <option value="300">5 min (Swing)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Live Activity Stream & Audit Log */}
      <div className="bg-card border border-border rounded-xl shadow-xs overflow-hidden">
        <div className="p-4 border-b border-border flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-foreground">Live Autonomous Trading Activity Stream</h2>
            <p className="text-xs text-muted">Real-time decisions, scans, risk gates, and paper order executions.</p>
          </div>

          <div className="flex items-center gap-1 bg-muted/20 p-1 rounded-lg text-xs">
            {["ALL", "BUYS", "SELLS", "SCANS", "RISK"].map((t) => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  filterType === t ? "bg-card text-foreground shadow-xs" : "text-muted hover:text-foreground"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-border max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="p-8 text-center text-sm text-muted">Loading live activity stream...</div>
          ) : filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted">
              No activity matching filter. Click <strong>Run 1 Step Now</strong> or <strong>Start Auto-Trader</strong> above.
            </div>
          ) : (
            filteredLogs.map((log, idx) => {
              const isBuy = log.event_type === "AUTO_BUY";
              const isSell = log.event_type.startsWith("AUTO_SELL");
              const isRisk = log.event_type === "RISK_LIMIT" || log.event_type === "PROTECTION" || log.event_type === "HALT";

              return (
                <div key={idx} className="p-3.5 hover:bg-muted/5 transition flex items-start justify-between gap-3 text-xs">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {isBuy ? (
                        <div className="p-1 rounded bg-green-100 text-green-700">
                          <ArrowUpRight className="h-4 w-4" />
                        </div>
                      ) : isSell ? (
                        <div className="p-1 rounded bg-red-100 text-red-700">
                          <ArrowDownRight className="h-4 w-4" />
                        </div>
                      ) : isRisk ? (
                        <div className="p-1 rounded bg-amber-100 text-amber-700">
                          <AlertTriangle className="h-4 w-4" />
                        </div>
                      ) : (
                        <div className="p-1 rounded bg-muted/30 text-muted-foreground">
                          <Clock className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground">{log.symbol}</span>
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-muted/20 text-muted-foreground">
                          {log.event_type}
                        </span>
                        <span className="text-[11px] text-muted font-mono">{log.timestamp}</span>
                      </div>
                      <div className="mt-1 text-foreground/90">{log.message}</div>
                    </div>
                  </div>

                  {log.details?.conviction && (
                    <div className="text-right shrink-0">
                      <div className="text-[10px] text-muted">CONVICTION</div>
                      <div className="font-mono font-bold text-green-700">{log.details.conviction}/100</div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

