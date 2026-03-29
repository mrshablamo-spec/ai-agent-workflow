from __future__ import annotations

import re

from supply_chain_intel.models import SupplierSignal
from supply_chain_intel.utils.text_utils import split_sentences, unique_preserve_order


DEPENDENCY_KEYWORDS = (
    "sole-source",
    "single-source",
    "limited number of suppliers",
    "depend on",
    "depends on",
    "rely on",
    "relies on",
    "supplied by",
    "source from",
    "strategic supplier",
    "manufacturing partner",
)

SUPPLIER_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9&.,-]+(?:\s+[A-Z][A-Za-z0-9&.,-]+){0,4})\b")
STOPWORDS = {
    "we",
    "our",
    "us",
    "company",
    "business",
    "item",
    "risk",
    "factors",
    "management",
    "board",
    "inc",
    "corp",
}


class EntityExtractor:
    def extract_supplier_signals(self, text: str, company_name: str) -> list[SupplierSignal]:
        signals: list[SupplierSignal] = []
        for sentence in split_sentences(text):
            lowered = sentence.lower()
            if not any(keyword in lowered for keyword in DEPENDENCY_KEYWORDS):
                continue
            candidates = [candidate.strip(" ,.;:") for candidate in SUPPLIER_PATTERN.findall(sentence)]
            filtered_candidates = []
            for candidate in candidates:
                normalized = candidate.lower().strip()
                if normalized == company_name.lower():
                    continue
                if normalized in STOPWORDS:
                    continue
                if len(candidate) <= 2:
                    continue
                filtered_candidates.append(candidate)
            for candidate in unique_preserve_order(filtered_candidates[:3]):
                confidence = 0.55
                if "sole-source" in lowered or "single-source" in lowered:
                    confidence = 0.9
                elif "depend" in lowered or "rely" in lowered:
                    confidence = 0.75
                signals.append(
                    SupplierSignal(
                        supplier=candidate,
                        relationship="dependency_signal",
                        evidence=sentence,
                        confidence=confidence,
                    )
                )
        return self._dedupe(signals)

    @staticmethod
    def _dedupe(signals: list[SupplierSignal]) -> list[SupplierSignal]:
        deduped: dict[str, SupplierSignal] = {}
        for signal in signals:
            key = signal.supplier.lower()
            if key not in deduped or signal.confidence > deduped[key].confidence:
                deduped[key] = signal
        return list(deduped.values())
