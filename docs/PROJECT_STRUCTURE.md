# Project Structure: Mini-Palantir Supply Chain Intelligence Engine

## Core Philosophy: Information Asymmetry

Palantir wins because they connect dots that look unrelated to everyone else.
This system does the same by surfacing **invisible connections** buried inside
SEC filings — before those weaknesses appear in the news or in a stock price.

Key insight: A retail investor reacts to a factory fire in Japan *after* the stock
drops. This engine finds the structural dependency *before* any news exists.

---

## Directory Layout

```
mini-palantir/
│
├── scripts/                     # All executable Python modules
│   ├── sec_client.py            # Ingestion: pulls 10-K filings from SEC EDGAR
│   ├── processor.py             # Extraction: parses Item 1 + 1A, finds hidden dependencies
│   └── graph_engine.py          # Intelligence: builds ontology, scores ripple risk, fires alerts
│
├── data/                        # Git-ignored. All raw + processed data lives here.
│   ├── raw/{TICKER}/            # Raw 10-K HTML from SEC (cached, never re-fetched)
│   └── processed/{TICKER}/      # Extracted text, entities CSV, dependency table CSV
│
├── docs/                        # Project documentation
│   ├── PLAN.md                  # 5-phase execution roadmap
│   ├── AGENTS.md                # Role definitions for Claude + Codex
│   └── PROJECT_STRUCTURE.md     # This file
│
├── outputs/                     # Git-ignored. Generated graphs and reports.
│   ├── graphs/                  # {TICKER}_supply_chain.gexf + .png
│   └── reports/                 # {TICKER}_risk_summary.json
│
├── config.py                    # Central settings: paths, rate limits, scoring weights
├── main.py                      # CLI entry point: python main.py --ticker AAPL
├── requirements.txt
├── README.md
└── .gitignore
```

---

## The Three Scripts

### `scripts/sec_client.py` — The Mouth (Ingestion)
Responsible for acquiring raw data. Nothing else.

| Function | Purpose |
|---|---|
| `get_filing(ticker)` | Top-level: resolves ticker → downloads 10-K → returns local path |
| `get_cik(ticker)` | Looks up CIK from EDGAR company_tickers.json |
| `get_latest_10k_url(cik)` | Finds most recent 10-K accession number from submissions API |
| `download_10k(ticker, force)` | Downloads primary 10-K document, caches to `data/raw/` |
| `get_headlines(entity)` | Fetches Google News RSS for a named entity |

SEC Fair Access compliance is enforced here: User-Agent header, ≤10 req/sec rate limit,
local caching to prevent redundant fetches.

---

### `scripts/processor.py` — The Stomach (Extraction)
Responsible for turning raw HTML into structured intelligence. Nothing else.

| Function | Purpose |
|---|---|
| `extract_sections(ticker)` | Pulls Item 1 + Item 1A text from raw HTML (heading + regex methods) |
| `extract_entities(ticker, sections)` | Finds suppliers, geographies, risk signals via keyword + sentence windowing |
| `build_dependency_table(ticker, entities_df)` | Scores entities, ranks by risk, co-locates suppliers with countries |

This is where Claude's analytical strength applies: understanding the difference
between a "preferred partner" (low risk) and a "sole-source dependency" (critical risk)
requires reading context, not just keyword matching.

---

### `scripts/graph_engine.py` — The Brain (Ontology + Ripple + Alert)
Responsible for the knowledge graph, ripple-effect simulation, and alerting.

| Function | Purpose |
|---|---|
| `build_graph(ticker, dep_df)` | Constructs directed DiGraph: Company → Supplier → Sub-Supplier → Country |
| `simulate_ripple(G, shocked_node)` | BFS from a "shocked" node — finds all downstream companies impacted |
| `score_ripple_severity(G, paths)` | Weights each ripple path by combined edge risk scores |
| `attach_news(G, news_data)` | Overlays current headlines onto graph nodes |
| `monitor_nodes(G, ticker)` | Scans news for all nodes; fires alert if a high-risk node is hit |
| `export_graph(G, ticker)` | Saves .gexf (Gephi) + .png visualization |
| `generate_risk_report(ticker, dep_df, G)` | Writes JSON risk summary |

The **ripple simulation** is what separates this from a simple scraper:
it answers "if Neon Gas supply in Ukraine is disrupted, which companies in my
portfolio are downstream?" — before any journalist writes that headline.

---

## Intelligence Flow (End-to-End)

```
  Ticker Symbol
       │
       ▼
[sec_client.py]  ──── EDGAR HTTPS ──── Cached 10-K HTML
       │
       ▼
[processor.py]   ──── Item 1 + Item 1A ──── Entities + Dependency Table
       │
       ▼
[graph_engine.py] ─── DiGraph Ontology ─── Company→Supplier→SubSupplier→Country
       │                    │
       │            [simulate_ripple()]
       │                    │
       │         Ripple paths + severity scores
       │
       ▼
[graph_engine.py] ─── [monitor_nodes()] ─── News RSS scan
       │
       ▼
  ALERT: "Neon Gas shortage (Ukraine) → Trumpf GmbH → ASML → NVDA exposure"
```

---

## Key Design Constraints

- **No paid APIs.** All data from SEC EDGAR HTTPS and public RSS feeds.
- **SEC Fair Access.** ≤10 req/sec. User-Agent includes contact email.
- **Local caching.** Raw filings never re-fetched if cached.
- **Ripple-first design.** The graph is built to simulate shocks, not just display relationships.
- **Pre-news advantage.** The system surfaces structural risks before they become headlines.
