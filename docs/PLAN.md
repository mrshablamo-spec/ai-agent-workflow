# Execution Plan: Mini-Palantir Supply Chain Intelligence Engine

## The Objective

Build a system that gives retail investors **pre-news structural intelligence** about
supply chain risk — the same informational edge that institutional analysts pay
millions for, using only free public data.

The system answers one question:
> "If X happens to Y, which companies in my portfolio are downstream — and how fast
> does the damage travel?"

---

## Phase 1: SEC Client Implementation

**Goal:** Reliable, SEC-compliant ingestion of 10-K filings for any public company.

**Owner:** Codex implements. Claude reviews for Fair Access compliance.

**Steps:**
1. Implement `scripts/sec_client.py` with mandatory SEC headers:
   ```python
   HEADERS = {'User-Agent': 'MiniPalantirProject your_email@example.com'}
   ```
2. Implement `get_cik(ticker)` using `https://www.sec.gov/files/company_tickers.json`
3. Implement `get_latest_10k_url(cik)` using `https://data.sec.gov/submissions/CIK{cik}.json`
4. Implement `download_10k(ticker)` — download primary document, cache to `data/raw/{TICKER}/`
5. Enforce: ≤10 req/sec, exponential backoff on failure, skip re-fetch if cached
6. Implement `get_headlines(entity)` — Google News RSS, no API key

**Deliverables:**
- `scripts/sec_client.py`
- `data/raw/{TICKER}/10k_latest.html` (after first run)

**Validation:** `python main.py --ticker AAPL --skip-graph` downloads without error.

---

## Phase 2: Item Extraction

**Goal:** Isolate Item 1 (Business) and Item 1A (Risk Factors) from the raw HTML.

**Owner:** Codex implements the parser. Claude defines the extraction rules.

**Claude's Extraction Rules:**
- Item 1 = everything between "Item 1. Business" and "Item 1A. Risk Factors"
- Item 1A = everything between "Item 1A. Risk Factors" and "Item 1B." or "Item 2."
- If HTML heading tags fail, fall back to regex over plain text
- Strip: navigation links, table-of-contents entries, XBRL inline tags
- Minimum viable section: >500 characters (shorter = extraction failure, log warning)

**Steps:**
1. Load raw HTML with BeautifulSoup
2. Try heading-based extraction (`<b>`, `<h2>` tags matching "Item 1" pattern)
3. Fallback: regex over `soup.get_text()` plain text
4. Save `data/processed/{TICKER}/item1.txt` and `item1a.txt`

**Deliverables:** `scripts/processor.py::extract_sections()`

**Validation:** Item 1A for AAPL is >5,000 characters and contains "supplier."

---

## Phase 3: Entity Extraction — Finding the "Hidden" Nodes

**Goal:** Extract supplier names, geographic exposures, and risk signals.
This is where Claude's language reasoning is critical.

**Owner:** Claude defines extraction logic. Codex implements.

**Claude's Intelligence Rules:**
- **Sole-source indicator words:** "sole supplier," "single source," "only supplier,"
  "exclusively," "only qualified" → flag as `CRITICAL`
- **Concentration risk words:** "concentration," "significant portion," "substantial,"
  "majority of" → flag as `HIGH`
- **Preferred partner language:** "preferred," "primary," "our largest" → flag as `MEDIUM`
- **Geographic exposure:** country/region names co-located with supplier language
  in the same sentence = supply chain geography (not just a sales market)
- **Sub-supplier detection:** phrases like "our suppliers rely on," "dependent on
  third parties for" → create an `inferred` sub-supplier node in the graph

**Steps:**
1. Split sections into sentences with ±1 sentence context window
2. Run keyword matching for supplier signals, risk signals, geo names
3. Co-locate: a supplier mention + a geo mention in the same sentence = edge evidence
4. Build `entities.csv` with columns:
   `[ticker, section, entity_type, entity_text, context, risk_signals, keyword_matched, severity]`
5. Save to `data/processed/{TICKER}/entities.csv`

**Deliverables:** `scripts/processor.py::extract_entities()`

**Validation:** AAPL entities.csv contains Taiwan, TSMC-related text, and at least one
"sole source" or "concentration" signal.

---

## Phase 4: Ontology + Risk Scoring

**Goal:** Build a scored dependency table that the graph engine can consume.
Produce the "pre-news" intelligence: which dependencies are most dangerous.

**Owner:** Claude defines scoring model. Codex implements.

**Scoring Model:**
```
risk_score = base_geo_tier                              # 1–5 scale
           × item1a_amplifier (2.0 if in Item 1A)      # Risk Factors = 2× weight
           × (1 + risk_phrase_weight × signal_count)   # Each risk phrase adds weight
           × severity_multiplier                        # CRITICAL=3, HIGH=2, MEDIUM=1
```

**Dependency Table Schema:**
```
[ticker, dependency, dependency_type, country, risk_score,
 evidence_count, severity, top_risk_phrase, flagged, inferred]
```

**Steps:**
1. Score all entities from Phase 3
2. Aggregate to one row per entity (max risk_score, total mention_count)
3. Cross-locate supplier hints with geo mentions (same-sentence co-occurrence)
4. Add `inferred=True` for sub-suppliers detected via "our suppliers rely on" language
5. Flag top 5 by risk_score
6. Save `data/processed/{TICKER}/dependency_table.csv`

**Deliverables:** `scripts/processor.py::build_dependency_table()`

---

## Phase 5: Knowledge Graph + Ripple Simulation + Alerting

**Goal:** The full "Mini-Palantir" experience. A live, queryable knowledge graph
that can simulate supply shocks and alert you before the news breaks.

**Owner:** Codex builds infrastructure. Claude defines ripple logic and alert thresholds.

**Graph Schema:**
```
Nodes: Company (blue) | Supplier (orange) | Sub-Supplier (yellow) | Country (risk-colored)
Edges: depends_on | sub_depends_on | located_in | exposed_to
Edge weight: risk_score (higher = more dangerous path)
Node attributes: risk_score, flagged, inferred, news_headlines
```

**Ripple Simulation Logic:**
1. Receive a "shock event" (e.g., `shocked_node="ukraine"` or `shocked_node="TSMC"`)
2. BFS from shocked node following reverse edges (who depends on this?)
3. For each reachable node, compute `cumulative_ripple_score`:
   ```
   ripple_score = Σ(edge_weights along path) × depth_decay(0.8 per hop)
   ```
4. Return ranked list: `[(company, ripple_score, path, depth), ...]`
5. Flag any path reaching the root ticker company

**Alerting Logic:**
1. For each HIGH/CRITICAL node in the graph, fetch Google News RSS
2. If any headline matches risk keywords → fire alert
3. Alert format: `"⚠ [TICKER] Risk: {node} hit by '{headline}' — estimated ripple score: {score}"`

**Steps:**
1. Build DiGraph from dependency table
2. Implement `simulate_ripple(G, shocked_node)` using BFS
3. Implement `monitor_nodes(G, ticker)` — news scan → alert
4. Render PNG with node colors by risk tier
5. Export GEXF for Gephi deep-dive
6. Generate `{TICKER}_risk_summary.json`

**Deliverables:** `scripts/graph_engine.py` (complete)

**Validation:**
- `simulate_ripple(G, 'taiwan')` returns AAPL in the result set
- PNG renders with at least 5 nodes
- `monitor_nodes()` returns a list (may be empty if no live news hits)

---

## Milestone Summary

| Phase | Script | Output |
|---|---|---|
| 1 — SEC Ingestion | `sec_client.py` | `data/raw/{TICKER}/10k_latest.html` |
| 2 — Section Parsing | `processor.py` | `item1.txt`, `item1a.txt` |
| 3 — Entity Extraction | `processor.py` | `entities.csv` |
| 4 — Ontology + Scoring | `processor.py` | `dependency_table.csv` |
| 5 — Graph + Ripple + Alert | `graph_engine.py` | `.gexf`, `.png`, `_risk_summary.json` |

---

## Target CLI Usage

```bash
# Full pipeline
python main.py --ticker AAPL

# Simulate a supply shock (e.g., Taiwan crisis)
python main.py --ticker AAPL --simulate-shock taiwan

# Monitor mode: scan news and print alerts
python main.py --ticker AAPL --monitor

# Re-fetch filing even if cached
python main.py --ticker AAPL --force-download
```
