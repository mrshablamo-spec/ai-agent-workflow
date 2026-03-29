import React, { startTransition, useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  AlertTriangle,
  ArrowRight,
  Factory,
  Globe2,
  Link2,
  Radar,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

const API_BASE = process.env.REACT_APP_API_URL || "";
const SAMPLE_TICKERS = ["NVDA", "ASML", "AAPL", "TSM", "AMD"];

function SectionCard({ title, eyebrow, action, children }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="panel-eyebrow">{eyebrow}</p>
          <h2 className="panel-title-main">{title}</h2>
        </div>
        {action}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function Metric({ label, value, tone = "default" }) {
  return (
    <div className={`metric metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}

function SignalList({ items, empty, renderItem }) {
  if (!items?.length) {
    return <div className="empty-state">{empty}</div>;
  }
  return <div className="stack">{items.map(renderItem)}</div>;
}

export default function App() {
  const [ticker, setTicker] = useState("NVDA");
  const [includeNews, setIncludeNews] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let isMounted = true;
    axios.get(`${API_BASE}/supply-chain/health`, { timeout: 15000 })
      .then((response) => {
        if (isMounted) {
          setHealth(response.data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setHealth({ warning: "Unable to reach supply-chain health endpoint." });
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const runAnalysis = async (targetTicker = ticker) => {
    setLoading(true);
    setError("");
    try {
      const response = await axios.post(
        `${API_BASE}/supply-chain/analyze`,
        { ticker: targetTicker, include_news: includeNews },
        { timeout: 90000 },
      );
      startTransition(() => {
        setTicker(targetTicker.toUpperCase());
        setAnalysis(response.data);
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Unable to complete analysis.");
    } finally {
      setLoading(false);
    }
  };

  const summary = useMemo(() => {
    if (!analysis) {
      return null;
    }

    const supplierCount = analysis.supplier_signals?.length || 0;
    const geographyCount = analysis.geography_signals?.length || 0;
    const riskCount = analysis.risk_signals?.length || 0;

    const topRisk = analysis.risk_signals?.[0];
    const topGeography = analysis.geography_signals?.[0];

    return {
      supplierCount,
      geographyCount,
      riskCount,
      topRisk: topRisk ? `${topRisk.category} / ${Math.round(topRisk.severity * 100)}% severity` : "No major risk classified yet",
      topGeography: topGeography ? `${topGeography.geography} / ${topGeography.mention_count} mentions` : "No geographic concentration detected",
    };
  }, [analysis]);

  const secWarning = analysis?.notes?.find((note) => note.toLowerCase().includes("placeholder")) || health?.warning;

  return (
    <div className="shell">
      <div className="backdrop-orbit backdrop-orbit-a" />
      <div className="backdrop-orbit backdrop-orbit-b" />

      <header className="hero panel">
        <div className="hero-copy">
          <p className="hero-kicker">Mini-Palantir Supply Chain Intelligence Engine</p>
          <h1>Map hidden suppliers, geographic chokepoints, and pre-news risk before the market notices.</h1>
          <p className="hero-text">
            This console scans the latest 10-K, extracts dependency language from Item 1 and Item 1A,
            enriches key nodes with free news, and returns a graph-ready risk picture without paid APIs.
          </p>
          <div className="hero-tags">
            <span>SEC Fair Access</span>
            <span>Dependency Signals</span>
            <span>Ripple-Effect Monitoring</span>
          </div>
        </div>

        <div className="command-box">
          <div className="command-topline">
            <Radar size={16} />
            <span>Mission Control</span>
          </div>

          {secWarning && (
            <div className="warning-banner">
              <AlertTriangle size={14} />
              <span>{secWarning}</span>
            </div>
          )}

          <label className="field-label" htmlFor="ticker">Target Ticker</label>
          <div className="ticker-input-row">
            <div className="ticker-input-shell">
              <Search size={16} />
              <input
                id="ticker"
                value={ticker}
                onChange={(event) => setTicker(event.target.value.toUpperCase())}
                placeholder="NVDA"
                maxLength={8}
              />
            </div>
            <button type="button" className="primary-button" onClick={() => runAnalysis()} disabled={loading || !ticker.trim()}>
              {loading ? <RefreshCw size={16} className="spin" /> : <Sparkles size={16} />}
              {loading ? "Analyzing" : "Run Analysis"}
            </button>
          </div>

          <div className="sample-row">
            {SAMPLE_TICKERS.map((sample) => (
              <button key={sample} type="button" className="sample-chip" onClick={() => runAnalysis(sample)} disabled={loading}>
                {sample}
              </button>
            ))}
          </div>

          <label className="toggle-row">
            <input type="checkbox" checked={includeNews} onChange={() => setIncludeNews((current) => !current)} />
            <span>Enrich with free news signals</span>
          </label>

          <div className="command-note">
            Use a real email in your `.env` for live SEC access. The engine caches filings, retries 429s, and throttles requests.
          </div>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      <main className="dashboard-grid">
        <SectionCard
          title="Mission Summary"
          eyebrow="Operator Brief"
          action={analysis ? <span className="status-pill">{analysis.company?.ticker} live map</span> : null}
        >
          {analysis ? (
            <>
              <div className="metrics-grid">
                <Metric label="Company" value={analysis.company?.name || analysis.company?.ticker || "Unknown"} />
                <Metric label="Suppliers" value={summary?.supplierCount || 0} tone="cyan" />
                <Metric label="Geographies" value={summary?.geographyCount || 0} tone="gold" />
                <Metric label="Risk Flags" value={summary?.riskCount || 0} tone="red" />
              </div>
              <div className="insight-strip">
                <div>
                  <span className="insight-label">Top Risk</span>
                  <p>{summary?.topRisk}</p>
                </div>
                <div>
                  <span className="insight-label">Primary Geography</span>
                  <p>{summary?.topGeography}</p>
                </div>
                <div>
                  <span className="insight-label">Filing Date</span>
                  <p>{analysis.filing?.filing_date || "Unknown"}</p>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state large">Run a ticker to generate the first dependency map.</div>
          )}
        </SectionCard>

        <SectionCard title="Supplier Dependency Signals" eyebrow="Invisible Connections">
          <SignalList
            items={analysis?.supplier_signals}
            empty="No supplier dependency cues detected yet. Try a different ticker or inspect the filing excerpts."
            renderItem={(item, index) => (
              <article key={`${item.supplier}-${index}`} className="signal-card supplier-card">
                <div className="signal-heading">
                  <div className="icon-chip">
                    <Factory size={14} />
                  </div>
                  <div>
                    <h3>{item.supplier}</h3>
                    <p>{Math.round(item.confidence * 100)}% confidence dependency signal</p>
                  </div>
                </div>
                <p className="signal-body">{item.evidence}</p>
              </article>
            )}
          />
        </SectionCard>

        <SectionCard title="Geographic Risk Lattice" eyebrow="Chokepoints & Exposure">
          <SignalList
            items={analysis?.geography_signals}
            empty="No geographic concentrations detected yet."
            renderItem={(item, index) => (
              <article key={`${item.geography}-${index}`} className="signal-card geography-card">
                <div className="signal-heading">
                  <div className="icon-chip warm">
                    <Globe2 size={14} />
                  </div>
                  <div>
                    <h3>{item.geography}</h3>
                    <p>{item.mention_count} mentions · {Math.round(item.risk_score * 100)} risk score</p>
                  </div>
                </div>
                <p className="signal-body">{item.context}</p>
              </article>
            )}
          />
        </SectionCard>

        <SectionCard title="Risk Factors" eyebrow="Item 1A Classification">
          <SignalList
            items={analysis?.risk_signals}
            empty="No structured risk factors classified yet."
            renderItem={(item, index) => (
              <article key={`${item.title}-${index}`} className="signal-card risk-card">
                <div className="signal-heading">
                  <div className="icon-chip danger">
                    <ShieldAlert size={14} />
                  </div>
                  <div>
                    <h3>{item.category}</h3>
                    <p>{Math.round(item.severity * 100)} severity</p>
                  </div>
                </div>
                <p className="signal-body">{item.evidence}</p>
              </article>
            )}
          />
        </SectionCard>

        <SectionCard title="Graph Edge Preview" eyebrow="Ontology Output">
          <SignalList
            items={analysis?.graph_preview?.slice(0, 10)}
            empty="Graph edges will appear after an analysis run."
            renderItem={(item, index) => (
              <article key={`${item.source}-${item.target}-${index}`} className="edge-row">
                <span>{item.source}</span>
                <ArrowRight size={14} />
                <span>{item.target}</span>
                <strong>{item.relation}</strong>
              </article>
            )}
          />
        </SectionCard>

        <SectionCard title="Monitoring Feed" eyebrow="News Hits On Hidden Nodes">
          <SignalList
            items={analysis?.news_signals}
            empty={includeNews ? "No matching news signals found for the detected nodes yet." : "News enrichment is turned off for this run."}
            renderItem={(item, index) => (
              <article key={`${item.link}-${index}`} className="signal-card news-card">
                <div className="signal-heading">
                  <div className="icon-chip cool">
                    <Link2 size={14} />
                  </div>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.source || "Google News"}</p>
                  </div>
                </div>
                <p className="signal-body">{item.summary || "No summary available."}</p>
                <div className="matched-entities">
                  {(item.matched_entities || []).map((entity) => (
                    <span key={entity}>{entity}</span>
                  ))}
                </div>
              </article>
            )}
          />
        </SectionCard>

        <SectionCard title="Filing Excerpts" eyebrow="Source Traceability">
          {analysis ? (
            <div className="excerpt-grid">
              <div>
                <p className="excerpt-label">Item 1 · Business</p>
                <div className="excerpt-box">{analysis.sections?.item_1_excerpt}</div>
              </div>
              <div>
                <p className="excerpt-label">Item 1A · Risk Factors</p>
                <div className="excerpt-box">{analysis.sections?.item_1a_excerpt}</div>
              </div>
            </div>
          ) : (
            <div className="empty-state">The filing excerpts appear here once a report is generated.</div>
          )}
        </SectionCard>
      </main>
    </div>
  );
}
