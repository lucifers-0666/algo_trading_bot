import React, { useState, useMemo } from "react";
import type { CandleRecord } from "../lib/types";

interface CandlestickChartProps {
  candles: CandleRecord[];
  symbol: string;
  height?: number;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  candles,
  symbol,
  height = 420,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const data = useMemo(() => {
    return candles.slice(-80); // Display last 80 candles for crisp readability
  }, [candles]);

  const stats = useMemo(() => {
    if (data.length === 0) return null;
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    let maxVol = 0;

    for (const c of data) {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
      if (c.sma_20 && c.sma_20 < minPrice) minPrice = c.sma_20;
      if (c.sma_20 && c.sma_20 > maxPrice) maxPrice = c.sma_20;
      if (c.sma_50 && c.sma_50 < minPrice) minPrice = c.sma_50;
      if (c.sma_50 && c.sma_50 > maxPrice) maxPrice = c.sma_50;
      if (c.volume > maxVol) maxVol = c.volume;
    }

    const pricePadding = (maxPrice - minPrice) * 0.05 || 1.0;
    return {
      minPrice: minPrice - pricePadding,
      maxPrice: maxPrice + pricePadding,
      maxVol: maxVol || 1,
    };
  }, [data]);

  if (data.length === 0 || !stats) {
    return (
      <div className="chart-empty" style={{ height }}>
        <span>No candle history available for {symbol}</span>
      </div>
    );
  }

  const svgWidth = 840;
  const pricePaneHeight = height * 0.62;
  const volPaneHeight = height * 0.18;
  const rsiPaneHeight = height * 0.20;

  const priceTop = 10;
  const volTop = pricePaneHeight + 15;
  const rsiTop = volTop + volPaneHeight + 15;

  const barStep = svgWidth / data.length;
  const candleWidth = Math.max(2, Math.min(8, barStep * 0.68));

  const getYPrice = (price: number) => {
    const range = stats.maxPrice - stats.minPrice;
    return priceTop + (pricePaneHeight - ((price - stats.minPrice) / range) * pricePaneHeight);
  };

  const getYVol = (vol: number) => {
    return volTop + (volPaneHeight - (vol / stats.maxVol) * volPaneHeight);
  };

  const getYRSI = (rsi: number) => {
    return rsiTop + (rsiPaneHeight - (Math.min(100, Math.max(0, rsi)) / 100) * rsiPaneHeight);
  };

  // Build SVG Paths for SMA 20 & SMA 50
  let sma20Path = "";
  let sma50Path = "";
  let rsiPath = "";

  data.forEach((c, idx) => {
    const x = idx * barStep + barStep / 2;
    if (c.sma_20 != null) {
      const y = getYPrice(c.sma_20);
      sma20Path += sma20Path === "" ? `M ${x} ${y}` : ` L ${x} ${y}`;
    }
    if (c.sma_50 != null) {
      const y = getYPrice(c.sma_50);
      sma50Path += sma50Path === "" ? `M ${x} ${y}` : ` L ${x} ${y}`;
    }
    if (c.rsi_14 != null) {
      const y = getYRSI(c.rsi_14);
      rsiPath += rsiPath === "" ? `M ${x} ${y}` : ` L ${x} ${y}`;
    }
  });

  const activeCandle = hoverIndex !== null ? data[hoverIndex] : data[data.length - 1];

  return (
    <div className="candlestick-chart-wrapper">
      <div className="chart-legend">
        <div className="legend-main">
          <strong>{symbol}</strong>
          <span className="legend-date">{activeCandle?.timestamp}</span>
        </div>
        <div className="legend-values">
          <span>O: <strong>₹{activeCandle?.open.toFixed(2)}</strong></span>
          <span>H: <strong>₹{activeCandle?.high.toFixed(2)}</strong></span>
          <span>L: <strong>₹{activeCandle?.low.toFixed(2)}</strong></span>
          <span>C: <strong>₹{activeCandle?.close.toFixed(2)}</strong></span>
          <span>Vol: <strong>{activeCandle?.volume.toLocaleString()}</strong></span>
          {activeCandle?.sma_20 != null && (
            <span className="legend-sma20">SMA20: <strong>₹{activeCandle.sma_20.toFixed(2)}</strong></span>
          )}
          {activeCandle?.sma_50 != null && (
            <span className="legend-sma50">SMA50: <strong>₹{activeCandle.sma_50.toFixed(2)}</strong></span>
          )}
          {activeCandle?.rsi_14 != null && (
            <span className="legend-rsi">RSI(14): <strong>{activeCandle.rsi_14.toFixed(1)}</strong></span>
          )}
        </div>
      </div>

      <div className="chart-canvas-container" style={{ position: "relative" }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${height}`}
          className="chart-svg"
          onMouseLeave={() => setHoverIndex(null)}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const idx = Math.floor((x / rect.width) * data.length);
            if (idx >= 0 && idx < data.length) {
              setHoverIndex(idx);
            }
          }}
        >
          {/* Horizontal grid lines for Price pane */}
          {[0.25, 0.5, 0.75].map((ratio) => {
            const price = stats.minPrice + (stats.maxPrice - stats.minPrice) * ratio;
            const y = getYPrice(price);
            return (
              <g key={`grid-price-${ratio}`}>
                <line x1={0} y1={y} x2={svgWidth} y2={y} stroke="#edf0ed" strokeDasharray="3 3" />
                <text x={svgWidth - 5} y={y - 3} fill="#a4b0a8" fontSize={9} textAnchor="end">
                  ₹{price.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* RSI Reference Bands (70 Overbought, 30 Oversold) */}
          <line x1={0} y1={getYRSI(70)} x2={svgWidth} y2={getYRSI(70)} stroke="#e0b8b8" strokeDasharray="2 2" />
          <text x={svgWidth - 5} y={getYRSI(70) - 2} fill="#b95d5d" fontSize={8} textAnchor="end">70 (Overbought)</text>
          <line x1={0} y1={getYRSI(30)} x2={svgWidth} y2={getYRSI(30)} stroke="#a8cbb8" strokeDasharray="2 2" />
          <text x={svgWidth - 5} y={getYRSI(30) + 9} fill="#207353" fontSize={8} textAnchor="end">30 (Oversold)</text>

          {/* Volume separator label */}
          <text x={8} y={volTop + 10} fill="#9aa59d" fontSize={8} fontWeight={700}>VOLUME</text>
          <text x={8} y={rsiTop + 10} fill="#9aa59d" fontSize={8} fontWeight={700}>RSI (14)</text>

          {/* Volume Bars */}
          {data.map((c, idx) => {
            const x = idx * barStep + (barStep - candleWidth) / 2;
            const y = getYVol(c.volume);
            const barH = volTop + volPaneHeight - y;
            const isGreen = c.close >= c.open;
            return (
              <rect
                key={`vol-${c.timestamp}-${idx}`}
                x={x}
                y={y}
                width={candleWidth}
                height={Math.max(1, barH)}
                fill={isGreen ? "#bde2ce" : "#f1cfcf"}
              />
            );
          })}

          {/* Candlesticks */}
          {data.map((c, idx) => {
            const centerX = idx * barStep + barStep / 2;
            const isGreen = c.close >= c.open;
            const color = isGreen ? "#207353" : "#b95d5d";
            const topBody = getYPrice(Math.max(c.open, c.close));
            const bottomBody = getYPrice(Math.min(c.open, c.close));
            const bodyHeight = Math.max(1.5, bottomBody - topBody);
            const highY = getYPrice(c.high);
            const lowY = getYPrice(c.low);

            return (
              <g key={`candle-${c.timestamp}-${idx}`}>
                {/* Wick */}
                <line x1={centerX} y1={highY} x2={centerX} y2={lowY} stroke={color} strokeWidth={1} />
                {/* Body */}
                <rect
                  x={centerX - candleWidth / 2}
                  y={topBody}
                  width={candleWidth}
                  height={bodyHeight}
                  fill={isGreen ? "#207353" : "#b95d5d"}
                  stroke={color}
                  strokeWidth={0.5}
                />
              </g>
            );
          })}

          {/* SMA 20 Overlay Line */}
          {sma20Path && <path d={sma20Path} fill="none" stroke="#2563eb" strokeWidth={1.5} />}

          {/* SMA 50 Overlay Line */}
          {sma50Path && <path d={sma50Path} fill="none" stroke="#d97706" strokeWidth={1.5} />}

          {/* RSI Line */}
          {rsiPath && <path d={rsiPath} fill="none" stroke="#7c3aed" strokeWidth={1.5} />}

          {/* Hover crosshair line */}
          {hoverIndex !== null && (
            <line
              x1={hoverIndex * barStep + barStep / 2}
              y1={priceTop}
              x2={hoverIndex * barStep + barStep / 2}
              y2={height}
              stroke="#6b7280"
              strokeWidth={1}
              strokeDasharray="2 2"
            />
          )}
        </svg>
      </div>
    </div>
  );
};

