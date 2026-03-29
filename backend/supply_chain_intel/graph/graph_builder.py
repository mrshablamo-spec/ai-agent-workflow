from __future__ import annotations

import networkx as nx
import pandas as pd

from supply_chain_intel.models import GeographySignal, NewsSignal, RiskSignal, SupplierSignal


class GraphBuilder:
    def build(
        self,
        company_name: str,
        supplier_signals: list[SupplierSignal],
        geographies: list[GeographySignal],
        risks: list[RiskSignal],
        news_signals: list[NewsSignal],
    ) -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_node(company_name, node_type="company")

        for supplier in supplier_signals:
            graph.add_node(supplier.supplier, node_type="supplier")
            graph.add_edge(company_name, supplier.supplier, relation="depends_on", confidence=supplier.confidence)

        for geography in geographies:
            graph.add_node(geography.geography, node_type="geography")
            graph.add_edge(company_name, geography.geography, relation="exposed_to", risk_score=geography.risk_score)

        for risk in risks:
            risk_id = f"risk::{risk.category}::{risk.title[:50]}"
            graph.add_node(risk_id, node_type="risk", category=risk.category, label=risk.title)
            graph.add_edge(company_name, risk_id, relation="faces_risk", severity=risk.severity)

        for article in news_signals:
            article_id = f"news::{article.title[:50]}"
            graph.add_node(article_id, node_type="news", label=article.title, link=article.link)
            for entity in article.matched_entities:
                if graph.has_node(entity):
                    graph.add_edge(article_id, entity, relation="impacts")

        return graph

    def to_node_link(self, graph: nx.DiGraph) -> dict:
        return nx.node_link_data(graph)

    def dataframe_preview(self, graph: nx.DiGraph) -> pd.DataFrame:
        rows = []
        for source, target, attrs in graph.edges(data=True):
            rows.append({"source": source, "target": target, **attrs})
        return pd.DataFrame(rows)
