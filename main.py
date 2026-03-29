"""
Supply Chain Intelligence Engine — CLI Entry Point

Usage:
    python main.py --ticker AAPL
    python main.py --ticker TSLA --force-download
    python main.py --ticker MSFT --no-news --skip-graph

Full pipeline:
    Phase 1: Download 10-K from SEC EDGAR
    Phase 2: Parse Item 1 + Item 1A sections
    Phase 3: Extract entities (suppliers, geographies, risk signals)
    Phase 4: Score and map dependencies
    Phase 5: Build risk graph, overlay news, export report
"""

import argparse
import logging
import sys
import os

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def run_pipeline(
    ticker: str,
    force_download: bool = False,
    skip_news: bool = False,
    skip_graph: bool = False,
) -> None:
    """Execute the full supply chain intelligence pipeline for a ticker."""

    ticker = ticker.upper()
    print(f"\n{'='*60}")
    print(f"  Supply Chain Intelligence Engine")
    print(f"  Target: {ticker}")
    print(f"{'='*60}\n")

    # ── Phase 1: SEC Scraper ──────────────────────────────────────────────
    print("[Phase 1] Downloading 10-K filing from SEC EDGAR...")
    from scrapers.sec_scraper import download_10k
    try:
        raw_path = download_10k(ticker, force=force_download)
        print(f"  ✓ 10-K cached at: {raw_path}\n")
    except Exception as exc:
        logger.error("Phase 1 failed: %s", exc)
        print(f"  ✗ Failed to download 10-K: {exc}")
        sys.exit(1)

    # ── Phase 2: 10-K Parser ─────────────────────────────────────────────
    print("[Phase 2] Parsing Item 1 (Business) and Item 1A (Risk Factors)...")
    from parsers.tenk_parser import extract_sections
    try:
        sections = extract_sections(ticker)
        for sec_name, text in sections.items():
            print(f"  ✓ {sec_name}: {len(text):,} characters extracted")
        print()
    except Exception as exc:
        logger.error("Phase 2 failed: %s", exc)
        print(f"  ✗ Parser failed: {exc}")
        sys.exit(1)

    if not sections:
        print("  ✗ No sections extracted — filing may be in an unsupported format.")
        sys.exit(1)

    # ── Phase 3: Entity Extraction ────────────────────────────────────────
    print("[Phase 3] Extracting entities (suppliers, geographies, risk signals)...")
    from parsers.entity_extractor import extract_entities
    try:
        entities_df = extract_entities(ticker, sections=sections)
        type_counts = entities_df["entity_type"].value_counts().to_dict() if not entities_df.empty else {}
        for etype, count in type_counts.items():
            print(f"  ✓ {etype}: {count} rows")
        print()
    except Exception as exc:
        logger.error("Phase 3 failed: %s", exc)
        print(f"  ✗ Entity extraction failed: {exc}")
        sys.exit(1)

    if entities_df.empty:
        print("  ✗ No entities extracted. Cannot proceed to scoring.")
        sys.exit(1)

    # ── Phase 4: Risk Scoring + Dependency Mapping ────────────────────────
    print("[Phase 4] Scoring risk and mapping dependencies...")
    from analysts.dependency_mapper import build_dependency_table, get_top_risk_nodes
    try:
        dep_df = build_dependency_table(ticker, entities_df)
        print(f"  ✓ {len(dep_df)} dependencies identified")
        flagged = dep_df[dep_df["flagged"] == True] if not dep_df.empty else dep_df
        if not flagged.empty:
            print(f"\n  Top {len(flagged)} flagged risks:")
            for _, row in flagged.iterrows():
                print(f"    [{row['risk_score']:.1f}] {row['dependency'][:40]} "
                      f"({row['dependency_type']}) — {row['top_risk_phrase']}")
        print()
    except Exception as exc:
        logger.error("Phase 4 failed: %s", exc)
        print(f"  ✗ Dependency mapping failed: {exc}")
        sys.exit(1)

    # ── Phase 5: Graph + News Overlay ─────────────────────────────────────
    if not skip_graph:
        print("[Phase 5] Building supply chain risk graph...")
        from graph.graph_generator import build_graph, attach_news, export_graph, generate_risk_report

        G = build_graph(ticker, dep_df)
        print(f"  ✓ Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        if not skip_news and not dep_df.empty:
            print("  Fetching news headlines for top-risk nodes...")
            from scrapers.news_scraper import get_headlines_batch
            top_nodes = get_top_risk_nodes(dep_df, n=5)
            news_data = get_headlines_batch(top_nodes)
            G = attach_news(G, news_data)
            total_headlines = sum(len(v) for v in news_data.values())
            print(f"  ✓ Attached {total_headlines} headlines across {len(top_nodes)} nodes")

        print("  Exporting graph...")
        exports = export_graph(G, ticker)
        for fmt, path in exports.items():
            print(f"  ✓ {fmt.upper()}: {path}")

        print("  Generating risk report...")
        report_path = generate_risk_report(ticker, dep_df, G)
        print(f"  ✓ Report: {report_path}")
        print()
    else:
        print("[Phase 5] Skipped (--skip-graph flag set)\n")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  Pipeline complete for {ticker}")
    print(f"{'='*60}")

    from config import DATA_PROCESSED_DIR, OUTPUTS_GRAPHS_DIR, OUTPUTS_REPORTS_DIR
    print(f"\n  Outputs:")
    print(f"    Processed data : {os.path.join(DATA_PROCESSED_DIR, ticker)}/")
    if not skip_graph:
        print(f"    Graph (GEXF)   : {os.path.join(OUTPUTS_GRAPHS_DIR, ticker)}_supply_chain.gexf")
        print(f"    Graph (PNG)    : {os.path.join(OUTPUTS_GRAPHS_DIR, ticker)}_supply_chain.png")
        print(f"    Risk report    : {os.path.join(OUTPUTS_REPORTS_DIR, ticker)}_risk_summary.json")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Mini-Palantir Supply Chain Intelligence Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --ticker AAPL
  python main.py --ticker TSLA --force-download
  python main.py --ticker MSFT --no-news
  python main.py --ticker AMZN --skip-graph

SEC Fair Access Note:
  All EDGAR requests include a User-Agent identifying this tool.
  Max rate: ~7 requests/second (safely under the 10 req/sec limit).
  Update SEC_USER_AGENT in config.py with your contact email.
        """,
    )
    parser.add_argument(
        "--ticker", "-t",
        required=True,
        help="Stock ticker symbol (e.g. AAPL, TSLA, MSFT)",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        default=False,
        help="Re-download the 10-K even if a cached copy exists",
    )
    parser.add_argument(
        "--no-news",
        action="store_true",
        default=False,
        help="Skip news headline fetching (faster, no network calls for news)",
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        default=False,
        help="Skip graph generation and export (Phases 1-4 only)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable DEBUG logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    run_pipeline(
        ticker=args.ticker,
        force_download=args.force_download,
        skip_news=args.no_news,
        skip_graph=args.skip_graph,
    )


if __name__ == "__main__":
    main()
