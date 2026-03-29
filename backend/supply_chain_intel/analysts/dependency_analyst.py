from __future__ import annotations

import pandas as pd

from supply_chain_intel.models import GeographySignal, NewsSignal, RiskSignal, SupplierSignal


class DependencyAnalyst:
    def build_dependency_table(
        self,
        company_name: str,
        supplier_signals: list[SupplierSignal],
        geographies: list[GeographySignal],
        risks: list[RiskSignal],
        news_signals: list[NewsSignal],
    ) -> pd.DataFrame:
        rows: list[dict] = []
        geography_lookup = {signal.geography.lower(): signal for signal in geographies}
        relevant_risks = risks[:5]
        for supplier in supplier_signals:
            linked_geographies = [
                geography.to_dict()
                for key, geography in geography_lookup.items()
                if key in supplier.evidence.lower()
            ]
            linked_news = [
                article.to_dict()
                for article in news_signals
                if supplier.supplier in article.matched_entities
            ]
            rows.append(
                {
                    "company": company_name,
                    "supplier": supplier.supplier,
                    "relationship": supplier.relationship,
                    "confidence": supplier.confidence,
                    "evidence": supplier.evidence,
                    "linked_geographies": linked_geographies,
                    "top_risks": [risk.to_dict() for risk in relevant_risks],
                    "linked_news": linked_news,
                }
            )
        return pd.DataFrame(rows)
