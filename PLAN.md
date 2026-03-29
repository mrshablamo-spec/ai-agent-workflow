# Implementation Plan: Mini-Palantir Supply Chain Intelligence Engine

## Objective

Build a 5-phase pipeline that, given a public company ticker, produces a supply chain risk graph derived entirely from free public data (SEC 10-K filings + news RSS).

---

## Phase 1: SEC Scraper Implementation

**Goal:** Reliably fetch 10-K filings for any given ticker from SEC EDGAR without violating Fair Access rules.

**Steps:**
1. Use `edgartools` to look up a company's CIK number from its ticker symbol.
2. Query the EDGAR submissions API (`https://data.sec.gov/submissions/CIK{cik}.json`) to get the list of 10-K filings.
3. Retrieve the most recent 10-K filing index and locate the primary document URL.
4. Download the filing HTML to `data/raw/{ticker}/10k_latest.html`.
5. Enforce rate limiting: ≤10 requests/sec. Set `User-Agent: supply-chain-intel <contact@example.com>` on every request.
6. Skip download if a cached file already exists (file-based caching).

**Deliverables:** `scrapers/sec_scraper.py` with functions `get_cik(ticker)`, `get_latest_10k_url(cik)`, `download_10k(ticker)`.

**SEC Fair Access Reference:** https://www.sec.gov/os/accessing-edgar-data

---

## Phase 2: 10-K Parser Implementation

**Goal:** Extract clean text from Item 1 (Business) and Item 1A (Risk Factors) sections of the raw 10-K HTML.

**Steps:**
1. Load the cached HTML filing with `BeautifulSoup`.
2. Locate section boundaries using a combination of:
   - HTML heading tags (`<h1>`, `<h2>`, `<b>`) containing "Item 1" or "Item 1A"
   - Regex fallback: `r'item\s+1[Aa]?\b'` (case-insensitive)
3. Extract all text between the located boundaries, stripping navigation/boilerplate.
4. Save extracted sections to `data/processed/{ticker}/item1.txt` and `item1a.txt`.
5. Handle common edge cases: table-of-contents links, inline XBRL tags, multi-page filings.

**Deliverables:** `parsers/tenk_parser.py` with function `extract_sections(ticker) -> dict`.

---

## Phase 3: Entity Extraction

**Goal:** From the parsed text, identify supplier names, geographic regions, and risk-signal phrases.

**Steps:**
1. Define keyword lists for:
   - **Supplier signals:** "supplier", "vendor", "manufacturer", "contract manufacturer", "sole source", "third-party"
   - **Geographic signals:** country and region names (use a curated list from `pandas` + manual additions)
   - **Risk signals:** "concentration risk", "tariff", "political instability", "natural disaster", "single source", "disruption"
2. For each keyword category, extract surrounding sentence context (±1 sentence window).
3. Co-locate supplier mentions with geographic mentions in the same sentence to build `(supplier_hint, country)` pairs.
4. Output a structured `pandas.DataFrame` with columns: `[ticker, section, entity_type, entity_text, context, risk_signal]`.
5. Save to `data/processed/{ticker}/entities.csv`.

**Deliverables:** `parsers/entity_extractor.py` with function `extract_entities(ticker) -> pd.DataFrame`.

---

## Phase 4: Risk Scoring and Dependency Mapping

**Goal:** Score each identified dependency by risk severity and rank the supply chain risks.

**Steps:**
1. **Geographic risk baseline:** Assign each country a base risk tier using a static lookup table (sourced from public indices like Fraser Institute or World Bank governance data — downloadable as CSV, no API needed).
2. **Mention frequency amplifier:** Multiply base risk by how often a country/supplier is mentioned in Item 1A vs. Item 1.
3. **Risk phrase weight:** Add points for each high-severity risk phrase found in the same context as the entity.
4. Produce a ranked `dependency_table.csv` with columns: `[ticker, dependency, dependency_type, country, risk_score, evidence_count, top_risk_phrase]`.
5. Flag the top 5 highest-risk dependencies for graph highlighting.

**Deliverables:** `analysts/risk_scorer.py`, `analysts/dependency_mapper.py`, output `data/processed/{ticker}/dependency_table.csv`.

---

## Phase 5: Graph Generation and News Overlay

**Goal:** Visualize the supply chain as a directed risk graph and overlay current news signals.

**Steps:**
1. Load `dependency_table.csv` into a `networkx.DiGraph`.
   - **Nodes:** Target company, supplier hints, countries
   - **Edges:** `target → supplier_hint` (weight = risk_score), `supplier_hint → country` (weight = geographic_risk)
   - **Node attributes:** `type` (company/supplier/country), `risk_score`
2. Fetch top 5 news headlines per high-risk node using BeautifulSoup + Google News RSS (`https://news.google.com/rss/search?q={entity}`).
3. Attach news headlines as node metadata.
4. Render graph with `matplotlib` using node color = risk tier (green/yellow/red).
5. Export to `outputs/graphs/{ticker}_supply_chain.gexf` (importable into Gephi for deeper analysis).
6. Print a summary risk report to console and save to `outputs/reports/{ticker}_risk_summary.json`.

**Deliverables:** `graph/graph_generator.py`, `scrapers/news_scraper.py`, `main.py` CLI entry point.

---

## Milestone Summary

| Phase | Module(s) | Output |
|---|---|---|
| 1 — SEC Scraper | `scrapers/sec_scraper.py` | Raw 10-K HTML cached locally |
| 2 — 10-K Parser | `parsers/tenk_parser.py` | Item 1 + Item 1A clean text |
| 3 — Entity Extraction | `parsers/entity_extractor.py` | `entities.csv` |
| 4 — Risk Scoring | `analysts/risk_scorer.py`, `dependency_mapper.py` | `dependency_table.csv` |
| 5 — Graph + News | `graph/graph_generator.py`, `scrapers/news_scraper.py`, `main.py` | Risk graph + JSON report |

---

## Usage (Target CLI)

```bash
python main.py --ticker AAPL
# Output: outputs/graphs/AAPL_supply_chain.gexf
#         outputs/reports/AAPL_risk_summary.json
```
