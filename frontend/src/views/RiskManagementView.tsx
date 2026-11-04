import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
} from "lucide-react";
import { getApiStatus, getPortfolio, setKillSwitch } from "../lib/api";
import { Badge } from "../components/Badge";

interface RiskManagementViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const RiskManagementView: React.FC<RiskManagementViewProps> = () => {
  const queryClient = useQueryClient();
  const [killReason, setKillReason] = useState("Manual operator intervention");

  const { data: status } = useQuery({
    queryKey: ["api-status"],
    queryFn: () => getApiStatus(),
    refetchInterval: 5000,
  });

  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => getPortfolio(),
    refetchInterval: 5000,
  });

  const killSwitchMutation = useMutation({
    mutationFn: (action: "engage" | "disengage") =>
      setKillSwitch(action, killReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-status"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
  });

  const isKillSwitchActive = status?.kill_switch_active ?? false;
  const equity = portfolio?.total_equity ?? 10000;
  const dayStartEquity = portfolio?.day_starting_equity ?? 10000;
  const openPositions = portfolio?.open_positions_count ?? 0;

  return (
    <div className="view-container">
      {/* Kill Switch Controller Panel */}
      <section className={`panel ${isKillSwitchActive ? "panel-kill-active" : ""}`}>
        <div className="panel-header">
          <div>
            <h2>Emergency Kill Switch Controller</h2>
            <p>Immediate fail-closed trading halt. Rejects all pending and new simulated orders</p>
          </div>
          <Badge variant={isKillSwitchActive ? "bad" : "good"}>
            {isKillSwitchActive ? "ENGAGED (HALTED)" : "DISENGAGED (NORMAL)"}
          </Badge>
        </div>

        <div className="kill-switch-body">
          <div className="kill-switch-left">
            <div className={`kill-switch-indicator ${isKillSwitchActive ? "kill-red" : "kill-green"}`}>
              {isKillSwitchActive ? <Lock size={28} /> : <Unlock size={28} />}
            </div>
            <div>
              <h3>
                {isKillSwitchActive
                  ? "Paper Trading is Currently HALTED"
                  : "Trading Guardrails Active & Enforcing"}
              </h3>
              <p className="text-muted">
                {isKillSwitchActive
                  ? `Halt Reason: ${status?.kill_switch_reason ?? "Operator engaged"}`
                  : "All simulated orders are subject to two-phase risk verification before fill."}
              </p>
            </div>
          </div>

          <div className="kill-switch-actions">
            <input
              type="text"
              placeholder="Audit reason for action..."
              value={killReason}
              onChange={(e) => setKillReason(e.target.value)}
              className="kill-reason-input"
            />
            {isKillSwitchActive ? (
              <button
                className="btn-disengage"
                onClick={() => killSwitchMutation.mutate("disengage")}
                disabled={killSwitchMutation.isPending}
              >
                <Unlock size={16} /> Disengage Kill Switch
              </button>
            ) : (
              <button
                className="btn-engage"
                onClick={() => killSwitchMutation.mutate("engage")}
                disabled={killSwitchMutation.isPending}
              >
                <ShieldAlert size={16} /> ENGAGE KILL SWITCH
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Guardrail Telemetry Gauges */}
      <div className="guardrail-section-header" style={{ marginTop: 22, marginBottom: 12 }}>
        <h2>Active Portfolio Risk Guardrails</h2>
        <p>Hard-coded limits enforced on every order proposal and fill revalidation</p>
      </div>

      <div className="guardrail-grid">
        <div className="guardrail-card">
          <div className="guardrail-top">
            <strong>1. Max Risk Per Trade (2.0%)</strong>
            <Badge variant="good">ENFORCED</Badge>
          </div>
          <p>Restricts dollar loss at stop-loss distance to ≤ 2% of total equity.</p>
          <div className="guardrail-metric">
            <span>Max Allowable Loss:</span>
            <strong>₹{(equity * 0.02).toFixed(2)}</strong>
          </div>
        </div>

        <div className="guardrail-card">
          <div className="guardrail-top">
            <strong>2. Daily Loss Limit (3.0%)</strong>
            <Badge variant="good">ENFORCED</Badge>
          </div>
          <p>Stops new entries if day's losses exceed 3% of today's starting equity.</p>
          <div className="guardrail-metric">
            <span>Daily Loss Limit:</span>
            <strong>₹{(dayStartEquity * 0.03).toFixed(2)}</strong>
          </div>
        </div>

        <div className="guardrail-card">
          <div className="guardrail-top">
            <strong>3. Concurrent Positions Limit</strong>
            <Badge variant="good">ENFORCED</Badge>
          </div>
          <p>Maximum 5 simultaneous open equity positions allowed in the portfolio.</p>
          <div className="guardrail-metric">
            <span>Active Positions:</span>
            <strong>{openPositions} / 5 max</strong>
          </div>
        </div>

        <div className="guardrail-card">
          <div className="guardrail-top">
            <strong>4. Single-Stock Exposure (25.0%)</strong>
            <Badge variant="good">ENFORCED</Badge>
          </div>
          <p>Caps capital allocation to any single ticker at 25% of total account value.</p>
          <div className="guardrail-metric">
            <span>Max Single Position:</span>
            <strong>₹{(equity * 0.25).toFixed(2)}</strong>
          </div>
        </div>
      </div>

      {/* Two-Phase Pre-Fill Architecture Card */}
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-header">
          <div>
            <h2>Two-Phase Pre-Trade & Pre-Fill Risk Revalidation Architecture</h2>
            <p>Prevents race conditions and market shifts between proposal time and simulated execution</p>
          </div>
          <ShieldCheck size={18} className="text-good" />
        </div>

        <div className="architecture-explain">
          <div className="arch-step">
            <span className="step-num">Phase 1</span>
            <strong>Pre-Trade Sizing Evaluation</strong>
            <p>
              When an order proposal arrives, the Risk Manager validates equity, calculates stop distance, checks penny-stock price filters, and computes position sizing.
            </p>
          </div>
          <div className="arch-divider">→</div>
          <div className="arch-step">
            <span className="step-num">Phase 2</span>
            <strong>Pre-Fill Atomic Revalidation</strong>
            <p>
              Immediately prior to updating cash balances and appending the fill to the position repository, the broker re-validates that cash remains sufficient and the kill-switch has not triggered.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
