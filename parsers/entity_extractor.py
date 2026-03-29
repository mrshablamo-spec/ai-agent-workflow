"""
Phase 3: Entity Extractor
Extracts supplier hints, geographic mentions, and risk signals from
parsed 10-K section text.

No paid NLP API required — uses keyword matching + sentence windowing.
Output is a pandas DataFrame saved to data/processed/{ticker}/entities.csv.
"""

import logging
import os
import re
import pandas as pd

from config import (
    SUPPLIER_KEYWORDS,
    RISK_KEYWORDS,
    GEO_RISK_TIERS,
    CONTEXT_WINDOW,
    DATA_PROCESSED_DIR,
)

logger = logging.getLogger(__name__)

# Pre-build geo lookup as lowercase set for fast matching
_GEO_NAMES = set(GEO_RISK_TIERS.keys())

# Additional common region/continent terms to capture
_EXTRA_REGIONS = {
    "asia", "asia-pacific", "apac", "europe", "emea", "latin america",
    "middle east", "africa", "north america", "southeast asia",
    "eastern europe", "western europe", "sub-saharan africa",
}

_ALL_GEO = _GEO_NAMES | _EXTRA_REGIONS


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter — splits on '. ', '.\n', '! ', '? '."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _get_context(sentences: list[str], idx: int, window: int = CONTEXT_WINDOW) -> str:
    """Return sentence at idx plus ±window surrounding sentences joined."""
    start = max(0, idx - window)
    end = min(len(sentences), idx + window + 1)
    return " ".join(sentences[start:end])


def _keyword_hits(sentence: str, keywords: list[str]) -> list[str]:
    """Return all keywords found (case-insensitive) in a sentence."""
    sentence_lower = sentence.lower()
    return [kw for kw in keywords if kw in sentence_lower]


def _geo_hits(sentence: str) -> list[str]:
    """Return all geographic names found in a sentence."""
    sentence_lower = sentence.lower()
    found = []
    for geo in _ALL_GEO:
        # Word-boundary check to avoid partial matches (e.g. "Iran" in "Ukraine")
        pattern = r"\b" + re.escape(geo) + r"\b"
        if re.search(pattern, sentence_lower):
            found.append(geo)
    return found


def extract_entities(ticker: str, sections: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Extract supplier hints, geographic mentions, and risk signals from
    Item 1 and Item 1A text for a given ticker.

    Args:
        ticker: Stock ticker symbol.
        sections: Optional dict of {section_name: text}. If None, loads from
                  data/processed/{ticker}/item1.txt and item1a.txt.

    Returns:
        pandas DataFrame with columns:
            ticker, section, entity_type, entity_text, context, risk_signals

    Raises:
        FileNotFoundError: If processed section files are not found and
                           sections arg is not provided.
    """
    ticker = ticker.upper()

    if sections is None:
        sections = _load_sections_from_disk(ticker)

    rows = []

    for section_name, text in sections.items():
        if not text:
            continue

        sentences = _split_sentences(text)
        logger.info(
            "Extracting entities from %s/%s (%d sentences)...",
            ticker, section_name, len(sentences),
        )

        for i, sentence in enumerate(sentences):
            context = _get_context(sentences, i)

            # 1. Supplier keyword hits
            supplier_hits = _keyword_hits(sentence, SUPPLIER_KEYWORDS)
            if supplier_hits:
                # Extract the surrounding noun phrase as a loose "supplier hint"
                hint = _extract_supplier_hint(sentence)
                rows.append({
                    "ticker": ticker,
                    "section": section_name,
                    "entity_type": "supplier_hint",
                    "entity_text": hint or sentence[:120],
                    "context": context,
                    "risk_signals": "",
                    "keyword_matched": ", ".join(supplier_hits[:3]),
                })

            # 2. Geographic hits
            geo_hits = _geo_hits(sentence)
            for geo in geo_hits:
                risk_hits = _keyword_hits(context, RISK_KEYWORDS)
                rows.append({
                    "ticker": ticker,
                    "section": section_name,
                    "entity_type": "geography",
                    "entity_text": geo,
                    "context": context,
                    "risk_signals": "; ".join(risk_hits[:5]),
                    "keyword_matched": geo,
                })

            # 3. Pure risk signal hits (not already attached to a geo)
            if not geo_hits:
                risk_hits = _keyword_hits(sentence, RISK_KEYWORDS)
                if risk_hits:
                    rows.append({
                        "ticker": ticker,
                        "section": section_name,
                        "entity_type": "risk_signal",
                        "entity_text": "; ".join(risk_hits[:5]),
                        "context": context,
                        "risk_signals": "; ".join(risk_hits[:5]),
                        "keyword_matched": ", ".join(risk_hits[:3]),
                    })

    df = pd.DataFrame(rows, columns=[
        "ticker", "section", "entity_type", "entity_text",
        "context", "risk_signals", "keyword_matched",
    ])

    logger.info("Extracted %d entity rows for %s", len(df), ticker)

    # Persist
    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entities.csv")
    df.to_csv(out_path, index=False)
    logger.info("Saved entities -> %s", out_path)

    return df


def _extract_supplier_hint(sentence: str) -> str:
    """
    Attempt to extract a plausible supplier name/hint from a sentence.
    Looks for capitalized noun phrases that appear near supplier keywords.

    This is heuristic — real NER would improve accuracy but requires spacy.
    """
    # Capitalized word sequences (likely proper nouns / company names)
    cap_phrases = re.findall(r"\b([A-Z][a-zA-Z&,\.\s]{2,40}(?:Inc|Corp|Co|Ltd|LLC|GmbH|AG|plc)?\.?)\b", sentence)
    if cap_phrases:
        # Return the longest capitalized phrase as the most likely entity name
        return max(cap_phrases, key=len).strip()
    return ""


def _load_sections_from_disk(ticker: str) -> dict[str, str]:
    """Load item1.txt and item1a.txt from the processed data directory."""
    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    sections = {}

    for name in ("item1", "item1a"):
        path = os.path.join(out_dir, f"{name}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                sections[name] = f.read()
        else:
            logger.warning("Section file not found: %s", path)

    if not sections:
        raise FileNotFoundError(
            f"No processed section files found for {ticker} in {out_dir}. "
            "Run parsers.tenk_parser.extract_sections() first."
        )

    return sections
