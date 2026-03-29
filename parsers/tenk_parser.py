"""
Phase 2: 10-K Parser
Extracts Item 1 (Business) and Item 1A (Risk Factors) sections from
raw 10-K HTML files downloaded by the SEC scraper.

10-K filings are notoriously inconsistent in formatting across filers and
years. This parser uses a layered approach:
  1. Try HTML heading tags (<b>, <h1>-<h4>) with 'Item 1' text
  2. Fall back to regex over plain text
  3. Trim to next section boundary to avoid over-capturing
"""

import logging
import os
import re
from bs4 import BeautifulSoup

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR

logger = logging.getLogger(__name__)

# Regex patterns for section headers (case-insensitive, flexible whitespace)
_ITEM1_PATTERN = re.compile(
    r"item\s+1\s*[\.\-\:—]?\s*(business|description\s+of\s+business)?",
    re.IGNORECASE,
)
_ITEM1A_PATTERN = re.compile(
    r"item\s+1a\s*[\.\-\:—]?\s*(risk\s+factors)?",
    re.IGNORECASE,
)
_ITEM1B_PATTERN = re.compile(
    r"item\s+1b\s*[\.\-\:—]?\s*",
    re.IGNORECASE,
)
_ITEM2_PATTERN = re.compile(
    r"item\s+2\s*[\.\-\:—]?\s*",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove excessive blank lines."""
    # Collapse multiple whitespace to single space, preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_by_headings(soup: BeautifulSoup) -> dict[str, str]:
    """
    Attempt to extract sections by locating bold/heading tags whose text
    matches an Item pattern. Returns dict with any found sections.
    """
    sections = {}

    # Collect all potential heading elements
    heading_candidates = soup.find_all(["b", "strong", "h1", "h2", "h3", "h4", "p"])

    markers = []  # List of (pattern_name, tag_element)
    for tag in heading_candidates:
        text = tag.get_text(" ", strip=True)
        if _ITEM1A_PATTERN.match(text) and len(text) < 80:
            markers.append(("item1a", tag))
        elif _ITEM1_PATTERN.match(text) and len(text) < 80 and "item 1a" not in text.lower():
            markers.append(("item1", tag))
        elif _ITEM1B_PATTERN.match(text) and len(text) < 80:
            markers.append(("item1b", tag))
        elif _ITEM2_PATTERN.match(text) and len(text) < 80:
            markers.append(("item2", tag))

    if not markers:
        return sections

    # For each item1 marker, collect text until item1a or item2
    for i, (name, tag) in enumerate(markers):
        if name not in ("item1", "item1a"):
            continue

        # Determine end marker
        end_names = {
            "item1": ("item1a", "item1b", "item2"),
            "item1a": ("item1b", "item2"),
        }
        end_tags = [
            markers[j][1]
            for j in range(i + 1, len(markers))
            if markers[j][0] in end_names.get(name, ())
        ]
        end_tag = end_tags[0] if end_tags else None

        # Gather sibling/following text
        text_parts = []
        current = tag.find_next_sibling() or tag.parent.find_next_sibling()
        while current:
            if end_tag and current == end_tag:
                break
            if end_tag and current.find(end_tag):
                break
            text_parts.append(current.get_text(" ", strip=True))
            current = current.find_next_sibling()
            if current is None and tag.parent:
                current = tag.parent.find_next_sibling()
                tag = tag.parent  # move parent context up once

        combined = " ".join(text_parts)
        if len(combined) > 200:  # sanity check — real sections are substantial
            sections[name] = _clean_text(combined)

    return sections


def _extract_by_regex(raw_text: str) -> dict[str, str]:
    """
    Fallback: split the full plain text by Item header patterns and
    extract the relevant slices.
    """
    sections = {}

    # Find all item boundary positions
    boundaries = []
    for pattern, name in [
        (_ITEM1_PATTERN, "item1"),
        (_ITEM1A_PATTERN, "item1a"),
        (_ITEM1B_PATTERN, "item1b"),
        (_ITEM2_PATTERN, "item2"),
    ]:
        for m in pattern.finditer(raw_text):
            boundaries.append((m.start(), name, m.end()))

    if not boundaries:
        return sections

    # Sort by position
    boundaries.sort(key=lambda x: x[0])

    # Extract slices between boundaries
    for i, (start, name, end) in enumerate(boundaries):
        if name not in ("item1", "item1a"):
            continue
        next_start = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(raw_text)
        content = raw_text[end:next_start]
        if len(content) > 200:
            sections[name] = _clean_text(content)

    return sections


def extract_sections(ticker: str) -> dict[str, str]:
    """
    Load the cached 10-K HTML for a ticker and extract Item 1 and Item 1A.

    Args:
        ticker: Stock ticker symbol (case-insensitive).

    Returns:
        Dict with keys 'item1' and/or 'item1a' mapped to extracted text.
        Missing sections will be absent from the dict.

    Raises:
        FileNotFoundError: If the raw 10-K has not been downloaded yet.
    """
    ticker = ticker.upper()
    raw_path = os.path.join(DATA_RAW_DIR, ticker, "10k_latest.html")

    if not os.path.exists(raw_path):
        raise FileNotFoundError(
            f"No cached 10-K found for {ticker} at {raw_path}. "
            "Run sec_scraper.download_10k() first."
        )

    logger.info("Parsing 10-K for %s from %s", ticker, raw_path)

    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    # Remove script/style noise
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    # Attempt heading-based extraction first
    sections = _extract_by_headings(soup)

    # Fill any missing sections with regex fallback
    missing = [k for k in ("item1", "item1a") if k not in sections]
    if missing:
        logger.debug("Heading extraction missed %s — trying regex fallback.", missing)
        plain_text = soup.get_text("\n")
        fallback = _extract_by_regex(plain_text)
        for key in missing:
            if key in fallback:
                sections[key] = fallback[key]

    found = list(sections.keys())
    logger.info("Extracted sections for %s: %s", ticker, found)

    if not sections:
        logger.warning(
            "Could not extract Item 1 or Item 1A from %s. "
            "The filing may use an unusual format.",
            ticker,
        )

    # Persist extracted text to processed dir
    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    os.makedirs(out_dir, exist_ok=True)
    for section_name, text in sections.items():
        out_path = os.path.join(out_dir, f"{section_name}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info("Saved %s -> %s (%d chars)", section_name, out_path, len(text))

    return sections
