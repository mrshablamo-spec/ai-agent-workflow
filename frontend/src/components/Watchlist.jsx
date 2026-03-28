import React from "react";

function WatchlistRow({ ticker }) {
  const positive = ticker.change_pct >= 0;
  const changeClass = positive ? "text-nexus-up" : "text-nexus-down";
  const sign = positive ? "+" : "";
  const hasError = !!ticker.error;

  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-nexus-border/50 hover:bg-nexus-accent/5 transition-colors">
      <div className="flex flex-col gap-0.5 w-14">
        <span className="text-xs font-bold text-nexus-text">{ticker.symbol}</span>
      </div>

      {hasError ? (
        <span className="text-[10px] text-nexus-down flex-1 text-center">ERR</span>
      ) : (
        <>
          <div className="flex flex-col items-center flex-1">
            <span className="text-xs font-bold tabular-nums">
              ${ticker.price?.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div className="flex flex-col items-end gap-0.5 w-24">
            <span className={`text-xs font-bold tabular-nums ${changeClass}`}>
              {sign}{ticker.change_pct?.toFixed(2)}%
            </span>
            <span className="text-[10px] text-nexus-muted tabular-nums">{ticker.market_cap}</span>
          </div>
        </>
      )}
    </div>
  );
}

export default function Watchlist({ data, loading, error }) {
  const tickers = data?.tickers || [];

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">// Watchlist</span>
        <span className="text-[10px] text-nexus-muted">{tickers.length} TICKERS</span>
      </div>

      {/* Column headers */}
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-nexus-border bg-nexus-bg/50">
        <span className="text-[9px] text-nexus-muted tracking-widest w-14">TICKER</span>
        <span className="text-[9px] text-nexus-muted tracking-widest flex-1 text-center">PRICE</span>
        <span className="text-[9px] text-nexus-muted tracking-widest w-24 text-right">CHG% / MKT CAP</span>
      </div>

      <div className="flex flex-col">
        {loading &&
          [...Array(8)].map((_, i) => (
            <div key={i} className="flex items-center justify-between px-4 py-2.5 border-b border-nexus-border/50">
              <div className="loading-pulse h-3 w-12" />
              <div className="loading-pulse h-3 w-16" />
              <div className="loading-pulse h-3 w-20" />
            </div>
          ))}

        {error && (
          <div className="px-4 py-3 text-[11px] text-nexus-down">
            <span className="text-nexus-muted">ERR:</span> {error}
          </div>
        )}

        {!loading && !error && tickers.map((t) => (
          <WatchlistRow key={t.symbol} ticker={t} />
        ))}
      </div>
    </div>
  );
}
