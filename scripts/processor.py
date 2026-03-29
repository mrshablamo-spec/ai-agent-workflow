"""
scripts/processor.py — The Stomach (Extraction Layer)

Turns raw 10-K HTML into structured supply chain intelligence.
Three responsibilities:
  1. extract_sections()      — isolate Item 1 + Item 1A text
  2. extract_entities()      — find suppliers, geographies, risk signals
  3. build_dependency_table()— score and rank all dependencies

Claude's Intelligence Rules (implemented here):
  - "sole source" / "single source" / "only qualified" → severity=CRITICAL
  - "concentration" / "substantial" / "majority" → severity=HIGH
  - "preferred" / "primary" / "our largest" → severity=MEDIUM
  - Geographic name co-located with supplier language = supply chain geography
  - "our suppliers rely on" / "dependent on third parties for" = inferred sub-supplier

Owner: Codex implements. Claude reviews for financial logic accuracy.
"""

import logging
import os
import re
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from config import (
        DATA_RAW_DIR, DATA_PROCESSED_DIR,
        SUPPLIER_KEYWORDS, RISK_KEYWORDS, GEO_RISK_TIERS,
        RISK_PHRASE_WEIGHT, ITEM1A_AMPLIFIER,
    )
except ImportError:
    _BASE = os.path.dirname(os.path.dirname(__file__))
    DATA_RAW_DIR = os.path.join(_BASE, "data", "raw")
    DATA_PROCESSED_DIR = os.path.join(_BASE, "data", "processed")
    SUPPLIER_KEYWORDS = [
        "supplier", "suppliers", "vendor", "vendors", "manufacturer",
        "manufacturers", "contract manufacturer", "sole source", "single source",
        "third-party", "third party", "subcontractor", "outsource",
        "supply chain", "procurement",
    ]
    RISK_KEYWORDS = [
        "concentration risk", "single source", "sole source", "disruption",
        "tariff", "trade restriction", "export control", "sanction",
        "political instability", "geopolitical", "natural disaster",
        "shortage", "capacity constraint", "price increase", "logistics",
        "dependency", "pandemic", "earthquake", "flood",
    ]
    GEO_RISK_TIERS = {
        "united states": 1, "canada": 1, "germany": 1, "japan": 1,
        "australia": 1, "netherlands": 1, "sweden": 1, "switzerland": 1,
        "south korea": 2, "united kingdom": 2, "france": 2, "singapore": 2,
        "israel": 2, "taiwan": 2,
        "china": 3, "india": 3, "brazil": 3, "mexico": 3, "vietnam": 3,
        "malaysia": 3, "thailand": 3, "philippines": 3, "indonesia": 3,
        "russia": 4, "ukraine": 4, "pakistan": 4, "bangladesh": 4, "myanmar": 4,
        "north korea": 5, "syria": 5, "afghanistan": 5, "yemen": 5, "venezuela": 5,
    }
    RISK_PHRASE_WEIGHT = 1.5
    ITEM1A_AMPLIFIER = 2.0

logger = logging.getLogger(__name__)

# ── Severity rules (Claude's intelligence layer) ──────────────────────────────
_CRITICAL_PATTERNS = re.compile(
    r"\b(sole\s+supplier|single\s+source|sole\s+source|only\s+supplier|"
    r"only\s+qualified|exclusively\s+supplied|sole\s+provider)\b",
    re.IGNORECASE,
)
_HIGH_PATTERNS = re.compile(
    r"\b(concentration\s+risk|significant\s+portion|substantial\s+portion|"
    r"majority\s+of\s+our|heavily\s+dependent|significant\s+dependence|"
    r"limited\s+number\s+of\s+suppliers?)\b",
    re.IGNORECASE,
)
_MEDIUM_PATTERNS = re.compile(
    r"\b(preferred\s+supplier|primary\s+supplier|our\s+largest\s+supplier|"
    r"primary\s+vendor|key\s+supplier|principal\s+supplier)\b",
    re.IGNORECASE,
)
_SUBSUPPLIER_PATTERNS = re.compile(
    r"\b(our\s+suppliers?\s+rely\s+on|dependent\s+on\s+third\s+parties?\s+for|"
    r"sub-?suppliers?|tier[\s\-]2\s+suppliers?|upstream\s+suppliers?|"
    r"suppliers?\s+of\s+our\s+suppliers?)\b",
    re.IGNORECASE,
)

_ALL_GEO = set(GEO_RISK_TIERS.keys()) | {
    "asia", "asia-pacific", "apac", "europe", "emea", "latin america",
    "middle east", "africa", "north america", "southeast asia",
    "eastern europe", "western europe", "sub-saharan africa", "taiwan",
}

# ── Section extraction ────────────────────────────────────────────────────────

_ITEM1_RE = re.compile(r"item\s+1\s*[\.\-\:—]?\s*(business|description\s+of\s+business)?", re.IGNORECASE)
_ITEM1A_RE = re.compile(r"item\s+1a\s*[\.\-\:—]?\s*(risk\s+factors)?", re.IGNORECASE)
_ITEM1B_RE = re.compile(r"item\s+1b\s*[\.\-\:—]?", re.IGNORECASE)
_ITEM2_RE = re.compile(r"item\s+2\s*[\.\-\:—]?", re.IGNORECASE)


def extract_sections(ticker: str) -> dict[str, str]:
    """
    Load cached 10-K HTML and extract Item 1 (Business) + Item 1A (Risk Factors).

    Approach:
      1. Try HTML heading tags (<b>, <h1>-<h4>) matching "Item 1" patterns
      2. Fall back to regex over plain text if heading method misses sections

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dict with keys 'item1' and/or 'item1a' → extracted clean text.

    Raises:
        FileNotFoundError: Raw 10-K not yet downloaded.
    """
    from bs4 import BeautifulSoup

    ticker = ticker.upper()
    raw_path = os.path.join(DATA_RAW_DIR, ticker, "10k_latest.html")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(
            f"No cached 10-K for {ticker} at {raw_path}. "
            "Run sec_client.download_10k() first."
        )

    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    sections = _extract_by_headings(soup)

    missing = [k for k in ("item1", "item1a") if k not in sections]
    if missing:
        logger.debug("Heading extraction missed %s — using regex fallback.", missing)
        plain = soup.get_text("\n")
        fallback = _extract_by_regex(plain)
        for key in missing:
            if key in fallback:
                sections[key] = fallback[key]

    # Persist
    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    os.makedirs(out_dir, exist_ok=True)
    for name, text in sections.items():
        path = os.path.join(out_dir, f"{name}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info("Saved %s/%s -> %s (%d chars)", ticker, name, path, len(text))

    if not sections:
        logger.warning("%s: No sections extracted — filing may use unsupported format.", ticker)

    return sections


def _extract_by_headings(soup) -> dict[str, str]:
    from bs4 import BeautifulSoup
    sections = {}
    candidates = soup.find_all(["b", "strong", "h1", "h2", "h3", "h4", "p"])
    markers = []
    for tag in candidates:
        text = tag.get_text(" ", strip=True)
        if len(text) > 80:
            continue
        if _ITEM1A_RE.match(text):
            markers.append(("item1a", tag))
        elif _ITEM1_RE.match(text) and "1a" not in text.lower():
            markers.append(("item1", tag))
        elif _ITEM1B_RE.match(text):
            markers.append(("item1b", tag))
        elif _ITEM2_RE.match(text):
            markers.append(("item2", tag))

    END_NAMES = {"item1": ("item1a", "item1b", "item2"), "item1a": ("item1b", "item2")}

    for i, (name, tag) in enumerate(markers):
        if name not in ("item1", "item1a"):
            continue
        end_tag = next(
            (markers[j][1] for j in range(i + 1, len(markers)) if markers[j][0] in END_NAMES.get(name, ())),
            None,
        )
        parts, current, parent = [], tag.find_next_sibling() or tag.parent.find_next_sibling(), tag
        while current:
            if end_tag and (current == end_tag or current.find(end_tag)):
                break
            parts.append(current.get_text(" ", strip=True))
            next_sib = current.find_next_sibling()
            if next_sib is None and parent:
                parent = parent.parent or parent
                current = parent.find_next_sibling()
            else:
                current = next_sib

        combined = _clean_text(" ".join(parts))
        if len(combined) > 500:
            sections[name] = combined
    return sections


def _extract_by_regex(text: str) -> dict[str, str]:
    sections = {}
    boundaries = []
    for pattern, name in [
        (_ITEM1_RE, "item1"), (_ITEM1A_RE, "item1a"),
        (_ITEM1B_RE, "item1b"), (_ITEM2_RE, "item2"),
    ]:
        for m in pattern.finditer(text):
            boundaries.append((m.start(), name, m.end()))
    boundaries.sort(key=lambda x: x[0])
    for i, (start, name, end) in enumerate(boundaries):
        if name not in ("item1", "item1a"):
            continue
        next_start = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        content = _clean_text(text[end:next_start])
        if len(content) > 500:
            sections[name] = content
    return sections


def _clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Entity extraction ─────────────────────────────────────────────────────────

def extract_entities(ticker: str, sections: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Extract supplier hints, geographic mentions, and risk signals from
    Item 1 + Item 1A text.

    Claude's rules are enforced here:
      - CRITICAL: sole/single source language
      - HIGH: concentration risk language
      - MEDIUM: preferred/primary supplier language
      - inferred=True: sub-supplier detection patterns

    Args:
        ticker: Stock ticker symbol.
        sections: Dict of {section_name: text}. Loads from disk if None.

    Returns:
        DataFrame: [ticker, section, entity_type, entity_text, context,
                    risk_signals, keyword_matched, severity, inferred]
    """
    ticker = ticker.upper()
    if sections is None:
        sections = _load_sections(ticker)

    rows = []
    for section_name, text in sections.items():
        if not text:
            continue
        sentences = _split_sentences(text)
        logger.info("Extracting from %s/%s (%d sentences)", ticker, section_name, len(sentences))

        for i, sentence in enumerate(sentences):
            ctx = _context(sentences, i)
            severity = _classify_severity(sentence)
            is_inferred = bool(_SUBSUPPLIER_PATTERNS.search(sentence))

            # Supplier hits
            sup_hits = _keyword_hits(sentence, SUPPLIER_KEYWORDS)
            if sup_hits:
                hint = _extract_supplier_hint(sentence)
                rows.append({
                    "ticker": ticker, "section": section_name,
                    "entity_type": "supplier_hint",
                    "entity_text": hint or sentence[:120],
                    "context": ctx,
                    "risk_signals": _risk_signals_in(ctx),
                    "keyword_matched": ", ".join(sup_hits[:3]),
                    "severity": severity,
                    "inferred": is_inferred,
                })

            # Geographic hits
            geo_hits = _geo_hits(sentence)
            for geo in geo_hits:
                rows.append({
                    "ticker": ticker, "section": section_name,
                    "entity_type": "geography",
                    "entity_text": geo,
                    "context": ctx,
                    "risk_signals": _risk_signals_in(ctx),
                    "keyword_matched": geo,
                    "severity": severity if sup_hits else "LOW",
                    "inferred": False,
                })

            # Pure risk signals (no geo co-located)
            if not geo_hits:
                risk_hits = _keyword_hits(sentence, RISK_KEYWORDS)
                if risk_hits:
                    rows.append({
                        "ticker": ticker, "section": section_name,
                        "entity_type": "risk_signal",
                        "entity_text": "; ".join(risk_hits[:5]),
                        "context": ctx,
                        "risk_signals": "; ".join(risk_hits[:5]),
                        "keyword_matched": ", ".join(risk_hits[:3]),
                        "severity": severity,
                        "inferred": is_inferred,
                    })

    df = pd.DataFrame(rows, columns=[
        "ticker", "section", "entity_type", "entity_text",
        "context", "risk_signals", "keyword_matched", "severity", "inferred",
    ])
    logger.info("Extracted %d entity rows for %s", len(df), ticker)

    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entities.csv")
    df.to_csv(out_path, index=False)
    logger.info("Saved entities -> %s", out_path)
    return df


# ── Dependency mapping + scoring ──────────────────────────────────────────────

_SEVERITY_MULTIPLIERS = {"CRITICAL": 3.0, "HIGH": 2.0, "MEDIUM": 1.0, "LOW": 0.5}
_DEFAULT_GEO_RISK = 2


def build_dependency_table(ticker: str, entities_df: pd.DataFrame) -> pd.DataFrame:
    """
    Score entities and build a ranked dependency table for the graph engine.

    Scoring formula:
        raw_score = base_geo_tier
                    × item1a_amplifier
                    × (1 + risk_phrase_weight × signal_count / 10)
                    × severity_multiplier

    Normalized to 0–10. Top 5 flagged.

    Args:
        ticker: Stock ticker symbol.
        entities_df: Output of extract_entities().

    Returns:
        DataFrame: [ticker, dependency, dependency_type, country, risk_score,
                    evidence_count, severity, top_risk_phrase, flagged, inferred]
    """
    ticker = ticker.upper()
    if entities_df.empty:
        logger.warning("No entities to build dependency table for %s", ticker)
        return pd.DataFrame()

    scored = _score_entities(entities_df)
    aggregated = _aggregate(scored)

    suppliers = aggregated[aggregated["entity_type"] == "supplier_hint"]
    geos = aggregated[aggregated["entity_type"] == "geography"]
    risk_sigs = aggregated[aggregated["entity_type"] == "risk_signal"]

    rows = []
    for _, row in suppliers.iterrows():
        rows.append({
            "ticker": ticker,
            "dependency": row["entity_text"],
            "dependency_type": "supplier",
            "country": _infer_country(row, scored, geos),
            "risk_score": row["risk_score"],
            "evidence_count": row["mention_count"],
            "severity": row.get("severity", "LOW"),
            "top_risk_phrase": _top_signal(row["risk_signals"]),
            "flagged": False,
            "inferred": bool(row.get("inferred", False)),
        })
    for _, row in geos.iterrows():
        rows.append({
            "ticker": ticker,
            "dependency": row["entity_text"],
            "dependency_type": "geography",
            "country": row["entity_text"],
            "risk_score": row["risk_score"],
            "evidence_count": row["mention_count"],
            "severity": row.get("severity", "LOW"),
            "top_risk_phrase": _top_signal(row["risk_signals"]),
            "flagged": False,
            "inferred": False,
        })
    for _, row in risk_sigs.iterrows():
        rows.append({
            "ticker": ticker,
            "dependency": row["entity_text"],
            "dependency_type": "risk_signal",
            "country": "",
            "risk_score": row["risk_score"],
            "evidence_count": row["mention_count"],
            "severity": row.get("severity", "LOW"),
            "top_risk_phrase": _top_signal(row["risk_signals"]),
            "flagged": False,
            "inferred": bool(row.get("inferred", False)),
        })

    dep_df = (
        pd.DataFrame(rows)
        .sort_values("risk_score", ascending=False)
        .reset_index(drop=True)
    )
    dep_df.loc[dep_df.head(5).index, "flagged"] = True

    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "dependency_table.csv")
    dep_df.to_csv(out_path, index=False)
    logger.info("Saved dependency table -> %s (%d rows)", out_path, len(dep_df))
    return dep_df


# ── Private helpers ───────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _context(sentences: list[str], idx: int, window: int = 1) -> str:
    return " ".join(sentences[max(0, idx - window): min(len(sentences), idx + window + 1)])


def _keyword_hits(sentence: str, keywords: list[str]) -> list[str]:
    s = sentence.lower()
    return [kw for kw in keywords if kw in s]


def _geo_hits(sentence: str) -> list[str]:
    s = sentence.lower()
    return [g for g in _ALL_GEO if re.search(r"\b" + re.escape(g) + r"\b", s)]


def _risk_signals_in(text: str) -> str:
    hits = _keyword_hits(text, RISK_KEYWORDS)
    return "; ".join(hits[:5])


def _classify_severity(sentence: str) -> str:
    if _CRITICAL_PATTERNS.search(sentence):
        return "CRITICAL"
    if _HIGH_PATTERNS.search(sentence):
        return "HIGH"
    if _MEDIUM_PATTERNS.search(sentence):
        return "MEDIUM"
    return "LOW"


def _extract_supplier_hint(sentence: str) -> str:
    cap = re.findall(r"\b([A-Z][a-zA-Z&,\.\s]{2,40}(?:Inc|Corp|Co|Ltd|LLC|GmbH|AG|plc)?\.?)\b", sentence)
    return max(cap, key=len).strip() if cap else ""


def _score_entities(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    raw_scores = []
    for _, row in df.iterrows():
        sec_amp = ITEM1A_AMPLIFIER if row.get("section") == "item1a" else 1.0
        sig_count = len([s for s in str(row.get("risk_signals", "")).split(";") if s.strip()])
        sig_amp = 1.0 + RISK_PHRASE_WEIGHT * min(sig_count, 10) / 10.0
        sev_mult = _SEVERITY_MULTIPLIERS.get(str(row.get("severity", "LOW")), 0.5)

        if row["entity_type"] == "geography":
            base = GEO_RISK_TIERS.get(str(row["entity_text"]).lower(), _DEFAULT_GEO_RISK)
            raw = base * sec_amp * sig_amp * sev_mult
        elif row["entity_type"] == "supplier_hint":
            raw = 2.0 * sec_amp * sig_amp * sev_mult
        else:
            raw = 1.0 * sec_amp * sig_amp * sev_mult
        raw_scores.append(raw)

    df["raw_score"] = raw_scores
    max_raw = df["raw_score"].max() or 1.0
    df["risk_score"] = (df["raw_score"] / max_raw * 10.0).round(2)
    return df


def _aggregate(scored: pd.DataFrame) -> pd.DataFrame:
    def union_signals(series):
        all_s = set()
        for s in series:
            if isinstance(s, str):
                all_s.update(x.strip() for x in s.split(";") if x.strip())
        return "; ".join(sorted(all_s))

    def top_severity(series):
        order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return max(series, key=lambda x: order.get(str(x), 0))

    return (
        scored.groupby(["entity_text", "entity_type"])
        .agg(
            risk_score=("risk_score", "max"),
            mention_count=("risk_score", "count"),
            item1a_count=("section", lambda s: (s == "item1a").sum()),
            risk_signals=("risk_signals", union_signals),
            severity=("severity", top_severity),
            inferred=("inferred", "any"),
        )
        .reset_index()
        .sort_values("risk_score", ascending=False)
    )


def _top_signal(signals_str: str) -> str:
    parts = [s.strip() for s in str(signals_str).split(";") if s.strip()]
    return parts[0] if parts else ""


def _infer_country(sup_row, scored_df, geos_df) -> str:
    text = str(sup_row["entity_text"])[:30].lower()
    co = scored_df[
        scored_df["context"].str.lower().str.contains(text, na=False, regex=False)
        & (scored_df["entity_type"] == "geography")
    ]
    if not co.empty:
        return str(co["entity_text"].value_counts().idxmax())
    return str(geos_df.iloc[0]["entity_text"]) if not geos_df.empty else "unknown"


def _load_sections(ticker: str) -> dict[str, str]:
    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    sections = {}
    for name in ("item1", "item1a"):
        path = os.path.join(out_dir, f"{name}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                sections[name] = f.read()
    if not sections:
        raise FileNotFoundError(
            f"No processed sections for {ticker} in {out_dir}. "
            "Run extract_sections() first."
        )
    return sections
