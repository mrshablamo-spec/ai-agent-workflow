# Project Structure: Mini-Palantir Supply Chain Intelligence Engine

## Overview

A modular Python system that maps relationships between a target company, its suppliers, and geographic risks using free public data sources (SEC EDGAR 10-K filings and news).

---

## Directory Layout

```
supply_chain_intelligence/
│
├── scrapers/                    # Data acquisition layer
│   ├── __init__.py
│   ├── sec_scraper.py           # Fetches 10-K filings from SEC EDGAR (EDGAR full-text search)
│   └── news_scraper.py          # Fetches news headlines via RSS/BeautifulSoup (no API key)
│
├── parsers/                     # Text extraction and structuring layer
│   ├── __init__.py
│   ├── tenk_parser.py           # Extracts Item 1 (Business) and Item 1A (Risk Factors) from 10-Ks
│   └── entity_extractor.py      # Pulls company names, geographies, and supplier mentions from text
│
├── analysts/                    # Intelligence and scoring layer
│   ├── __init__.py
│   ├── risk_scorer.py           # Scores geographic and supplier concentration risk
│   └── dependency_mapper.py     # Identifies and ranks supply chain dependencies
│
├── graph/                       # Visualization and relationship layer
│   ├── __init__.py
│   └── graph_generator.py       # Builds NetworkX graph of company → supplier → risk relationships
│
├── data/                        # Local cache for raw and processed data
│   ├── raw/                     # Raw HTML/XML from SEC EDGAR
│   └── processed/               # Cleaned DataFrames (CSV/Parquet)
│
├── outputs/                     # Final deliverables
│   ├── graphs/                  # Exported graph files (.gexf, .graphml, .png)
│   └── reports/                 # Summary risk reports (CSV, JSON)
│
├── main.py                      # CLI entry point: accepts ticker symbol, runs full pipeline
├── config.py                    # Global settings (rate limits, target sections, output paths)
├── requirements.txt
└── README.md
```

---

## Module Responsibilities

### 1. Scrapers
| Module | Role |
|---|---|
| `sec_scraper.py` | Uses `edgartools` (or direct EDGAR HTTPS) to locate and download 10-K filings by ticker. Respects SEC Fair Access rules: ≤10 requests/sec, identifies bot with email in User-Agent header. |
| `news_scraper.py` | Scrapes public RSS feeds (Google News, Reuters, AP) for supplier/risk mentions. Uses `BeautifulSoup` + `requests`. No API key required. |

### 2. Parsers
| Module | Role |
|---|---|
| `tenk_parser.py` | Parses raw 10-K HTML/text. Locates Item 1 and Item 1A sections by regex/anchor tags. Outputs clean text blocks. |
| `entity_extractor.py` | Runs lightweight NLP over clean text to extract: company names, country/region mentions, supplier/vendor keywords, and risk phrases. Uses `re`, `pandas`, optionally `spacy` (small model). |

### 3. Analysts
| Module | Role |
|---|---|
| `risk_scorer.py` | Assigns scores to geographic regions based on frequency of risk-related language (e.g., "political instability", "tariff", "single-source"). |
| `dependency_mapper.py` | Aggregates entity extraction output into a ranked dependency table (company → supplier → country → risk_score). |

### 4. Graph Generator
| Module | Role |
|---|---|
| `graph_generator.py` | Takes the dependency table and builds a directed `networkx.DiGraph`. Nodes = companies/regions. Edges = supply relationships weighted by risk score. Exports to `.gexf` for Gephi or renders inline with `matplotlib`. |

---

## Data Flow

```
Ticker Symbol (CLI)
      │
      ▼
[sec_scraper.py] ──── EDGAR HTTPS ──── 10-K Filing (HTML/XML)
      │
      ▼
[tenk_parser.py] ──── Item 1 + Item 1A text
      │
      ▼
[entity_extractor.py] ──── Entities: suppliers, countries, risk phrases
      │
      ▼
[risk_scorer.py + dependency_mapper.py] ──── Scored dependency table
      │
      ▼
[graph_generator.py] ──── Supply chain graph (visual + export)
      │
      ▼
[news_scraper.py] ──── Overlay current news signals on graph nodes
```

---

## Key Design Constraints

- **No paid APIs.** All data from SEC EDGAR public endpoints and open RSS feeds.
- **SEC Fair Access compliance.** Max 10 req/sec. User-Agent must include email contact.
- **Local caching.** Raw filings cached in `data/raw/` to avoid redundant requests.
- **Modular.** Each layer can be run and tested independently.
