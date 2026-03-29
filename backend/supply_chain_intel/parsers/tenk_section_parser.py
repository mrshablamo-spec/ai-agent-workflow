from __future__ import annotations

import re
from dataclasses import dataclass

from supply_chain_intel.parsers.html_cleaner import HTMLCleaner


ITEM_PATTERNS = {
    "item_1": re.compile(r"item\s+1\.?\s+business", re.IGNORECASE),
    "item_1a": re.compile(r"item\s+1a\.?\s+risk\s+factors", re.IGNORECASE),
    "item_1b": re.compile(r"item\s+1b\.?", re.IGNORECASE),
    "item_2": re.compile(r"item\s+2\.?", re.IGNORECASE),
}

MIN_SECTION_LENGTH = 500


@dataclass
class SectionCandidate:
    item_1_start: int
    item_1a_start: int
    item_1a_end: int

    @property
    def item_1_length(self) -> int:
        return self.item_1a_start - self.item_1_start

    @property
    def item_1a_length(self) -> int:
        return self.item_1a_end - self.item_1a_start


class TenKSectionParser:
    def __init__(self) -> None:
        self.cleaner = HTMLCleaner()

    def extract_sections(self, raw_html: str) -> dict[str, str]:
        text = self.cleaner.to_text(raw_html)
        item_1_positions = self._positions(ITEM_PATTERNS["item_1"], text)
        item_1a_positions = self._positions(ITEM_PATTERNS["item_1a"], text)
        item_1b_positions = self._positions(ITEM_PATTERNS["item_1b"], text)
        item_2_positions = self._positions(ITEM_PATTERNS["item_2"], text)

        candidate = self._best_candidate(text, item_1_positions, item_1a_positions, item_1b_positions, item_2_positions)
        if candidate is None:
            raise ValueError("Unable to reliably locate Item 1 and Item 1A in the filing.")

        return {
            "item_1": text[candidate.item_1_start:candidate.item_1a_start].strip(),
            "item_1a": text[candidate.item_1a_start:candidate.item_1a_end].strip(),
        }

    def _best_candidate(
        self,
        text: str,
        item_1_positions: list[int],
        item_1a_positions: list[int],
        item_1b_positions: list[int],
        item_2_positions: list[int],
    ) -> SectionCandidate | None:
        candidates: list[SectionCandidate] = []
        boundaries = sorted(item_1b_positions + item_2_positions)

        for item_1_start in item_1_positions:
            for item_1a_start in item_1a_positions:
                if item_1a_start <= item_1_start:
                    continue
                item_1a_end = next((point for point in boundaries if point > item_1a_start), len(text))
                candidate = SectionCandidate(item_1_start=item_1_start, item_1a_start=item_1a_start, item_1a_end=item_1a_end)
                if candidate.item_1_length <= 0 or candidate.item_1a_length <= 0:
                    continue
                candidates.append(candidate)

        if not candidates:
            return None

        long_enough = [
            candidate
            for candidate in candidates
            if candidate.item_1_length >= MIN_SECTION_LENGTH and candidate.item_1a_length >= MIN_SECTION_LENGTH
        ]
        ranked = long_enough or candidates
        return max(ranked, key=lambda candidate: (candidate.item_1_length + candidate.item_1a_length, candidate.item_1a_start))

    @staticmethod
    def _positions(pattern: re.Pattern[str], text: str) -> list[int]:
        return [match.start() for match in pattern.finditer(text)]
