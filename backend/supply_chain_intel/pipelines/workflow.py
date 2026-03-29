from __future__ import annotations

from pathlib import Path

import yfinance as yf

from supply_chain_intel.analysts.dependency_analyst import DependencyAnalyst
from supply_chain_intel.analysts.geography_analyst import GeographyAnalyst
from supply_chain_intel.analysts.risk_analyst import RiskAnalyst
from supply_chain_intel.graph.graph_builder import GraphBuilder
from supply_chain_intel.models import FilingMetadata
from supply_chain_intel.parsers.entity_extractor import EntityExtractor
from supply_chain_intel.parsers.tenk_section_parser import TenKSectionParser
from supply_chain_intel.scrapers.filing_index import FilingIndex
from supply_chain_intel.scrapers.news_collector import NewsCollector
from supply_chain_intel.scrapers.sec_client import SECClient


def _company_profile(ticker: str) -> dict:
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.fast_info if hasattr(ticker_obj, "fast_info") else {}
    return {
        "ticker": ticker.upper(),
        "last_price": info.get("lastPrice") if hasattr(info, "get") else None,
        "currency": info.get("currency") if hasattr(info, "get") else None,
    }


def run_supply_chain_workflow(ticker: str, include_news: bool = True) -> dict:
    client = SECClient()
    filing_index = FilingIndex(client)
    parser = TenKSectionParser()
    entity_extractor = EntityExtractor()
    geography_analyst = GeographyAnalyst()
    risk_analyst = RiskAnalyst()
    dependency_analyst = DependencyAnalyst()
    graph_builder = GraphBuilder()
    news_collector = NewsCollector()

    filing: FilingMetadata = filing_index.latest_10k(ticker)
    filing_path = client.download_filing(filing.filing_url, f"{filing.ticker.lower()}_{filing.accession_number}.html")
    sections = parser.extract_sections(filing_path.read_text(encoding="utf-8"))

    supplier_signals = entity_extractor.extract_supplier_signals(sections["item_1"], filing.company_name)
    geographies = geography_analyst.analyze(sections["item_1"], sections["item_1a"])
    risks = risk_analyst.analyze(sections["item_1a"])
    news_signals = news_collector.collect(filing.company_name, [signal.supplier for signal in supplier_signals]) if include_news else []

    dependency_table = dependency_analyst.build_dependency_table(
        filing.company_name,
        supplier_signals,
        geographies,
        risks,
        news_signals,
    )
    graph = graph_builder.build(filing.company_name, supplier_signals, geographies, risks, news_signals)

    return {
        "company": _company_profile(filing.ticker) | {"name": filing.company_name},
        "filing": filing.to_dict() | {"cache_path": str(filing_path)},
        "sections": {
            "item_1_excerpt": sections["item_1"][:1600],
            "item_1a_excerpt": sections["item_1a"][:1600],
        },
        "supplier_signals": [signal.to_dict() for signal in supplier_signals],
        "geography_signals": [signal.to_dict() for signal in geographies],
        "risk_signals": [signal.to_dict() for signal in risks],
        "news_signals": [signal.to_dict() for signal in news_signals],
        "dependency_table": dependency_table.to_dict(orient="records"),
        "graph": graph_builder.to_node_link(graph),
        "graph_preview": graph_builder.dataframe_preview(graph).to_dict(orient="records"),
        "notes": [
            "Signals are heuristic and intended for pre-news triage, not final investment decisions.",
            "SEC access follows a descriptive User-Agent, local caching, and throttle-aware retrieval.",
        ],
    }
