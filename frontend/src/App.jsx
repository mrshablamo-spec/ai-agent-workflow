import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import {
  RefreshCw,
  Activity,
  Wifi,
  WifiOff,
  Clock,
} from "lucide-react";
import NewsFeed from "./components/NewsFeed";
import EconomicIndicators from "./components/EconomicIndicators";
import MarketsOverview from "./components/MarketsOverview";
import AISignalEngine from "./components/AISignalEngine";
import Watchlist from "./components/Watchlist";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";
const REFRESH_INTERVAL = 15 * 60 * 1000; // 15 minutes

function useDataFetch(url, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetch = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await axios.get(`${API_BASE}${url}`, { params, timeout: 30000 });
      setData(resp.data);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [url]);

  return { data, loading, error, lastUpdated, refetch: fetch };
}

function Clock24() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span className="tabular-nums text-nexus-accent2 font-bold tracking-widest">
      {time.toISOString().replace("T", " ").slice(0, 19)} UTC
    </span>
  );
}

function CountdownTimer({ nextRefresh }) {
  const [remaining, setRemaining] = useState("");
  useEffect(() => {
    if (!nextRefresh) return;
    const t = setInterval(() => {
      const diff = nextRefresh - Date.now();
      if (diff <= 0) {
        setRemaining("00:00");
        return;
      }
      const m = Math.floor(diff / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setRemaining(`${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`);
    }, 1000);
    return () => clearInterval(t);
  }, [nextRefresh]);
  return <span className="tabular-nums text-nexus-muted text-[10px]">REFRESH IN {remaining}</span>;
}

export default function App() {
  const [newsCategory, setNewsCategory] = useState("all");
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [nextRefresh, setNextRefresh] = useState(null);
  const refreshTimerRef = useRef(null);

  const newsApi = useDataFetch("/news/");
  const econApi = useDataFetch("/economics/");
  const marketsApi = useDataFetch("/markets/");
  const watchlistApi = useDataFetch("/watchlist/");
  const [signalData, setSignalData] = useState(null);
  const [signalLoading, setSignalLoading] = useState(false);
  const [signalError, setSignalError] = useState(null);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => { window.removeEventListener("online", onOnline); window.removeEventListener("offline", onOffline); };
  }, []);

  const fetchSignal = useCallback(async (headlines, indicators) => {
    setSignalLoading(true);
    setSignalError(null);
    try {
      const resp = await axios.post(`${API_BASE}/signals/analyze`, {
        headlines,
        indicators,
      }, { timeout: 30000 });
      setSignalData(resp.data);
    } catch (e) {
      setSignalError(e.response?.data?.detail || e.message);
    } finally {
      setSignalLoading(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    const category = newsCategory === "all" ? undefined : newsCategory;
    await Promise.all([
      newsApi.refetch(category ? { category } : {}),
      econApi.refetch(),
      marketsApi.refetch(),
      watchlistApi.refetch(),
    ]);
    setNextRefresh(Date.now() + REFRESH_INTERVAL);
  }, [newsCategory]);

  // Initial load
  useEffect(() => {
    refreshAll();
  }, []);

  // Auto-refresh timer
  useEffect(() => {
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    refreshTimerRef.current = setInterval(refreshAll, REFRESH_INTERVAL);
    return () => clearInterval(refreshTimerRef.current);
  }, [refreshAll]);

  // Fetch signal once news + econ data available
  useEffect(() => {
    if (newsApi.data && econApi.data && !signalData) {
      const headlines = newsApi.data.articles?.slice(0, 15).map((a) => a.title) || [];
      const indicators = econApi.data?.indicators || {};
      fetchSignal(headlines, indicators);
    }
  }, [newsApi.data, econApi.data]);

  const handleCategoryChange = useCallback((cat) => {
    setNewsCategory(cat);
    newsApi.refetch(cat !== "all" ? { category: cat } : {});
  }, [newsApi]);

  const handleManualRefresh = useCallback(() => {
    const headlines = newsApi.data?.articles?.slice(0, 15).map((a) => a.title) || [];
    const indicators = econApi.data?.indicators || {};
    setSignalData(null);
    refreshAll().then(() => fetchSignal(headlines, indicators));
  }, [newsApi.data, econApi.data, refreshAll, fetchSignal]);

  return (
    <div className="min-h-screen bg-nexus-bg scanline">
      {/* Top Bar */}
      <header className="sticky top-0 z-50 bg-nexus-bg/95 backdrop-blur border-b border-nexus-border">
        <div className="flex items-center justify-between px-4 py-2">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-7 h-7 border-2 border-nexus-accent2 rotate-45 flex items-center justify-center">
                <div className="w-2 h-2 bg-nexus-accent2 rotate-[-45deg]" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-black tracking-[0.3em] text-nexus-accent2 leading-none">
                NEXUS
              </span>
              <span className="text-[8px] tracking-[0.2em] text-nexus-muted uppercase">
                Intelligence Platform
              </span>
            </div>
          </div>

          {/* Center: Clock */}
          <div className="hidden md:flex items-center gap-2 text-[11px]">
            <Clock size={12} className="text-nexus-muted" />
            <Clock24 />
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            <CountdownTimer nextRefresh={nextRefresh} />

            {isOnline ? (
              <Wifi size={12} className="text-nexus-up" />
            ) : (
              <WifiOff size={12} className="text-nexus-down" />
            )}

            <button
              onClick={handleManualRefresh}
              className="flex items-center gap-1.5 text-[10px] px-3 py-1.5 bg-nexus-accent/10 text-nexus-accent2 border border-nexus-accent/30 rounded-sm hover:bg-nexus-accent/20 transition-colors"
            >
              <RefreshCw size={11} />
              REFRESH
            </button>
          </div>
        </div>

        {/* Status bar */}
        <div className="flex items-center gap-4 px-4 py-1 bg-nexus-panel/50 border-t border-nexus-border/30">
          <div className="flex items-center gap-1.5">
            <Activity size={8} className="text-nexus-up" />
            <span className="text-[9px] text-nexus-muted tracking-widest">LIVE</span>
          </div>
          <span className="text-[9px] text-nexus-muted">
            NEWS: {newsApi.data?.total ?? "—"} articles
          </span>
          <span className="text-[9px] text-nexus-muted">
            CACHE: {newsApi.data?.cached_summaries ?? 0} summaries
          </span>
          {newsApi.lastUpdated && (
            <span className="text-[9px] text-nexus-muted">
              UPDATED: {newsApi.lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      {/* Main Grid */}
      <main className="p-3 grid grid-cols-12 gap-3" style={{ minHeight: "calc(100vh - 80px)" }}>
        {/* Left column: News Feed (5 cols, full height) */}
        <div className="col-span-12 lg:col-span-5 flex flex-col" style={{ minHeight: "800px" }}>
          <NewsFeed
            data={newsApi.data}
            loading={newsApi.loading}
            error={newsApi.error}
            onCategoryChange={handleCategoryChange}
          />
        </div>

        {/* Middle column: Economics + Markets + Signal (4 cols) */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-3">
          <EconomicIndicators
            data={econApi.data}
            loading={econApi.loading}
            error={econApi.error}
          />
          <MarketsOverview
            data={marketsApi.data}
            loading={marketsApi.loading}
            error={marketsApi.error}
          />
        </div>

        {/* Right column: AI Signal + Watchlist (3 cols) */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-3">
          <AISignalEngine
            data={signalData}
            loading={signalLoading}
            error={signalError}
          />
          <Watchlist
            data={watchlistApi.data}
            loading={watchlistApi.loading}
            error={watchlistApi.error}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-nexus-border px-4 py-2">
        <div className="flex items-center justify-between text-[9px] text-nexus-muted tracking-widest">
          <span>NEXUS v1.0 // FOR INFORMATIONAL PURPOSES ONLY // NOT FINANCIAL ADVICE</span>
          <span>DATA: NEWSAPI · FRED · YFINANCE · GROQ/LLAMA-3.1-8B</span>
        </div>
      </footer>
    </div>
  );
}

// Missing Clock import fix
function Clock({ size, className }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}
