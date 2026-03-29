"""
scripts/graph_engine.py — The Brain (Ontology + Ripple Simulation + Alerting)

This is where Mini-Palantir becomes more than a scraper.

Core capabilities:
  1. build_graph()          — constructs the supply chain knowledge graph
  2. simulate_ripple()      — BFS shock propagation: "if X is hit, who feels it?"
  3. score_ripple_severity()— weighted path scoring with depth decay
  4. monitor_nodes()        — live news scan → alerts when a node is hit
  5. export_graph()         — GEXF (Gephi) + PNG visualization
  6. generate_risk_report() — JSON summary with top risks and ripple paths

The "Pre-News" Advantage:
  Most investors react to news AFTER a stock drops. This engine maps the
  structural dependency BEFORE news exists, enabling pre-emptive hedging.

  Example chain:
    Ukraine → (Neon Gas shortage) → Trumpf GmbH → ASML → TSMC → NVIDIA → [portfolio hit]

Owner: Codex implements. Claude defines ripple logic + alert thresholds.
"""

import json
import logging
import os
from collections import deque

import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from config import GEO_RISK_TIERS, OUTPUTS_GRAPHS_DIR, OUTPUTS_REPORTS_DIR, RISK_KEYWORDS
except ImportError:
    _BASE = os.path.dirname(os.path.dirname(__file__))
    OUTPUTS_GRAPHS_DIR = os.path.join(_BASE, "outputs", "graphs")
    OUTPUTS_REPORTS_DIR = os.path.join(_BASE, "outputs", "reports")
    GEO_RISK_TIERS = {
        "united states": 1, "canada": 1, "germany": 1, "japan": 1,
        "taiwan": 2, "south korea": 2, "singapore": 2,
        "china": 3, "india": 3, "vietnam": 3, "malaysia": 3,
        "russia": 4, "ukraine": 4,
        "north korea": 5, "syria": 5, "venezuela": 5,
    }
    RISK_KEYWORDS = [
        "concentration risk", "sole source", "disruption", "tariff",
        "sanction", "political instability", "shortage", "dependency",
    ]

DEPTH_DECAY = 0.8       # ripple score multiplier per hop (e.g., 3 hops = 0.8^3 = 0.512)
MAX_RIPPLE_DEPTH = 4    # truncate BFS at this depth (>4 hops = immaterial per Claude's rule)
ALERT_RISK_THRESHOLD = 6.0   # nodes with risk_score >= this are monitored for news

logger = logging.getLogger(__name__)

# ── Color scheme ──────────────────────────────────────────────────────────────
_NODE_COLORS = {
    "company": "#2196f3",        # blue
    "supplier": "#ff9800",       # orange
    "sub_supplier": "#ffc107",   # yellow
    "geography": None,           # risk-tier colored (see _risk_color)
    "risk_signal": "#9e9e9e",    # grey
}
_RISK_TIER_COLORS = {1: "#4caf50", 2: "#8bc34a", 3: "#ffc107", 4: "#ff5722", 5: "#f44336"}
_UNKNOWN_COLOR = "#9e9e9e"


def _risk_color(score: float) -> str:
    if score < 2: return _RISK_TIER_COLORS[1]
    if score < 4: return _RISK_TIER_COLORS[2]
    if score < 6: return _RISK_TIER_COLORS[3]
    if score < 8: return _RISK_TIER_COLORS[4]
    return _RISK_TIER_COLORS[5]


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph(ticker: str, dep_df: pd.DataFrame) -> nx.DiGraph:
    """
    Build the supply chain knowledge graph from the dependency table.

    Graph schema:
      Nodes: Company (root) | Supplier | Sub-Supplier (inferred) | Country | Risk Signal
      Edges: depends_on | sub_depends_on | located_in | exposed_to | risk_factor
      Edge attributes: weight (risk_score), relationship, evidence_count

    The graph supports BFS ripple simulation — edges point FROM depender TO dependency
    so reversing them gives us "who depends on X?".

    Args:
        ticker: Root company ticker.
        dep_df: Dependency table from processor.build_dependency_table()

    Returns:
        nx.DiGraph representing the supply chain ontology.
    """
    G = nx.DiGraph()
    ticker = ticker.upper()

    # Root company node
    G.add_node(ticker, node_type="company", risk_score=0.0, flagged=False,
               label=ticker, inferred=False)

    for _, row in dep_df.iterrows():
        dep = str(row["dependency"])
        dtype = str(row["dependency_type"])
        rscore = float(row.get("risk_score", 0.0))
        flagged = bool(row.get("flagged", False))
        country = str(row.get("country", ""))
        phrase = str(row.get("top_risk_phrase", ""))
        evidence = int(row.get("evidence_count", 1))
        severity = str(row.get("severity", "LOW"))
        inferred = bool(row.get("inferred", False))
        node_type = "sub_supplier" if inferred else dtype

        if dtype == "supplier":
            if not G.has_node(dep):
                G.add_node(dep, node_type=node_type, risk_score=rscore,
                           flagged=flagged, label=dep[:30],
                           top_risk_phrase=phrase, severity=severity, inferred=inferred)
            rel = "sub_depends_on" if inferred else "depends_on"
            G.add_edge(ticker, dep, weight=rscore, relationship=rel,
                       evidence_count=evidence, severity=severity)

            # Supplier → Country edge
            if country and country not in ("unknown", ""):
                geo_risk = GEO_RISK_TIERS.get(country.lower(), 2)
                if not G.has_node(country):
                    G.add_node(country, node_type="geography",
                               risk_score=float(geo_risk * 2),
                               flagged=geo_risk >= 4, label=country, inferred=False)
                G.add_edge(dep, country, weight=float(geo_risk),
                           relationship="located_in", evidence_count=1, severity=severity)

        elif dtype == "geography":
            if not G.has_node(dep):
                G.add_node(dep, node_type="geography", risk_score=rscore,
                           flagged=flagged, label=dep,
                           top_risk_phrase=phrase, severity=severity, inferred=False)
            G.add_edge(ticker, dep, weight=rscore, relationship="exposed_to",
                       evidence_count=evidence, severity=severity)

        elif dtype == "risk_signal":
            node_id = f"RISK:{dep[:40]}"
            if not G.has_node(node_id):
                G.add_node(node_id, node_type="risk_signal", risk_score=rscore,
                           flagged=flagged, label=dep[:40],
                           top_risk_phrase=phrase, severity=severity, inferred=inferred)
            G.add_edge(ticker, node_id, weight=rscore, relationship="risk_factor",
                       evidence_count=evidence, severity=severity)

    logger.info("Built graph for %s: %d nodes, %d edges",
                ticker, G.number_of_nodes(), G.number_of_edges())
    return G


# ── Ripple simulation ─────────────────────────────────────────────────────────

def simulate_ripple(G: nx.DiGraph, shocked_node: str) -> list[dict]:
    """
    BFS shock propagation: find all nodes that depend (directly or transitively)
    on the shocked node, and score the severity of each impact path.

    This answers: "If Neon Gas supply from Ukraine is disrupted, which companies
    in this graph are downstream — and how hard are they hit?"

    Algorithm:
        1. Reverse the graph (edges now point FROM dependency TO depender)
        2. BFS from shocked_node up to MAX_RIPPLE_DEPTH hops
        3. cumulative_ripple_score = Σ(edge_weights) × DEPTH_DECAY^depth

    Args:
        G: Supply chain DiGraph from build_graph()
        shocked_node: Node name to simulate the shock on (case-insensitive match)

    Returns:
        List of dicts sorted by ripple_score desc:
            {node, ripple_score, depth, path, path_weights}
    """
    # Case-insensitive node lookup
    node_map = {str(n).lower(): n for n in G.nodes()}
    start = node_map.get(shocked_node.lower())
    if start is None:
        # Partial match fallback
        matches = [n for key, n in node_map.items() if shocked_node.lower() in key]
        if not matches:
            logger.warning("Shocked node '%s' not found in graph.", shocked_node)
            return []
        start = matches[0]
        logger.info("Partial match: '%s' -> '%s'", shocked_node, start)

    R = G.reverse(copy=True)  # reverse: dependency → depender
    results = []
    visited = {start}
    queue = deque([(start, 0, [start], [])])  # (node, depth, path, edge_weights)

    while queue:
        node, depth, path, weights = queue.popleft()
        if depth > 0:
            cum_score = sum(weights) * (DEPTH_DECAY ** depth)
            results.append({
                "node": node,
                "ripple_score": round(cum_score, 3),
                "depth": depth,
                "path": " → ".join(str(p) for p in path),
                "path_weights": weights,
            })

        if depth >= MAX_RIPPLE_DEPTH:
            continue

        for neighbor in R.successors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                edge_data = R.edges[node, neighbor]
                w = float(edge_data.get("weight", 1.0))
                queue.append((neighbor, depth + 1, path + [neighbor], weights + [w]))

    results.sort(key=lambda x: x["ripple_score"], reverse=True)
    logger.info("Ripple from '%s': %d nodes affected (max depth=%d)",
                shocked_node, len(results), MAX_RIPPLE_DEPTH)
    return results


def score_ripple_severity(ripple_results: list[dict]) -> dict[str, str]:
    """
    Classify each ripple result as CRITICAL / HIGH / MEDIUM / LOW based on score.

    Args:
        ripple_results: Output of simulate_ripple()

    Returns:
        Dict: {node_name: severity_label}
    """
    labels = {}
    for r in ripple_results:
        score = r["ripple_score"]
        if score >= 7:
            labels[r["node"]] = "CRITICAL"
        elif score >= 4:
            labels[r["node"]] = "HIGH"
        elif score >= 2:
            labels[r["node"]] = "MEDIUM"
        else:
            labels[r["node"]] = "LOW"
    return labels


# ── News overlay + alerting ───────────────────────────────────────────────────

def attach_news(G: nx.DiGraph, news_data: dict[str, list[dict]]) -> nx.DiGraph:
    """
    Attach fetched news headlines to matching graph nodes.

    Args:
        G: Supply chain graph.
        news_data: {entity_name: [headline_dicts]} from sec_client.get_headlines_batch()

    Returns:
        Graph with 'news_headlines' attribute on matching nodes.
    """
    for node in G.nodes():
        node_lower = str(node).lower()
        for entity, headlines in news_data.items():
            if entity.lower() in node_lower or node_lower in entity.lower():
                G.nodes[node]["news_headlines"] = [h["title"] for h in headlines[:3]]
                break
    return G


def monitor_nodes(G: nx.DiGraph, ticker: str) -> list[dict]:
    """
    Scan news for all HIGH/CRITICAL nodes in the graph.
    Fire an alert if any headline matches risk keywords.

    This is the "Voice" of the system — it speaks before the news cycle does.

    Alert format:
        "⚠ [TICKER] Risk: {node} hit by '{headline}' — estimated ripple score: {score}"

    Args:
        G: Supply chain graph (should have risk_score node attributes).
        ticker: Root company ticker.

    Returns:
        List of alert dicts: {ticker, node, headline, ripple_score, alert_text}
    """
    from scripts.sec_client import get_headlines

    alerts = []
    monitored = [
        (n, G.nodes[n])
        for n in G.nodes()
        if float(G.nodes[n].get("risk_score", 0)) >= ALERT_RISK_THRESHOLD
        and G.nodes[n].get("node_type") != "risk_signal"
    ]

    logger.info("Monitoring %d high-risk nodes for %s...", len(monitored), ticker)

    for node_name, attrs in monitored:
        headlines = get_headlines(str(node_name), max_results=5)
        for h in headlines:
            title_lower = h["title"].lower()
            matching_keywords = [kw for kw in RISK_KEYWORDS if kw in title_lower]
            if matching_keywords:
                # Estimate ripple if we shock this node
                ripple = simulate_ripple(G, str(node_name))
                ripple_score = ripple[0]["ripple_score"] if ripple else 0.0
                alert_text = (
                    f"⚠ [{ticker}] Risk: '{node_name}' hit by \"{h['title']}\" "
                    f"— ripple score: {ripple_score:.2f} "
                    f"(matched: {', '.join(matching_keywords[:2])})"
                )
                alerts.append({
                    "ticker": ticker,
                    "node": node_name,
                    "headline": h["title"],
                    "source": h.get("source", ""),
                    "matched_keywords": matching_keywords,
                    "ripple_score": ripple_score,
                    "alert_text": alert_text,
                })
                logger.warning(alert_text)

    logger.info("Generated %d alerts for %s", len(alerts), ticker)
    return alerts


# ── Export + report ───────────────────────────────────────────────────────────

def export_graph(G: nx.DiGraph, ticker: str) -> dict[str, str]:
    """
    Export graph to GEXF (Gephi-compatible) and PNG visualization.

    Args:
        G: Supply chain DiGraph.
        ticker: Ticker symbol for filenames.

    Returns:
        Dict: {format: output_path}
    """
    ticker = ticker.upper()
    os.makedirs(OUTPUTS_GRAPHS_DIR, exist_ok=True)
    outputs = {}

    gexf_path = os.path.join(OUTPUTS_GRAPHS_DIR, f"{ticker}_supply_chain.gexf")
    nx.write_gexf(G, gexf_path)
    outputs["gexf"] = gexf_path
    logger.info("Exported GEXF -> %s", gexf_path)

    png_path = os.path.join(OUTPUTS_GRAPHS_DIR, f"{ticker}_supply_chain.png")
    _render_png(G, ticker, png_path)
    outputs["png"] = png_path

    return outputs


def _render_png(G: nx.DiGraph, ticker: str, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(18, 11))
    ax.set_facecolor("#0d1117")
    fig.patch.set_facecolor("#0d1117")

    try:
        pos = nx.spring_layout(G, seed=42, k=2.8)
    except Exception:
        pos = nx.random_layout(G, seed=42)

    node_colors, node_sizes, node_shapes = [], [], []
    for node in G.nodes():
        attrs = G.nodes[node]
        ntype = attrs.get("node_type", "unknown")
        rscore = float(attrs.get("risk_score", 0.0))
        if ntype == "company":
            node_colors.append("#2196f3")
            node_sizes.append(2200)
        elif ntype in ("supplier", "sub_supplier"):
            node_colors.append(_risk_color(rscore))
            node_sizes.append(900 if ntype == "supplier" else 600)
        elif ntype == "geography":
            node_colors.append(_risk_color(rscore))
            node_sizes.append(800)
        else:
            node_colors.append(_UNKNOWN_COLOR)
            node_sizes.append(350)

    edge_colors = [_risk_color(float(d.get("weight", 1))) for _, _, d in G.edges(data=True)]
    edge_widths = [max(0.5, min(3.5, float(d.get("weight", 1)) / 2.5)) for _, _, d in G.edges(data=True)]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax, alpha=0.92)
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, ax=ax,
                           alpha=0.65, arrows=True, arrowsize=14,
                           connectionstyle="arc3,rad=0.12")

    labels = {n: G.nodes[n].get("label", str(n))[:22] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7,
                            font_color="white", ax=ax, font_weight="bold")

    legend_items = [
        mpatches.Patch(color="#2196f3", label="Target Company"),
        mpatches.Patch(color=_RISK_TIER_COLORS[1], label="Low Risk (tier 1-2)"),
        mpatches.Patch(color=_RISK_TIER_COLORS[3], label="Moderate Risk (tier 3)"),
        mpatches.Patch(color=_RISK_TIER_COLORS[4], label="High Risk (tier 4)"),
        mpatches.Patch(color=_RISK_TIER_COLORS[5], label="Critical Risk (tier 5)"),
        mpatches.Patch(color=_UNKNOWN_COLOR, label="Risk Signal"),
    ]
    ax.legend(handles=legend_items, loc="upper left", framealpha=0.25,
              labelcolor="white", facecolor="#0d1117", edgecolor="#444", fontsize=8)

    ax.set_title(f"{ticker} — Supply Chain Risk Graph  (Mini-Palantir)",
                 color="white", fontsize=13, pad=12)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("Rendered PNG -> %s", out_path)


def generate_risk_report(
    ticker: str,
    dep_df: pd.DataFrame,
    G: nx.DiGraph,
    ripple_results: list[dict] | None = None,
    alerts: list[dict] | None = None,
) -> str:
    """
    Generate a JSON risk summary including top dependencies, ripple paths, and alerts.

    Args:
        ticker: Ticker symbol.
        dep_df: Dependency table.
        G: Supply chain graph.
        ripple_results: Optional output of simulate_ripple() for a shocked node.
        alerts: Optional output of monitor_nodes().

    Returns:
        Path to the saved JSON report.
    """
    ticker = ticker.upper()
    os.makedirs(OUTPUTS_REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUTS_REPORTS_DIR, f"{ticker}_risk_summary.json")

    flagged = dep_df[dep_df["flagged"] == True].to_dict(orient="records") if not dep_df.empty else []
    high_geo = dep_df[
        (dep_df["dependency_type"] == "geography") & (dep_df["risk_score"] >= 6)
    ]["dependency"].tolist() if not dep_df.empty else []
    critical_suppliers = dep_df[
        (dep_df["dependency_type"] == "supplier") & (dep_df["severity"] == "CRITICAL")
    ]["dependency"].tolist() if not dep_df.empty else []

    report = {
        "ticker": ticker,
        "summary": {
            "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges(),
            "total_dependencies": len(dep_df),
            "high_risk_geographies": high_geo,
            "critical_suppliers": critical_suppliers,
        },
        "top_5_risks": [
            {
                "dependency": r.get("dependency", ""),
                "type": r.get("dependency_type", ""),
                "country": r.get("country", ""),
                "risk_score": r.get("risk_score", 0),
                "severity": r.get("severity", ""),
                "top_risk_phrase": r.get("top_risk_phrase", ""),
                "evidence_count": r.get("evidence_count", 0),
                "inferred": r.get("inferred", False),
            }
            for r in flagged[:5]
        ],
        "ripple_simulation": (ripple_results or [])[:10],
        "alerts": (alerts or []),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Saved risk report -> %s", out_path)
    return out_path
