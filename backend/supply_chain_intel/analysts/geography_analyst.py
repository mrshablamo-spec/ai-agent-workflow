from __future__ import annotations

from collections import Counter

from supply_chain_intel.models import GeographySignal
from supply_chain_intel.utils.text_utils import split_sentences


GEOGRAPHIES = [
    "China",
    "Taiwan",
    "Japan",
    "South Korea",
    "Germany",
    "Ukraine",
    "Russia",
    "United States",
    "Mexico",
    "Vietnam",
    "Malaysia",
    "Singapore",
    "Israel",
    "India",
]


class GeographyAnalyst:
    def analyze(self, item_1_text: str, item_1a_text: str) -> list[GeographySignal]:
        counter: Counter[str] = Counter()
        contexts: dict[str, str] = {}
        for sentence in split_sentences(f"{item_1_text} {item_1a_text}"):
            for geography in GEOGRAPHIES:
                if geography.lower() in sentence.lower():
                    counter[geography] += 1
                    contexts.setdefault(geography, sentence)
        return [
            GeographySignal(
                geography=geography,
                context=contexts[geography],
                mention_count=count,
                risk_score=min(1.0, 0.2 + (count * 0.15)),
            )
            for geography, count in counter.most_common()
        ]
