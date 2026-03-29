"""
Phase 4: Risk Scorer
Scores each geographic entity and supplier hint by combining:
  1. Base geographic risk tier (from config.GEO_RISK_TIERS)
  2. Mention frequency amplifier (Item 1A mentions weighted higher)
  3. Risk phrase co-occurrence weight

Input: entities DataFrame from entity_extractor
Output: scored DataFrame with a normalized risk_score column (0.0–10.0)
"""

import logging
import re
import pandas as pd

from config import GEO_RISK_TIERS, RISK_PHRASE_WEIGHT, ITEM1A_AMPLIFIER

logger = logging.getLogger(__name__)

_DEFAULT_GEO_RISK = 2  # Tier for unrecognized geographies


def _base_geo_risk(geo_name: str) -> int:
    """Return the base risk tier (1–5) for a geographic name."""
    return GEO_RISK_TIERS.get(geo_name.lower(), _DEFAULT_GEO_RISK)


def _count_risk_signals(risk_signals_str: str) -> int:
    """Count the number of distinct risk signals in a semicolon-separated string."""
    if not risk_signals_str or not isinstance(risk_signals_str, str):
        return 0
    signals = [s.strip() for s in risk_signals_str.split(";") if s.strip()]
    return len(signals)


def score_entities(entities_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a risk_score to each row in the entities DataFrame.

    Scoring formula for geography rows:
        raw_score = base_geo_risk
                    * (ITEM1A_AMPLIFIER if section == 'item1a' else 1.0)
                    * (1 + RISK_PHRASE_WEIGHT * risk_signal_count / 5)

    Scoring formula for supplier_hint rows:
        raw_score = (ITEM1A_AMPLIFIER if section == 'item1a' else 1.0)
                    * (1 + RISK_PHRASE_WEIGHT * risk_signal_count / 5)
                    * 2  (base multiplier — suppliers are inherently dependency nodes)

    risk_score is then normalized to a 0–10 scale based on the max raw score
    in the dataset.

    Args:
        entities_df: DataFrame from entity_extractor.extract_entities()

    Returns:
        Copy of the DataFrame with an added 'risk_score' column.
    """
    df = entities_df.copy()

    raw_scores = []
    for _, row in df.iterrows():
        section_amp = ITEM1A_AMPLIFIER if row.get("section") == "item1a" else 1.0
        signal_count = _count_risk_signals(row.get("risk_signals", ""))
        signal_amp = 1.0 + RISK_PHRASE_WEIGHT * min(signal_count, 10) / 10.0

        if row["entity_type"] == "geography":
            base = _base_geo_risk(str(row["entity_text"]))
            raw = base * section_amp * signal_amp
        elif row["entity_type"] == "supplier_hint":
            raw = 2.0 * section_amp * signal_amp
        else:  # risk_signal only
            raw = 1.0 * section_amp * signal_amp

        raw_scores.append(raw)

    df["raw_score"] = raw_scores

    # Normalize to 0–10
    max_raw = df["raw_score"].max() if not df.empty else 1.0
    df["risk_score"] = (df["raw_score"] / max_raw * 10.0).round(2)

    return df


def aggregate_scores(scored_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate scores per entity_text to produce a single risk score per entity.

    Aggregation:
        - risk_score: max (worst-case exposure)
        - mention_count: total row count
        - item1a_count: mentions in Item 1A specifically
        - risk_signals: union of all unique signals

    Args:
        scored_df: DataFrame output from score_entities()

    Returns:
        Aggregated DataFrame with one row per unique entity.
    """
    if scored_df.empty:
        return pd.DataFrame(columns=[
            "entity_text", "entity_type", "risk_score",
            "mention_count", "item1a_count", "risk_signals",
        ])

    def agg_signals(series):
        all_signals = set()
        for s in series:
            if isinstance(s, str):
                for sig in s.split(";"):
                    sig = sig.strip()
                    if sig:
                        all_signals.add(sig)
        return "; ".join(sorted(all_signals))

    agg = (
        scored_df.groupby(["entity_text", "entity_type"])
        .agg(
            risk_score=("risk_score", "max"),
            mention_count=("risk_score", "count"),
            item1a_count=("section", lambda s: (s == "item1a").sum()),
            risk_signals=("risk_signals", agg_signals),
        )
        .reset_index()
        .sort_values("risk_score", ascending=False)
    )

    logger.info("Aggregated %d unique entities", len(agg))
    return agg
