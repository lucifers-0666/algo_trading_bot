import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BrainCircuit,
  CandlestickChart,
  ChevronDown,
  CircleHelp,
  Database,
  FlaskConical,
  LayoutDashboard,
  Menu,
  Search,
  ShieldCheck,
  Wallet,
  X,
  Layers,
  Scale,
  ShoppingCart,
  History,
  TrendingUp,
  FileText,
  Sliders,
  HardDrive,
  Globe,
  CheckCircle2,
  Cpu,
  Bot,
} from "lucide-react";
import { getApiHealth, getMarketSession } from "./lib/api";

// Import all Views
import { OverviewView } from "./views/OverviewView";
import { MarketScannerView } from "./views/MarketScannerView";
import { InstrumentMasterView } from "./views/InstrumentMasterView";
import { StockResearchView } from "./views/StockResearchView";
import { FinancialIntelligenceView } from "./views/FinancialIntelligenceView";
import { LocalAiResearchView } from "./views/LocalAiResearchView";
import { DecisionSupportView } from "./views/DecisionSupportView";
import { LookaheadAuditView } from "./views/LookaheadAuditView";
import { AutoTraderBotView } from "./views/AutoTraderBotView";
import { StrategyLabView } from "./views/StrategyLabView";
import { MlResearchLabView } from "./views/MlResearchLabView";
import { BacktestingLabView } from "./views/BacktestingLabView";
import { StrategyComparisonView } from "./views/StrategyComparisonView";
import { ModelRegistryView } from "./views/ModelRegistryView";
import { TradingTerminalView } from "./views/TradingTerminalView";
import { PortfolioView } from "./views/PortfolioView";
import { OrderHistoryView } from "./views/OrderHistoryView";
import { PerformanceAnalyticsView } from "./views/PerformanceAnalyticsView";
import { RiskManagementView } from "./views/RiskManagementView";
import { AuditLogsView } from "./views/AuditLogsView";
import { MarketDataSettingsView } from "./views/MarketDataSettingsView";
import { SystemSettingsView } from "./views/SystemSettingsView";
import { NextSessionForecastView } from "./views/NextSessionForecastView";

export type PageKey =
  | "Overview"
  | "Decision support"
  | "Market scanner"
  | "Stock research"
  | "Instrument master"
  | "Next-session forecasting"
  | "Local financial AI"
  | "ML research lab"
  | "Model registry"
  | "Global intelligence"
  | "Strategy lab"
  | "Backtests"
  | "Lookahead & Hyperopt"
  | "Strategy comparison"
  | "Trading terminal"
  | "Auto-trading bot"
  | "Portfolio & holdings"
  | "Order history"
  | "Performance analytics"
  | "Market data & feeds"
  | "Risk management"
  | "Audit logs"
  | "System settings";

interface NavGroup {
  group: string;
  items: { label: PageKey; icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }> }[];
}

const navigation: NavGroup[] = [
  {
    group: "1. OVERVIEW",
    items: [
      { label: "Overview", icon: LayoutDashboard },
      { label: "Decision support", icon: ShieldCheck },
    ],
  },
  {
    group: "2. MARKETS",
    items: [
      { label: "Stock research", icon: CandlestickChart },
      { label: "Market scanner", icon: Search },
      { label: "Instrument master", icon: Database },
    ],
  },
  {
    group: "3. RESEARCH & AI",
    items: [
      { label: "Next-session forecasting", icon: TrendingUp },
      { label: "Local financial AI", icon: BrainCircuit },
      { label: "ML research lab", icon: Cpu },
      { label: "Model registry", icon: Layers },
      { label: "Global intelligence", icon: Globe },
    ],
  },
  {
    group: "4. STRATEGIES & BACKTESTS",
    items: [
      { label: "Strategy lab", icon: Sliders },
      { label: "Backtests", icon: FlaskConical },
      { label: "Lookahead & Hyperopt", icon: CheckCircle2 },
      { label: "Strategy comparison", icon: Scale },
    ],
  },
  {
    group: "5. PAPER TRADING",
    items: [
      { label: "Trading terminal", icon: ShoppingCart },
      { label: "Auto-trading bot", icon: Bot },
      { label: "Portfolio & holdings", icon: Wallet },
      { label: "Order history", icon: History },
      { label: "Performance analytics", icon: TrendingUp },
    ],
  },
  {
    group: "6. SETTINGS & SYSTEM",
    items: [
      { label: "Market data & feeds", icon: Database },
      { label: "Risk management", icon: ShieldCheck },
      { label: "Audit logs", icon: FileText },
      { label: "System settings", icon: HardDrive },
    ],
  },
];

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>("Overview");
  const [activeSymbol, setActiveSymbol] = useState<string>("INFY");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const health = useQuery({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => getApiHealth(signal),
    refetchInterval: 15_000,
  });

  const session = useQuery({
    queryKey: ["market-session-topbar"],
    queryFn: ({ signal }) => getMarketSession(signal),
    refetchInterval: 15_000,
  });

  const apiOnline = health.isSuccess;

  const handleNavigate = (page: string, symbol?: string) => {
    setActivePage(page as PageKey);
    if (symbol) {
      setActiveSymbol(symbol);
    }
    setSidebarOpen(false);
  };

  const currentGroup = useMemo(() => {
    return navigation.find((grp) => grp.items.some((item) => item.label === activePage));
  }, [activePage]);

  const subtitle = useMemo(() => {
    const titles: Record<PageKey, string> = {
      "Overview": "A unified executive telemetry of your research and simulated portfolio.",
      "Decision support": "Unified confluence engine synthesizing technical signals, ML probabilities, regime, and news sentiment into explainable dossiers.",
      "Market scanner": "Discover eligible NSE swing candidates using multi-factor technical screening.",
      "Global intelligence": "Global macroeconomic news, corporate disclosure filings, and event sentiment tracking.",
      "Local financial AI": "Local quantized reasoning models (Fin-R1 / FinGPT) running on RTX 5060 GPU with heuristic fallback.",
      "Instrument master": "Authoritative instrument master records, lot sizing, and tick specifications.",
      "Stock research": "High-density technical analysis charts, indicators, and market regime classification.",
      "Next-session forecasting": "Ensemble econometric & statistical model forecasting next-session direction, returns %, and volatility range cones.",
      "Strategy lab": "Configure quantitative trading rules and review look-ahead bias prevention.",
      "Lookahead & Hyperopt": "Strategy audit verifying 0% future data leakage and systematic Sortino/Calmar parameter optimization.",
      "ML research lab": "Train chronological machine-learning models with purge gaps and zero label leakage.",
      "Backtests": "Event-driven historical backtesting with realistic execution and statutory taxes.",
      "Strategy comparison": "Evaluate multiple strategies side-by-side under identical market conditions.",
      "Model registry": "Catalog of registered machine-learning models and out-of-sample metrics.",
      "Trading terminal": "Simulated order proposal, pre-trade risk verification, and virtual execution.",
      "Auto-trading bot": "Autonomous paper trading daemon monitoring the Indian market, scanning alpha setups, and executing simulated trades.",
      "Portfolio & holdings": "Active open equity holdings with mark-to-market valuation and P&L.",
      "Order history": "Immutable audit trail of all simulated orders, fills, and rejections.",
      "Performance analytics": "In-depth portfolio return metrics, equity curves, and fee attribution.",
      "Risk management": "Emergency kill-switch controller and real-time portfolio guardrail gauges.",
      "Audit logs": "Cryptographically sequenced event stream of system actions and risk verdicts.",
      "Market data & feeds": "Data provenance tracking, latency monitoring, and provider configuration.",
      "System settings": "Localhost binding verification, SQLite WAL database, and virtual account reset.",
    };
    return titles[activePage] ?? "Quantitative research and simulated trading workstation.";
  }, [activePage]);

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <CandlestickChart size={19} strokeWidth={2.1} />
          </div>
          <div>
            <div className="brand-name">northstar<span>.</span></div>
            <div className="brand-caption">QUANT RESEARCH</div>
          </div>
          <button
            className="icon-button sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <div className="workspace-switcher">
          <div className="workspace-avatar">NSE</div>
          <div className="workspace-copy">
            <strong>Indian Equity Workspace</strong>
            <span>Cash Equities · Paper Mode</span>
          </div>
          <ChevronDown size={14} className="muted-icon" />
        </div>

        <nav className="nav-groups" aria-label="Main navigation">
          {navigation.map((group) => (
            <div className="nav-group" key={group.group}>
              <div className="nav-label">{group.group}</div>
              {group.items.map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  className={`nav-item ${activePage === label ? "nav-item-active" : ""}`}
                  onClick={() => handleNavigate(label)}
                >
                  <Icon size={16} strokeWidth={1.8} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <CircleHelp size={16} />
            <span>Research Guide</span>
            <span className="help-shortcut">?</span>
          </div>
          <div className="profile-row">
            <div className="profile-avatar">L</div>
            <div className="profile-copy">
              <strong>Local Quantitative Researcher</strong>
              <span>Paper Sandbox · ₹10k Base</span>
            </div>
            <span className="profile-dot" />
          </div>
          <div className="version-row">
            <span>INDIA · NSE CASH</span>
            <span>v0.2.0</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-area">
        {/* Top Header Bar */}
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={19} />
          </button>

          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="crumb-slash">/</span>
            <span>{currentGroup?.group.split(". ")[1] ?? "Console"}</span>
            <span className="crumb-slash">/</span>
            <strong>{activePage}</strong>
          </div>

          <div className="topbar-actions">
            <div className={`connection-chip ${apiOnline ? "connection-ok" : "connection-off"}`}>
              <span className="connection-dot" />
              {apiOnline ? "FastAPI Online (127.0.0.1)" : "Backend Offline"}
            </div>

            <div className="topbar-divider" />

            <div className="mode-pill">
              <span /> STRICT PAPER TRADING
            </div>
          </div>
        </header>

        {/* Dynamic Page Container */}
        <div className="page-container">
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                INDIAN EQUITY QUANTITATIVE RESEARCH <span>·</span> NSE CASH
              </div>
              <h1>{activePage}</h1>
              <p>{subtitle}</p>
            </div>

            <div className="heading-actions">
              <div className="market-state">
                <span className={`state-dot ${session.data?.is_open ? "state-dot-good" : ""}`} />
                <span>
                  NSE: {session.data?.is_open ? "OPEN (09:15-15:30 IST)" : "CLOSED"}
                </span>
              </div>
              <button
                className="button-secondary"
                onClick={() => {
                  void health.refetch();
                  void session.refetch();
                }}
              >
                <Activity size={14} /> Refresh Telemetry
              </button>
            </div>
          </section>

          {/* 6-Section Sub-Navigation Pill Bar */}
          {currentGroup && currentGroup.items.length > 1 && (
            <div className="flex items-center gap-2 p-1.5 bg-[#0d131f] rounded-lg border border-[#1e2638] overflow-x-auto mb-4">
              <span className="text-[10px] font-bold text-slate-500 px-2.5 shrink-0 uppercase tracking-wider">
                {currentGroup.group.split(". ")[1] || currentGroup.group}:
              </span>
              <div className="flex items-center gap-1.5 flex-nowrap">
                {currentGroup.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activePage === item.label;
                  return (
                    <button
                      key={item.label}
                      onClick={() => handleNavigate(item.label)}
                      className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all whitespace-nowrap cursor-pointer ${
                        isActive
                          ? "bg-[#1e293b] text-[#38bdf8] border border-sky-500/30 shadow-xs font-semibold"
                          : "text-slate-400 hover:text-slate-200 hover:bg-[#161e30] border border-transparent"
                      }`}
                    >
                      <Icon size={13} strokeWidth={isActive ? 2.2 : 1.8} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Render Active View */}
          <div className="active-view-wrapper">
            {activePage === "Overview" && <OverviewView onNavigate={handleNavigate} />}
            {activePage === "Decision support" && (
              <DecisionSupportView
                activeSymbol={activeSymbol}
                onNavigateToPortfolio={() => setActivePage("Portfolio & holdings")}
              />
            )}
            {activePage === "Market scanner" && <MarketScannerView onNavigate={handleNavigate} />}
            {activePage === "Global intelligence" && (
              <FinancialIntelligenceView onSelectSymbol={(sym) => handleNavigate("Stock research", sym)} />
            )}
            {activePage === "Next-session forecasting" && (
              <NextSessionForecastView onNavigateToAi={(sym) => handleNavigate("Local financial AI", sym)} />
            )}
            {activePage === "Local financial AI" && <LocalAiResearchView activeSymbol={activeSymbol} />}
            {activePage === "Instrument master" && <InstrumentMasterView onNavigate={handleNavigate} />}
            {activePage === "Stock research" && (
              <StockResearchView initialSymbol={activeSymbol} onNavigate={handleNavigate} />
            )}
            {activePage === "Strategy lab" && <StrategyLabView onNavigate={handleNavigate} />}
            {activePage === "Lookahead & Hyperopt" && <LookaheadAuditView activeSymbol={activeSymbol} />}
            {activePage === "ML research lab" && <MlResearchLabView onNavigate={handleNavigate} />}
            {activePage === "Backtests" && <BacktestingLabView onNavigate={handleNavigate} />}
            {activePage === "Strategy comparison" && <StrategyComparisonView onNavigate={handleNavigate} />}
            {activePage === "Model registry" && <ModelRegistryView onNavigate={handleNavigate} />}
            {activePage === "Trading terminal" && (
              <TradingTerminalView initialSymbol={activeSymbol} onNavigate={handleNavigate} />
            )}
            {activePage === "Auto-trading bot" && <AutoTraderBotView />}
            {activePage === "Portfolio & holdings" && <PortfolioView onNavigate={handleNavigate} />}
            {activePage === "Order history" && <OrderHistoryView onNavigate={handleNavigate} />}
            {activePage === "Performance analytics" && (
              <PerformanceAnalyticsView onNavigate={handleNavigate} />
            )}
            {activePage === "Risk management" && <RiskManagementView onNavigate={handleNavigate} />}
            {activePage === "Audit logs" && <AuditLogsView onNavigate={handleNavigate} />}
            {activePage === "Market data & feeds" && (
              <MarketDataSettingsView onNavigate={handleNavigate} />
            )}
            {activePage === "System settings" && <SystemSettingsView onNavigate={handleNavigate} />}
          </div>

          <footer className="page-footer">
            <span>Northstar Quantitative Research Platform · NSE Cash Equities</span>
            <span>Strictly Virtual Paper Trading · No Broker Demat Connection · Asia/Kolkata</span>
            <span>Version 0.2.0</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
