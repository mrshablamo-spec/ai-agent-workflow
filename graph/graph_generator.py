"""
Phase 5: Graph Generator
Builds a directed NetworkX graph from the dependency table and exports it.

Graph schema:
  Nodes: target company, supplier hints, countries
  Edges: target -> supplier (weight=risk_score), supplier -> country (weight=geo_risk)
  Node attributes: type (company/supplier/geography/risk_signal), risk_score, flagged
  Edge attributes: weight, relationship

Exports:
  - outputs/graphs/{ticker}_supply_chain.gexf  (for Gephi)
  - outputs/graphs/{ticker}_supply_chain.png   (quick visual)
"""

import logging
import os
import json
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — safe for headless environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from config import (
    GEO_RISK_TIERS,
    OUTPUTS_GRAPHS_DIR,
    OUTPUTS_REPORTS_DIR,
)

logger = logging.getLogger(__name__)

# Risk tier -> color mapping for visualization
_RISK_COLORS = {
    1: "#4caf50",   # green
    2: "#8bc34a",   # light green
    3: "#ffc107",   # amber
    4: "#ff5722",   # deep orange
    5: "#f44336",   # red
}
_DEFAULT_COLOR = "#9e9e9e"  # grey for unknown


def _risk_color(risk_score: float) -> str:
    """Map a normalized risk_score (0–10) to a display color."""
    if risk_score < 2:
        return _RISK_COLORS[1]
    elif risk_score < 4:
        return _RISK_COLORS[2]
    elif risk_score < 6:
        return _RISK_COLORS[3]
    elif risk_score < 8:
        return _RISK_COLORS[4]
    else:
        return _RISK_COLORS[5]


def build_graph(ticker: str, dep_df: pd.DataFrame) -> nx.DiGraph:
    """
    Build a directed supply chain risk graph from the dependency table.

    Args:
        ticker: Target company ticker symbol.
        dep_df: Dependency table from dependency_mapper.build_dependency_table()

    Returns:
        networkx.DiGraph representing the supply chain.
    """
    G = nx.DiGraph()
    ticker = ticker.upper()

    # Add the root company node
    G.add_node(ticker, node_type="company", risk_score=0.0, flagged=False, label=ticker)

    for _, row in dep_df.iterrows():
        dep_name = str(row["dependency"])
        dep_type = str(row["dependency_type"])
        risk_score = float(row.get("risk_score", 0.0))
        flagged = bool(row.get("flagged", False))
        country = str(row.get("country", ""))
        top_phrase = str(row.get("top_risk_phrase", ""))
        evidence = int(row.get("evidence_count", 1))

        if dep_type == "supplier":
            # Add supplier node
            if not G.has_node(dep_name):
                G.add_node(
                    dep_name,
                    node_type="supplier",
                    risk_score=risk_score,
                    flagged=flagged,
                    label=dep_name[:30],
                    top_risk_phrase=top_phrase,
                )
            # Edge: company -> supplier
            G.add_edge(
                ticker, dep_name,
                weight=risk_score,
                relationship="depends_on",
                evidence_count=evidence,
            )
            # Edge: supplier -> country (if known)
            if country and country != "unknown":
                if not G.has_node(country):
                    geo_risk = GEO_RISK_TIERS.get(country.lower(), 2)
                    G.add_node(
                        country,
                        node_type="geography",
                        risk_score=float(geo_risk * 2),  # scale to 0–10
                        flagged=geo_risk >= 4,
                        label=country,
                    )
                G.add_edge(
                    dep_name, country,
                    weight=float(GEO_RISK_TIERS.get(country.lower(), 2)),
                    relationship="located_in",
                    evidence_count=1,
                )

        elif dep_type == "geography":
            if not G.has_node(dep_name):
                G.add_node(
                    dep_name,
                    node_type="geography",
                    risk_score=risk_score,
                    flagged=flagged,
                    label=dep_name,
                    top_risk_phrase=top_phrase,
                )
            # Edge: company -> geography (direct exposure)
            G.add_edge(
                ticker, dep_name,
                weight=risk_score,
                relationship="exposed_to",
                evidence_count=evidence,
            )

        elif dep_type == "risk_signal":
            node_id = f"RISK:{dep_name[:40]}"
            if not G.has_node(node_id):
                G.add_node(
                    node_id,
                    node_type="risk_signal",
                    risk_score=risk_score,
                    flagged=flagged,
                    label=dep_name[:40],
                    top_risk_phrase=top_phrase,
                )
            G.add_edge(
                ticker, node_id,
                weight=risk_score,
                relationship="risk_factor",
                evidence_count=evidence,
            )

    logger.info(
        "Built graph for %s: %d nodes, %d edges",
        ticker, G.number_of_nodes(), G.number_of_edges(),
    )
    return G


def attach_news(G: nx.DiGraph, news_data: dict[str, list[dict]]) -> nx.DiGraph:
    """
    Attach news headlines to matching graph nodes as node attributes.

    Args:
        G: Supply chain graph.
        news_data: Dict of {entity_name: [headline_dicts]} from news_scraper.

    Returns:
        Graph with news_headlines attribute added to matching nodes.
    """
    for node in G.nodes():
        node_lower = str(node).lower()
        for entity, headlines in news_data.items():
            if entity.lower() in node_lower or node_lower in entity.lower():
                G.nodes[node]["news_headlines"] = [h["title"] for h in headlines[:3]]
                break
    return G


def export_graph(G: nx.DiGraph, ticker: str) -> dict[str, str]:
    """
    Export the graph to GEXF (Gephi-compatible) and render a PNG visualization.

    Args:
        G: Supply chain DiGraph.
        ticker: Ticker symbol (used in output filenames).

    Returns:
        Dict of {format: output_path} for all exported files.
    """
    ticker = ticker.upper()
    os.makedirs(OUTPUTS_GRAPHS_DIR, exist_ok=True)
    outputs = {}

    # ── GEXF export ──────────────────────────────────────────────────────
    gexf_path = os.path.join(OUTPUTS_GRAPHS_DIR, f"{ticker}_supply_chain.gexf")
    nx.write_gexf(G, gexf_path)
    outputs["gexf"] = gexf_path
    logger.info("Exported GEXF -> %s", gexf_path)

    # ── PNG visualization ─────────────────────────────────────────────────
    png_path = os.path.join(OUTPUTS_GRAPHS_DIR, f"{ticker}_supply_chain.png")
    _render_png(G, ticker, png_path)
    outputs["png"] = png_path

    return outputs


def _render_png(G: nx.DiGraph, ticker: str, out_path: str) -> None:
    """Render the graph as a PNG using matplotlib."""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    # Layout — spring layout works well for supply chain graphs
    try:
        pos = nx.spring_layout(G, seed=42, k=2.5)
    except Exception:
        pos = nx.random_layout(G, seed=42)

    # Node colors and sizes by type
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        attrs = G.nodes[node]
        ntype = attrs.get("node_type", "unknown")
        rscore = attrs.get("risk_score", 0.0)
        color = _risk_color(rscore)
        if ntype == "company":
            node_sizes.append(1800)
            node_colors.append("#2196f3")  # blue for the root company
        elif ntype == "geography":
            node_sizes.append(900)
            node_colors.append(color)
        elif ntype == "supplier":
            node_sizes.append(700)
            node_colors.append(color)
        else:
            node_sizes.append(400)
            node_colors.append(_DEFAULT_COLOR)

    # Edge colors by weight
    edge_colors = []
    edge_widths = []
    for u, v, data in G.edges(data=True):
        w = data.get("weight", 1.0)
        edge_colors.append(_risk_color(w))
        edge_widths.append(max(0.5, min(3.0, w / 3.0)))

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax, alpha=0.9)
    nx.draw_networkx_edges(
        G, pos, edge_color=edge_colors, width=edge_widths,
        ax=ax, alpha=0.7, arrows=True, arrowsize=15,
        connectionstyle="arc3,rad=0.1",
    )

    # Labels — truncate long names
    labels = {n: G.nodes[n].get("label", str(n))[:20] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, font_color="white", ax=ax)

    # Legend
    legend_patches = [
        mpatches.Patch(color="#2196f3", label="Target Company"),
        mpatches.Patch(color=_RISK_COLORS[1], label="Low Risk"),
        mpatches.Patch(color=_RISK_COLORS[3], label="Moderate Risk"),
        mpatches.Patch(color=_RISK_COLORS[5], label="High Risk"),
        mpatches.Patch(color=_DEFAULT_COLOR, label="Risk Signal"),
    ]
    ax.legend(handles=legend_patches, loc="upper left", framealpha=0.3, labelcolor="white",
              facecolor="#1a1a2e", edgecolor="grey", fontsize=8)

    ax.set_title(
        f"{ticker} — Supply Chain Risk Graph",
        color="white", fontsize=14, pad=15,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("Rendered PNG -> %s", out_path)


def generate_risk_report(ticker: str, dep_df: pd.DataFrame, G: nx.DiGraph) -> str:
    """
    Generate a JSON risk summary report.

    Args:
        ticker: Ticker symbol.
        dep_df: Dependency table.
        G: Supply chain graph.

    Returns:
        File path of the saved JSON report.
    """
    ticker = ticker.upper()
    os.makedirs(OUTPUTS_REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUTS_REPORTS_DIR, f"{ticker}_risk_summary.json")

    top_risks = dep_df[dep_df["flagged"] == True].to_dict(orient="records") if not dep_df.empty else []

    report = {
        "ticker": ticker,
        "graph_stats": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
        },
        "top_5_risks": [
            {
                "dependency": r.get("dependency", ""),
                "type": r.get("dependency_type", ""),
                "country": r.get("country", ""),
                "risk_score": r.get("risk_score", 0),
                "top_risk_phrase": r.get("top_risk_phrase", ""),
                "evidence_count": r.get("evidence_count", 0),
            }
            for r in top_risks[:5]
        ],
        "total_dependencies": len(dep_df),
        "high_risk_geographies": dep_df[
            (dep_df["dependency_type"] == "geography") & (dep_df["risk_score"] >= 6)
        ]["dependency"].tolist() if not dep_df.empty else [],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Saved risk report -> %s", out_path)
    return out_path
