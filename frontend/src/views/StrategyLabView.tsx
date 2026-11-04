import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BrainCircuit,
  Sliders,
  CheckCircle2,
  Play,
  TrendingUp,
  BarChart,
  Target,
} from "lucide-react";
import { getStrategies } from "../lib/api";
import { Badge } from "../components/Badge";

interface StrategyLabViewProps {
  onNavigate: (page: string, symbol?: string) => void;
}

export const StrategyLabView: React.FC<StrategyLabViewProps> = ({ onNavigate }) => {
  const { data: strategies, isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => getStrategies(),
  });

  const [selectedStrategyId, setSelectedStrategyId] = useState("baseline_swing");
  const [smaFast, setSmaFast] = useState(20);
  const [smaSlow, setSmaSlow] = useState(50);
  const [rsiMin, setRsiMin] = useState(45);
  const [rsiMax, setRsiMax] = useState(65);
  const [stopAtrMult, setStopAtrMult] = useState(2.0);

  const activeStrat = strategies?.find((s) => s.id === selectedStrategyId) ?? strategies?.[0];

  return (
    <div className="view-container">
      {/* Strategy Selector Header Cards */}
      <div className="strategy-card-grid">
        {isLoading ? (
          <div className="table-empty">Loading strategies...</div>
        ) : (
          strategies?.map((strat) => (
            <div
              key={strat.id}
              className={`strategy-select-card ${selectedStrategyId === strat.id ? "strategy-card-active" : ""}`}
              onClick={() => setSelectedStrategyId(strat.id)}
            >
              <div className="strat-top">
                <BrainCircuit size={18} className="text-good" />
                <Badge variant={selectedStrategyId === strat.id ? "good" : "neutral"}>
                  {strat.id.toUpperCase()}
                </Badge>
              </div>
              <h3>{strat.name}</h3>
              <p>{strat.description}</p>
            </div>
          ))
        )}
      </div>

      {activeStrat && (
        <div className="content-grid" style={{ marginTop: 18 }}>
          {/* Left: Parameter Tuner */}
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Configurable Parameters ({activeStrat.name})</h2>
                <p>Fine-tune quantitative rules without editing Python source code</p>
              </div>
              <Sliders size={16} className="text-muted" />
            </div>

            <div className="param-form">
              <div className="param-row">
                <div className="param-label">
                  <label htmlFor="sma-fast">Fast Moving Average (SMA)</label>
                  <span>Short-term trend direction indicator</span>
                </div>
                <div className="param-input-wrap">
                  <input
                    id="sma-fast"
                    type="number"
                    min={5}
                    max={50}
                    value={smaFast}
                    onChange={(e) => setSmaFast(Number(e.target.value))}
                  />
                  <span>bars</span>
                </div>
              </div>

              <div className="param-row">
                <div className="param-label">
                  <label htmlFor="sma-slow">Slow Moving Average (SMA)</label>
                  <span>Medium-term structural trend filter</span>
                </div>
                <div className="param-input-wrap">
                  <input
                    id="sma-slow"
                    type="number"
                    min={20}
                    max={200}
                    value={smaSlow}
                    onChange={(e) => setSmaSlow(Number(e.target.value))}
                  />
                  <span>bars</span>
                </div>
              </div>

              <div className="param-row">
                <div className="param-label">
                  <label>RSI Pullback Range</label>
                  <span>Momentum pullback band (Min - Max)</span>
                </div>
                <div className="param-input-wrap dual-input">
                  <input
                    type="number"
                    min={20}
                    max={50}
                    value={rsiMin}
                    onChange={(e) => setRsiMin(Number(e.target.value))}
                  />
                  <span>to</span>
                  <input
                    type="number"
                    min={50}
                    max={80}
                    value={rsiMax}
                    onChange={(e) => setRsiMax(Number(e.target.value))}
                  />
                </div>
              </div>

              <div className="param-row">
                <div className="param-label">
                  <label htmlFor="stop-atr">Stop Loss Volatility Distance</label>
                  <span>Multiple of Average True Range (14-day ATR)</span>
                </div>
                <div className="param-input-wrap">
                  <input
                    id="stop-atr"
                    type="number"
                    step="0.1"
                    min={1.0}
                    max={5.0}
                    value={stopAtrMult}
                    onChange={(e) => setStopAtrMult(Number(e.target.value))}
                  />
                  <span>x ATR</span>
                </div>
              </div>

              <div className="param-actions">
                <button
                  className="btn-action-primary"
                  onClick={() => onNavigate("Backtests")}
                  style={{ width: "100%", justifyContent: "center" }}
                >
                  <Play size={15} /> Execute Backtest with Parameters
                </button>
              </div>
            </div>
          </section>

          {/* Right: Strategy Logic & Explainability Breakdown */}
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Rule Explainability & Architecture</h2>
                <p>Explicit execution timeline and look-ahead bias prevention</p>
              </div>
            </div>

            <div className="rule-cards">
              <div className="rule-card">
                <div className="rule-card-icon">
                  <TrendingUp size={16} className="text-good" />
                </div>
                <div>
                  <strong>1. Trend Qualification & Signal Generation</strong>
                  <p>
                    Signals are computed strictly after candle completion at 15:30 IST. Price must close above SMA {smaSlow} and SMA {smaFast} must exceed SMA {smaSlow}.
                  </p>
                </div>
              </div>

              <div className="rule-card">
                <div className="rule-card-icon">
                  <BarChart size={16} className="text-good" />
                </div>
                <div>
                  <strong>2. Entry Execution on Next Eligible Bar</strong>
                  <p>
                    Execution occurs at the NEXT session open (09:15 IST) without look-ahead bias. Stocks in 5% circuit locks or zero volume are rejected.
                  </p>
                </div>
              </div>

              <div className="rule-card">
                <div className="rule-card-icon">
                  <Target size={16} className="text-warning" />
                </div>
                <div>
                  <strong>3. Volatility-Based Stop Loss Protection</strong>
                  <p>
                    Stop-loss is placed at Entry Price - ({stopAtrMult} × ATR 14). Intrabar stop checks and gap-through-stop protection execute at the realistic open price.
                  </p>
                </div>
              </div>

              <div className="rule-card">
                <div className="rule-card-icon">
                  <CheckCircle2 size={16} className="text-good" />
                </div>
                <div>
                  <strong>4. Realistic Statutory Delivery Costs</strong>
                  <p>
                    Every trade deducts official Indian STT (0.1%), NSE Txn charges (0.00297%), SEBI fee, Stamp duty (0.0015%), GST (18%), and slippage.
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
