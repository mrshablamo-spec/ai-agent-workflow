"""
Phase 4: Dependency Mapper
Combines scored entities into a ranked dependency table showing:
  target company -> supplier hints -> countries -> risk scores

Produces dependency_table.csv and identifies top high-risk dependencies
for graph highlighting.
"""

import logging
import os
import pandas as pd

from config import DATA_PROCESSED_DIR
from analysts.risk_scorer import score_entities, aggregate_scores

logger = logging.getLogger(__name__)


def build_dependency_table(ticker: str, entities_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a ranked dependency table from the raw entities DataFrame.

    Steps:
        1. Score all entities
        2. Aggregate to one row per entity
        3. Cross-join supplier hints with nearby geography mentions to
           create (supplier, country) dependency pairs
        4. Save to data/processed/{ticker}/dependency_table.csv

    Args:
        ticker: Stock ticker symbol.
        entities_df: Raw entities from entity_extractor.extract_entities()

    Returns:
        DataFrame with columns:
            ticker, dependency, dependency_type, country, risk_score,
            evidence_count, top_risk_phrase, flagged
    """
    ticker = ticker.upper()

    # Score and aggregate
    scored = score_entities(entities_df)
    aggregated = aggregate_scores(scored)

    if aggregated.empty:
        logger.warning("No entities to build dependency table for %s", ticker)
        return pd.DataFrame()

    # Separate suppliers and geographies
    suppliers = aggregated[aggregated["entity_type"] == "supplier_hint"].copy()
    geos = aggregated[aggregated["entity_type"] == "geography"].copy()
    risk_signals = aggregated[aggregated["entity_type"] == "risk_signal"].copy()

    rows = []

    # ── Supplier dependencies ─────────────────────────────────────────────
    for _, sup_row in suppliers.iterrows():
        rows.append({
            "ticker": ticker,
            "dependency": sup_row["entity_text"],
            "dependency_type": "supplier",
            "country": _infer_country_for_supplier(sup_row, scored, geos),
            "risk_score": sup_row["risk_score"],
            "evidence_count": sup_row["mention_count"],
            "top_risk_phrase": _top_signal(sup_row["risk_signals"]),
            "flagged": False,
        })

    # ── Geographic dependencies ──────────────────────────────────────────
    for _, geo_row in geos.iterrows():
        rows.append({
            "ticker": ticker,
            "dependency": geo_row["entity_text"],
            "dependency_type": "geography",
            "country": geo_row["entity_text"],
            "risk_score": geo_row["risk_score"],
            "evidence_count": geo_row["mention_count"],
            "top_risk_phrase": _top_signal(geo_row["risk_signals"]),
            "flagged": False,
        })

    # ── Standalone risk signals ──────────────────────────────────────────
    for _, sig_row in risk_signals.iterrows():
        rows.append({
            "ticker": ticker,
            "dependency": sig_row["entity_text"],
            "dependency_type": "risk_signal",
            "country": "",
            "risk_score": sig_row["risk_score"],
            "evidence_count": sig_row["mention_count"],
            "top_risk_phrase": _top_signal(sig_row["risk_signals"]),
            "flagged": False,
        })

    dep_df = pd.DataFrame(rows).sort_values("risk_score", ascending=False).reset_index(drop=True)

    # Flag top 5 highest-risk dependencies
    top5_idx = dep_df.head(5).index
    dep_df.loc[top5_idx, "flagged"] = True

    # Persist
    out_dir = os.path.join(DATA_PROCESSED_DIR, ticker)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "dependency_table.csv")
    dep_df.to_csv(out_path, index=False)
    logger.info("Saved dependency table -> %s (%d rows)", out_path, len(dep_df))

    return dep_df


def _top_signal(signals_str: str) -> str:
    """Return the first (highest priority) risk signal from a semicolon string."""
    if not signals_str or not isinstance(signals_str, str):
        return ""
    parts = [s.strip() for s in signals_str.split(";") if s.strip()]
    return parts[0] if parts else ""


def _infer_country_for_supplier(
    supplier_row: pd.Series,
    scored_df: pd.DataFrame,
    geos_df: pd.DataFrame,
) -> str:
    """
    Heuristic: find which country most frequently co-occurs in the same
    context sentences as this supplier hint.

    Falls back to the highest-risk country in the filing if no co-occurrence found.
    """
    supplier_text = supplier_row["entity_text"].lower()

    # Find rows in scored_df whose context mentions the supplier text
    context_mask = scored_df["context"].str.lower().str.contains(
        supplier_text[:30], na=False, regex=False
    )
    co_occurring = scored_df[context_mask & (scored_df["entity_type"] == "geography")]

    if not co_occurring.empty:
        # Return the most-mentioned co-occurring country
        top = co_occurring["entity_text"].value_counts().idxmax()
        return str(top)

    # Fallback: highest-risk country overall
    if not geos_df.empty:
        return str(geos_df.iloc[0]["entity_text"])

    return "unknown"


def get_top_risk_nodes(dep_df: pd.DataFrame, n: int = 5) -> list[str]:
    """
    Return the top-n highest risk dependency names for news overlay.

    Args:
        dep_df: Dependency table from build_dependency_table()
        n: Number of top nodes to return.

    Returns:
        List of entity names sorted by risk_score descending.
    """
    if dep_df.empty:
        return []
    top = dep_df.nlargest(n, "risk_score")
    return top["dependency"].tolist()
