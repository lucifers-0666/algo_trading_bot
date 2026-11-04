import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, ArrowDownRight, ArrowUpRight, Bell, BrainCircuit, CandlestickChart,
  ChevronDown, CircleHelp, Command, Database, FlaskConical, Gauge, LayoutDashboard,
  ListFilter, Menu, Search, Settings2, ShieldCheck, SlidersHorizontal, Wallet,
  WifiOff, X,
} from "lucide-react";
import { getApiHealth } from "./lib/api";

type PageKey = "Overview" | "Market scanner" | "Research lab" | "Backtests" | "Paper portfolio" | "Risk & audit" | "Settings";

const navigation: { group: string; items: { label: PageKey; icon: typeof LayoutDashboard }[] }[] = [
  { group: "WORKSPACE", items: [
    { label: "Overview", icon: LayoutDashboard },
    { label: "Market scanner", icon: CandlestickChart },
    { label: "Research lab", icon: BrainCircuit },
    { label: "Backtests", icon: FlaskConical },
  ]},
  { group: "PAPER TRADING", items: [
    { label: "Paper portfolio", icon: Wallet },
    { label: "Risk & audit", icon: ShieldCheck },
  ]},
  { group: "PREFERENCES", items: [{ label: "Settings", icon: Settings2 }] },
];

function App() {
  const [activePage, setActivePage] = useState<PageKey>("Overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const health = useQuery({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => getApiHealth(signal),
    refetchInterval: 15_000,
  });
  const apiOnline = health.isSuccess;

  const subtitle = useMemo(() => ({
    "Overview": "A clear view of your research and simulated portfolio.",
    "Market scanner": "Discover eligible NSE candidates from verified market data.",
    "Research lab": "Compare deterministic rules and machine-learning experiments.",
    "Backtests": "Review event-driven simulations after costs and slippage.",
    "Paper portfolio": "Track virtual cash, positions and simulated orders.",
    "Risk & audit": "Review portfolio guardrails and every simulated decision.",
    "Settings": "Configure local services and data-source connectivity.",
  } satisfies Record<PageKey, string>)[activePage], [activePage]);

  const choosePage = (page: PageKey) => {
    setActivePage(page);
    setSidebarOpen(false);
  };

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><CandlestickChart size={19} strokeWidth={2.1} /></div>
          <div><div className="brand-name">northstar<span>.</span></div><div className="brand-caption">QUANT RESEARCH</div></div>
          <button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={18}/></button>
        </div>

        <div className="workspace-switcher">
          <div className="workspace-avatar">AI</div>
          <div className="workspace-copy"><strong>Personal workspace</strong><span>Local environment</span></div>
          <ChevronDown size={15} className="muted-icon"/>
        </div>

        <nav className="nav-groups" aria-label="Main navigation">
          {navigation.map((group) => (
            <div className="nav-group" key={group.group}>
              <div className="nav-label">{group.group}</div>
              {group.items.map(({ label, icon: Icon }) => (
                <button key={label} className={`nav-item ${activePage === label ? "nav-item-active" : ""}`} onClick={() => choosePage(label)}>
                  <Icon size={17} strokeWidth={1.8}/><span>{label}</span>
                  {label === "Market scanner" && <span className="nav-count">0</span>}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help"><CircleHelp size={17}/><span>Research guide</span><span className="help-shortcut">?</span></div>
          <div className="profile-row">
            <div className="profile-avatar">L</div>
            <div className="profile-copy"><strong>Local researcher</strong><span>Paper environment</span></div>
            <span className="profile-dot"/>
          </div>
          <div className="version-row"><span>INDIA · NSE CASH</span><span>v0.2.0</span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={19}/></button>
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>{activePage}</strong></div>
          <div className="topbar-actions">
            <div className={`connection-chip ${apiOnline ? "connection-ok" : "connection-off"}`}>
              <span className="connection-dot"/>{apiOnline ? "Backend connected" : "Backend offline"}
            </div>
            <button className="icon-button" aria-label="Notifications"><Bell size={18}/><i className="notification-dot"/></button>
            <div className="topbar-divider"/>
            <div className="mode-pill"><span/>PAPER MODE</div>
          </div>
        </header>

        <div className="page-container">
          <section className="page-heading">
            <div><div className="eyebrow">INDIAN EQUITY RESEARCH <span>·</span> NSE</div><h1>{activePage}</h1><p>{subtitle}</p></div>
            <div className="heading-actions"><div className="market-state"><span className="state-dot"/><span>Market status unavailable</span></div><button className="button-secondary" onClick={() => void health.refetch()}><Activity size={15}/> Refresh status</button></div>
          </section>

          {activePage === "Overview" ? <Overview apiOnline={apiOnline} /> : <SectionPlaceholder page={activePage} apiOnline={apiOnline}/>}
          <footer className="page-footer"><span>Northstar Research Platform</span><span>Virtual trading only · No broker order routing</span><span>Asia/Kolkata</span></footer>
        </div>
      </main>
    </div>
  );
}

function Overview({ apiOnline }: { apiOnline: boolean }) {
  return (
    <>
      <div className="notice-bar">
        <div className="notice-icon"><ShieldCheck size={17}/></div>
        <div><strong>Simulation environment</strong><span>All orders are virtual. No demat account or live order connection is enabled.</span></div>
        <span className="notice-status">SAFE BY DEFAULT</span>
      </div>

      <section className="metric-grid" aria-label="Paper account overview">
        <MetricCard label="VIRTUAL EQUITY" value="₹10,000.00" detail="Configured starting capital" icon={Wallet} />
        <MetricCard label="AVAILABLE CASH" value="₹10,000.00" detail="No simulated positions yet" icon={Database} />
        <MetricCard label="TODAY'S P&L" value="—" detail="Waiting for paper-trading data" icon={Activity} muted />
        <MetricCard label="MAX DRAWDOWN" value="—" detail="Available after simulation runs" icon={Gauge} muted />
      </section>

      <div className="content-grid">
        <section className="panel scanner-panel">
          <div className="panel-header"><div><h2>Market opportunities</h2><p>Candidate discovery · NSE cash equities</p></div><button className="text-button" disabled>Open scanner <ArrowUpRight size={14}/></button></div>
          <div className="empty-state">
            <div className="empty-icon"><CandlestickChart size={23}/></div>
            <strong>{apiOnline ? "Market data not connected" : "Waiting for local backend"}</strong>
            <p>{apiOnline ? "The API is reachable, but no licensed market-data feed or validated scanner snapshot is available yet." : "Start the local API to connect the dashboard. Market prices will remain hidden until a verified provider or historical dataset is configured."}</p>
            <div className="empty-meta"><span className="mini-dot"/>No stock prices are being simulated in this view</div>
          </div>
        </section>

        <section className="panel feed-panel">
          <div className="panel-header"><div><h2>System health</h2><p>Services and data freshness</p></div><span className={`status-label ${apiOnline ? "status-good" : "status-neutral"}`}>{apiOnline ? "API ONLINE" : "OFFLINE"}</span></div>
          <HealthRow icon={Activity} label="Application API" value={apiOnline ? "Connected" : "Not connected"} good={apiOnline}/>
          <HealthRow icon={Database} label="Market data feed" value="Not configured" />
          <HealthRow icon={BrainCircuit} label="ML inference" value="Not active" />
          <HealthRow icon={ShieldCheck} label="Paper risk controls" value="Awaiting backend" />
          <div className="feed-footnote"><WifiOff size={14}/> Live data status is not inferred from API availability.</div>
        </section>
      </div>

      <section className="panel portfolio-panel">
        <div className="panel-header"><div><h2>Portfolio activity</h2><p>Recent virtual orders and simulated fills</p></div><button className="filter-button" disabled><ListFilter size={15}/> Filters</button></div>
        <div className="table-wrap">
          <table><thead><tr><th>INSTRUMENT</th><th>SIDE</th><th>QUANTITY</th><th>FILL PRICE</th><th>STATUS</th><th>TIME (IST)</th></tr></thead>
          <tbody><tr><td colSpan={6}><div className="table-empty">No simulated orders have been recorded.</div></td></tr></tbody></table>
        </div>
      </section>
    </>
  );
}

function MetricCard({ label, value, detail, icon: Icon, muted = false }: { label: string; value: string; detail: string; icon: typeof Wallet; muted?: boolean }) {
  return <article className="metric-card"><div className="metric-top"><span>{label}</span><div className="metric-icon"><Icon size={17}/></div></div><div className={`metric-value ${muted ? "metric-muted" : ""}`}>{value}</div><div className="metric-detail">{detail}</div></article>;
}

function HealthRow({ icon: Icon, label, value, good = false }: { icon: typeof Activity; label: string; value: string; good?: boolean }) {
  return <div className="health-row"><div className="health-icon"><Icon size={15}/></div><span>{label}</span><strong className={good ? "text-good" : "text-neutral"}>{value}</strong></div>;
}

function SectionPlaceholder({ page, apiOnline }: { page: PageKey; apiOnline: boolean }) {
  const icon = page === "Research lab" ? BrainCircuit : page === "Backtests" ? FlaskConical : page === "Paper portfolio" ? Wallet : page === "Risk & audit" ? ShieldCheck : page === "Settings" ? SlidersHorizontal : Search;
  const Icon = icon;
  return <section className="panel route-placeholder"><div className="placeholder-icon"><Icon size={25}/></div><h2>{page} is being connected</h2><p>This React route is scaffolded. Its data view will be enabled when the corresponding FastAPI contract and tested Python service are ready.</p><div className="placeholder-state"><span className={apiOnline ? "state-dot" : "state-dot state-dot-off"}/>{apiOnline ? "Backend reachable; feature endpoint not implemented." : "Backend is offline."}</div></section>;
}

export default App;
