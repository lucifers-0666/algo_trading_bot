import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Play,
} from "lucide-react";
import { getModels } from "../lib/api";
import { Badge } from "../components/Badge";

interface ModelRegistryViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const ModelRegistryView: React.FC<ModelRegistryViewProps> = ({ onNavigate }) => {
  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: () => getModels(),
  });

  return (
    <div className="view-container">
      {/* Header Bar */}
      <div className="filter-header-bar">
        <div>
          <h2>Financial Machine Learning Model Registry</h2>
          <p>Versioned artifact repository of trained scikit-learn models with out-of-sample metrics</p>
        </div>

        <div className="filter-controls">
          <button
            className="btn-action-primary"
            onClick={() => onNavigate("ML research lab")}
          >
            <Play size={14} /> Train New Model
          </button>
        </div>
      </div>

      {/* Models Catalog Table */}
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>MODEL ID</th>
                <th>ARCHITECTURE</th>
                <th>TRAINED AT (IST)</th>
                <th>TRAIN / TEST SPAN</th>
                <th>SAMPLES</th>
                <th>ACCURACY</th>
                <th>PRECISION</th>
                <th>ROC-AUC</th>
                <th>BRIER SCORE</th>
                <th>PRECISION@K</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={10}>
                    <div className="table-empty">Loading registered models...</div>
                  </td>
                </tr>
              ) : !models || models.length === 0 ? (
                <tr>
                  <td colSpan={10}>
                    <div className="table-empty">
                      No models have been registered yet. Navigate to the ML Research Lab to train your first model.
                    </div>
                  </td>
                </tr>
              ) : (
                models.map((m) => (
                  <tr key={m.model_id}>
                    <td>
                      <code style={{ fontSize: "11px", fontWeight: 700, color: "#2563eb" }}>
                        {m.model_id}
                      </code>
                    </td>
                    <td>
                      <Badge variant="good">{m.model_type.toUpperCase()}</Badge>
                    </td>
                    <td className="text-muted" style={{ fontSize: "11px" }}>
                      {new Date(m.trained_at).toLocaleDateString("en-IN", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                    <td className="text-muted" style={{ fontSize: "11px" }}>
                      {m.train_start} to {m.test_end}
                    </td>
                    <td className="tabular-num">
                      {m.train_samples} tr / {m.test_samples} te
                    </td>
                    <td className="tabular-num">
                      {m.metrics.accuracy != null ? `${(m.metrics.accuracy * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="tabular-num">
                      {m.metrics.precision != null ? `${(m.metrics.precision * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="tabular-num">
                      {m.metrics.roc_auc != null ? m.metrics.roc_auc.toFixed(2) : "—"}
                    </td>
                    <td className="tabular-num">
                      {m.metrics.brier_score != null ? m.metrics.brier_score.toFixed(3) : "—"}
                    </td>
                    <td className="tabular-num">
                      {m.metrics.precision_at_k != null
                        ? `${(m.metrics.precision_at_k * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
