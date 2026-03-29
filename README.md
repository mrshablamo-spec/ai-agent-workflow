# Mini-Palantir Supply Chain Intelligence Engine

Maps relationships between a target company, its suppliers, and geographic risks using SEC 10-K filings and news — no paid APIs required.

## Quick Start

```bash
pip install -r requirements.txt
python main.py --ticker AAPL
```

## What It Does

Given a ticker symbol, the pipeline:

1. Downloads the latest 10-K filing from SEC EDGAR
2. Extracts Item 1 (Business) and Item 1A (Risk Factors) text
3. Identifies supplier hints, geographic mentions, and risk signals
4. Scores each dependency by risk severity
5. Builds a supply chain risk graph and overlays current news headlines

## Outputs

| File | Description |
|---|---|
| `data/processed/{TICKER}/entities.csv` | All extracted entities with risk signals |
| `data/processed/{TICKER}/dependency_table.csv` | Ranked dependency table |
| `outputs/graphs/{TICKER}_supply_chain.gexf` | Graph export for Gephi |
| `outputs/graphs/{TICKER}_supply_chain.png` | Visual risk graph |
| `outputs/reports/{TICKER}_risk_summary.json` | JSON risk report |

## Configuration

Edit `config.py` to:
- Set your contact email in `SEC_USER_AGENT` (required for SEC Fair Access compliance)
- Adjust risk tiers in `GEO_RISK_TIERS`
- Tune scoring weights (`RISK_PHRASE_WEIGHT`, `ITEM1A_AMPLIFIER`)

## SEC Fair Access

All EDGAR requests comply with SEC Fair Access rules:
- Rate limited to ~7 requests/second (limit is 10)
- `User-Agent` header identifies the bot and includes a contact email
- Raw filings cached locally to avoid redundant requests

See: https://www.sec.gov/os/accessing-edgar-data

## CLI Options

```
python main.py --ticker AAPL             # Full pipeline
python main.py --ticker AAPL --force-download  # Re-fetch filing
python main.py --ticker AAPL --no-news   # Skip news overlay
python main.py --ticker AAPL --skip-graph  # Phases 1-4 only
python main.py --ticker AAPL --verbose   # Debug logging
```
