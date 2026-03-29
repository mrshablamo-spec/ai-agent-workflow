from __future__ import annotations

from bs4 import BeautifulSoup

from supply_chain_intel.utils.text_utils import normalize_whitespace


class HTMLCleaner:
    def to_text(self, raw_html: str) -> str:
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(" ")
        return normalize_whitespace(text)
