import React from "react";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";

function Sparkline({ data, positive }) {
  if (!data || data.length < 2) return null;
  const chartData = data.map((v, i) => ({ v, i }));
  const color = positive ? "#00e676" : "#ff1744";

  return (
    <ResponsiveContainer width={80} height={32}>
      <LineChart data={chartData}>
        <Line
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
        <Tooltip
          contentStyle={{ display: "none" }}
          cursor={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function MarketRow({ data }) {
  const positive = data.change_pct >= 0;
  const changeClass = positive ? "text-nexus-up" : "text-nexus-down";
  const sign = positive ? "+" : "";

  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-nexus-border/50 hover:bg-nexus-accent/5 transition-colors">
      <div className="flex flex-col gap-0.5 w-24">
        <span className="text-xs font-bold text-nexus-text">{data.symbol}</span>
        <span className="text-[10px] text-nexus-muted truncate">{data.name}</span>
      </div>

      <div className="flex-1 flex justify-center">
        <Sparkline data={data.sparkline} positive={positive} />
      </div>

      <div className="flex flex-col items-end gap-0.5 w-28">
        <span className="text-xs font-bold tabular-nums">${data.price?.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        <span className={`text-[11px] font-semibold tabular-nums ${changeClass}`}>
          {sign}{data.change_pct?.toFixed(2)}%
          <span className="text-[10px] ml-1 opacity-70">({sign}{data.change_abs?.toFixed(2)})</span>
        </span>
      </div>
    </div>
  );
}

export default function MarketsOverview({ data, loading, error }) {
  const markets = data?.markets ? Object.values(data.markets) : [];

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">// Markets Overview</span>
        <span className="text-[10px] text-nexus-muted">5D SPARKLINE</span>
      </div>

      <div className="flex flex-col">
        {loading &&
          [...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center justify-between px-4 py-2.5 border-b border-nexus-border/50">
              <div className="loading-pulse h-3 w-16" />
              <div className="loading-pulse h-8 w-20" />
              <div className="loading-pulse h-3 w-20" />
            </div>
          ))}

        {error && (
          <div className="px-4 py-3 text-[11px] text-nexus-down">
            <span className="text-nexus-muted">ERR:</span> {error}
          </div>
        )}

        {!loading && !error && markets.map((mkt) => (
          <MarketRow key={mkt.symbol} data={mkt} />
        ))}
      </div>
    </div>
  );
}
