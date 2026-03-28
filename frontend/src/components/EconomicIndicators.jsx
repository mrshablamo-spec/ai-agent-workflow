import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

function DirectionIcon({ direction, size = 14 }) {
  if (direction === "up") return <TrendingUp size={size} className="text-nexus-up" />;
  if (direction === "down") return <TrendingDown size={size} className="text-nexus-down" />;
  return <Minus size={size} className="text-nexus-neutral" />;
}

function IndicatorCard({ data }) {
  const dirClass =
    data.direction === "up"
      ? "text-nexus-up"
      : data.direction === "down"
      ? "text-nexus-down"
      : "text-nexus-neutral";

  const bgClass =
    data.direction === "up"
      ? "border-nexus-up/20 bg-nexus-up/5"
      : data.direction === "down"
      ? "border-nexus-down/20 bg-nexus-down/5"
      : "border-nexus-neutral/20 bg-nexus-neutral/5";

  return (
    <div className={`border ${bgClass} rounded-sm p-3 flex flex-col gap-1.5`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-nexus-muted tracking-widest uppercase">{data.name}</span>
        <DirectionIcon direction={data.direction} />
      </div>

      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-bold ${dirClass} tabular-nums`}>
          {data.current}
        </span>
        <span className="text-xs text-nexus-muted">{data.unit}</span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[10px] text-nexus-muted">
          prev: <span className="text-nexus-text">{data.previous}{data.unit}</span>
        </span>
        <span className={`text-[10px] font-semibold ${dirClass}`}>
          {data.direction === "up" ? "▲" : data.direction === "down" ? "▼" : "—"}
          {" "}
          {Math.abs(data.current - data.previous).toFixed(2)}{data.unit}
        </span>
      </div>

      {data.date && (
        <span className="text-[9px] text-nexus-muted/60">{data.date}</span>
      )}
    </div>
  );
}

export default function EconomicIndicators({ data, loading, error }) {
  const indicators = data?.indicators ? Object.values(data.indicators) : [];

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">// Economic Indicators</span>
        <span className="text-[10px] text-nexus-muted">FRED</span>
      </div>

      <div className="p-3 grid grid-cols-2 gap-2">
        {loading &&
          [...Array(6)].map((_, i) => (
            <div key={i} className="border border-nexus-border rounded-sm p-3 flex flex-col gap-2">
              <div className="loading-pulse h-2 w-20" />
              <div className="loading-pulse h-6 w-16" />
              <div className="loading-pulse h-2 w-24" />
            </div>
          ))}

        {error && (
          <div className="col-span-2 text-[11px] text-nexus-down p-2">
            <span className="text-nexus-muted">ERR:</span> {error}
          </div>
        )}

        {!loading && !error && indicators.map((ind) => (
          <IndicatorCard key={ind.key} data={ind} />
        ))}
      </div>
    </div>
  );
}
