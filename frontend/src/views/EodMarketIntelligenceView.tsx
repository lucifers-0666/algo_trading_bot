import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, ArrowUpRight, RefreshCw, ShieldAlert } from "lucide-react";
import { getApiStatus, getLatestEodReport, getPortfolio, setKillSwitch } from "../lib/api";
import type { EODCandidate } from "../lib/types";

interface Props {
  onNavigate: (page: string, symbol?: string) => void;
}

const inr = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);

export function EodMarketIntelligenceView({ onNavigate }: Props) {
  const report = useQuery({
    queryKey: ["eod-latest"],
    queryFn: ({ signal }) => getLatestEodReport(signal),
    retry: false,
    staleTime: 30_000,
  });
  const portfolio = useQuery({
    queryKey: ["eod-portfolio"],
    queryFn: ({ signal }) => getPortfolio(signal),
    refetchInterval: 15_000,
  });
  const status = useQuery({
    queryKey: ["eod-api-status"],
    queryFn: ({ signal }) => getApiStatus(signal),
    refetchInterval: 15_000,
  });

  const data = report.data;
  const market = data?.report;
  const drawdown = useMemo(() => {
    const p = portfolio.data;
    if (!p || !p.day_starting_equity) return 0;
    return Math.max(0, ((p.day_starting_equity - p.total_equity) / p.day_starting_equity) * 100);
  }, [portfolio.data]);

  const handleKillSwitch = async () => {
    const active = Boolean(status.data?.kill_switch_active);
    const action = active ? "disengage" : "engage";
    const reason = active ? "Operator requested manual reset from EOD workstation" : "Emergency stop engaged from EOD workstation";
    await setKillSwitch(action, reason);
    await status.refetch();
  };

  const candidateRows = market?.candidates ?? [];

  return (
    <div className="eod-workspace">
      <section className="eod-header-grid">
        <div className="eod-glass eod-regime-card">
          <div className="eod-label">NEXT SESSION REGIME</div>
          <div className="eod-regime-line">
            <span className={`eod-regime-dot ${market?.bias.bias === "Bullish Trend" ? "is-long" : market?.bias.bias === "Risk-Off" ? "is-risk" : "is-neutral"}`} />
            <strong>{market?.bias.bias ?? "AWAITING REPORT"}</strong>
          </div>
          <div className="eod-muted">NIFTY 50 · ADX {market?.bias.adx_14?.toFixed(1) ?? "—"} · INDIA VIX {market?.bias.india_vix?.toFixed(2) ?? "—"}</div>
        </div>
        <div className="eod-glass eod-metric-card">
          <div className="eod-label">PAPER EQUITY</div>
          <strong>{portfolio.data ? inr(portfolio.data.total_equity) : "—"}</strong>
          <span className="eod-muted">Virtual portfolio · no live orders</span>
        </div>
        <div className="eod-glass eod-metric-card">
          <div className="eod-label">DAILY DRAWDOWN</div>
          <strong className={drawdown > 0 ? "eod-risk-text" : "eod-long-text"}>{drawdown.toFixed(2)}%</strong>
          <div className="eod-progress"><span style={{ width: `${Math.min(100, drawdown / 1 * 100)}%` }} /></div>
          <span className="eod-muted">Daily loss reference · start-of-day equity</span>
        </div>
        <div className="eod-glass eod-kill-card">
          <div className="eod-label">EMERGENCY KILL SWITCH</div>
          <strong className={status.data?.kill_switch_active ? "eod-risk-text" : "eod-long-text"}>
            {status.data?.kill_switch_active ? "ENGAGED" : "DISENGAGED"}
          </strong>
          <button className={status.data?.kill_switch_active ? "eod-button eod-button-safe" : "eod-button eod-button-danger"} onClick={() => void handleKillSwitch()}>
            <ShieldAlert size={14} /> {status.data?.kill_switch_active ? "Reset switch" : "Engage stop"}
          </button>
        </div>
      </section>

      <section className="eod-glass eod-session-card">
        <div className="eod-section-heading">
          <div>
            <div className="eod-label">SESSION REVIEW</div>
            <h2>Prior NSE session</h2>
          </div>
          <button className="eod-icon-button" onClick={() => void report.refetch()} title="Refresh report">
            <RefreshCw size={15} />
          </button>
        </div>
        {report.isLoading && <p className="eod-muted">Loading latest EOD report…</p>}
        {report.isError && <p className="eod-warning"><AlertTriangle size={15} /> No EOD report found. Run scripts/run_eod_analysis.ps1 after the data provider has finalized the session.</p>}
        {market && (
          <>
            <p>{market.next_session_plan}</p>
            <div className="eod-session-stats">
              <div><span className="eod-label">SESSION DATE</span><strong>{market.session_date}</strong></div>
              <div><span className="eod-label">NIFTY CLOSE</span><strong>{market.bias.nifty_close.toFixed(2)}</strong></div>
              <div><span className="eod-label">20 EMA SLOPE</span><strong>{market.bias.sma20_slope_pct.toFixed(2)}%</strong></div>
              <div><span className="eod-label">50 EMA SLOPE</span><strong>{market.bias.sma50_slope_pct.toFixed(2)}%</strong></div>
              <div><span className="eod-label">SECTOR BREADTH</span><strong>{market.bias.positive_sector_count}/{market.bias.sector_count}</strong></div>
              <div><span className="eod-label">UNIVERSE COVERAGE</span><strong>{market.universe_covered}/{market.universe_requested}</strong></div>
            </div>
            <div className="eod-facts">{market.bias.reasons.map((fact) => <span key={fact}>{fact}</span>)}</div>
            {market.data_warning && <p className="eod-warning"><AlertTriangle size={14} /> {market.data_warning}</p>}
            <div className="eod-muted">Provider: {data?.provider} · Universe: {data?.universe_version} · Generated: {data?.generated_at_ist}</div>
          </>
        )}
      </section>

      <section className="eod-glass eod-candidates-card">
        <div className="eod-section-heading">
          <div>
            <div className="eod-label">QUANTITATIVE SELECTION</div>
            <h2>Next-session candidates <span>{candidateRows.length.toString().padStart(2, "0")}</span></h2>
          </div>
          <div className="eod-risk-cap">MAX RISK / TRADE <b>0.50% · ₹50 @ ₹10K</b></div>
        </div>
        <div className="eod-table-wrap">
          <table className="eod-table">
            <thead><tr><th>SYMBOL / PATTERN</th><th>TRIGGER</th><th>STOP LOSS</th><th>QTY</th><th>TARGET 1</th><th>TARGET 2</th><th>R:R</th><th>PLANNED RISK</th><th>ACTION</th></tr></thead>
            <tbody>
              {candidateRows.map((candidate: EODCandidate) => (
                <tr key={candidate.symbol}>
                  <td><strong>{candidate.symbol}</strong><small>{candidate.setup_pattern.replaceAll("_", " ")}</small></td>
                  <td>{inr(candidate.trigger_price)}</td>
                  <td className="eod-risk-text">{inr(candidate.stop_loss)}</td>
                  <td>{candidate.quantity}</td>
                  <td className="eod-long-text">{inr(candidate.target_1)}</td>
                  <td className="eod-long-text">{inr(candidate.target_2)}</td>
                  <td>2R / 3R</td>
                  <td>{inr(candidate.planned_risk_inr)}</td>
                  <td><button className="eod-button eod-button-review" onClick={() => onNavigate("Trading terminal", candidate.symbol)}>Review setup <ArrowUpRight size={13} /></button></td>
                </tr>
              ))}
              {!candidateRows.length && <tr><td colSpan={9} className="eod-empty">No qualified setups in the latest report. No-trade is a valid outcome.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="eod-footnote">Review setup opens the existing paper terminal. It does not execute an order. Next-open price, gap, freshness, available cash, exposure, kill switch and the 0.5% risk cap must be revalidated before any paper fill.</p>
      </section>

      <section className="eod-glass eod-narrative-card">
        <div className="eod-label">LOCAL OLLAMA RESEARCH NOTES</div>
        <h2>Technical rationale</h2>
        <div className="eod-narrative-grid">
          {candidateRows.slice(0, 3).map((candidate) => (
            <article key={candidate.symbol}>
              <strong>{candidate.symbol}</strong>
              <ul>{(candidate.llm_narrative.length ? candidate.llm_narrative : candidate.rationale_facts).map((line, index) => <li key={index}>{line}</li>)}</ul>
            </article>
          ))}
          {!candidateRows.length && <p className="eod-muted">Narratives appear after a successful EOD run with Ollama enabled.</p>}
        </div>
      </section>
      <div className="eod-footer"><Activity size={13} /> STRICT PAPER MODE · NO LIVE BROKER ROUTING · EOD REPORTS ARE CONDITIONAL RESEARCH, NOT ORDERS</div>
    </div>
  );
}
