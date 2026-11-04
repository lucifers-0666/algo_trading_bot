import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BrainCircuit,
  Target,
  BarChart2,
  Layers,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
} from "lucide-react";
import { trainModel } from "../lib/api";
import type { ModelMetadata } from "../lib/types";
import { Badge } from "../components/Badge";

interface MlResearchLabViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const MlResearchLabView: React.FC<MlResearchLabViewProps> = ({ onNavigate }) => {
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState("INFY");
  const [modelType, setModelType] = useState("random_forest");
  const [horizonBars, setHorizonBars] = useState(5);
  const [latestResult, setLatestResult] = useState<ModelMetadata | null>(null);

  const trainMutation = useMutation({
    mutationFn: (params: { symbol: string; model_type: string; horizon_bars: number }) =>
      trainModel(params),
    onSuccess: (data) => {
      setLatestResult(data.metadata);
      queryClient.invalidateQueries({ queryKey: ["models"] });
    },
  });

  const handleTrain = (e: React.FormEvent) => {
    e.preventDefault();
    trainMutation.mutate({
      symbol,
      model_type: modelType,
      horizon_bars: horizonBars,
    });
  };

  return (
    <div className="view-container">
      {/* ML Training Pipeline Control Panel */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Train Financial ML Prediction Model</h2>
            <p>Chronological out-of-sample training with purge gaps and zero label leakage</p>
          </div>
          <button
            className="button-secondary"
            onClick={() => onNavigate("Model registry")}
          >
            <Layers size={14} /> View Registered Models
          </button>
        </div>

        <form onSubmit={handleTrain} className="ml-training-form">
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="target-symbol">Target Instrument</label>
              <select
                id="target-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
              >
                <option value="INFY">INFY (Infosys Ltd)</option>
                <option value="RELIANCE">RELIANCE (Reliance Ind)</option>
                <option value="TCS">TCS (Tata Consultancy)</option>
                <option value="HDFCBANK">HDFCBANK (HDFC Bank)</option>
                <option value="ICICIBANK">ICICIBANK (ICICI Bank)</option>
                <option value="TATAMOTORS">TATAMOTORS (Tata Motors)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="model-algo">Model Architecture</label>
              <select
                id="model-algo"
                value={modelType}
                onChange={(e) => setModelType(e.target.value)}
              >
                <option value="random_forest">Random Forest Classifier (100 trees, max_depth=5)</option>
                <option value="gradient_boosting">Gradient Boosting (learning_rate=0.05)</option>
                <option value="logistic_regression">L2-Regularized Logistic Regression</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="horizon-bars">Prediction Horizon</label>
              <div className="input-unit">
                <input
                  id="horizon-bars"
                  type="number"
                  min={1}
                  max={20}
                  value={horizonBars}
                  onChange={(e) => setHorizonBars(Number(e.target.value))}
                />
                <span>trading sessions forward</span>
              </div>
            </div>
          </div>

          <div className="form-footer-actions">
            <button
              type="submit"
              className="btn-action-primary"
              disabled={trainMutation.isPending}
            >
              {trainMutation.isPending ? (
                <>
                  <RotateCcw size={15} className="spin" /> Training Walk-Forward Pipeline...
                </>
              ) : (
                <>
                  <Play size={15} /> Train & Validate Model
                </>
              )}
            </button>
            {trainMutation.isError && (
              <span className="text-bad" style={{ fontSize: "12px" }}>
                Error: {trainMutation.error.message}
              </span>
            )}
          </div>
        </form>
      </section>

      {/* Validation Results & Evaluation Report */}
      {latestResult && (
        <div className="ml-results-container" style={{ marginTop: 18 }}>
          <div className="notice-bar">
            <div className="notice-icon">
              <CheckCircle2 size={18} className="text-good" />
            </div>
            <div>
              <strong>Model Successfully Trained & Registered: {latestResult.model_id}</strong>
              <span>
                Chronological Train ({latestResult.train_samples} samples: {latestResult.train_start} to {latestResult.train_end}) · Out-of-sample Test ({latestResult.test_samples} samples: {latestResult.test_start} to {latestResult.test_end})
              </span>
            </div>
            <Badge variant="good">{latestResult.model_type.toUpperCase()}</Badge>
          </div>

          {/* Validation Metrics Grid */}
          <section className="metric-grid" style={{ marginTop: 14 }}>
            <article className="metric-card">
              <div className="metric-top">
                <span>ACCURACY (OUT-OF-SAMPLE)</span>
                <div className="metric-icon"><Target size={16} /></div>
              </div>
              <div className="metric-value">
                {latestResult.metrics.accuracy != null
                  ? `${(latestResult.metrics.accuracy * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <div className="metric-detail">Test Set Baseline</div>
            </article>

            <article className="metric-card">
              <div className="metric-top">
                <span>PRECISION (BUY SIGNALS)</span>
                <div className="metric-icon"><BrainCircuit size={16} /></div>
              </div>
              <div className="metric-value">
                {latestResult.metrics.precision != null
                  ? `${(latestResult.metrics.precision * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <div className="metric-detail">False positive minimizer</div>
            </article>

            <article className="metric-card">
              <div className="metric-top">
                <span>BRIER SCORE (CALIBRATION)</span>
                <div className="metric-icon"><BarChart2 size={16} /></div>
              </div>
              <div className="metric-value">
                {latestResult.metrics.brier_score != null
                  ? latestResult.metrics.brier_score.toFixed(3)
                  : "—"}
              </div>
              <div className="metric-detail">Lower is better (&lt; 0.25 is calibrated)</div>
            </article>

            <article className="metric-card">
              <div className="metric-top">
                <span>PRECISION@K (TOP RANKED)</span>
                <div className="metric-icon"><Target size={16} /></div>
              </div>
              <div className="metric-value">
                {latestResult.metrics.precision_at_k != null
                  ? `${(latestResult.metrics.precision_at_k * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <div className="metric-detail">Quality of top conviction decile</div>
            </article>
          </section>

          {/* Feature Importance Table */}
          <section className="panel" style={{ marginTop: 14 }}>
            <div className="panel-header">
              <div>
                <h2>Engineered Feature Set & Permutation Importance</h2>
                <p>Quant indicators transformed into normalized feature vectors</p>
              </div>
            </div>

            <div className="feature-tags-list">
              {latestResult.feature_names.map((fname, idx) => (
                <div key={fname} className="feature-tag-item">
                  <span className="feature-idx">#{idx + 1}</span>
                  <strong>{fname}</strong>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* Methodological Integrity Note */}
      <div className="info-box" style={{ marginTop: 18 }}>
        <div className="info-box-header">
          <AlertCircle size={16} className="text-good" />
          <strong>Quantitative Research Integrity: No Forward-Looking Leakage</strong>
        </div>
        <p>
          Unlike naive machine-learning pipelines that use random k-fold cross-validation, Northstar strictly enforces chronological forward splits with purge gaps between training and testing windows. This ensures future return labels do not leak backwards into the training set.
        </p>
      </div>
    </div>
  );
};
