import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Database, Clock, Lock, ShieldCheck, Wifi } from "lucide-react";
import { getDataHealth, getMarketSession, getMarketDataStatus, selectMarketDataProvider } from "../lib/api";
import { Badge } from "../components/Badge";

export const MarketDataSettingsView: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: dataHealth } = useQuery({
    queryKey: ["data-health"],
    queryFn: () => getDataHealth(),
    refetchInterval: 5000,
  });
  const { data: session } = useQuery({
    queryKey: ["market-session"],
    queryFn: () => getMarketSession(),
    refetchInterval: 10000,
  });
  const { data: providerStatus } = useQuery({
    queryKey: ["market-data-status"],
    queryFn: () => getMarketDataStatus(),
    refetchInterval: 5000,
  });

  const switchProviderMutation = useMutation({
    mutationFn: (provider: string) => selectMarketDataProvider(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market-data-status"] });
      queryClient.invalidateQueries({ queryKey: ["data-health"] });
      queryClient.invalidateQueries({ queryKey: ["api-status"] });
    },
  });

  const activeProvider = providerStatus?.active_provider_setting ?? "unknown";

  return (
    <div className="view-container space-y-6">
      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-top"><span>ACTIVE DATA PROVIDER</span><div className="metric-icon"><Database size={16} /></div></div>
          <div className="metric-value font-mono font-bold text-slate-100">{providerStatus?.resolved_source_type ?? "UNKNOWN"}</div>
          <div className="metric-detail">Provider: {activeProvider}</div>
        </article>
        <article className="metric-card">
          <div className="metric-top"><span>FEED LATENCY</span><div className="metric-icon"><Wifi size={16} /></div></div>
          <div className="metric-value font-mono">{dataHealth?.latency_seconds ?? "—"}s</div>
          <div className="metric-detail">Status: {dataHealth?.feed_status ?? "UNKNOWN"}</div>
        </article>
        <article className="metric-card">
          <div className="metric-top"><span>NSE MARKET SESSION</span><div className="metric-icon"><Clock size={16} /></div></div>
          <div className="metric-value font-mono">{session?.is_open ? "OPEN" : "CLOSED"}</div>
          <div className="metric-detail">{session?.regular_hours ?? "09:15 - 15:30 IST"}</div>
        </article>
        <article className="metric-card">
          <div className="metric-top"><span>NEXT TRADING SESSION</span><div className="metric-icon"><Clock size={16} /></div></div>
          <div className="metric-value font-mono" style={{ fontSize: "15px", marginTop: 14 }}>
            {session?.next_session_open ? session.next_session_open.split(" ")[0] : "Unknown"}
          </div>
          <div className="metric-detail">{session?.statutory_holidays_count ?? "—"} exchange holidays loaded</div>
        </article>
      </section>

      <section className="panel p-5 bg-slate-900/60 rounded-xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-base font-bold text-slate-100">Market data source</h2>
            <p className="text-xs text-slate-400">Only providers actually wired into the current historical-data resolver are selectable here.</p>
          </div>
          <Badge variant={providerStatus?.is_live ? "good" : "neutral"}>{providerStatus?.data_provenance ?? "UNKNOWN"}</Badge>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => switchProviderMutation.mutate("yfinance")}
            className={`p-4 rounded-lg border text-left transition ${activeProvider === "yfinance" ? "bg-lime-950/20 border-lime-500/50" : "bg-slate-950/60 border-slate-800 hover:border-slate-700"}`}
          >
            <strong className="text-sm text-slate-100">Yahoo Finance adapter</strong>
            <p className="text-[11px] text-slate-400 mt-2">Convenient research source. Verify data completeness, latency and terms; do not treat it as an exchange-authorized real-time feed.</p>
          </button>
          <button
            type="button"
            onClick={() => switchProviderMutation.mutate("csv")}
            className={`p-4 rounded-lg border text-left transition ${activeProvider === "csv" ? "bg-lime-950/20 border-lime-500/50" : "bg-slate-950/60 border-slate-800 hover:border-slate-700"}`}
          >
            <strong className="text-sm text-slate-100">Local CSV history</strong>
            <p className="text-[11px] text-slate-400 mt-2">Deterministic offline research using files already stored locally. Source and entitlement must be recorded.</p>
          </button>
        </div>
        {switchProviderMutation.isError && <p className="text-xs text-rose-300">{(switchProviderMutation.error as Error).message}</p>}
      </section>

      <section className="panel p-5 bg-slate-900/60 rounded-xl border border-slate-800 space-y-3">
        <div className="flex items-center gap-2"><Lock className="w-4 h-4 text-lime-400" /><h2 className="text-base font-bold text-slate-100">Server-side credentials only</h2></div>
        <p className="text-xs text-slate-400 leading-6">
          This browser does not collect, store or transmit broker API keys, client codes, PINs or TOTP secrets. Configure any future authorized provider credentials in the backend process environment (.env on the local machine), restart FastAPI, and keep them out of Vite variables, frontend source, localStorage and browser logs.
        </p>
        <div className="rounded-md border border-slate-800 bg-slate-950 p-3 text-[11px] text-lime-300 font-mono">
          DATA_PROVIDER=yfinance<br />
          # Add provider credentials only to the backend .env when a verified adapter is implemented.
        </div>
        <div className="flex items-start gap-2 text-xs text-slate-400">
          <ShieldCheck className="w-4 h-4 text-lime-400 shrink-0" />
          <span>All state-changing FastAPI operations remain localhost-restricted and token-protected when NORTHSTAR_API_TOKEN is configured. The local API token is exchanged for an HttpOnly session cookie, not browser localStorage.</span>
        </div>
      </section>

      <div className="text-[10px] text-slate-500 flex items-center gap-2"><Activity size={13} /> Research data is not automatically proof of exchange licensing or executable quote quality.</div>
    </div>
  );
};
