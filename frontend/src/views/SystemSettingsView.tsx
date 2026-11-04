import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  Database,
  Lock,
  RotateCcw,
  AlertTriangle,
  HardDrive,
  CheckCircle2,
} from "lucide-react";
import { resetPaperAccount } from "../lib/api";
import { Modal } from "../components/Modal";
import { Badge } from "../components/Badge";

interface SystemSettingsViewProps {
  onNavigate?: (page: string, symbol?: string) => void;
}

export const SystemSettingsView: React.FC<SystemSettingsViewProps> = () => {
  const queryClient = useQueryClient();
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetSuccessMsg, setResetSuccessMsg] = useState<string | null>(null);

  const resetMutation = useMutation({
    mutationFn: () => resetPaperAccount(true),
    onSuccess: (data) => {
      setResetModalOpen(false);
      setResetSuccessMsg(data.message);
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
      setTimeout(() => setResetSuccessMsg(null), 5000);
    },
  });

  return (
    <div className="view-container">
      {/* Security & Isolation Status Cards */}
      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-top">
            <span>NETWORK BINDING</span>
            <div className="metric-icon"><Lock size={16} /></div>
          </div>
          <div className="metric-value text-good">
            127.0.0.1
          </div>
          <div className="metric-detail">Loopback only · Zero external exposure</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>LIVE ORDER ROUTING</span>
            <div className="metric-icon"><ShieldCheck size={16} /></div>
          </div>
          <div className="metric-value text-good">
            DISABLED
          </div>
          <div className="metric-detail">Strict paper-trading sandbox mode</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>SQLITE WAL MODE</span>
            <div className="metric-icon"><Database size={16} /></div>
          </div>
          <div className="metric-value text-good">
            ACTIVE
          </div>
          <div className="metric-detail">Write-Ahead Logging enabled</div>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>DATABASE LOCATION</span>
            <div className="metric-icon"><HardDrive size={16} /></div>
          </div>
          <div className="metric-value" style={{ fontSize: "14px", marginTop: 14 }}>
            data/trader.db
          </div>
          <div className="metric-detail">Local persistent ACID storage</div>
        </article>
      </section>

      {/* Account Reset Panel */}
      <section className="panel" style={{ marginTop: 18 }}>
        <div className="panel-header">
          <div>
            <h2>Virtual Paper Account Reset Center</h2>
            <p>Restore starting virtual cash (₹10,000) and clear simulated positions</p>
          </div>
          <Badge variant="warning">DESTRUCTIVE ACTION</Badge>
        </div>

        <div className="reset-panel-body" style={{ padding: "18px" }}>
          <p style={{ color: "#6c7a71", fontSize: "13px", lineHeight: 1.6, maxWidth: 640 }}>
            Resetting your virtual account will wipe all open paper positions, restore cash to exactly ₹10,000, and reset day-starting equity for risk limits. Historical backtests and trained ML models are preserved.
          </p>

          {resetSuccessMsg && (
            <div className="notice-bar" style={{ marginBottom: 16 }}>
              <div className="notice-icon">
                <CheckCircle2 size={18} className="text-good" />
              </div>
              <div>
                <strong>Account Reset Complete</strong>
                <span>{resetSuccessMsg}</span>
              </div>
            </div>
          )}

          <button
            className="btn-danger"
            onClick={() => setResetModalOpen(true)}
            style={{ marginTop: 10 }}
          >
            <RotateCcw size={15} /> Reset Virtual Paper Account to ₹10,000
          </button>
        </div>
      </section>

      {/* Reset Confirmation Modal */}
      <Modal
        isOpen={resetModalOpen}
        onClose={() => setResetModalOpen(false)}
        title="Confirm Virtual Account Reset"
        description="This action will restore paper balances to ₹10,000."
      >
        <div className="modal-confirm-body">
          <div className="modal-warning-box">
            <AlertTriangle size={24} className="text-bad" />
            <div>
              <strong>Are you absolutely sure?</strong>
              <p>
                All open positions will be closed without P&L credit, and virtual cash balance will be reset to ₹10,000. This cannot be undone.
              </p>
            </div>
          </div>

          <div className="modal-actions" style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
            <button
              className="button-secondary"
              onClick={() => setResetModalOpen(false)}
              disabled={resetMutation.isPending}
            >
              Cancel
            </button>
            <button
              className="btn-danger"
              onClick={() => resetMutation.mutate()}
              disabled={resetMutation.isPending}
            >
              {resetMutation.isPending ? "Resetting Account..." : "Yes, Reset Virtual Account"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
