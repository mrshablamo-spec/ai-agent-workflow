"""
Mini-Palantir Supply Chain Intelligence Engine — CLI Entry Point

Full pipeline:
  Phase 1: Download 10-K from SEC EDGAR          (scripts/sec_client.py)
  Phase 2: Parse Item 1 + Item 1A                (scripts/processor.py)
  Phase 3: Extract entities                      (scripts/processor.py)
  Phase 4: Score + build dependency table        (scripts/processor.py)
  Phase 5: Build graph, simulate ripple, alert   (scripts/graph_engine.py)

Usage:
  python main.py --ticker AAPL
  python main.py --ticker TSLA --force-download
  python main.py --ticker NVDA --simulate-shock taiwan
  python main.py --ticker AAPL --monitor
  python main.py --ticker MSFT --no-news --skip-graph

Before running:
  1. pip install -r requirements.txt
  2. Edit config.py — set SEC_USER_AGENT to include your email
"""

import argparse
import logging
import sys
import os

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
    simulate_shock: str | None = None,
    monitor: bool = False,
) -> None:
    ticker = ticker.upper()
    _header(ticker)

    # ── Phase 1: Ingestion ────────────────────────────────────────────────
    _phase("1", "Downloading 10-K filing from SEC EDGAR")
    from scripts.sec_client import download_10k
    try:
        raw_path = download_10k(ticker, force=force_download)
        _ok(f"10-K cached at: {raw_path}")
    except Exception as exc:
        _fail(f"Download failed: {exc}")
        sys.exit(1)

    # ── Phase 2: Section parsing ──────────────────────────────────────────
    _phase("2", "Parsing Item 1 (Business) + Item 1A (Risk Factors)")
    from scripts.processor import extract_sections
    try:
        sections = extract_sections(ticker)
        for name, text in sections.items():
            _ok(f"{name}: {len(text):,} characters extracted")
    except Exception as exc:
        _fail(f"Parser failed: {exc}")
        sys.exit(1)

    if not sections:
        _fail("No sections extracted — filing may use unsupported format.")
        sys.exit(1)

    # ── Phase 3: Entity extraction ────────────────────────────────────────
    _phase("3", "Extracting entities (suppliers, geographies, risk signals)")
    from scripts.processor import extract_entities
    try:
        entities_df = extract_entities(ticker, sections=sections)
        for etype, count in entities_df["entity_type"].value_counts().items():
            _ok(f"{etype}: {count} rows")
        crits = entities_df[entities_df["severity"] == "CRITICAL"]
        if not crits.empty:
            print(f"\n  *** {len(crits)} CRITICAL sole-source/single-source dependencies found ***")
    except Exception as exc:
        _fail(f"Entity extraction failed: {exc}")
        sys.exit(1)

    if entities_df.empty:
        _fail("No entities extracted — cannot proceed to scoring.")
        sys.exit(1)

    # ── Phase 4: Dependency scoring ───────────────────────────────────────
    _phase("4", "Scoring risk and building dependency table")
    from scripts.processor import build_dependency_table
    try:
        dep_df = build_dependency_table(ticker, entities_df)
        _ok(f"{len(dep_df)} dependencies identified")
        flagged = dep_df[dep_df["flagged"] == True] if not dep_df.empty else dep_df
        if not flagged.empty:
            print(f"\n  Top {len(flagged)} flagged dependencies:")
            for _, row in flagged.iterrows():
                inferred_tag = " [inferred]" if row.get("inferred") else ""
                print(f"    [{row['risk_score']:.1f}] {str(row['dependency'])[:38]:<38} "
                      f"({row['severity']}) — {row['top_risk_phrase']}{inferred_tag}")
    except Exception as exc:
        _fail(f"Dependency mapping failed: {exc}")
        sys.exit(1)

    # ── Phase 5: Graph + ripple + alerts ──────────────────────────────────
    if not skip_graph:
        _phase("5", "Building supply chain knowledge graph")
        from scripts.graph_engine import (
            build_graph, simulate_ripple, score_ripple_severity,
            attach_news, monitor_nodes, export_graph, generate_risk_report,
        )

        G = build_graph(ticker, dep_df)
        _ok(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        # Ripple simulation
        ripple_results = []
        if simulate_shock:
            print(f"\n  Simulating supply shock: '{simulate_shock}'...")
            ripple_results = simulate_ripple(G, simulate_shock)
            severity_map = score_ripple_severity(ripple_results)
            if ripple_results:
                print(f"  {len(ripple_results)} downstream nodes affected:")
                for r in ripple_results[:8]:
                    sev = severity_map.get(r["node"], "LOW")
                    print(f"    [{r['ripple_score']:.2f}] {str(r['node'])[:35]:<35} "
                          f"depth={r['depth']} ({sev}) — {r['path']}")
            else:
                print(f"  Node '{simulate_shock}' not found in graph or no downstream impact.")

        # News overlay
        alerts = []
        if not skip_news and not dep_df.empty:
            if monitor:
                print("\n  Monitor mode: scanning news for all high-risk nodes...")
                alerts = monitor_nodes(G, ticker)
                if alerts:
                    print(f"\n  {'='*55}")
                    print(f"  {len(alerts)} ALERT(S) FIRED:")
                    for a in alerts:
                        print(f"  {a['alert_text']}")
                    print(f"  {'='*55}")
                else:
                    print("  No alerts triggered — no news matched risk keywords.")
            else:
                print("\n  Fetching news for top-risk nodes...")
                from scripts.sec_client import get_headlines_batch
                from scripts.graph_engine import ALERT_RISK_THRESHOLD
                top_nodes = dep_df.nlargest(5, "risk_score")["dependency"].tolist()
                news_data = get_headlines_batch(top_nodes)
                G = attach_news(G, news_data)
                total = sum(len(v) for v in news_data.values())
                _ok(f"Attached {total} headlines across {len(top_nodes)} nodes")

        # Export
        print("\n  Exporting graph...")
        exports = export_graph(G, ticker)
        for fmt, path in exports.items():
            _ok(f"{fmt.upper()}: {path}")

        print("  Generating risk report...")
        report_path = generate_risk_report(ticker, dep_df, G, ripple_results, alerts)
        _ok(f"Report: {report_path}")
    else:
        print("\n[Phase 5] Skipped (--skip-graph)")

    # ── Summary ───────────────────────────────────────────────────────────
    from config import DATA_PROCESSED_DIR, OUTPUTS_GRAPHS_DIR, OUTPUTS_REPORTS_DIR
    print(f"\n{'='*60}")
    print(f"  Pipeline complete for {ticker}")
    print(f"{'='*60}")
    print(f"\n  Outputs:")
    print(f"    Data     : {os.path.join(DATA_PROCESSED_DIR, ticker)}/")
    if not skip_graph:
        print(f"    Graph    : {os.path.join(OUTPUTS_GRAPHS_DIR, ticker)}_supply_chain.gexf")
        print(f"    PNG      : {os.path.join(OUTPUTS_GRAPHS_DIR, ticker)}_supply_chain.png")
        print(f"    Report   : {os.path.join(OUTPUTS_REPORTS_DIR, ticker)}_risk_summary.json")
    print()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(ticker: str):
    print(f"\n{'='*60}")
    print(f"  Mini-Palantir Supply Chain Intelligence Engine")
    print(f"  Target: {ticker}")
    print(f"{'='*60}\n")

def _phase(n: str, desc: str):
    print(f"[Phase {n}] {desc}...")

def _ok(msg: str):
    print(f"  ✓ {msg}")

def _fail(msg: str):
    print(f"  ✗ {msg}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Mini-Palantir Supply Chain Intelligence Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --ticker AAPL
  python main.py --ticker NVDA --simulate-shock taiwan
  python main.py --ticker TSLA --monitor
  python main.py --ticker MSFT --force-download
  python main.py --ticker AMZN --skip-graph

The ripple simulator answers: "If X is disrupted, which portfolio
companies are downstream — and how hard are they hit?"
        """,
    )
    parser.add_argument("--ticker", "-t", required=True,
                        help="Stock ticker (e.g. AAPL, TSLA, NVDA)")
    parser.add_argument("--force-download", action="store_true",
                        help="Re-download 10-K even if cached")
    parser.add_argument("--no-news", action="store_true",
                        help="Skip all news headline fetching")
    parser.add_argument("--skip-graph", action="store_true",
                        help="Run Phases 1-4 only, skip graph output")
    parser.add_argument("--simulate-shock", metavar="NODE",
                        help="Simulate a supply shock on a node (e.g. taiwan, ukraine, TSMC)")
    parser.add_argument("--monitor", action="store_true",
                        help="Scan live news for all high-risk nodes and fire alerts")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable DEBUG logging")

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    run_pipeline(
        ticker=args.ticker,
        force_download=args.force_download,
        skip_news=args.no_news,
        skip_graph=args.skip_graph,
        simulate_shock=args.simulate_shock,
        monitor=args.monitor,
    )


if __name__ == "__main__":
    main()
