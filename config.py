"""
Global configuration for the Mini-Palantir Supply Chain Intelligence Engine.
Edit this file to tune scoring weights, add geographies, or change paths.

IMPORTANT: Set SEC_USER_AGENT to include your real email before running at scale.
SEC Fair Access requires a bot-identifying User-Agent with contact info.
Reference: https://www.sec.gov/os/accessing-edgar-data
"""

import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUTS_GRAPHS_DIR = os.path.join(BASE_DIR, "outputs", "graphs")
OUTPUTS_REPORTS_DIR = os.path.join(BASE_DIR, "outputs", "reports")

# ── SEC EDGAR ─────────────────────────────────────────────────────────────────
# IMPORTANT: Replace with your real email to comply with SEC Fair Access rules.
SEC_USER_AGENT = "MiniPalantirProject your_email@example.com"

SEC_RATE_LIMIT_DELAY = 0.15   # seconds between EDGAR requests (~6-7/sec, limit is 10)
SEC_MAX_RETRIES = 3
SEC_RETRY_BACKOFF = 2.0       # doubles each retry: 2s, 4s, 8s

# ── Entity extraction keywords ────────────────────────────────────────────────
SUPPLIER_KEYWORDS = [
    "supplier", "suppliers", "vendor", "vendors", "manufacturer",
    "manufacturers", "contract manufacturer", "sole source", "single source",
    "third-party", "third party", "subcontractor", "outsource", "outsourced",
    "supply chain", "procurement", "component supplier", "original equipment",
]

RISK_KEYWORDS = [
    "concentration risk", "single source", "sole source", "disruption",
    "tariff", "tariffs", "trade restriction", "export control", "sanction",
    "sanctions", "political instability", "geopolitical", "natural disaster",
    "earthquake", "flood", "pandemic", "shortage", "capacity constraint",
    "price increase", "logistics", "port congestion", "regulatory risk",
    "compliance risk", "dependency", "inflation", "supply disruption",
]

# Context window: ±N sentences around a keyword hit
CONTEXT_WINDOW = 1

# ── Geographic risk tiers (1=stable, 5=high risk) ────────────────────────────
# Based on public governance/stability indices — no API required.
# Sources: World Bank governance indicators, geopolitical risk research.
GEO_RISK_TIERS = {
    # Tier 1 — Stable, rule-of-law, low supply chain risk
    "united states": 1, "canada": 1, "germany": 1, "japan": 1,
    "australia": 1, "netherlands": 1, "sweden": 1, "switzerland": 1,
    "norway": 1, "denmark": 1, "finland": 1, "new zealand": 1,
    # Tier 2 — Generally stable, some geopolitical or regulatory risk
    "south korea": 2, "taiwan": 2, "united kingdom": 2, "france": 2,
    "singapore": 2, "israel": 2, "spain": 2, "italy": 2,
    "czech republic": 2, "poland": 2, "portugal": 2, "austria": 2, "ireland": 2,
    # Tier 3 — Moderate risk: policy uncertainty, IP risk, or logistics friction
    "china": 3, "india": 3, "brazil": 3, "mexico": 3, "turkey": 3,
    "indonesia": 3, "malaysia": 3, "thailand": 3, "vietnam": 3,
    "philippines": 3, "south africa": 3, "colombia": 3, "peru": 3,
    "argentina": 3, "chile": 3, "egypt": 3, "morocco": 3,
    # Tier 4 — Elevated risk: active conflict, sanctions, governance concerns
    "russia": 4, "ukraine": 4, "pakistan": 4, "bangladesh": 4,
    "nigeria": 4, "kenya": 4, "cambodia": 4, "myanmar": 4,
    "ethiopia": 4, "ghana": 4, "tanzania": 4, "iraq": 4, "iran": 4,
    # Tier 5 — High risk: active war, failed state, severe sanctions
    "north korea": 5, "syria": 5, "afghanistan": 5, "yemen": 5,
    "somalia": 5, "libya": 5, "sudan": 5, "venezuela": 5,
}

# ── Scoring weights ───────────────────────────────────────────────────────────
# Item 1A (Risk Factors) mentions are weighted 2x vs Item 1 (Business)
ITEM1A_AMPLIFIER = 2.0

# Each risk keyword hit adds RISK_PHRASE_WEIGHT / 10 to the score multiplier
RISK_PHRASE_WEIGHT = 1.5

# ── Ripple simulation ─────────────────────────────────────────────────────────
# Score decays by this factor per hop (0.8 = 80% propagation per step)
DEPTH_DECAY = 0.8

# BFS depth limit — beyond 4 hops, impact is considered immaterial
MAX_RIPPLE_DEPTH = 4

# Nodes with risk_score >= this threshold are monitored for live news alerts
ALERT_RISK_THRESHOLD = 6.0

# ── News scraper ──────────────────────────────────────────────────────────────
NEWS_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
NEWS_MAX_HEADLINES = 5
NEWS_REQUEST_DELAY = 1.0  # seconds between news RSS requests
