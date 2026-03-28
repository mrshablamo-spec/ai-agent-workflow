import React, { useState } from "react";
import { ExternalLink, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { formatDistanceToNow, parseISO } from "date-fns";

const CATEGORY_COLORS = {
  geopolitics: "text-red-400 border-red-400/30 bg-red-400/10",
  energy: "text-orange-400 border-orange-400/30 bg-orange-400/10",
  central_banks: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  tech: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  defense: "text-purple-400 border-purple-400/30 bg-purple-400/10",
};

const CATEGORY_LABELS = {
  geopolitics: "GEO",
  energy: "NRG",
  central_banks: "CB",
  tech: "TECH",
  defense: "DEF",
};

const CATEGORIES = ["all", "geopolitics", "energy", "central_banks", "tech", "defense"];

function ArticleCard({ article }) {
  const [expanded, setExpanded] = useState(false);

  let timeAgo = "";
  try {
    if (article.published) {
      timeAgo = formatDistanceToNow(parseISO(article.published), { addSuffix: true });
    }
  } catch {
    timeAgo = article.published?.slice(0, 10) || "";
  }

  const catColor = CATEGORY_COLORS[article.category] || CATEGORY_COLORS.geopolitics;
  const catLabel = CATEGORY_LABELS[article.category] || "GEO";

  return (
    <div className="border-b border-nexus-border/50 px-4 py-3 hover:bg-nexus-accent/5 transition-colors group">
      <div className="flex items-start gap-3">
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge text-[9px] px-1.5 py-0.5 rounded-sm font-bold border ${catColor}`}>
              {catLabel}
            </span>
            <span className="text-[10px] text-nexus-muted">{article.source}</span>
            <span className="text-[10px] text-nexus-muted ml-auto">{timeAgo}</span>
          </div>

          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-nexus-text font-medium leading-tight hover:text-nexus-accent2 transition-colors line-clamp-2 group-hover:line-clamp-none"
          >
            {article.title}
          </a>

          {article.summary && (
            <div className="mt-1">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-[10px] text-nexus-muted hover:text-nexus-accent2 transition-colors"
              >
                {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                AI SUMMARY
              </button>
              {expanded && (
                <p className="mt-1 text-[11px] text-nexus-muted/90 leading-relaxed italic border-l-2 border-nexus-accent/40 pl-2">
                  {article.summary}
                </p>
              )}
            </div>
          )}
        </div>

        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="opacity-0 group-hover:opacity-60 transition-opacity mt-1 shrink-0"
        >
          <ExternalLink size={12} className="text-nexus-accent2" />
        </a>
      </div>
    </div>
  );
}

export default function NewsFeed({ data, loading, error, onCategoryChange }) {
  const [activeCategory, setActiveCategory] = useState("all");

  const handleCategoryChange = (cat) => {
    setActiveCategory(cat);
    onCategoryChange(cat);
  };

  return (
    <div className="panel flex flex-col h-full">
      <div className="panel-header">
        <span className="panel-title">// News & Intelligence</span>
        {data && (
          <span className="text-[10px] text-nexus-muted">
            {data.total} items
          </span>
        )}
      </div>

      {/* Category filter */}
      <div className="flex gap-1 px-3 py-2 border-b border-nexus-border/50 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => handleCategoryChange(cat)}
            className={`text-[9px] px-2 py-0.5 rounded-sm font-bold tracking-widest uppercase transition-all border ${
              activeCategory === cat
                ? "bg-nexus-accent/20 text-nexus-accent2 border-nexus-accent/50"
                : "text-nexus-muted border-nexus-border hover:text-nexus-text hover:border-nexus-muted"
            }`}
          >
            {cat === "central_banks" ? "C.BANKS" : cat === "all" ? "ALL" : CATEGORY_LABELS[cat] || cat}
          </button>
        ))}
      </div>

      {/* Articles */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex flex-col gap-3 p-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex flex-col gap-2">
                <div className="loading-pulse h-2 w-24" />
                <div className="loading-pulse h-3 w-full" />
                <div className="loading-pulse h-3 w-3/4" />
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="p-4 text-[11px] text-nexus-down">
            <span className="text-nexus-muted">ERR:</span> {error}
          </div>
        )}

        {!loading && !error && data?.articles?.map((article, i) => (
          <ArticleCard key={article.url || i} article={article} />
        ))}

        {!loading && !error && data?.articles?.length === 0 && (
          <div className="p-4 text-xs text-nexus-muted text-center">
            No articles found for this category
          </div>
        )}
      </div>
    </div>
  );
}
