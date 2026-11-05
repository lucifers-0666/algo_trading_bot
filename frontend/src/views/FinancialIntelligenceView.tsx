import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, RefreshCw, TrendingUp, TrendingDown, ExternalLink, ShieldAlert } from "lucide-react";
import { getFinancialNews, getFinancialSummary, refreshFinancialNews } from "../lib/api";

export function FinancialIntelligenceView({ onSelectSymbol }: { onSelectSymbol?: (sym: string) => void }) {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchSymbol, setSearchSymbol] = useState<string>("");

  const { data: summary } = useQuery({
    queryKey: ["financialSummary"],
    queryFn: () => getFinancialSummary(),
    refetchInterval: 30000,
  });

  const { data: newsItems, isLoading: isNewsLoading } = useQuery({
    queryKey: ["financialNews", selectedCategory, searchSymbol],
    queryFn: () =>
      getFinancialNews(
        selectedCategory === "ALL" ? undefined : selectedCategory,
        searchSymbol ? searchSymbol.trim().toUpperCase() : undefined,
        50
      ),
    refetchInterval: 15000,
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshFinancialNews(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financialNews"] });
      queryClient.invalidateQueries({ queryKey: ["financialSummary"] });
    },
  });

  const categories = [
    { key: "ALL", label: "All News" },
    { key: "EARNINGS", label: "Earnings & Results" },
    { key: "ORDER_WIN", label: "Order Wins & Deals" },
    { key: "REGULATORY", label: "Regulatory & SEBI" },
    { key: "MACRO", label: "Macro & Economy" },
    { key: "GEOPOLITICAL", label: "Geopolitical & Trade" },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Globe className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Global Financial Intelligence</h1>
          </div>
          <p className="text-sm text-muted mt-1">
            Real-time macroeconomic intelligence, official NSE/BSE corporate filings, and global news telemetry.
          </p>
        </div>

        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-secondary px-4 py-2 text-xs font-medium text-foreground hover:bg-surface-elevated border border-border disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin text-primary" : ""}`} />
          {refreshMutation.isPending ? "Ingesting Feeds..." : "Refresh Feeds"}
        </button>
      </div>

      {/* Sentiment Overview Bar */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="text-xs font-medium text-muted uppercase tracking-wider">Overall Market Sentiment</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span
                className={`text-2xl font-bold font-mono ${
                  summary.sentiment_label === "BULLISH"
                    ? "text-emerald-400"
                    : summary.sentiment_label === "BEARISH"
                    ? "text-rose-400"
                    : "text-amber-400"
                }`}
              >
                {summary.sentiment_label}
              </span>
              <span className="text-xs font-mono text-muted">
                ({summary.overall_sentiment_score > 0 ? `+${summary.overall_sentiment_score}` : summary.overall_sentiment_score})
              </span>
            </div>
            <div className="text-xs text-muted mt-1">{summary.total_events_analyzed} events analyzed (48h window)</div>
          </div>

          <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="text-xs font-medium text-muted uppercase tracking-wider">Positive Catalysts</div>
            <div className="mt-2 text-2xl font-bold font-mono text-emerald-400">{summary.positive_count}</div>
            <div className="text-xs text-muted mt-1">Earnings surges, order wins, and dividend hikes</div>
          </div>

          <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="text-xs font-medium text-muted uppercase tracking-wider">Negative Headwinds</div>
            <div className="mt-2 text-2xl font-bold font-mono text-rose-400">{summary.negative_count}</div>
            <div className="text-xs text-muted mt-1">Regulatory notices, investigations, and margin compression</div>
          </div>

          <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="text-xs font-medium text-muted uppercase tracking-wider">Neutral / Macro Updates</div>
            <div className="mt-2 text-2xl font-bold font-mono text-amber-400">{summary.neutral_count}</div>
            <div className="text-xs text-muted mt-1">Routine corporate filings and broad trade policy</div>
          </div>
        </div>
      )}

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-surface p-3 rounded-lg border border-border">
        <div className="flex flex-wrap items-center gap-1.5">
          {categories.map((c) => (
            <button
              key={c.key}
              onClick={() => setSelectedCategory(c.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                selectedCategory === c.key
                  ? "bg-primary text-background font-semibold"
                  : "bg-surface-elevated text-muted hover:text-foreground"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="relative min-w-[200px]">
          <input
            type="text"
            placeholder="Filter by Symbol (e.g. INFY)..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-xs text-foreground placeholder-muted focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* News Stream Feed */}
      <div className="space-y-3">
        {isNewsLoading ? (
          <div className="p-12 text-center text-sm text-muted">Loading financial intelligence feeds...</div>
        ) : !newsItems || newsItems.length === 0 ? (
          <div className="p-12 text-center text-sm text-muted border border-dashed border-border rounded-lg bg-surface">
            No events found matching category '{selectedCategory}' and symbol '{searchSymbol}'.
          </div>
        ) : (
          newsItems.map((item) => (
            <div
              key={item.event_id}
              className="p-4 rounded-lg border border-border bg-surface hover:bg-surface-elevated/40 transition-colors flex flex-col sm:flex-row sm:items-start justify-between gap-4"
            >
              <div className="space-y-2 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase bg-secondary text-foreground border border-border">
                    {item.source}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase bg-surface-elevated text-muted">
                    {item.category}
                  </span>
                  {item.symbols.map((sym) => (
                    <button
                      key={sym}
                      onClick={() => onSelectSymbol?.(sym)}
                      className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                    >
                      {sym}
                    </button>
                  ))}
                  <span className="text-xs text-muted ml-auto font-mono">
                    {new Date(item.published_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "short", timeStyle: "short" })}
                  </span>
                </div>

                <div className="text-sm font-medium text-foreground leading-snug">{item.headline}</div>

                {item.summary && <div className="text-xs text-muted line-clamp-2">{item.summary}</div>}
              </div>

              {/* Sentiment Badge */}
              <div className="sm:self-center shrink-0 flex items-center gap-2">
                <div
                  className={`px-2.5 py-1 rounded text-xs font-mono font-semibold flex items-center gap-1.5 ${
                    item.impact_level === "POSITIVE"
                      ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"
                      : item.impact_level === "NEGATIVE"
                      ? "bg-rose-950/60 text-rose-400 border border-rose-800/60"
                      : item.impact_level === "HIGH_VOLATILITY"
                      ? "bg-purple-950/60 text-purple-400 border border-purple-800/60"
                      : "bg-surface-elevated text-muted border border-border"
                  }`}
                >
                  {item.impact_level === "POSITIVE" && <TrendingUp className="h-3 w-3" />}
                  {item.impact_level === "NEGATIVE" && <TrendingDown className="h-3 w-3" />}
                  {item.impact_level === "HIGH_VOLATILITY" && <ShieldAlert className="h-3 w-3" />}
                  <span>{item.impact_level}</span>
                  <span className="opacity-80">
                    ({item.sentiment_score > 0 ? `+${item.sentiment_score.toFixed(2)}` : item.sentiment_score.toFixed(2)})
                  </span>
                </div>

                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 text-muted hover:text-foreground rounded hover:bg-surface-elevated transition-colors"
                    title="Open original source"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
