import React from "react";
import { Brain, AlertTriangle, TrendingUp, Globe } from "lucide-react";

function SentimentBadge({ sentiment, score }) {
  const configs = {
    Bullish: {
      bg: "bg-nexus-up/10",
      border: "border-nexus-up/40",
      text: "text-nexus-up",
      bar: "bg-nexus-up",
      glow: "shadow-nexus-up/20",
    },
    Bearish: {
      bg: "bg-nexus-down/10",
      border: "border-nexus-down/40",
      text: "text-nexus-down",
      bar: "bg-nexus-down",
      glow: "shadow-nexus-down/20",
    },
    Neutral: {
      bg: "bg-nexus-neutral/10",
      border: "border-nexus-neutral/40",
      text: "text-nexus-neutral",
      bar: "bg-nexus-neutral",
      glow: "shadow-nexus-neutral/20",
    },
  };

  const cfg = configs[sentiment] || configs.Neutral;
  const barWidth = Math.abs(score || 0);
  const barOffset = score >= 0 ? 50 : 50 - barWidth;

  return (
    <div className={`${cfg.bg} ${cfg.border} border rounded-sm p-4 flex flex-col gap-3`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={14} className={cfg.text} />
          <span className="text-[10px] text-nexus-muted tracking-widest uppercase">Market Sentiment</span>
        </div>
        <span className={`text-[10px] font-bold ${cfg.text}`}>SCORE: {score > 0 ? "+" : ""}{score}</span>
      </div>

      <span className={`text-3xl font-black tracking-tight ${cfg.text}`}>{sentiment}</span>

      {/* Sentiment bar */}
      <div className="relative h-1.5 bg-nexus-border rounded-full overflow-hidden">
        <div
          className={`absolute h-full ${cfg.bar} rounded-full transition-all duration-1000`}
          style={{ left: `${barOffset}%`, width: `${barWidth}%`, minWidth: "2%" }}
        />
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-nexus-muted/50" />
      </div>
      <div className="flex justify-between text-[9px] text-nexus-muted">
        <span>BEARISH</span>
        <span>NEUTRAL</span>
        <span>BULLISH</span>
      </div>
    </div>
  );
}

function RiskOpportunityList({ title, items, icon: Icon, color }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Icon size={12} className={color} />
        <span className="text-[10px] font-semibold tracking-widest uppercase" style={{ color }}>
          {title}
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        {items?.map((item, i) => (
          <div key={i} className="flex gap-2 text-[11px]">
            <span className={`font-bold shrink-0 mt-0.5`} style={{ color }}>
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="flex flex-col gap-0.5">
              <span className="font-semibold text-nexus-text">{item.title}</span>
              <span className="text-nexus-muted leading-relaxed">{item.detail}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AISignalEngine({ data, loading, error }) {
  const signal = data?.signal;

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">// AI Signal Engine</span>
        <div className="flex items-center gap-2">
          {data?.source && (
            <span className="text-[9px] text-nexus-muted">{data.source}</span>
          )}
          <span className="text-[9px] px-1.5 py-0.5 bg-nexus-accent/10 text-nexus-accent2 border border-nexus-accent/30 rounded-sm">
            LLAMA-3.1-8B
          </span>
        </div>
      </div>

      <div className="p-4 flex flex-col gap-4">
        {loading && (
          <div className="flex flex-col gap-3">
            <div className="loading-pulse h-24 w-full rounded-sm" />
            <div className="loading-pulse h-3 w-3/4" />
            <div className="loading-pulse h-3 w-full" />
            <div className="loading-pulse h-3 w-2/3" />
          </div>
        )}

        {error && (
          <div className="text-[11px] text-nexus-down">
            <span className="text-nexus-muted">ERR:</span> {error}
          </div>
        )}

        {!loading && !error && signal && (
          <>
            {/* Key Theme */}
            {signal.key_theme && (
              <div className="flex items-center gap-2 text-[10px]">
                <span className="text-nexus-muted tracking-widest">KEY THEME:</span>
                <span className="text-nexus-accent2 font-semibold uppercase">{signal.key_theme}</span>
              </div>
            )}

            <SentimentBadge sentiment={signal.sentiment} score={signal.sentiment_score} />

            <div className="grid grid-cols-2 gap-4">
              <RiskOpportunityList
                title="Top Risks"
                items={signal.risks}
                icon={AlertTriangle}
                color="#ff1744"
              />
              <RiskOpportunityList
                title="Opportunities"
                items={signal.opportunities}
                icon={TrendingUp}
                color="#00e676"
              />
            </div>

            {/* Geopolitical Brief */}
            <div className="border border-nexus-border/60 rounded-sm p-3 bg-nexus-bg/50">
              <div className="flex items-center gap-2 mb-2">
                <Globe size={12} className="text-nexus-accent2" />
                <span className="text-[10px] font-semibold tracking-widest text-nexus-accent2 uppercase">
                  Geopolitical Brief
                </span>
              </div>
              <p className="text-[11px] text-nexus-muted leading-relaxed">
                {signal.geopolitical_brief}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
