from __future__ import annotations

from collections import Counter

from supply_chain_intel.models import GeographySignal
from supply_chain_intel.utils.text_utils import split_sentences


GEOGRAPHY_ALIASES = {
    "United States": ["united states", "u.s.", "u.s", "usa", "us market"],
    "China": ["china", "prc", "people's republic of china"],
    "Taiwan": ["taiwan"],
    "Japan": ["japan"],
    "South Korea": ["south korea", "korea", "republic of korea"],
    "Germany": ["germany"],
    "Netherlands": ["netherlands", "dutch"],
    "France": ["france"],
    "United Kingdom": ["united kingdom", "u.k.", "uk", "britain"],
    "Ireland": ["ireland"],
    "Italy": ["italy"],
    "Spain": ["spain"],
    "Switzerland": ["switzerland"],
    "Belgium": ["belgium"],
    "Austria": ["austria"],
    "Poland": ["poland"],
    "Czech Republic": ["czech republic", "czechia"],
    "Ukraine": ["ukraine"],
    "Russia": ["russia"],
    "Mexico": ["mexico"],
    "Canada": ["canada"],
    "Brazil": ["brazil"],
    "Vietnam": ["vietnam"],
    "Malaysia": ["malaysia"],
    "Singapore": ["singapore"],
    "Thailand": ["thailand"],
    "Indonesia": ["indonesia"],
    "Philippines": ["philippines"],
    "India": ["india"],
    "Israel": ["israel"],
    "Saudi Arabia": ["saudi arabia"],
    "United Arab Emirates": ["united arab emirates", "uae"],
    "Australia": ["australia"],
}


class GeographyAnalyst:
    def analyze(self, item_1_text: str, item_1a_text: str) -> list[GeographySignal]:
        counter: Counter[str] = Counter()
        contexts: dict[str, str] = {}
        for sentence in split_sentences(f"{item_1_text} {item_1a_text}"):
            lowered = sentence.lower()
            for geography, aliases in GEOGRAPHY_ALIASES.items():
                if any(alias in lowered for alias in aliases):
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
