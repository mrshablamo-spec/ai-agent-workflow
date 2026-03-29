# PROJECT_STRUCTURE

## Objective
Build a Mini-Palantir Supply Chain Intelligence Engine that maps relationships among a target company, its suppliers, and geographic risk signals using public 10-K filings and free market/news data.

## Proposed Python Modules

```text
mini_palantir/
  config/
    settings.py              # User-Agent, rate limits, cache paths, source toggles
  scrapers/
    sec_client.py            # SEC-compliant filing fetcher with retry, backoff, and caching
    filing_index.py          # Resolve company tickers/CIKs and locate recent 10-K filings
    news_collector.py        # Optional free-source news harvesting for enrichment
    market_data.py           # Lightweight yfinance-based company context
  parsers/
    tenk_section_parser.py   # Extract Item 1 and Item 1A from raw filing HTML/text
    html_cleaner.py          # Normalize SEC markup into structured text
    entity_extractor.py      # Rule-based extraction of suppliers, products, and geographies
  analysts/
    dependency_analyst.py    # Score supplier and operational dependency signals
    geography_analyst.py     # Detect country/region exposure and location-linked risks
    risk_analyst.py          # Classify risk factors from Item 1A narratives
  graph/
    graph_builder.py         # Build NetworkX graph of entities and relationships
    graph_exporter.py        # Export graph to JSON, CSV, or GEXF for visualization
  pipelines/
    run_company_workflow.py  # End-to-end workflow for a target company
  utils/
    logging_utils.py
    text_utils.py
    cache.py
tests/
  test_tenk_section_parser.py
  test_entity_extractor.py
  test_graph_builder.py
```

## Data Flow
1. `scrapers.filing_index` locates the target company's latest 10-K filing.
2. `scrapers.sec_client` downloads the filing under SEC Fair Access rules using descriptive headers, modest request rates, and local caching.
3. `parsers.tenk_section_parser` isolates `Item 1. Business` and `Item 1A. Risk Factors`.
4. `parsers.entity_extractor` and `analysts.*` identify supplier entities, geographic exposure, and dependency/risk relationships.
5. `graph.graph_builder` creates a relationship graph linking company, supplier, geography, and risk nodes.
6. `graph.graph_exporter` emits artifacts suitable for exploration and visualization.

## Design Principles
- Keep ingestion, parsing, analysis, and graph generation decoupled.
- Treat SEC compliance as a first-class concern: descriptive identity, throttling, retry/backoff, and caching.
- Prefer deterministic extraction first, then layer heuristics where recall is weak.
- Preserve source provenance so every graph edge can be traced back to filing text or enrichment data.
- Avoid paid APIs and keep all integrations replaceable.

## Initial Interfaces
- `fetch_latest_10k(ticker: str) -> Path`
- `extract_core_sections(filing_path: Path) -> dict[str, str]`
- `analyze_dependencies(item_1_text: str, item_1a_text: str) -> pandas.DataFrame`
- `build_supply_chain_graph(records: pandas.DataFrame) -> networkx.Graph`
