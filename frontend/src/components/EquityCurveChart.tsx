import React, { useMemo } from "react";

interface EquityCurveChartProps {
  data: { date: string; equity: number }[];
  initialCapital?: number;
  height?: number;
}

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  data,
  initialCapital = 10000,
  height = 240,
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data;
  }, [data]);

  const stats = useMemo(() => {
    if (chartData.length === 0) return null;
    let min = initialCapital;
    let max = initialCapital;
    for (const d of chartData) {
      if (d.equity < min) min = d.equity;
      if (d.equity > max) max = d.equity;
    }
    const pad = (max - min) * 0.1 || 100;
    return {
      min: min - pad,
      max: max + pad,
    };
  }, [chartData, initialCapital]);

  if (chartData.length === 0 || !stats) {
    return (
      <div className="chart-empty" style={{ height }}>
        <span>No equity curve points recorded yet.</span>
      </div>
    );
  }

  const svgWidth = 700;
  const padding = { top: 20, right: 30, bottom: 25, left: 10 };
  const chartW = svgWidth - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const getY = (val: number) => {
    const range = stats.max - stats.min;
    return padding.top + chartH - ((val - stats.min) / range) * chartH;
  };

  const getX = (idx: number) => {
    return padding.left + (idx / (chartData.length - 1 || 1)) * chartW;
  };

  let linePath = "";
  let areaPath = "";

  chartData.forEach((d, idx) => {
    const x = getX(idx);
    const y = getY(d.equity);
    if (idx === 0) {
      linePath = `M ${x} ${y}`;
      areaPath = `M ${x} ${padding.top + chartH} L ${x} ${y}`;
    } else {
      linePath += ` L ${x} ${y}`;
      areaPath += ` L ${x} ${y}`;
    }
  });

  const lastX = getX(chartData.length - 1);
  areaPath += ` L ${lastX} ${padding.top + chartH} Z`;

  const initialY = getY(initialCapital);
  const finalEquity = chartData[chartData.length - 1]?.equity ?? initialCapital;
  const isProfitable = finalEquity >= initialCapital;

  return (
    <div className="equity-chart-wrapper">
      <div className="equity-chart-header">
        <span className="equity-chart-label">EQUITY TRAJECTORY (INR)</span>
        <span className={`equity-chart-final ${isProfitable ? "text-good" : "text-bad"}`}>
          ₹{finalEquity.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          {" "}({(((finalEquity - initialCapital) / initialCapital) * 100).toFixed(2)}%)
        </span>
      </div>
      <svg viewBox={`0 0 ${svgWidth} ${height}`} className="equity-svg">
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isProfitable ? "#207353" : "#b95d5d"} stopOpacity="0.25" />
            <stop offset="100%" stopColor={isProfitable ? "#207353" : "#b95d5d"} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Baseline initial capital dashed line */}
        <line
          x1={padding.left}
          y1={initialY}
          x2={svgWidth - padding.right}
          y2={initialY}
          stroke="#b8c2bc"
          strokeDasharray="3 3"
        />
        <text x={svgWidth - padding.right} y={initialY - 4} fill="#8a968e" fontSize={9} textAnchor="end">
          Base: ₹{initialCapital.toLocaleString()}
        </text>

        {/* Area fill under curve */}
        <path d={areaPath} fill="url(#equityGrad)" />

        {/* Line curve */}
        <path
          d={linePath}
          fill="none"
          stroke={isProfitable ? "#207353" : "#b95d5d"}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Start and end points */}
        <circle cx={getX(0)} cy={getY(chartData[0].equity)} r={3} fill="#207353" />
        <circle cx={lastX} cy={getY(finalEquity)} r={3.5} fill={isProfitable ? "#207353" : "#b95d5d"} />

        {/* Date labels */}
        <text x={padding.left} y={height - 5} fill="#8a968e" fontSize={9}>
          {chartData[0].date}
        </text>
        <text x={lastX} y={height - 5} fill="#8a968e" fontSize={9} textAnchor="end">
          {chartData[chartData.length - 1].date}
        </text>
      </svg>
    </div>
  );
};

