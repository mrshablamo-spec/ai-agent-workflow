# Mini-Palantir Supply Chain Intelligence Engine

> "Most retail investors react to news *after* the stock drops. This engine finds the
> structural dependency *before* any news exists."

Maps relationships between a target company, its suppliers, and geographic risks using
SEC 10-K filings and public news RSS — no paid APIs, no API keys required.

## Quick Start

```bash
pip install -r requirements.txt

# Edit config.py — set your email in SEC_USER_AGENT (required for SEC Fair Access)

python main.py --ticker AAPL
```

## What It Does

Given a ticker, the full pipeline:

| Phase | What Happens |
|---|---|
| 1 | Downloads the latest 10-K from SEC EDGAR (cached locally) |
| 2 | Extracts Item 1 (Business) + Item 1A (Risk Factors) text |
| 3 | Finds suppliers, geographies, and risk signals — including CRITICAL sole-source dependencies |
| 4 | Scores each dependency: geo tier × Item1A weight × severity × risk phrase density |
| 5 | Builds supply chain knowledge graph, runs ripple simulation, overlays news alerts |

## The Ripple Simulator

Answers the question institutional analysts pay for:

> "If Taiwan is disrupted, which companies in my portfolio are downstream — and how hard are they hit?"

```bash
python main.py --ticker NVDA --simulate-shock taiwan
python main.py --ticker AAPL --simulate-shock ukraine
```

BFS propagation with depth decay: the further the hop, the lower the impact score.
Max depth: 4 hops (beyond that, impact is considered immaterial).

## Live Monitoring

Scans news RSS for all high-risk nodes. Fires alerts when a headline matches risk keywords.

```bash
python main.py --ticker AAPL --monitor
# Output: ⚠ [AAPL] Risk: 'taiwan' hit by "..." — ripple score: 6.24
```

## Outputs

| File | Description |
|---|---|
| `data/processed/{TICKER}/entities.csv` | All extracted entities with severity and risk signals |
| `data/processed/{TICKER}/dependency_table.csv` | Ranked dependency table (flagged top 5) |
| `outputs/graphs/{TICKER}_supply_chain.gexf` | Gephi-importable graph export |
| `outputs/graphs/{TICKER}_supply_chain.png` | Dark-theme visual risk graph |
| `outputs/reports/{TICKER}_risk_summary.json` | JSON report with top risks + ripple paths |

## CLI Reference

```
python main.py --ticker AAPL                         # Full pipeline
python main.py --ticker AAPL --force-download        # Re-fetch filing
python main.py --ticker AAPL --simulate-shock taiwan # Ripple simulation
python main.py --ticker AAPL --monitor               # Live news alerts
python main.py --ticker AAPL --no-news               # Skip news fetching
python main.py --ticker AAPL --skip-graph            # Phases 1-4 only
python main.py --ticker AAPL --verbose               # Debug logging
```

## Two-Agent Workflow

| Agent | Role |
|---|---|
| Claude Code | Lead Analyst & Architect — defines extraction rules, ripple logic, and scoring model |
| ChatGPT Codex | Senior Engineer — implements scrapers, parsers, graph infrastructure |

See `docs/AGENTS.md` for full role definitions and collaboration protocol.

## SEC Fair Access

All EDGAR requests comply with SEC Fair Access rules:
- Rate limited to ~7 req/sec (limit: 10)
- `User-Agent` identifies the bot and includes a contact email
- Raw filings cached locally — never re-fetched unless `--force-download`

Set `SEC_USER_AGENT` in `config.py` before running at scale.
Reference: https://www.sec.gov/os/accessing-edgar-data
