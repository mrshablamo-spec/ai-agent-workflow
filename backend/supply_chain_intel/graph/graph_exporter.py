from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pandas as pd


class GraphExporter:
    def export_json(self, payload: dict, destination: Path) -> Path:
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

    def export_csv(self, dataframe: pd.DataFrame, destination: Path) -> Path:
        dataframe.to_csv(destination, index=False)
        return destination

    def export_gexf(self, graph: nx.DiGraph, destination: Path) -> Path:
        nx.write_gexf(graph, destination)
        return destination
