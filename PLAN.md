# PLAN

## Phase 1 Roadmap

1. SEC Scraper Implementation
   - Build a compliant 10-K retrieval module that follows the SEC's Fair Access guidance, sets a descriptive User-Agent, throttles requests, and caches filings locally.
2. Filing Parser Development
   - Extract and normalize `Item 1. Business` and `Item 1A. Risk Factors` sections from 10-K filings for target companies and key suppliers.
3. Entity and Dependency Analysis
   - Identify supplier names, operational dependencies, strategic partners, products, and risk-bearing geographies using rule-based parsing and analyst heuristics.
4. News and Market Context Enrichment
   - Add free-source news and finance context to validate or challenge relationships discovered in SEC filings without relying on paid APIs.
5. Graph Generation and Intelligence Output
   - Build a graph representation of company, supplier, geography, and risk links, then expose exportable outputs for visualization and downstream analysis.
