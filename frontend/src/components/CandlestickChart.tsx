import React, { useEffect, useRef, useState, useMemo } from "react";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { CandleRecord } from "../lib/types";

interface CandlestickChartProps {
  candles: CandleRecord[];
  symbol: string;
  height?: number;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  candles,
  symbol,
  height = 440,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const sma20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const sma50SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [activeCandle, setActiveCandle] = useState<CandleRecord | null>(null);

  // Parse and sort unique data points for Lightweight Charts
  const chartData = useMemo(() => {
    if (!candles || candles.length === 0) return { candles: [], volumes: [], sma20: [], sma50: [] };

    const seenTimes = new Set<number>();
    const candleItems: Array<{ time: UTCTimestamp; open: number; high: number; low: number; close: number }> = [];
    const volumeItems: Array<{ time: UTCTimestamp; value: number; color: string }> = [];
    const sma20Items: Array<{ time: UTCTimestamp; value: number }> = [];
    const sma50Items: Array<{ time: UTCTimestamp; value: number }> = [];

    // Sort chronologically
    const sorted = [...candles].sort((a, b) => {
      const ta = new Date(a.timestamp).getTime();
      const tb = new Date(b.timestamp).getTime();
      return ta - tb;
    });

    for (const c of sorted) {
      let timeSec = Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp;
      if (isNaN(timeSec)) continue;

      // Ensure strictly ascending unique timestamps
      if (seenTimes.has(timeSec)) {
        timeSec = (timeSec + 1) as UTCTimestamp;
      }
      seenTimes.add(timeSec);

      candleItems.push({
        time: timeSec,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      });

      const isUp = c.close >= c.open;
      volumeItems.push({
        time: timeSec,
        value: c.volume,
        color: isUp ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)",
      });

      if (c.sma_20 != null && !isNaN(c.sma_20)) {
        sma20Items.push({ time: timeSec, value: c.sma_20 });
      }
      if (c.sma_50 != null && !isNaN(c.sma_50)) {
        sma50Items.push({ time: timeSec, value: c.sma_50 });
      }
    }

    return {
      candles: candleItems,
      volumes: volumeItems,
      sma20: sma20Items,
      sma50: sma50Items,
    };
  }, [candles]);

  // Set default active candle to latest on data change
  useEffect(() => {
    if (candles.length > 0) {
      setActiveCandle(candles[candles.length - 1]);
    }
  }, [candles]);

  // Initialize and update Lightweight Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart instance if not exists
    if (!chartRef.current) {
      const chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth || 800,
        height: height,
        layout: {
          background: { type: ColorType.Solid, color: "#080c14" },
          textColor: "#94a3b8",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "rgba(30, 41, 59, 0.35)" },
          horzLines: { color: "rgba(30, 41, 59, 0.35)" },
        },
        crosshair: {
          mode: 1,
          vertLine: { color: "#64748b", width: 1, style: 2 },
          horzLine: { color: "#64748b", width: 1, style: 2 },
        },
        rightPriceScale: {
          borderColor: "#1e293b",
          scaleMargins: {
            top: 0.1,
            bottom: 0.22,
          },
        },
        timeScale: {
          borderColor: "#1e293b",
          timeVisible: true,
          secondsVisible: false,
        },
      });

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#10b981",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#10b981",
        wickDownColor: "#ef4444",
      });

      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume_pane",
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.82,
          bottom: 0,
        },
      });

      const sma20Series = chart.addSeries(LineSeries, {
        color: "#38bdf8",
        lineWidth: 2,
        title: "SMA 20",
      });

      const sma50Series = chart.addSeries(LineSeries, {
        color: "#f59e0b",
        lineWidth: 2,
        title: "SMA 50",
      });

      // Crosshair inspection tracking
      chart.subscribeCrosshairMove((param) => {
        if (!param.time || param.point === undefined) {
          if (candles.length > 0) {
            setActiveCandle(candles[candles.length - 1]);
          }
          return;
        }

        const dataPoint = param.seriesData.get(candleSeries);
        if (dataPoint && "open" in dataPoint) {
          const matching = candles.find((c) => {
            const t = Math.floor(new Date(c.timestamp).getTime() / 1000);
            return t === param.time;
          });
          if (matching) {
            setActiveCandle(matching);
          } else {
            setActiveCandle({
              timestamp: new Date((param.time as number) * 1000).toISOString().replace("T", " ").substring(0, 16),
              open: (dataPoint as any).open,
              high: (dataPoint as any).high,
              low: (dataPoint as any).low,
              close: (dataPoint as any).close,
              volume: 0,
            });
          }
        }
      });

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;
      volumeSeriesRef.current = volumeSeries;
      sma20SeriesRef.current = sma20Series;
      sma50SeriesRef.current = sma50Series;
    }

    // Update series data
    if (candleSeriesRef.current && chartData.candles.length > 0) {
      candleSeriesRef.current.setData(chartData.candles);
    }
    if (volumeSeriesRef.current && chartData.volumes.length > 0) {
      volumeSeriesRef.current.setData(chartData.volumes);
    }
    if (sma20SeriesRef.current) {
      sma20SeriesRef.current.setData(chartData.sma20);
    }
    if (sma50SeriesRef.current) {
      sma50SeriesRef.current.setData(chartData.sma50);
    }

    chartRef.current.timeScale().fitContent();

    // Responsive window resize observer
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: height,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [chartData, height, candles]);

  // Clean cleanup on component unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  if (!candles || candles.length === 0) {
    return (
      <div
        className="flex items-center justify-center border border-slate-800 bg-[#080c14] rounded-lg text-slate-500 font-mono text-sm"
        style={{ height }}
      >
        <span>No candlestick data available for {symbol}</span>
      </div>
    );
  }

  const latest = activeCandle || candles[candles.length - 1];
  const isUp = latest ? latest.close >= latest.open : true;
  const pctChange = latest ? ((latest.close - latest.open) / latest.open) * 100 : 0;

  return (
    <div className="flex flex-col border border-slate-800 rounded-lg bg-[#080c14] overflow-hidden shadow-2xl">
      {/* Top Legend Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 bg-[#0c121e] border-b border-slate-800 text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="font-bold text-slate-200 text-sm tracking-wide">{symbol}</span>
          <span className="text-slate-400">{latest?.timestamp}</span>
          <span
            className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${isUp ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/60" : "bg-rose-950/80 text-rose-400 border border-rose-800/60"
              }`}
          >
            {pctChange >= 0 ? `+${pctChange.toFixed(2)}%` : `${pctChange.toFixed(2)}%`}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-slate-300">
          <span>O: <strong className="text-white">₹{latest?.open?.toFixed(2)}</strong></span>
          <span>H: <strong className="text-white">₹{latest?.high?.toFixed(2)}</strong></span>
          <span>L: <strong className="text-white">₹{latest?.low?.toFixed(2)}</strong></span>
          <span>C: <strong className={isUp ? "text-emerald-400" : "text-rose-400"}>₹{latest?.close?.toFixed(2)}</strong></span>
          <span>Vol: <strong className="text-slate-200">{latest?.volume ? latest.volume.toLocaleString() : "—"}</strong></span>
          {latest?.sma_20 != null && (
            <span className="text-sky-400">SMA20: <strong>₹{latest.sma_20.toFixed(2)}</strong></span>
          )}
          {latest?.sma_50 != null && (
            <span className="text-amber-400">SMA50: <strong>₹{latest.sma_50.toFixed(2)}</strong></span>
          )}
          {latest?.rsi_14 != null && (
            <span className="text-purple-400">RSI: <strong>{latest.rsi_14.toFixed(1)}</strong></span>
          )}
        </div>
      </div>

      {/* TradingView Lightweight Charts Canvas */}
      <div
        ref={chartContainerRef}
        className="relative w-full"
        style={{ height }}
      />
    </div>
  );
};
