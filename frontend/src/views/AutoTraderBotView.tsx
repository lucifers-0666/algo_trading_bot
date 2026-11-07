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
    <div className="space-y-5">
      {/* Top Header Card */}
      <div className="bg-[#101623] border border-[#1e2638] rounded-lg p-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`p-2.5 rounded-lg border ${
              isRunning
                ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                : "bg-[#161e30] text-slate-400 border-[#1e2638]"
            }`}
          >
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <div className="text-base font-bold text-slate-100 flex items-center gap-2">
              Autonomous Paper Trading Daemon
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10.5px] font-mono font-semibold border ${
                  isRunning
                    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 animate-pulse"
                    : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                }`}
              >
                {isRunning ? "● DAEMON ACTIVE (AUTO-TRADING)" : "○ DAEMON PAUSED / IDLE"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Autonomous swing/momentum alpha screener and paper order execution engine for Indian equities.
            </p>
          </div>
        </div>

        {/* Bot Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {isRunning ? (
            <button
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-semibold bg-rose-600 text-white hover:bg-rose-500 transition cursor-pointer"
            >
              <Pause className="h-4 w-4" />
              Pause Auto-Trader
            </button>
          ) : (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition cursor-pointer"
            >
              <Play className="h-4 w-4" />
              Start Auto-Trader
            </button>
          )}

          <button
            onClick={() => stepMutation.mutate()}
            disabled={stepMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-medium border border-[#1e2638] bg-[#161e30] text-slate-200 hover:bg-[#1c263c] transition cursor-pointer"
            title="Execute 1 evaluation and paper trading cycle now"
          >
            <RefreshCw className={`h-4 w-4 ${stepMutation.isPending ? "animate-spin text-sky-400" : ""}`} />
            Run 1 Step Now
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-[#101623] border border-[#1e2638] rounded-lg p-4">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
            <span>MARKET STATUS</span>
            <Clock className="h-4 w-4 text-sky-400" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            {status?.is_market_hours ? (
              <span className="text-emerald-400">NSE Open</span>
            ) : (
              <span className="text-amber-400">NSE Closed</span>
            )}
            <span className="text-xs font-normal text-slate-400">
              ({status?.force_market_open ? "24/7 Sim Active" : "Hours Only"})
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center justify-between">
            <span>Last Scan:</span>
            <span className="font-mono text-slate-200">{status?.last_scan_time ?? "Pending"}</span>
          </div>
        </div>

        <div className="bg-[#101623] border border-[#1e2638] rounded-lg p-4">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
            <span>TOTAL AUTO TRADES</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-slate-100 font-mono">
            {status?.total_auto_trades ?? 0}
          </div>
          <div className="mt-2 text-xs text-slate-400">Executed by Autonomous Daemon</div>
        </div>

        <div className="bg-[#101623] border border-[#1e2638] rounded-lg p-4">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
            <span>ACTIVE HOLDINGS</span>
            <Layers className="h-4 w-4 text-sky-400" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-slate-100 font-mono">
            {status?.open_positions_count ?? 0} <span className="text-xs text-slate-400 font-normal">/ 5 max</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">Monitored for Trailing Stops & Targets</div>
        </div>

        <div className="bg-[#101623] border border-[#1e2638] rounded-lg p-4">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
            <span>VIRTUAL CASH</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-xl font-bold tracking-tight text-slate-100 font-mono">
            ₹{(status?.cash_balance ?? 10000).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Equity: ₹{(status?.total_equity ?? 10000).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Autonomous Controls & Parameters */}
      <div className="bg-[#101623] border border-[#1e2638] rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-md bg-[#161e30] border border-[#1e2638] text-sky-400">
            <Sliders className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-200">Execution Frequency & Scope</div>
            <div className="text-xs text-slate-400">
              Configure whether the bot evaluates solely during 09:15-15:30 IST market hours or also in 24/7 simulation mode.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={status?.force_market_open ?? true}
              onChange={(e) => configMutation.mutate({ force_market_open: e.target.checked })}
              className="rounded bg-[#0b0f19] border-[#1e2638] text-emerald-500 focus:ring-emerald-500"
            />
            <span>Allow Simulated Trades Outside Market Hours</span>
          </label>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-medium">Interval:</span>
            <select
              value={status?.scan_interval_seconds ?? 30}
              onChange={(e) => configMutation.mutate({ interval: Number(e.target.value) })}
              className="border border-[#1e2638] rounded-md px-2 py-1 text-xs bg-[#0b0f19] text-slate-200 outline-none"
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
      <div className="bg-[#101623] border border-[#1e2638] rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-[#1e2638] bg-[#0d131f] flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-100">Live Autonomous Trading Activity Stream</h2>
            <p className="text-xs text-slate-400">Real-time decisions, scans, risk gates, and paper order executions.</p>
          </div>

          <div className="flex items-center gap-1 bg-[#161e30] border border-[#1e2638] p-1 rounded-md text-xs">
            {["ALL", "BUYS", "SELLS", "SCANS", "RISK"].map((t) => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                  filterType === t
                    ? "bg-[#1e293b] text-sky-400 border border-sky-500/30 shadow-xs"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-[#161f33] max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="p-8 text-center text-sm text-slate-400">Loading live activity stream...</div>
          ) : filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-400">
              No activity matching filter. Click <strong className="text-slate-200">Run 1 Step Now</strong> or <strong className="text-slate-200">Start Auto-Trader</strong> above.
            </div>
          ) : (
            filteredLogs.map((log, idx) => {
              const isBuy = log.event_type === "AUTO_BUY";
              const isSell = log.event_type.startsWith("AUTO_SELL");
              const isRisk = log.event_type === "RISK_LIMIT" || log.event_type === "PROTECTION" || log.event_type === "HALT";

              return (
                <div key={idx} className="p-3 hover:bg-[#141c2c] transition flex items-start justify-between gap-3 text-xs">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {isBuy ? (
                        <div className="p-1 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <ArrowUpRight className="h-4 w-4" />
                        </div>
                      ) : isSell ? (
                        <div className="p-1 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          <ArrowDownRight className="h-4 w-4" />
                        </div>
                      ) : isRisk ? (
                        <div className="p-1 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                          <AlertTriangle className="h-4 w-4" />
                        </div>
                      ) : (
                        <div className="p-1 rounded bg-[#161e30] text-slate-400 border border-[#1e2638]">
                          <Clock className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-100">{log.symbol}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#161e30] border border-[#1e2638] text-slate-300">
                          {log.event_type}
                        </span>
                        <span className="text-[10.5px] text-slate-400 font-mono">{log.timestamp}</span>
                      </div>
                      <div className="mt-1 text-slate-300">{log.message}</div>
                    </div>
                  </div>

                  {log.details?.conviction && (
                    <div className="text-right shrink-0">
                      <div className="text-[9.5px] text-slate-400 font-bold">CONVICTION</div>
                      <div className="font-mono font-bold text-emerald-400">{log.details.conviction}/100</div>
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
