"""
Global configuration for the Supply Chain Intelligence Engine.
"""

import os

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUTS_GRAPHS_DIR = os.path.join(BASE_DIR, "outputs", "graphs")
OUTPUTS_REPORTS_DIR = os.path.join(BASE_DIR, "outputs", "reports")

# ── SEC EDGAR ────────────────────────────────────────────────────────────────
# Fair Access: https://www.sec.gov/os/accessing-edgar-data
# Max 10 requests/second. Must identify bot with contact email in User-Agent.
EDGAR_BASE_URL = "https://data.sec.gov"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data"

# IMPORTANT: Replace with your real email to comply with SEC Fair Access rules.
SEC_USER_AGENT = "supply-chain-intel contact@example.com"

SEC_RATE_LIMIT_DELAY = 0.15  # seconds between requests (~6-7 req/sec, safely under 10)
SEC_MAX_RETRIES = 3
SEC_RETRY_BACKOFF = 2.0  # seconds; doubles on each retry

# ── Parsing ──────────────────────────────────────────────────────────────────
# 10-K sections to extract
TARGET_SECTIONS = {
    "item1": "Item 1",       # Business
    "item1a": "Item 1A",     # Risk Factors
}

# ── Entity Extraction ────────────────────────────────────────────────────────
SUPPLIER_KEYWORDS = [
    "supplier", "suppliers", "vendor", "vendors", "manufacturer",
    "manufacturers", "contract manufacturer", "sole source", "single source",
    "third-party", "third party", "subcontractor", "outsource", "outsourced",
    "supply chain", "procurement", "component supplier",
]

RISK_KEYWORDS = [
    "concentration risk", "single source", "sole source", "disruption",
    "tariff", "tariffs", "trade restriction", "export control", "sanction",
    "sanctions", "political instability", "geopolitical", "natural disaster",
    "earthquake", "flood", "pandemic", "shortage", "capacity constraint",
    "price increase", "inflation", "logistics", "port congestion",
    "regulatory risk", "compliance risk", "dependency",
]

# Context window (sentences) around a keyword hit
CONTEXT_WINDOW = 1

# ── Risk Scoring ─────────────────────────────────────────────────────────────
# Base geographic risk tiers (1 = low, 5 = high).
# Derived from public governance/stability indices — no API required.
# Expand as needed.
GEO_RISK_TIERS = {
    # Tier 1 — Stable
    "united states": 1, "canada": 1, "germany": 1, "japan": 1,
    "australia": 1, "netherlands": 1, "sweden": 1, "switzerland": 1,
    "norway": 1, "denmark": 1, "finland": 1, "new zealand": 1,
    # Tier 2 — Generally stable, some risk
    "south korea": 2, "united kingdom": 2, "france": 2, "singapore": 2,
    "israel": 2, "spain": 2, "italy": 2, "czech republic": 2, "poland": 2,
    "portugal": 2, "austria": 2, "ireland": 2,
    # Tier 3 — Moderate risk
    "china": 3, "india": 3, "brazil": 3, "mexico": 3, "turkey": 3,
    "indonesia": 3, "malaysia": 3, "thailand": 3, "vietnam": 3,
    "philippines": 3, "south africa": 3, "colombia": 3, "peru": 3,
    "argentina": 3, "chile": 3, "egypt": 3, "morocco": 3,
    # Tier 4 — Elevated risk
    "russia": 4, "ukraine": 4, "pakistan": 4, "bangladesh": 4,
    "nigeria": 4, "kenya": 4, "cambodia": 4, "myanmar": 4,
    "ethiopia": 4, "ghana": 4, "tanzania": 4, "iraq": 4, "iran": 4,
    # Tier 5 — High risk
    "north korea": 5, "syria": 5, "afghanistan": 5, "yemen": 5,
    "somalia": 5, "libya": 5, "sudan": 5, "venezuela": 5,
}

# Weight multipliers for risk phrase hits in Item 1A
RISK_PHRASE_WEIGHT = 1.5
# Amplifier for mentions in Item 1A vs Item 1
ITEM1A_AMPLIFIER = 2.0

# ── News Scraper ─────────────────────────────────────────────────────────────
NEWS_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
NEWS_MAX_HEADLINES = 5
NEWS_REQUEST_DELAY = 1.0  # seconds between news requests
