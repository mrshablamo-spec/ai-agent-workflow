from __future__ import annotations

import re

from supply_chain_intel.parsers.html_cleaner import HTMLCleaner


ITEM_PATTERNS = {
    "item_1": re.compile(r"item\s+1\.?\s+business", re.IGNORECASE),
    "item_1a": re.compile(r"item\s+1a\.?\s+risk\s+factors", re.IGNORECASE),
    "item_1b": re.compile(r"item\s+1b\.?", re.IGNORECASE),
    "item_2": re.compile(r"item\s+2\.?", re.IGNORECASE),
}


class TenKSectionParser:
    def __init__(self) -> None:
        self.cleaner = HTMLCleaner()

    def extract_sections(self, raw_html: str) -> dict[str, str]:
        text = self.cleaner.to_text(raw_html)
        item_1_start = self._search(ITEM_PATTERNS["item_1"], text)
        item_1a_start = self._search(ITEM_PATTERNS["item_1a"], text)
        item_1b_start = self._search(ITEM_PATTERNS["item_1b"], text)
        item_2_start = self._search(ITEM_PATTERNS["item_2"], text)

        if item_1_start is None or item_1a_start is None:
            raise ValueError("Unable to reliably locate Item 1 and Item 1A in the filing.")

        item_1_end = item_1a_start
        item_1a_end = item_1b_start or item_2_start or len(text)

        return {
            "item_1": text[item_1_start:item_1_end].strip(),
            "item_1a": text[item_1a_start:item_1a_end].strip(),
        }

    @staticmethod
    def _search(pattern: re.Pattern[str], text: str) -> int | None:
        match = pattern.search(text)
        return match.start() if match else None
