from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx
import pandas as pd

from supply_chain_intel.graph.graph_exporter import GraphExporter
from supply_chain_intel.pipelines.workflow import run_supply_chain_workflow


def export_artifacts(payload: dict, export_dir: Path) -> dict[str, str]:
    export_dir.mkdir(parents=True, exist_ok=True)
    exporter = GraphExporter()

    payload_path = exporter.export_json(payload, export_dir / "analysis.json")
    preview_frame = pd.DataFrame(payload.get("graph_preview", []))
    preview_path = exporter.export_csv(preview_frame, export_dir / "graph_edges.csv")
    graph = nx.node_link_graph(payload.get("graph", {}))
    gexf_path = exporter.export_gexf(graph, export_dir / "graph.gexf")

    return {
        "analysis_json": str(payload_path),
        "graph_edges_csv": str(preview_path),
        "graph_gexf": str(gexf_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Mini-Palantir supply-chain workflow.")
    parser.add_argument("ticker", help="Ticker to analyze, e.g. NVDA")
    parser.add_argument("--no-news", action="store_true", help="Skip Google News enrichment")
    parser.add_argument("--export-dir", help="Optional directory to write analysis.json, graph_edges.csv, and graph.gexf")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON instead of pretty formatted output")
    args = parser.parse_args()

    payload = run_supply_chain_workflow(args.ticker, include_news=not args.no_news)
    if args.export_dir:
        payload["exports"] = export_artifacts(payload, Path(args.export_dir))

    if args.compact:
        print(json.dumps(payload))
        return

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
