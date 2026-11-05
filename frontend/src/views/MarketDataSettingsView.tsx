import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Wifi,
  Database,
  Clock,
  Save,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Sparkles,
  Lock,
} from "lucide-react";
import {
  getDataHealth,
  getMarketSession,
  getMarketDataStatus,
  configureMarketData,
  selectMarketDataProvider,
} from "../lib/api";
import { Badge } from "../components/Badge";

interface MarketDataSettingsViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const MarketDataSettingsView: React.FC<MarketDataSettingsViewProps> = () => {
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

  // Angel One Credentials Form State
  const [angelApiKey, setAngelApiKey] = useState("");
  const [angelClientCode, setAngelClientCode] = useState("");
  const [angelPin, setAngelPin] = useState("");
  const [angelTotpSecret, setAngelTotpSecret] = useState("");
  const [angelFeedback, setAngelFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const configureMutation = useMutation({
    mutationFn: () =>
      configureMarketData({
        api_key: angelApiKey,
        client_code: angelClientCode,
        pin: angelPin,
        totp_secret: angelTotpSecret,
        test_connection: true,
      }),
    onSuccess: (data) => {
      setAngelFeedback({ type: "success", message: data.message });
      queryClient.invalidateQueries({ queryKey: ["market-data-status"] });
      queryClient.invalidateQueries({ queryKey: ["data-health"] });
      queryClient.invalidateQueries({ queryKey: ["api-status"] });
    },
    onError: (err: Error) => {
      setAngelFeedback({ type: "error", message: err.message || "Failed to authenticate with Angel One SmartAPI" });
    },
  });

  const switchProviderMutation = useMutation({
    mutationFn: (provider: string) => selectMarketDataProvider(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market-data-status"] });
      queryClient.invalidateQueries({ queryKey: ["data-health"] });
      queryClient.invalidateQueries({ queryKey: ["api-status"] });
    },
  });

  const handleSaveAngel = (e: React.FormEvent) => {
    e.preventDefault();
    setAngelFeedback(null);
    configureMutation.mutate();
  };

  return (
    <div className="view-container space-y-6">
      {/* Telemetry Status Cards */}
      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-top">
            <span>ACTIVE DATA PROVIDER</span>
            <div className="metric-icon"><Database size={16} /></div>
          </div>
          <div className="metric-value font-mono font-bold text-slate-100">
            {providerStatus?.resolved_source_type ?? "SYNTHETIC"}
          </div>
          <div className="metric-detail">
            Mode: {providerStatus?.is_live ? "Live Broker Feed" : "Synthetic / Offline Simulation"}
          </div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>FEED LATENCY</span>
            <div className="metric-icon"><Wifi size={16} /></div>
          </div>
          <div className="metric-value font-mono">
            {dataHealth?.latency_seconds ?? 0}s
          </div>
          <div className="metric-detail">Status: {dataHealth?.feed_status ?? "HEALTHY"}</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>NSE MARKET SESSION</span>
            <div className="metric-icon"><Clock size={16} /></div>
          </div>
          <div className="metric-value font-mono">
            {session?.is_open ? "OPEN" : "CLOSED"}
          </div>
          <div className="metric-detail">{session?.regular_hours ?? "09:15 - 15:30 IST"}</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>NEXT TRADING SESSION</span>
            <div className="metric-icon"><Clock size={16} /></div>
          </div>
          <div className="metric-value font-mono" style={{ fontSize: "15px", marginTop: 14 }}>
            {session?.next_session_open ? session.next_session_open.split(" ")[0] : "Next Business Day"}
          </div>
          <div className="metric-detail">{session?.statutory_holidays_count ?? 15} Statutory Holidays Active</div>
        </article>
      </section>

      {/* Provider Switcher Selector */}
      <section className="panel p-5 bg-slate-900/60 rounded-xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-base font-bold text-slate-100">Select Market Data Provider</h2>
            <p className="text-xs text-slate-400">
              Choose the data feed used for live charts, scanners, next-session forecasting, and paper trading.
            </p>
          </div>
          <Badge variant={providerStatus?.is_live ? "good" : "neutral"}>
            {providerStatus?.data_provenance ?? "SYNTHETIC"}
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Angel One SmartAPI */}
          <button
            type="button"
            onClick={() => switchProviderMutation.mutate("angelone")}
            className={`p-3.5 rounded-xl border text-left transition ${
              providerStatus?.active_provider_setting === "angelone"
                ? "bg-indigo-950/40 border-indigo-500/80 shadow-sm"
                : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-slate-200">Angel One SmartAPI</span>
              {providerStatus?.angelone.connected ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold">CONNECTED</span>
              ) : providerStatus?.angelone.configured ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 font-bold">CONFIGURED</span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">RECOMMENDED</span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              ₹0 Free Market Data, historical OHLCV & 5-level order depth for Demat account holders.
            </p>
          </button>

          {/* Synthetic Procedural Generator */}
          <button
            type="button"
            onClick={() => switchProviderMutation.mutate("synthetic")}
            className={`p-3.5 rounded-xl border text-left transition ${
              providerStatus?.active_provider_setting === "synthetic"
                ? "bg-indigo-950/40 border-indigo-500/80 shadow-sm"
                : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-slate-200">Synthetic Generator</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 font-bold">BUILT-IN</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              100% deterministic offline math simulator for strategy debugging and offline testing.
            </p>
          </button>

          {/* DhanHQ */}
          <button
            type="button"
            onClick={() => switchProviderMutation.mutate("dhan")}
            className={`p-3.5 rounded-xl border text-left transition ${
              providerStatus?.active_provider_setting === "dhan"
                ? "bg-indigo-950/40 border-indigo-500/80 shadow-sm"
                : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-slate-200">DhanHQ Data</span>
              {providerStatus?.dhan.configured ? (
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold">CONFIGURED</span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">₹499/mo Data Fee</span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Note: Dhan charges ₹499+GST/mo for market data feeds (Trading APIs are ₹0).
            </p>
          </button>
        </div>
      </section>

      {/* Angel One SmartAPI Setup Panel */}
      <section className="panel p-5 bg-slate-900/60 rounded-xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <h2 className="text-base font-bold text-slate-100">Angel One SmartAPI Setup (Free Market Data)</h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Enter your SmartAPI credentials. Requires standard SmartAPI Developer account and TOTP secret.
            </p>
          </div>
          <a
            href="https://smartapi.angelbroking.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
          >
            <span>SmartAPI Portal</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        <form onSubmit={handleSaveAngel} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">SmartAPI Key</label>
              <input
                type="text"
                placeholder="e.g. 5x8Y..."
                value={angelApiKey}
                onChange={(e) => setAngelApiKey(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">Create an app on SmartAPI portal to get key</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Angel One Client Code</label>
              <input
                type="text"
                placeholder="e.g. A123456"
                value={angelClientCode}
                onChange={(e) => setAngelClientCode(e.target.value.toUpperCase())}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">Your 6-8 digit Angel One Demat account login ID</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Trading PIN (4-digit)</label>
              <input
                type="password"
                placeholder="••••"
                maxLength={4}
                value={angelPin}
                onChange={(e) => setAngelPin(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">The 4-digit PIN you use to log in to Angel One</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">TOTP Secret Key (pyotp)</label>
              <input
                type="password"
                placeholder="e.g. JBSWY3DPEHPK3PXP..."
                value={angelTotpSecret}
                onChange={(e) => setAngelTotpSecret(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">Alphanumeric TOTP key obtained when enabling 2FA</span>
            </div>
          </div>

          {angelFeedback && (
            <div
              className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                angelFeedback.type === "success"
                  ? "bg-emerald-950/50 border border-emerald-800 text-emerald-300"
                  : "bg-rose-950/50 border border-rose-800 text-rose-300"
              }`}
            >
              {angelFeedback.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0" />
              )}
              <span>{angelFeedback.message}</span>
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={configureMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{configureMutation.isPending ? "Authenticating Session..." : "Save & Verify Connection"}</span>
            </button>
          </div>
        </form>
      </section>

      {/* Safety & Isolation Guarantee */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-3 text-xs text-slate-400">
        <Lock className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-200 block mb-0.5">Strict Read-Only Market Data Isolation</strong>
          <span>
            Northstar's <code>AngelOneAdapter</code> only calls market data endpoints (historical OHLCV candles, 5-level market depth, and quote snapshots). The adapter contains hard architectural assertions blocking order placement, position modification, or account fund withdrawals. All trades execute inside the virtual paper-trading engine with ₹10,000 starting cash.
          </span>
        </div>
      </div>
    </div>
  );
};
