from __future__ import annotations

from supply_chain_intel.models import RiskSignal
from supply_chain_intel.utils.text_utils import split_sentences


CATEGORY_KEYWORDS = {
    "geopolitical": ("war", "sanction", "geopolitical", "trade restriction", "export control"),
    "supplier": ("supplier", "sole-source", "single-source", "third-party", "outsource"),
    "manufacturing": ("factory", "manufacturing", "capacity", "yield", "production"),
    "logistics": ("shipping", "logistics", "transportation", "freight", "port"),
    "commodity": ("neon", "rare earth", "energy", "gas", "raw material"),
}


class RiskAnalyst:
    def analyze(self, item_1a_text: str) -> list[RiskSignal]:
        signals: list[RiskSignal] = []
        for sentence in split_sentences(item_1a_text):
            lowered = sentence.lower()
            for category, keywords in CATEGORY_KEYWORDS.items():
                if any(keyword in lowered for keyword in keywords):
                    severity = 0.45 + (0.1 * sum(keyword in lowered for keyword in keywords))
                    signals.append(
                        RiskSignal(
                            title=sentence[:120],
                            category=category,
                            severity=min(severity, 0.95),
                            evidence=sentence,
                        )
                    )
                    break
        return signals[:20]
