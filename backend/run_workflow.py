from __future__ import annotations

import argparse
import json

from supply_chain_intel.pipelines.workflow import run_supply_chain_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Mini-Palantir supply-chain workflow.")
    parser.add_argument("ticker", help="Ticker to analyze, e.g. NVDA")
    parser.add_argument("--no-news", action="store_true", help="Skip Google News enrichment")
    args = parser.parse_args()

    payload = run_supply_chain_workflow(args.ticker, include_news=not args.no_news)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
